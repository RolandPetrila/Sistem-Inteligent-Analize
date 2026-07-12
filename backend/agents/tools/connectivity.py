"""
Connectivity ping registry — un test minimal de reachability per sursa externa
FARA endpoint dedicat de test (ANAF TVA/Bilant, BNR, openapi.ro, SEAP, BPI,
Monitorul Oficial, Sanctiuni, Eurostat, INS TEMPO, AEGRM, Portal Just, Brave,
Jina, Google Maps).

DE CE UN REGISTRY, NU 15 BLOCURI ELIF: `test_service()` din
backend/routers/settings.py avea deja 4 blocuri elif pentru providerii AI —
inca 15 identice ca forma ar deveni greu de intretinut. PING_REGISTRY e un
dict {nume_serviciu: functie_async}, extensibil cu o singura linie noua.

Fiecare functie ping_* e async, NU arunca exceptii (le prinde intern) si
returneaza {"ok": bool, "message": str, **extra}.

Surse GRATUITE (fara cost/cota) -> ping face un apel real, minimal:
    anaf_tva, anaf_bilant, bnr, seap, bpi, monitorul_oficial, sanctions,
    eurostat, ins_tempo, aegrm, just, jina

Surse cu COST/COTA limitata -> pingul foloseste calea cea mai ieftina posibila,
dar tot consuma o cerere reala (ca test-ul Tavily existent) — marcate
"live_safe: False" in dashboard (necesita click manual, nu auto-test):
    openapi_ro (100/luna), brave (2000/luna), google_maps ($200 credit/luna)

BPI si Monitorul Oficial folosesc DELIBERAT calea gratuita (nu Tavily) —
un ping nu trebuie sa consume din cota de 1000/luna Tavily.
"""

import time

from loguru import logger

# CUI folosit ca test de conectivitate — firma reala, verificata repetat in
# sweep-ul E2E din 2026-07-12 (raspunde consistent la ANAF/openapi.ro/SEAP).
TEST_CUI = "14399840"

_NETWORK_ERROR_MARKERS = (
    "timeout", "connect", "refused", "unreachable", "dns",
    "getaddrinfo", "name or service not known", "nodename nor servname",
    "certificate", "ssl", "11001",  # 11001 = Windows getaddrinfoW DNS failure
)


def _looks_like_network_error(msg: str) -> bool:
    m = (msg or "").lower()
    return any(marker in m for marker in _NETWORK_ERROR_MARKERS)


async def ping_anaf_tva() -> dict:
    from backend.agents.tools.anaf_client import get_anaf_data
    try:
        data = await get_anaf_data(TEST_CUI)
    except Exception as e:
        return {"ok": False, "message": f"ANAF TVA eroare: {e}"[:200]}
    if "found" not in data:
        return {"ok": False, "message": "ANAF TVA: raspuns neasteptat (fara camp 'found')"}
    return {"ok": True, "message": f"ANAF TVA OK (CUI test {TEST_CUI}, found={data.get('found')})"}


async def ping_anaf_bilant() -> dict:
    from datetime import date

    from backend.agents.tools.anaf_bilant_client import get_bilant
    year = date.today().year - 1
    try:
        data = await get_bilant(TEST_CUI, year)
    except Exception as e:
        return {"ok": False, "message": f"ANAF Bilant eroare: {e}"[:200]}
    err = data.get("error", "")
    if err and _looks_like_network_error(err):
        return {"ok": False, "message": f"ANAF Bilant indisponibil: {err}"[:200]}
    return {"ok": True, "message": f"ANAF Bilant OK (an {year}, found={data.get('found')})"}


async def ping_bnr() -> dict:
    from backend.agents.tools.bnr_client import get_exchange_rates
    try:
        data = await get_exchange_rates()
    except Exception as e:
        return {"ok": False, "message": f"BNR eroare: {e}"[:200]}
    rates = data.get("rates", {})
    if "EUR" not in rates:
        return {"ok": False, "message": f"BNR: raspuns fara curs EUR ({data.get('error', 'necunoscut')})"}
    return {"ok": True, "message": f"BNR OK (EUR={rates['EUR']}, data={data.get('date')})"}


async def ping_openapi_ro() -> dict:
    from backend.config import settings
    if not settings.openapi_ro_key:
        return {"ok": False, "message": "OPENAPI_RO_KEY nu este configurat"}
    from backend.agents.tools.openapi_client import get_company_onrc
    try:
        data = await get_company_onrc(TEST_CUI)
    except Exception as e:
        return {"ok": False, "message": f"openapi.ro eroare: {e}"[:200]}
    if data.get("error") == "quota_exceeded":
        return {"ok": False, "message": "openapi.ro: cota lunara epuizata (100/luna)"}
    remaining = data.get("api_requests_remaining")
    quota_msg = f", requests ramase: {remaining}" if remaining is not None else ""
    return {"ok": True, "message": f"openapi.ro OK (found={data.get('found')}{quota_msg})"}


async def ping_seap() -> dict:
    from backend.agents.tools.seap_client import get_contracts_won
    try:
        data = await get_contracts_won(TEST_CUI, page_size=5, use_cache=True)
    except Exception as e:
        return {"ok": False, "message": f"SEAP eroare: {e}"[:200]}
    if "notices_error" in data and "direct_error" in data:
        return {"ok": False, "message": f"SEAP indisponibil: {data.get('notices_error')}"[:200]}
    return {"ok": True, "message": f"SEAP OK ({data.get('total_contracts', 0)} contracte gasite pt CUI test)"}


async def ping_bpi() -> dict:
    from backend.agents.tools.bpi_client import check_insolvency
    try:
        # use_tavily_fallback=False — pingul nu trebuie sa consume cota Tavily
        data = await check_insolvency(TEST_CUI, use_tavily_fallback=False)
    except Exception as e:
        return {"ok": False, "message": f"BPI eroare: {e}"[:200]}
    if data.get("error"):
        return {"ok": False, "message": f"BPI (buletinul.ro) indisponibil: {data['error']}"}
    return {"ok": True, "message": f"BPI OK (buletinul.ro, found={data.get('found')})"}


async def ping_monitorul_oficial() -> dict:
    """Verifica doar reachability-ul sitului (fallback direct), fara Tavily."""
    from backend.agents.tools.monitorul_oficial_client import MO_BASE
    from backend.http_client import get_client
    try:
        client = get_client()
        resp = await client.get(MO_BASE, timeout=10.0, follow_redirects=True)
    except Exception as e:
        return {"ok": False, "message": f"Monitorul Oficial eroare: {e}"[:200]}
    if resp.status_code >= 500:
        return {"ok": False, "message": f"Monitorul Oficial HTTP {resp.status_code}"}
    return {"ok": True, "message": f"Monitorul Oficial OK (HTTP {resp.status_code})"}


async def ping_sanctions() -> dict:
    import os

    from backend.agents.tools.sanctions_client import CACHE_PATH, screen
    try:
        data = await screen([])
    except Exception as e:
        return {"ok": False, "message": f"Sanctiuni eroare: {e}"[:200]}
    if data.get("status") == "unavailable":
        return {"ok": False, "message": "Sanctiuni: nicio sursa incarcata (OFAC/UE/ONU indisponibile)"}
    lists_checked = data.get("lists_checked", [])
    lists_missing = data.get("lists_missing", [])
    age_msg = ""
    try:
        if os.path.exists(CACHE_PATH):
            age_h = (time.time() - os.path.getmtime(CACHE_PATH)) / 3600
            age_msg = f", cache varsta {age_h:.1f}h"
    except OSError:
        pass
    msg = f"Sanctiuni OK ({', '.join(lists_checked)}, {data.get('total_entries', 0)} intrari{age_msg})"
    if lists_missing:
        msg += f" — LIPSA: {', '.join(lists_missing)}"
    return {"ok": True, "message": msg}


async def ping_eurostat() -> dict:
    from backend.agents.tools.eurostat_client import get_sector_context
    try:
        data = await get_sector_context("6201")  # IT/software — sector comun, date stabile
    except Exception as e:
        return {"ok": False, "message": f"Eurostat eroare: {e}"[:200]}
    if not data.get("available"):
        return {"ok": False, "message": f"Eurostat indisponibil: {data.get('reason') or data.get('error')}"}
    return {"ok": True, "message": f"Eurostat OK (NACE {data.get('nace_used')}, an {data.get('year')})"}


async def ping_ins_tempo() -> dict:
    from backend.agents.tools.caen_context import _fetch_ins_tempo_all
    try:
        data = await _fetch_ins_tempo_all("62")  # sectiune IT — cerere INS TEMPO reala
    except Exception as e:
        return {"ok": False, "message": f"INS TEMPO eroare: {e}"[:200]}
    if not data:
        return {"ok": False, "message": "INS TEMPO indisponibil (timeout sau fara date pt sectiunea test)"}
    return {"ok": True, "message": f"INS TEMPO OK ({data})"}


async def ping_aegrm() -> dict:
    from backend.agents.tools.aegrm_client import check_aegrm_guarantees
    try:
        data = await check_aegrm_guarantees(TEST_CUI)
    except Exception as e:
        return {"ok": False, "message": f"AEGRM eroare neasteptata: {e}"[:200]}
    if data.get("has_data"):
        return {"ok": True, "message": f"AEGRM OK ({data.get('count', 0)} garantii pt CUI test)"}
    err = data.get("error", "")
    if _looks_like_network_error(err):
        return {"ok": False, "message": f"AEGRM indisponibil (posibil DNS-dead): {err}"[:200]}
    return {"ok": False, "message": f"AEGRM: raspuns fara date ({err})"[:200]}


async def ping_just() -> dict:
    """Verifica doar ca 'zeep' e instalat — un apel SOAP complet e prea lent/nesigur pt un ping."""
    try:
        import zeep  # noqa: F401
    except ImportError:
        return {"ok": False, "message": "Pachetul 'zeep' NU e instalat (pip install zeep) — portal.just.ro indisponibil"}
    return {"ok": True, "message": "zeep instalat — portal.just.ro apelabil (SOAP)"}


async def ping_brave() -> dict:
    from backend.config import settings
    if not settings.brave_api_key:
        return {"ok": False, "message": "BRAVE_API_KEY nu este configurat"}
    from backend.http_client import get_client
    try:
        client = get_client()
        resp = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"Accept": "application/json", "X-Subscription-Token": settings.brave_api_key},
            params={"q": "test", "count": 1},
            timeout=10,
        )
    except Exception as e:
        return {"ok": False, "message": f"Brave Search eroare: {e}"[:200]}
    return {"ok": resp.status_code == 200, "message": f"Brave Search HTTP {resp.status_code}"}


async def ping_jina() -> dict:
    from backend.agents.tools.jina_client import fetch_clean_content
    try:
        text = await fetch_clean_content("https://example.com")
    except Exception as e:
        return {"ok": False, "message": f"Jina Reader eroare: {e}"[:200]}
    if not text:
        return {"ok": False, "message": "Jina Reader: niciun continut extras"}
    return {"ok": True, "message": f"Jina Reader OK ({len(text)} caractere extrase din example.com)"}


async def ping_google_maps() -> dict:
    from backend.config import settings
    if not settings.google_cloud_api_key:
        return {"ok": False, "message": "GOOGLE_CLOUD_API_KEY nu este configurat"}
    from backend.agents.tools.maps_client import get_maps_rating
    try:
        data = await get_maps_rating("Primaria Municipiului Bucuresti", "Bucuresti")
    except Exception as e:
        return {"ok": False, "message": f"Google Maps eroare: {e}"[:200]}
    err = data.get("error", "")
    if err == "request_denied":
        return {"ok": False, "message": "Google Maps: REQUEST_DENIED (cheie invalida sau billing dezactivat)"}
    if err == "over_query_limit":
        return {"ok": False, "message": "Google Maps: credit lunar epuizat (OVER_QUERY_LIMIT)"}
    return {"ok": True, "message": f"Google Maps OK (found={data.get('found')})"}


PING_REGISTRY = {
    "anaf_tva": ping_anaf_tva,
    "anaf_bilant": ping_anaf_bilant,
    "bnr": ping_bnr,
    "openapi_ro": ping_openapi_ro,
    "seap": ping_seap,
    "bpi": ping_bpi,
    "monitorul_oficial": ping_monitorul_oficial,
    "sanctions": ping_sanctions,
    "eurostat": ping_eurostat,
    "ins_tempo": ping_ins_tempo,
    "aegrm": ping_aegrm,
    "just": ping_just,
    "brave": ping_brave,
    "jina": ping_jina,
    "google_maps": ping_google_maps,
}


async def run_ping(service: str) -> dict:
    """Ruleaza ping-ul pentru un serviciu din registry. Nu arunca — orice eroare neprinsa
    de functia individuala e capturata aici ca ultima plasa de siguranta."""
    fn = PING_REGISTRY[service]
    try:
        return await fn()
    except Exception as e:
        logger.warning(f"[connectivity] ping {service} a esuat neasteptat: {e}")
        return {"ok": False, "message": f"Eroare neasteptata: {e}"[:200]}
