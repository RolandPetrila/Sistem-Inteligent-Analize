"""
Fixtures + harness de executie pentru testul de caracterizare al
`OfficialAgent.execute()` (Pas 0, PLAN refactor #1 — vezi Roland_Opus_Sonnet.md
2026-07-14).

De ce mock la nivelul `fetch_with_retry` si nu la nivelul clientilor HTTP:
`fetch_with_retry(coro_factory, source_name, source_url)` e apelat cu acelasi
`source_name` in toate cele 8 locuri unde e folosit in execute() (5 din gather-ul
principal + 3 fallback-uri Tavily) -- un singur mock dispecerizat dupa `source_name`
le acopera pe toate, fara sa depinda de cache_service/retea reala si fara
non-determinism de `response_time_ms` (control complet, nu doar toleranta de rotunjire
ca la golden-ul de scoring). AEGRM NU trece prin acest seam (apelat direct in cod,
linia 141) -- mockuit separat pe `_fetch_aegrm`.

Toate importurile LOCALE din interiorul lui execute() (store_administrators,
get_maps_rating, search_company_publications, search_monitorul_oficial) sunt
mockuite la MODULUL SURSA, nu pe `agent_official` -- pentru ca sunt re-importate
la fiecare apel (`from X import Y` in interiorul functiei).
"""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

FIXED_REF_DATETIME = datetime(2026, 7, 14, 12, 0, 0, tzinfo=UTC)

# CUI real, valid MOD11 (folosit si live in aceasta sesiune -- MOSSLEIN S.R.L.)
VALID_CUI = "26313362"
# CUI care PICA MOD11 (verificat manual: cifra de control calculata = 4, primita = 8)
INVALID_CUI = "12345678"

ANAF_URL = "https://webservicesp.anaf.ro"
OPENAPI_URL = "https://openapi.ro"
BILANT_URL = "https://webservicesp.anaf.ro/bilant"
BNR_URL = "https://www.bnr.ro/nbrfxrates.xml"
BPI_URL = "https://www.buletinul.ro"
FIN_TAVILY_URL = "https://listafirme.ro"
LEGAL_URL = "https://bpi.ro + portal.just.ro"


def _sr(source_name: str, source_url: str, found: bool, data: dict) -> dict:
    """Construieste un SourceResult identic cu ce produce fetch_with_retry real."""
    return {
        "source_name": source_name,
        "source_url": source_url,
        "status": "OK" if found else "NO_DATA",
        "data_found": found,
        "response_time_ms": 0,
        "data": data,
    }


def _fail(error: str = "no data") -> dict:
    return {"error": error}


ANAF_OK = {
    "cui": VALID_CUI, "denumire": "MOSSLEIN TEST SRL", "stare": "INREGISTRAT",
    "platitor_tva": True, "inactiv": False, "split_tva": False,
    "stare_inregistrare": "INREGISTRAT", "cod_caen": "3600",
    "data_inactivare": "", "data_reactivare": "", "found": True,
}
OPENAPI_OK = {
    "found": True, "caen_code": "3600", "judet": "Arad",
    "asociati": [{"nume": "Ion Popescu", "procent": 100}],
    "administratori": [{"nume": "Ion Popescu"}],
    "capital_social": 200,
}
BILANT_OK = {"data": {"2024": {
    "cifra_afaceri": 1000000, "profit_net": 100000,
    "numar_mediu_salariati": 10, "caen_code": "3600",
}}}
BNR_OK = {"EUR": 5.05, "USD": 4.6}
BPI_OK = {"found": False}
AEGRM_OK_NO_GUARANTEES = {"has_data": True, "count": 0, "has_guarantees": False, "guarantees": []}
AEGRM_NO_DATA = {"has_data": False, "error": "no data"}

CAEN_CTX_OK = {
    "available": True, "caen_description": "Captarea, tratarea si distributia apei",
    "caen_section_name": "Utilitati",
}
CAEN_CTX_MISSING = {"available": False}

DOSARE_FOUND = {"found": True, "total_dosare": 1, "dosare": [
    {"numar": "123/2026", "instanta": "Tribunalul Arad"},
]}
DOSARE_NOT_FOUND = {"found": False}

ONRC_TAVILY_OK = {"results": [{"title": "MOSSLEIN pe recom.onrc.ro", "url": "https://recom.onrc.ro/x", "content": "date firma"}]}


FIXTURES: dict[str, dict] = {
    # --- 1. Branch structural: CUI invalid MOD11 -> EARLY RETURN (linia 87-104) ---
    "invalid_cui_early_return": {
        "input_params": {"cui": INVALID_CUI},
        "analysis_type": "FULL_COMPANY_PROFILE",
        "fetch_canned": {},  # nu se ajunge la niciun fetch
        "aegrm_result": AEGRM_NO_DATA,
        "dosare_result": DOSARE_NOT_FOUND,
        "maps_result": {"found": False},
        "mo_partea_iv_result": [],
        "osint_result": {"historical_flags": []},
        "brave_avail": False,
        "brave_result": None,
        "tavily_quota_ok": True,
        "caen_ctx_result": CAEN_CTX_MISSING,
        "google_key": None,
    },

    # --- 2. Branch structural: FARA cui_clean -> ramura else (linia 345-357) ---
    # Numele firmei e introdus direct in campul "cui" (scenariul MARKET_ENTRY_ANALYSIS/
    # LEAD_GENERATION/CUSTOM_REPORT descris in comentariul liniilor 57-63).
    "no_cui_provided": {
        "input_params": {"cui": "Firma Fara CUI Exemplu SRL"},
        "analysis_type": "LEAD_GENERATION",
        "fetch_canned": {
            "BNR": _sr("BNR", BNR_URL, True, BNR_OK),
            "ONRC (Tavily)": _sr("ONRC (Tavily)", "https://recom.onrc.ro", True, ONRC_TAVILY_OK),
            "Date financiare (listafirme.ro)": _sr("Date financiare (listafirme.ro)", FIN_TAVILY_URL, False, _fail()),
            "Legal (BPI+Litigii)": _sr("Legal (BPI+Litigii)", LEGAL_URL, False, _fail()),
        },
        "aegrm_result": AEGRM_NO_DATA,
        "dosare_result": DOSARE_NOT_FOUND,
        "maps_result": {"found": False},
        "mo_partea_iv_result": [],
        "osint_result": {"historical_flags": []},
        "brave_avail": False,
        "brave_result": None,
        "tavily_quota_ok": True,
        "caen_ctx_result": CAEN_CTX_MISSING,
        "google_key": None,
    },

    # --- 2b. Pas 3: fallback pe TEXT LIBER -> AMBIGUU (2 CUI distincte valide) -> niciun
    # CUI rezolvat -> marcaj cui_warning "text liber" (branch-ul 3c largit). Exercita BUCLA
    # fallback (input FARA camp cui dedicat), spre deosebire de no_cui_provided (nume in
    # slotul cui -> bucla sarita). Fara acest fixture, calea fallback-gol e tacuta (advisor).
    "fallback_ambiguous_no_cui": {
        "input_params": {"ideal_client": "firma 26313362 si partenerul 18189442"},
        "analysis_type": "LEAD_GENERATION",
        "fetch_canned": {
            "BNR": _sr("BNR", BNR_URL, True, BNR_OK),
            "ONRC (Tavily)": _sr("ONRC (Tavily)", "https://recom.onrc.ro", True, ONRC_TAVILY_OK),
            "Date financiare (listafirme.ro)": _sr("Date financiare (listafirme.ro)", FIN_TAVILY_URL, False, _fail()),
            "Legal (BPI+Litigii)": _sr("Legal (BPI+Litigii)", LEGAL_URL, False, _fail()),
        },
        "aegrm_result": AEGRM_NO_DATA,
        "dosare_result": DOSARE_NOT_FOUND,
        "maps_result": {"found": False},
        "mo_partea_iv_result": [],
        "osint_result": {"historical_flags": []},
        "brave_avail": False,
        "brave_result": None,
        "tavily_quota_ok": True,
        "caen_ctx_result": CAEN_CTX_MISSING,
        "google_key": None,
    },

    # --- 3. Happy path complet: toate 6 surse din gather reusesc ---
    "all_sources_succeed": {
        "input_params": {"cui": VALID_CUI, "company_name": "MOSSLEIN TEST SRL"},
        "analysis_type": "FULL_COMPANY_PROFILE",
        "fetch_canned": {
            "ANAF": _sr("ANAF", ANAF_URL, True, ANAF_OK),
            "openapi.ro": _sr("openapi.ro", OPENAPI_URL, True, OPENAPI_OK),
            "ANAF Bilant": _sr("ANAF Bilant", BILANT_URL, True, BILANT_OK),
            "BNR": _sr("BNR", BNR_URL, True, BNR_OK),
            "BPI (buletinul.ro)": _sr("BPI (buletinul.ro)", BPI_URL, True, BPI_OK),
            # ONRC (Tavily) + Date financiare (listafirme.ro) NU trebuie apelate --
            # openapi.ro + ANAF Bilant au reusit deja (guard-urile `not official_data.get(...)`).
            # Daca dispatcher-ul ar primi aceste nume, ar arunca -- garda implicita.
            "Legal (BPI+Litigii)": _sr("Legal (BPI+Litigii)", LEGAL_URL, True, {
                "results": [{"title": "fara insolventa/litigii", "url": "https://bpi.ro/x", "content": "curat"}],
                "answer": "Nicio mentiune gasita.", "query": "test",
            }),
        },
        "aegrm_result": AEGRM_OK_NO_GUARANTEES,
        "dosare_result": DOSARE_FOUND,
        "maps_result": {"found": False},  # nefolosit -- google_key=None, blocul se sare
        "mo_partea_iv_result": [],
        "osint_result": {"historical_flags": []},
        "brave_avail": False,
        "brave_result": None,
        "tavily_quota_ok": True,
        "caen_ctx_result": CAEN_CTX_OK,
        "google_key": None,
    },

    # --- 4. CRITICA #2: ANAF pica, restul reusesc -- cui/company_name trebuie sa ramana setate ---
    "anaf_fails_rest_succeed": {
        "input_params": {"cui": VALID_CUI, "company_name": "MOSSLEIN TEST SRL"},
        "analysis_type": "FULL_COMPANY_PROFILE",
        "fetch_canned": {
            "ANAF": _sr("ANAF", ANAF_URL, False, _fail("ANAF timeout")),
            "openapi.ro": _sr("openapi.ro", OPENAPI_URL, True, OPENAPI_OK),
            "ANAF Bilant": _sr("ANAF Bilant", BILANT_URL, True, BILANT_OK),
            "BNR": _sr("BNR", BNR_URL, True, BNR_OK),
            "BPI (buletinul.ro)": _sr("BPI (buletinul.ro)", BPI_URL, True, BPI_OK),
            "Legal (BPI+Litigii)": _sr("Legal (BPI+Litigii)", LEGAL_URL, True, {
                "results": [], "answer": "", "query": "test",
            }),
        },
        "aegrm_result": AEGRM_OK_NO_GUARANTEES,
        "dosare_result": DOSARE_FOUND,
        "maps_result": {"found": False},
        "mo_partea_iv_result": [],
        "osint_result": {"historical_flags": []},
        "brave_avail": False,
        "brave_result": None,
        "tavily_quota_ok": True,
        "caen_ctx_result": CAEN_CTX_OK,  # rezolvat via openapi.ro, NU via ANAF
        "google_key": None,
    },

    # --- 5. CUI valid dar TOTUL pica (gather + ambele fallback-uri + legal-merged + Portal Just) ---
    "all_sources_fail": {
        "input_params": {"cui": VALID_CUI, "company_name": "MOSSLEIN TEST SRL"},
        "analysis_type": "FULL_COMPANY_PROFILE",
        "fetch_canned": {
            "ANAF": _sr("ANAF", ANAF_URL, False, _fail("timeout")),
            "openapi.ro": _sr("openapi.ro", OPENAPI_URL, False, _fail("timeout")),
            "ANAF Bilant": _sr("ANAF Bilant", BILANT_URL, False, _fail("no financial data")),
            "BNR": _sr("BNR", BNR_URL, False, _fail("unavailable")),
            "BPI (buletinul.ro)": _sr("BPI (buletinul.ro)", BPI_URL, False, _fail("check failed")),
            "ONRC (Tavily)": _sr("ONRC (Tavily)", "https://recom.onrc.ro", False, _fail()),
            "Date financiare (listafirme.ro)": _sr("Date financiare (listafirme.ro)", FIN_TAVILY_URL, False, _fail()),
            "Legal (BPI+Litigii)": _sr("Legal (BPI+Litigii)", LEGAL_URL, False, _fail()),
        },
        "aegrm_result": AEGRM_NO_DATA,
        "dosare_result": DOSARE_NOT_FOUND,
        "maps_result": {"found": False},
        "mo_partea_iv_result": [],
        "osint_result": {"historical_flags": []},
        "brave_avail": False,
        "brave_result": None,
        "tavily_quota_ok": True,
        "caen_ctx_result": CAEN_CTX_MISSING,  # nu conteaza -- caen_code ramane gol, fetch-ul se sare
        "google_key": None,
    },

    # --- 6. Mix realist: succes partial + Google Maps activ + quota Tavily epuizata ---
    # NOTA (descoperire in timpul proiectarii fixture-ului): `tavily_quota_ok` gateaza SI
    # legal-merged (linia 395) SI OSINT (linia 591) -- ACELASI flag. Cu quota epuizata,
    # OSINT NU se executa deloc (nu doar legal-merged) -- `osint_result` de mai jos e
    # NEFOLOSIT in acest fixture ca urmare directa a acestei descoperiri (vezi raport).
    "realistic_mixed": {
        "input_params": {"cui": VALID_CUI, "company_name": "MOSSLEIN TEST SRL"},
        "analysis_type": "FULL_COMPANY_PROFILE",
        "fetch_canned": {
            "ANAF": _sr("ANAF", ANAF_URL, True, ANAF_OK),
            "openapi.ro": _sr("openapi.ro", OPENAPI_URL, True, OPENAPI_OK),
            "ANAF Bilant": _sr("ANAF Bilant", BILANT_URL, False, _fail("no financial data")),
            "BNR": _sr("BNR", BNR_URL, True, BNR_OK),
            "BPI (buletinul.ro)": _sr("BPI (buletinul.ro)", BPI_URL, False, _fail("check failed")),
            "Date financiare (listafirme.ro)": _sr("Date financiare (listafirme.ro)", FIN_TAVILY_URL, False, _fail()),
            # "Legal (BPI+Litigii)" absent intentionat -- quota epuizata -> blocul se sare,
            # daca ar fi apelat oricum dispatcher-ul ar arunca (garda de regresie).
        },
        "aegrm_result": AEGRM_NO_DATA,
        "dosare_result": DOSARE_FOUND,
        "maps_result": {"found": True, "name": "MOSSLEIN TEST SRL", "rating": 4.2},
        "mo_partea_iv_result": [],
        "osint_result": {"historical_flags": [{
            "type": "cesiune_parti_sociale", "label": "Cesiune parti sociale detectata",
            "severity": "HIGH", "snippet": "test snippet",
        }]},  # NEFOLOSIT -- vezi nota de mai sus (quota epuizata sare blocul OSINT)
        "brave_avail": False,
        "brave_result": None,
        "tavily_quota_ok": False,
        "caen_ctx_result": CAEN_CTX_OK,  # rezolvat via openapi.ro
        "google_key": "fake-google-key-for-test",
    },
}


async def run_execute_with_fixture(fixture: dict) -> dict:
    """Aplica toate patch-urile necesare si ruleaza OfficialAgent.execute() PE CODUL
    REAL (neschimbat) cu dependintele externe inlocuite de raspunsuri canned."""
    import backend.agents.agent_official as mod
    import backend.database as database_mod
    from backend.agents.agent_official import OfficialAgent
    from backend.agents.tools import maps_client, monitorul_oficial_client, network_client, osint_client

    fetch_canned = fixture["fetch_canned"]

    def _dispatch(coro_factory, source_name, source_url=""):
        if source_name not in fetch_canned:
            raise AssertionError(
                f"[characterization] source_name neasteptat/nedeclarat in fixture: {source_name!r}"
            )
        return fetch_canned[source_name]

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return FIXED_REF_DATETIME

    with patch.object(OfficialAgent, "fetch_with_retry", new=AsyncMock(side_effect=_dispatch)), \
         patch.object(OfficialAgent, "_fetch_aegrm", new=AsyncMock(return_value=fixture["aegrm_result"])), \
         patch.object(mod, "search_dosare", new=AsyncMock(return_value=fixture["dosare_result"])), \
         patch.object(mod, "get_caen_context", new=AsyncMock(return_value=fixture["caen_ctx_result"])), \
         patch.object(mod, "enrich_tavily_results", new=AsyncMock(side_effect=lambda results, max_urls=3: results)), \
         patch.object(mod, "brave_available", new=lambda: fixture["brave_avail"]), \
         patch.object(mod, "brave_search", new=AsyncMock(return_value=fixture["brave_result"])), \
         patch.object(mod.tavily_client, "_check_quota", new=AsyncMock(
             return_value=(fixture["tavily_quota_ok"], {"used": 0, "limit": 1000}))), \
         patch.object(mod.settings, "google_cloud_api_key", fixture["google_key"]), \
         patch.object(network_client, "store_administrators", new=AsyncMock(return_value=None)), \
         patch.object(maps_client, "get_maps_rating", new=AsyncMock(return_value=fixture["maps_result"])), \
         patch.object(monitorul_oficial_client, "search_company_publications",
                      new=AsyncMock(return_value=fixture["mo_partea_iv_result"])), \
         patch.object(osint_client, "search_monitorul_oficial", new=AsyncMock(return_value=fixture["osint_result"])), \
         patch.object(database_mod.db, "fetch_one", new=AsyncMock(return_value=None)), \
         patch.object(mod, "datetime", new=_FrozenDatetime):
        agent = OfficialAgent()
        state = {
            "input_params": fixture["input_params"],
            "analysis_type": fixture["analysis_type"],
            "job_id": "characterization-test",
        }
        return await agent.execute(state)
