"""
Client openapi.ro — Date ONRC structurate.
100 req/luna gratuit. Returneaza: CAEN, adresa, asociati, administratori, capital social.
"""

import httpx
from loguru import logger
from backend.http_client import get_client

from backend.config import settings

OPENAPI_BASE = "https://api.openapi.ro/api/companies"


async def get_company_onrc(cui: str) -> dict:
    """Interogheaza openapi.ro pentru date ONRC structurate."""
    if not settings.openapi_ro_key:
        return {"error": "OPENAPI_RO_KEY nu este configurat", "found": False}

    cui_clean = str(cui).strip().replace("RO", "").replace("ro", "")
    if not cui_clean.isdigit():
        return {"error": f"CUI invalid: {cui}", "found": False}

    headers = {"x-api-key": settings.openapi_ro_key}

    try:
        from backend.agents.tools.retry import with_retry

        async def _do_request():
            c = get_client()
            return await c.get(f"{OPENAPI_BASE}/{cui_clean}", headers=headers)

        logger.debug(f"openapi.ro: fetching CUI {cui_clean}")
        response = await with_retry(_do_request, retries=1, backoff=[3], source_name="openapi.ro")

        if response.status_code == 404:
            return {"cui": cui_clean, "found": False, "error": "CUI negasit in ONRC"}

        if response.status_code == 429:
            return {"cui": cui_clean, "found": False, "error": "Quota openapi.ro depasita (100 req/luna)"}

        if response.status_code != 200:
            return {"cui": cui_clean, "found": False, "error": f"HTTP {response.status_code}"}

        # D3 fix: Safe JSON parsing
        try:
            data = response.json()
        except (ValueError, Exception):
            return {"cui": cui_clean, "found": False, "error": "Invalid JSON from openapi.ro"}

        result = {
            "cui": cui_clean,
            "found": True,
            "source": "openapi.ro",
            "source_url": f"https://openapi.ro/api/companies/{cui_clean}",
            "denumire": data.get("denumire", ""),
            "judet": data.get("judet", ""),
            "adresa": data.get("adresa", ""),
            "cod_postal": data.get("cod_postal", ""),
            "telefon": data.get("telefon", ""),
            "fax": data.get("fax", ""),
            "numar_reg_com": data.get("numar_reg_com", ""),
            "stare": data.get("stare", ""),
            "radiata": data.get("radiata", False),
            "impozit_micro": data.get("impozit_micro", False),
            "impozit_profit": data.get("impozit_profit", False),
            "accize": data.get("accize", False),
            "act_autorizare": data.get("act_autorizare", ""),
            # DF2: Actionariat
            "asociati": data.get("asociati", []),
            "administratori": data.get("administratori", []),
            "capital_social": data.get("capital_social"),
            "caen_code": data.get("cod_caen", ""),
            "caen_description": data.get("caen", ""),
        }

        # Meta info (requests ramase)
        meta = data.get("meta", {})
        if meta:
            result["api_requests_remaining"] = meta.get("remaining_requests")

        logger.debug(f"openapi.ro: OK for CUI {cui_clean}")
        return result

    except httpx.TimeoutException:
        return {"cui": cui_clean, "found": False, "error": "Timeout openapi.ro"}
    except Exception as e:
        logger.warning(f"openapi.ro error: {e}")
        return {"cui": cui_clean, "found": False, "error": str(e)}
