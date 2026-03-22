"""
Client SEAP (e-licitatie.ro) — Licitatii si achizitii directe per CUI.
API public, rate limit strict — delay 3s intre request-uri.
"""

import asyncio

from loguru import logger
from backend.http_client import get_client
from backend.agents.tools.retry import with_retry


SEAP_NOTICES_URL = "https://e-licitatie.ro/api-pub/NoticeCommon/GetCANoticeList/"
SEAP_DIRECT_URL = "https://e-licitatie.ro/api-pub/DirectAcquisitionCommon/GetDirectAcquisitionList/"
REQUEST_DELAY = 3


async def get_contracts_won(cui: str, page_size: int = 20, use_cache: bool = True) -> dict:
    """Cauta contracte/licitatii castigate de o firma pe SEAP. Cu cache optional."""
    cui_clean = str(cui).strip()
    if not cui_clean.isdigit():
        return {"error": "CUI invalid", "contracts": []}

    # Cache check
    if use_cache:
        from backend.services import cache_service
        cache_key = cache_service.make_cache_key("seap_history", cui_clean)
        cached = await cache_service.get(cache_key)
        if cached is not None:
            logger.debug(f"SEAP: cache hit for CUI {cui_clean}")
            return cached

    results = {"cui": cui_clean, "contracts": [], "direct_acquisitions": [], "source": "SEAP"}

    # 1. Licitatii (CA Notices)
    try:
        payload = {
            "pageSize": page_size,
            "pageIndex": 0,
            "spiCuiSupplier": cui_clean,
            "sortField": "publicationDate",
            "sortOrder": "desc",
        }

        async def _fetch_notices():
            c = get_client()
            return await c.post(SEAP_NOTICES_URL, json=payload)

        logger.debug(f"SEAP: searching notices for CUI {cui_clean}")
        response = await with_retry(_fetch_notices, retries=1, backoff=[3], source_name="SEAP notices")

        if response.status_code == 200:
            data = response.json()
            items = data.get("items", data.get("searchResult", {}).get("items", []))
            if isinstance(items, list):
                for item in items[:10]:
                    results["contracts"].append({
                        "title": item.get("contractTitle", item.get("noticeTitle", "")),
                        "value": item.get("ronContractValue", item.get("estimatedValue")),
                        "currency": item.get("contractCurrency", "RON"),
                        "authority": item.get("contractingAuthorityName", ""),
                        "date": item.get("publicationDate", ""),
                        "type": item.get("sysNoticeTypeDescription", ""),
                    })
            results["contracts_count"] = len(results["contracts"])
            logger.debug(f"SEAP notices: {len(results['contracts'])} results")
        else:
            logger.warning(f"SEAP notices HTTP {response.status_code}")
            results["notices_error"] = f"HTTP {response.status_code}"

    except Exception as e:
        logger.warning(f"SEAP notices error: {e}")
        results["notices_error"] = str(e)

    await asyncio.sleep(REQUEST_DELAY)

    # 2. Achizitii directe
    try:
        da_payload = {
            "pageSize": page_size,
            "pageIndex": 0,
            "spiCuiSupplier": cui_clean,
            "sortField": "publicationDate",
            "sortOrder": "desc",
        }

        async def _fetch_direct():
            c = get_client()
            return await c.post(SEAP_DIRECT_URL, json=da_payload)

        logger.debug(f"SEAP: searching direct acquisitions for CUI {cui_clean}")
        response = await with_retry(_fetch_direct, retries=1, backoff=[3], source_name="SEAP direct")

        if response.status_code == 200:
            data = response.json()
            items = data.get("items", data.get("searchResult", {}).get("items", []))
            if isinstance(items, list):
                for item in items[:10]:
                    results["direct_acquisitions"].append({
                        "title": item.get("directAcquisitionName", item.get("title", "")),
                        "value": item.get("closingValue", item.get("estimatedValue")),
                        "authority": item.get("contractingAuthorityName", ""),
                        "date": item.get("publicationDate", ""),
                        "state": item.get("sysDirectAcqStateName", ""),
                    })
            results["direct_count"] = len(results["direct_acquisitions"])
            logger.debug(f"SEAP direct: {len(results['direct_acquisitions'])} results")
        else:
            logger.warning(f"SEAP direct HTTP {response.status_code}")
            results["direct_error"] = f"HTTP {response.status_code}"

    except Exception as e:
        logger.warning(f"SEAP direct error: {e}")
        results["direct_error"] = str(e)

    # Total valoare contracte
    total_value = 0
    for c in results["contracts"] + results["direct_acquisitions"]:
        val = c.get("value")
        if isinstance(val, (int, float)):
            total_value += val
    results["total_value"] = total_value
    results["total_contracts"] = len(results["contracts"]) + len(results["direct_acquisitions"])

    # Cache save
    if use_cache:
        from backend.services import cache_service
        cache_key = cache_service.make_cache_key("seap_history", cui_clean)
        await cache_service.set(cache_key, results, "seap_history")

    return results
