"""
Test de regresie: `_filter_active_tenders` (backend/agents/tools/lead_search.py)
citea `market.get("seap", {}).get("total_contracts", 0)` DIRECT, fara unwrap
`.value`. `verified["market"]["seap"]` e infasurat de `_verify_market()` ->
`_make_field()` (backend/agents/agent_verification.py:639-645), forma
`{"value": {...total_contracts...}, "trust":..., "source":..., "timestamp":...}`
— confirmat pe date reale din `data/ris.db` (`reports.full_data`, coloana
scrisa direct din `verified_data`, vezi `job_service._save_job_results`):
wrapper-ul are cheile `value/trust/source/timestamp`, iar `total_contracts`
exista DOAR in interiorul `value` (in proba reala: 20), niciodata pe wrapper
insusi (`None`).

Efect pe codul vechi: `won_count` era mereu 0, deci LEAD_GENERATION nu
prioritiza NICIODATA firmele cu contracte SEAP castigate reale.

Acelasi bug, acelasi pattern, ca cel reparat in commit 738cf22 in alte 4
situri (agent_synthesis.py + section_prompts.py) — fix-ul nu ajunsese si in
acest fisier.

`tender_opportunities.count` NU are aceeasi problema: e assignat direct in
`agent_verification.py::_fetch_tender_opportunities`, fara trecere prin
`_make_field()` — verificat pe aceleasi date reale, cheia `count` e la nivel
de top. Testele de mai jos verifica explicit ca ramane neschimbat.

Rulat pe codul dinaintea fix-ului (git stash), primul test PICA: won_count == 0
desi firma are 20 de contracte SEAP reale.
"""
import asyncio
import json

from backend.agents.tools import lead_search


def _wrapped_seap(total_contracts: int) -> dict:
    """Forma REALA produsa de _verify_market() -> _make_field(), confirmata
    in data/ris.db pe un raport real (contracte SEAP reale)."""
    return {
        "value": {
            "cui": "12345678",
            "contracts": [],
            "total_contracts": total_contracts,
            "won_cpv_codes": ["7213"],
        },
        "trust": "VERIFICAT",
        "source": "SEAP",
        "timestamp": "2026-01-01T00:00:00+00:00",
    }


def _unwrapped_tenders(count: int) -> dict:
    """Forma REALA a tender_opportunities — assignata direct, fara wrapper."""
    return {
        "available": True,
        "source": "SICAP",
        "caen_code": "6201",
        "count": count,
        "opportunities": [],
    }


class _FakeDB:
    def __init__(self, full_data: dict):
        self._full_data = full_data

    async def fetch_one(self, query, params=None):
        return {"full_data": json.dumps(self._full_data, ensure_ascii=False)}

    async def fetch_all(self, query, params=None):
        return []


class TestFilterActiveTendersSeapUnwrap:
    def test_contracte_seap_reale_se_regasesc_in_match_reason(self, monkeypatch):
        full_data = {
            "market": {"seap": _wrapped_seap(20)},
            "tender_opportunities": _unwrapped_tenders(0),
        }
        fake_db = _FakeDB(full_data)
        monkeypatch.setattr(lead_search, "db", fake_db)

        candidates = [{"id": "c1", "name": "Firma Test SRL"}]
        result = asyncio.run(lead_search._filter_active_tenders(candidates))

        assert len(result) == 1, "firma cu 20 contracte SEAP reale a fost exclusa — won_count citit gresit ca 0"
        assert "20 contracte castigate" in result[0]["match_reason"]

    def test_fara_contracte_seap_si_fara_licitatii_deschise_firma_exclusa(self, monkeypatch):
        full_data = {
            "market": {"seap": _wrapped_seap(0)},
            "tender_opportunities": _unwrapped_tenders(0),
        }
        fake_db = _FakeDB(full_data)
        monkeypatch.setattr(lead_search, "db", fake_db)

        candidates = [{"id": "c1", "name": "Firma Fara Contracte SRL"}]
        result = asyncio.run(lead_search._filter_active_tenders(candidates))

        assert result == []

    def test_tender_opportunities_count_ramane_neinfasurat_top_level(self, monkeypatch):
        """tender_opportunities.count NU trece prin _make_field() — trebuie sa
        ramana citit direct la nivel de top, neschimbat de fix-ul de unwrap SEAP."""
        full_data = {
            "market": {"seap": _wrapped_seap(0)},
            "tender_opportunities": _unwrapped_tenders(15),
        }
        fake_db = _FakeDB(full_data)
        monkeypatch.setattr(lead_search, "db", fake_db)

        candidates = [{"id": "c1", "name": "Firma Cu Licitatii Deschise SRL"}]
        result = asyncio.run(lead_search._filter_active_tenders(candidates))

        assert len(result) == 1
        assert "15 licitatii deschise" in result[0]["match_reason"]
