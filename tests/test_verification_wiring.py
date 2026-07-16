"""
P0-1 — test de cablare NON-VACUU: campurile orfane `official_data` -> `verified`
(maps_rating + monitorul_oficial) trebuie sa treaca prin executia REALA a
`VerificationAgent.execute()` (nu o reimplementare a logicii) si sa declanseze
efectiv cele 2 cai de scoring dependente (reputational Google Maps, juridic MO).

Fara cablare, scoring.py primeste maps_rating={}/risk fara monitorul_oficial
si ambele cai raman moarte in tacere -- de-aia testul verifica atat forma
campului copiat, cat si reason-ul efectiv aparut in risk_score.dimensions.
"""

from backend.agents.agent_verification import VerificationAgent


def _state(official: dict) -> dict:
    return {"official_data": official, "web_data": {}, "market_data": {}}


async def test_maps_rating_wired_raw_and_triggers_reputational_scoring():
    official = {"maps_rating": {"found": True, "rating": 4.6, "reviews_count": 120}}
    result = await VerificationAgent().execute(_state(official))
    verified = result["verified_data"]

    # Forma: RAW, top-level, FARA _make_field (contract impus de _score_reputational).
    assert verified["maps_rating"] == {"found": True, "rating": 4.6, "reviews_count": 120}

    rep_reasons = verified["risk_score"]["dimensions"]["reputational"]["reasons"]
    maps_reasons = [r for r in rep_reasons if "Google Maps" in r["text"]]
    assert maps_reasons, f"reason Google Maps lipseste din reputational: {rep_reasons}"
    assert maps_reasons[0]["impact"] == 15


async def test_monitorul_oficial_wired_wrapped_and_triggers_juridic_scoring():
    mo_events = [{"type": "dizolvare", "label": "Dizolvare", "snippet": "Dizolvare in curs"}]
    official = {"monitorul_oficial": mo_events}
    result = await VerificationAgent().execute(_state(official))
    verified = result["verified_data"]

    # Forma: WRAPPED cu _make_field, in verified["risk"] (contract impus de _score_juridic,
    # care gateaza pe isinstance(..., dict) + .get("value", [])).
    assert isinstance(verified["risk"]["monitorul_oficial"], dict)
    assert verified["risk"]["monitorul_oficial"]["value"] == mo_events

    jur_reasons = verified["risk_score"]["dimensions"]["juridic"]["reasons"]
    mo_reasons = [r for r in jur_reasons if "Dizolvare" in r["text"]]
    assert mo_reasons, f"reason Monitorul Oficial lipseste din juridic: {jur_reasons}"
    assert mo_reasons[0]["impact"] == -20


async def test_both_orphan_scoring_fields_wired_together():
    official = {
        "maps_rating": {"found": True, "rating": 4.6, "reviews_count": 120},
        "monitorul_oficial": [{"type": "dizolvare", "label": "Dizolvare", "snippet": "x"}],
    }
    result = await VerificationAgent().execute(_state(official))
    verified = result["verified_data"]

    assert verified["maps_rating"]["found"] is True
    assert verified["risk"]["monitorul_oficial"]["value"]


async def test_absent_orphan_fields_stay_absent():
    """Fara camp in official -> nu se seteaza chei fantoma (nu None) in verified."""
    result = await VerificationAgent().execute(_state({}))
    verified = result["verified_data"]

    assert "maps_rating" not in verified
    assert "monitorul_oficial" not in verified.get("risk", {})
    assert "web_intelligence" not in verified
    assert "brave_reputation" not in verified
    assert "data_freshness" not in verified
    assert "tavily_quota_exhausted" not in verified


async def test_staging_fields_wired_without_consumer_in_scoring():
    official = {
        "web_intelligence": {"summary": "x", "categories": {}},
        "brave_reputation": {"found": True, "results": []},
        "data_freshness": {"anaf": "2026-07-15"},
    }
    result = await VerificationAgent().execute(_state(official))
    verified = result["verified_data"]

    assert verified["web_intelligence"] == official["web_intelligence"]
    assert verified["brave_reputation"] == official["brave_reputation"]
    assert verified["data_freshness"] == official["data_freshness"]


async def test_tavily_quota_exhausted_wired_when_flagged():
    """A6 (2026-07-16): official_data["tavily_quota_exhausted"] (set by
    agent_official._check_tavily_quota when the monthly Tavily quota runs out --
    gates BOTH the legal search AND OSINT historical flags) must reach `verified`
    so reports can say "verification NOT performed" instead of silently looking
    like a clean firm. Executed through the REAL VerificationAgent.execute(),
    not a reimplementation."""
    official = {"tavily_quota_exhausted": True, "tavily_usage": 950}
    result = await VerificationAgent().execute(_state(official))
    verified = result["verified_data"]

    assert verified["tavily_quota_exhausted"] == {"value": True, "usage": 950}


async def test_tavily_quota_ok_leaves_field_absent():
    """official_data without the flag (quota healthy, or search_term absent) must
    NOT create a phantom key in verified — absence of the key IS the signal that
    verification ran normally."""
    official = {"tavily_usage": 12}  # usage present but no exhaustion flag
    result = await VerificationAgent().execute(_state(official))
    verified = result["verified_data"]

    assert "tavily_quota_exhausted" not in verified
