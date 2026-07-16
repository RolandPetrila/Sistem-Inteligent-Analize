"""
Fixtures + harness de executie pentru testul de caracterizare al
`VerificationAgent.execute()` (Pas 0, refactor #2 -- vezi brief Roland_Opus_Sonnet.md
2026-07-16, acelasi tipar ca `tests/fixtures/agent_official_characterization_inputs.py`).

De ce mock la nivelul functiilor client (nu al retelei/DB reale): `execute()` face
apeluri reale catre `backend.database.db` (2 query-uri pentru praguri dinamice + 1
UPDATE pentru `latest_ca`), catre `sanctions_client.screen`, `eurostat_client.get_
sector_context`, `seap_client.search_open_tenders`, `network_client.get_company_
network` si (doar pentru LEAD_GENERATION) `lead_search.parse_lead_criteria` +
`search_candidate_companies`. Toate sunt IMPORTATE LOCAL in interiorul metodelor
(`from X import Y`), deci sunt mockuite la MODULUL SURSA (nu pe `agent_verification`),
la fel ca in fixture-urile agent_official.

Restul logicii (`_verify_*`, `_cross_validate`, `_detect_anomalies`, scoring,
due_diligence, early_warnings, completeness, predictive_models, credit_exposure,
funding_programs) e PURA (fara I/O) si ruleaza REAL pe fiecare fixture -- singurul
non-determinism e `datetime.now()`/`date.today()`, inghetate explicit.
"""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

FIXED_REF_DATETIME = datetime(2026, 7, 16, 12, 0, 0, tzinfo=UTC)
FIXED_REF_DATE = FIXED_REF_DATETIME.date()


# ---------------------------------------------------------------------------
# Fixture 1: aproape totul absent -- verifica ramurile "sursa lipsa" pe intreg
# `execute()` (niciun `if X:` din blocurile principale nu se declanseaza).
# ---------------------------------------------------------------------------
MINIMAL_EMPTY = {
    "official_data": {},
    "web_data": {},
    "market_data": {},
    "analysis_type": "FULL_COMPANY_PROFILE",
    "input_params": {},
}

# ---------------------------------------------------------------------------
# Fixture 2: happy path complet -- toate sursele populate, toate blocurile
# opționale declansate, inclusiv LEAD_GENERATION (singurul tip care ruleaza
# `_search_lead_candidates`) si praguri dinamice pe calea CA-percentila
# (>=5 firme cu `latest_ca` real in DB pentru acelasi CAEN).
# ---------------------------------------------------------------------------
ANAF_RICH = {
    "found": True,
    "cui": "26313362",
    "denumire": "MOSSLEIN TEST SRL",
    "adresa": "Str. Exemplu nr. 1, Arad",
    "numar_reg_com": "J02/123/2015",
    "stare_inregistrare": "INREGISTRAT",
    "data_inregistrare": "2015-03-10",
    "platitor_tva": True,
    "inactiv": False,
    "split_tva": False,
    "cod_caen": "6201",
}

ONRC_STRUCTURED_RICH = {
    "found": True,
    "caen_code": "6201",
    "caen_description": "Activitati de realizare a soft-ului la comanda",
    "judet": "Arad",
    "telefon": "0257000000",
    "stare": "FUNCTIONEAZA",
    "numar_reg_com": "J02/123/2015",
    "capital_social": 200,
    "asociati": [{"nume": "Ion Popescu", "procent": 100}],
    "administratori": [{"nume": "Ion Popescu"}],
}

BILANT_RICH = {
    "data": {
        "2024": {
            "cifra_afaceri_neta": 2_000_000,
            "profit_net": 150_000,
            "numar_mediu_salariati": 12,
            "capitaluri_proprii": 400_000,
            "datorii_totale": 300_000,
            "active_totale": 700_000,
            "caen_code": "6201",
            "caen_description": "Activitati de realizare a soft-ului la comanda",
        },
        "2023": {
            "cifra_afaceri_neta": 1_500_000,
            "profit_net": 90_000,
            "numar_mediu_salariati": 9,
            "capitaluri_proprii": 300_000,
            "datorii_totale": 250_000,
            "active_totale": 550_000,
            "caen_code": "6201",
            "caen_description": "Activitati de realizare a soft-ului la comanda",
        },
    },
    "trend": {
        "cifra_afaceri_neta": {
            "name": "CA", "growth_percent": 33.3, "direction": "crestere",
            "values": [{"year": "2023", "value": 1_500_000}, {"year": "2024", "value": 2_000_000}],
            "first_year": "2023", "last_year": "2024",
        },
        "profit_net": {
            "name": "Profit Net", "growth_percent": 66.7, "direction": "crestere",
            "values": [{"year": "2023", "value": 90_000}, {"year": "2024", "value": 150_000}],
            "first_year": "2023", "last_year": "2024",
        },
        "numar_mediu_salariati": {
            "name": "Angajati", "growth_percent": 33.3, "direction": "crestere",
            "values": [{"year": "2023", "value": 9}, {"year": "2024", "value": 12}],
            "first_year": "2023", "last_year": "2024",
        },
        "capitaluri_proprii": {
            "name": "Capitaluri", "growth_percent": 33.3, "direction": "crestere",
            "values": [{"year": "2023", "value": 300_000}, {"year": "2024", "value": 400_000}],
            "first_year": "2023", "last_year": "2024",
        },
    },
    "years_found": ["2023", "2024"],
}

CAEN_CTX_RICH = {
    "available": True,
    "caen_code": "6201",
    "caen_description": "Activitati de realizare a soft-ului la comanda",
    "caen_section_name": "Servicii IT",
    "nr_firme_caen": 4200,
    "benchmark": {"ca_medie": 900_000, "angajati_medii": 8},
}

RICH_FULL_LEAD_GENERATION = {
    "official_data": {
        "anaf": ANAF_RICH,
        "onrc_structured": ONRC_STRUCTURED_RICH,
        "financial_official": BILANT_RICH,
        "bnr_rates": {"rates": {"EUR": 5.05, "USD": 4.6}, "date": "2026-07-16"},
        "insolvency": {"results": [{"title": "fara insolventa", "content": "curat"}]},
        "litigation": {"results": [{"title": "un litigiu minor", "content": "detalii"}]},
        "bpi_insolventa": {"found": False, "status": "NICIO PROCEDURA"},
        "aegrm_guarantees": {"has_data": True, "has_guarantees": True, "count": 2},
        "dosare_just": {
            "found": True, "total_dosare": 3, "reclamant": 2, "parat": 1,
            "dosare": [{"numar": "123/2026", "instanta": "Tribunalul Arad"}],
        },
        "risc_fiscal": {"tip_risc": "RISC SCAZUT"},
        "caen_context": CAEN_CTX_RICH,
        "maps_rating": {"found": True, "rating": 4.5, "reviews": 12},
        "monitorul_oficial": [{"tip": "cesiune", "data": "2025-01-01"}],
        "web_intelligence": {"classified": "prezenta activa", "score": 0.8},
        "brave_reputation": {"mentions": 5, "sentiment": "neutru"},
        "data_freshness": {"anaf": "2026-07-01", "bilant": "2025-12-01"},
        "diagnostics": {"completeness_score": 90, "missing_sources": []},
        "osint_historical": {
            "historical_flags": [{
                "type": "cesiune_parti_sociale", "label": "Cesiune parti sociale detectata",
                "severity": "HIGH", "snippet": "test snippet",
            }],
        },
        "tavily_quota_exhausted": True,
        "tavily_usage": {"used": 1000, "limit": 1000},
    },
    "web_data": {
        "online_presence": {"source": "Tavily", "found": True, "urls": ["https://mosslein.example"]},
        "news": {"source": "Tavily", "found": False},
    },
    "market_data": {
        "seap": {
            "total_contracts": 4,
            "won_cpv_codes": ["72212000"],
        },
    },
    "analysis_type": "LEAD_GENERATION",
    "input_params": {"ideal_client": "firme IT din Arad cu peste 5 angajati", "priority": "crestere", "count": "5"},
}

# Randuri DB pentru calea CA-percentila (>=5 firme cu latest_ca real pe acelasi CAEN)
RICH_CA_ROWS = [{"latest_ca": v} for v in (300_000, 600_000, 900_000, 1_200_000, 1_800_000, 2_400_000)]


# ---------------------------------------------------------------------------
# Fixture 3: surse partiale + fallback-uri (ANAF absent -> profil din ONRC/Tavily,
# date financiare din listafirme.ro, risc doar din Tavily). Praguri dinamice:
# CAEN necunoscut (nu se rezolva din nicio sursa) -> None fara apel DB.
# ---------------------------------------------------------------------------
FALLBACK_PARTIAL = {
    "official_data": {
        "onrc": {"results": [{"title": "MOSSLEIN pe recom.onrc.ro", "url": "https://recom.onrc.ro/x", "content": "date firma"}]},
        "financial": {"results": [{"title": "date financiare agregate", "content": "CA estimat 500K"}]},
        "insolvency": {"results": []},
        "litigation": {"results": [{"title": "litigiu gasit", "content": "detalii litigiu"}]},
    },
    "web_data": {},
    "market_data": {},
    "analysis_type": "FULL_COMPANY_PROFILE",
    "input_params": {"cui": "26313362"},
}

# ---------------------------------------------------------------------------
# Fixture 4: CAEN cunoscut (din ANAF) + judet cunoscut (adresa ANAF ca dict) ->
# praguri dinamice pe calea "score_proxy" prin query-ul CU judet (CA-percentila
# insuficienta, primul query <5 randuri). Acopera si mai multe reguli de
# anomalii (0 angajati + CA mare, capital minim + CA mare, pierdere neta,
# firma sub 1 an, CA zero) intr-un singur job -- caz adversarial concentrat.
# ---------------------------------------------------------------------------
ANAF_ANOMALY_PRONE = {
    "found": True,
    "cui": "26313362",
    "denumire": "ANOMALY TEST SRL",
    "adresa": {"judet": "Arad", "localitate": "Arad", "strada": "Str. Test nr. 2"},
    "numar_reg_com": "J02/999/2026",
    "stare_inregistrare": "INREGISTRAT",
    "data_inregistrare": "2026-01-05",  # sub 1 an fata de FIXED_REF_DATE
    "platitor_tva": True,
    "inactiv": False,
    "split_tva": False,
    "cod_caen": "6201",
}

BILANT_ANOMALY = {
    "data": {
        "2025": {
            "cifra_afaceri_neta": 6_000_000,   # CA mare
            "profit_net": -50_000,             # pierdere neta
            "pierdere_neta": 50_000,
            "numar_mediu_salariati": 0,         # 0 angajati + CA mare -> SUSPECT
            "capital_social": 200,              # capital minim + CA mare -> ATENTIE
            "capitaluri_proprii": 200,
            "caen_code": "6201",
            "caen_description": "Activitati de realizare a soft-ului la comanda",
        },
    },
    "trend": {},
    "years_found": ["2025"],
}

SCORE_PROXY_ANOMALY = {
    "official_data": {
        "anaf": ANAF_ANOMALY_PRONE,
        "financial_official": BILANT_ANOMALY,
    },
    "web_data": {},
    "market_data": {},
    "analysis_type": "FULL_COMPANY_PROFILE",
    "input_params": {"cui": "26313362"},
}

# Randuri DB pentru calea "score_proxy" (query CU judet reuseste cu >=5 firme)
SCORE_PROXY_COUNTY_ROWS = [{"numeric_score": v} for v in (40.0, 55.0, 60.0, 70.0, 80.0, 85.0)]


FIXTURES: dict[str, dict] = {
    "minimal_empty": MINIMAL_EMPTY,
    "rich_full_lead_generation": RICH_FULL_LEAD_GENERATION,
    "fallback_partial": FALLBACK_PARTIAL,
    "score_proxy_anomaly": SCORE_PROXY_ANOMALY,
}

# Config auxiliar per fixture pentru mock-urile DB si client-urile externe --
# separat de `FIXTURES` (care e trimis direct in `state["official_data"]` etc.)
# ca sa nu polueze structura de intrare reala cu detalii de test.
_DB_CONFIG: dict[str, dict] = {
    "minimal_empty": {"ca_rows": [], "score_rows_county": [], "score_rows_national": []},
    "rich_full_lead_generation": {"ca_rows": RICH_CA_ROWS, "score_rows_county": [], "score_rows_national": []},
    "fallback_partial": {"ca_rows": [], "score_rows_county": [], "score_rows_national": []},
    "score_proxy_anomaly": {"ca_rows": [], "score_rows_county": SCORE_PROXY_COUNTY_ROWS, "score_rows_national": []},
}

_EXTERNAL_CONFIG: dict[str, dict] = {
    "minimal_empty": {},
    "rich_full_lead_generation": {
        "sanctions_result": {
            "status": "ok", "hits": [{"name": "Ion Popescu", "list": "TEST"}],
            "checked": ["MOSSLEIN TEST SRL", "Ion Popescu"],
        },
        "eurostat_result": {
            "available": True, "source": "Eurostat", "caen_code": "6201",
            "nr_firme_ue": 250000, "angajati_per_firma_ue": 6.2,
        },
        "tenders_result": {
            "available": True, "count": 2,
            "tenders": [{"title": "Licitatie software", "cpv": "72212000"}],
        },
        "network_result": {
            "nodes": [{"cui": "26313362", "role": "self"}],
            "risk_flags": [{"severity": "RED", "detail": "Administrator comun cu 3 firme radiate"}],
        },
        "lead_criteria_result": {"caen_prefix": "62", "judet": "Arad", "min_angajati": 5},
        "lead_candidates_result": [
            {"cui": "11111111", "denumire": "CANDIDAT UNU SRL", "score": 72},
            {"cui": "22222222", "denumire": "CANDIDAT DOI SRL", "score": 65},
        ],
    },
    "fallback_partial": {},
    "score_proxy_anomaly": {},
}


async def run_execute_with_fixture(fixture_name: str) -> dict:
    """Aplica toate patch-urile necesare si ruleaza VerificationAgent.execute() PE
    CODUL REAL (neschimbat) cu toate dependintele I/O inlocuite de raspunsuri canned."""
    import backend.agents.agent_verification as mod
    import backend.database as database_mod
    from backend.agents.agent_verification import VerificationAgent
    from backend.agents.tools import eurostat_client, lead_search, network_client, sanctions_client, seap_client
    from backend.agents.tools import funding_programs as funding_mod
    from backend.agents.verification import scoring as scoring_mod

    fixture = FIXTURES[fixture_name]
    db_cfg = _DB_CONFIG[fixture_name]
    ext_cfg = _EXTERNAL_CONFIG.get(fixture_name, {})

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return FIXED_REF_DATETIME

    def _fetch_all_dispatch(sql, params=()):
        if "score_history" not in sql:
            return db_cfg.get("ca_rows", [])
        if "c.county = ?" in sql:
            return db_cfg.get("score_rows_county", [])
        return db_cfg.get("score_rows_national", [])

    with patch.object(mod, "datetime", new=_FrozenDatetime), \
         patch.object(database_mod.db, "fetch_all", new=AsyncMock(side_effect=_fetch_all_dispatch)), \
         patch.object(database_mod.db, "execute", new=AsyncMock(return_value=None)), \
         patch.object(scoring_mod, "date") as mock_date, \
         patch.object(funding_mod, "date") as mock_date2, \
         patch.object(sanctions_client, "screen", new=AsyncMock(
             return_value=ext_cfg.get("sanctions_result", {"status": "unavailable", "hits": [], "checked": []}))), \
         patch.object(eurostat_client, "get_sector_context", new=AsyncMock(
             return_value=ext_cfg.get("eurostat_result", {"available": False, "source": "Eurostat"}))), \
         patch.object(seap_client, "search_open_tenders", new=AsyncMock(
             return_value=ext_cfg.get("tenders_result", {"available": False}))), \
         patch.object(network_client, "get_company_network", new=AsyncMock(
             return_value=ext_cfg.get("network_result", {"nodes": [], "risk_flags": []}))), \
         patch.object(lead_search, "parse_lead_criteria", new=AsyncMock(
             return_value=ext_cfg.get("lead_criteria_result", {}))), \
         patch.object(lead_search, "search_candidate_companies", new=AsyncMock(
             return_value=ext_cfg.get("lead_candidates_result", []))):
        mock_date.today.return_value = FIXED_REF_DATE
        mock_date2.today.return_value = FIXED_REF_DATE
        agent = VerificationAgent()
        state = {
            "official_data": fixture.get("official_data", {}),
            "web_data": fixture.get("web_data"),
            "market_data": fixture.get("market_data"),
            "analysis_type": fixture.get("analysis_type", "FULL_COMPANY_PROFILE"),
            "input_params": fixture.get("input_params", {}),
        }
        return await agent.execute(state)
