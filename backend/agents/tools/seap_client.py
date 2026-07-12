"""
Client SEAP (e-licitatie.ro) — Licitatii si achizitii directe per CUI.
API public, rate limit strict — delay 3s intre request-uri.
"""

import asyncio

from loguru import logger

from backend.agents.tools.retry import with_retry
from backend.http_client import get_client

SEAP_NOTICES_URL = "https://e-licitatie.ro/api-pub/NoticeCommon/GetCANoticeList/"
SEAP_DIRECT_URL = "https://e-licitatie.ro/api-pub/DirectAcquisitionCommon/GetDirectAcquisitionList/"
# Angle A: proceduri DESCHISE (oportunitati). api-pub cere Referer OBLIGATORIU, altfel respinge.
SEAP_CNOTICE_URL = "https://e-licitatie.ro/api-pub/NoticeCommon/GetCNoticeList/"
_SICAP_HEADERS = {"Content-Type": "application/json", "Referer": "https://e-licitatie.ro"}
OPEN_NOTICE_TYPE_IDS = [2, 17]  # CN (anunt de participare) + SCN (simplificat) = proceduri deschise
REQUEST_DELAY = 3


async def get_contracts_won(cui: str, page_size: int = 20, use_cache: bool = True, eur_ron_rate: float | None = None) -> dict:
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

    # B4 fix: Sum contract values with RON conversion
    # D1 fix: Use BNR rate if provided, fallback 4.97 (closer to real rate)
    total_value_ron = 0
    eur_rate = eur_ron_rate or 4.97
    for c in results["contracts"] + results["direct_acquisitions"]:
        val = c.get("value")
        if isinstance(val, (int, float)):
            currency = str(c.get("currency", "RON")).upper()
            if currency == "EUR":
                total_value_ron += val * eur_rate
            else:
                total_value_ron += val
    results["total_value"] = round(total_value_ron)
    results["total_value_currency"] = "RON"
    results["total_contracts"] = len(results["contracts"]) + len(results["direct_acquisitions"])

    # Cache save
    if use_cache:
        from backend.services import cache_service
        cache_key = cache_service.make_cache_key("seap_history", cui_clean)
        await cache_service.set(cache_key, results, "seap_history")

    return results


async def search_open_tenders(
    caen_code: str,
    days_back: int = 30,
    max_pages: int = 2,
    max_results: int = 15,
    use_cache: bool = True,
) -> dict:
    """
    Angle A: licitatii/proceduri DESCHISE relevante pt sectorul firmei.

    Interogheaza SICAP GetCNoticeList (proceduri deschise, ultimele `days_back` zile), apoi
    filtreaza LOCAL pe prefix CPV (diviziune) obtinut din maparea ORIENTATIVA CAEN->CPV.
    Cache pe setul de prefixe CPV (firme din acelasi sector reutilizeaza). Rezilient: {available: False} la eroare.
    """
    from backend.agents.tools.caen_cpv_map import caen_to_cpv_prefixes

    prefixes = set(caen_to_cpv_prefixes(caen_code))
    if not prefixes:
        return {"available": False, "reason": "CAEN necunoscut in maparea CPV", "caen_code": str(caen_code)}

    cache_id = "".join(sorted(prefixes)) + f"_{days_back}"
    if use_cache:
        from backend.services import cache_service
        cache_key = cache_service.make_cache_key("seap_open_tenders", cache_id)
        cached = await cache_service.get(cache_key)
        if cached is not None:
            logger.debug(f"SEAP open tenders: cache hit pentru CAEN {caen_code}")
            return cached

    from datetime import UTC, datetime, timedelta
    start = (datetime.now(UTC) - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00.000Z")

    matched: list[dict] = []
    try:
        for page in range(max_pages):
            body = {
                "sysNoticeTypeIds": OPEN_NOTICE_TYPE_IDS, "sortProperties": [],
                "pageSize": 100, "pageIndex": page, "hasUnansweredQuestions": False,
                "startTenderReceiptDeadline": None, "sysProcedureStateId": None,
                "sysProcedurePhaseId": None, "startPublicationDate": start, "endPublicationDate": None,
            }

            async def _fetch(b=body):
                c = get_client()
                return await c.post(SEAP_CNOTICE_URL, json=b, headers=_SICAP_HEADERS)

            resp = await with_retry(_fetch, retries=1, backoff=[3], source_name="SEAP open tenders")
            if resp.status_code != 200:
                logger.warning(f"SEAP CNoticeList HTTP {resp.status_code}")
                break
            data = resp.json()
            items = data.get("items") or (data.get("searchResult") or {}).get("items") or []
            if not items:
                break
            for it in items:
                if not isinstance(it, dict):
                    continue
                cca = str(it.get("cpvCodeAndName") or "")
                cpv = cca.split(" - ", 1)[0].strip() if cca else ""
                cpv_div = "".join(c for c in cpv if c.isdigit())[:2]
                if not cpv_div or cpv_div not in prefixes:
                    continue
                matched.append({
                    "title": it.get("contractTitle", ""),
                    "authority": it.get("contractingAuthorityNameAndFN", ""),
                    "cpv": cpv,
                    "cpv_name": cca.split(" - ", 1)[1].strip() if " - " in cca else "",
                    "value": it.get("estimatedValueRon"),
                    "deadline": it.get("maxTenderReceiptDeadline") or it.get("minTenderReceiptDeadline") or "",
                    "notice_no": it.get("noticeNo", ""),
                    "procedure_id": it.get("procedureId"),
                })
            if page < max_pages - 1:
                await asyncio.sleep(REQUEST_DELAY)  # politicos intre pagini
    except Exception as e:
        logger.warning(f"[seap] search_open_tenders esuat: {e}")
        return {"available": False, "error": str(e), "caen_code": str(caen_code)}

    # dedup pe notice_no + plafon
    seen: set = set()
    uniq: list[dict] = []
    for m in matched:
        k = m["notice_no"] or (m["title"], m["authority"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(m)
    uniq = uniq[:max_results]

    result = {
        "available": True,
        "source": "SICAP",
        "source_url": "https://e-licitatie.ro",
        "caen_code": str(caen_code),
        "cpv_prefixes": sorted(prefixes),
        "days_back": days_back,
        "count": len(uniq),
        "opportunities": uniq,
        "note": "Orientativ — filtrare pe mapare CAEN->CPV la nivel de diviziune",
    }
    if use_cache:
        from backend.services import cache_service
        cache_key = cache_service.make_cache_key("seap_open_tenders", cache_id)
        await cache_service.set(cache_key, result, "seap_open_tenders")
    return result
