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


def _cpv_code8(raw: str) -> str:
    """Extrage codul CPV de 8 cifre dintr-un sir gen '09123000-7 - Gaze naturale' sau '09123000-7'."""
    head = str(raw or "").split(" - ", 1)[0].split("-")[0]
    digits = "".join(c for c in head if c.isdigit())
    return digits[:8] if len(digits) >= 8 else ""


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
            # Referer OBLIGATORIU la api-pub SICAP — fara el da HTTP 403 (bug istoric: lipsea)
            return await c.post(SEAP_NOTICES_URL, json=payload, headers=_SICAP_HEADERS)

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
                        "cpv": _cpv_code8(item.get("cpvCodeAndName") or item.get("cpvCode") or ""),
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
            return await c.post(SEAP_DIRECT_URL, json=da_payload, headers=_SICAP_HEADERS)

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
                        "cpv": _cpv_code8(item.get("cpvCode") or item.get("cpvCodeAndName") or ""),
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

    # Angle A v2: CPV-uri reale castigate (competente dovedite) — matching precis al oportunitatilor
    won_cpv: list[str] = []
    _seen_cpv: set[str] = set()
    for c in results["contracts"] + results["direct_acquisitions"]:
        code = c.get("cpv", "")
        if code and code not in _seen_cpv:
            _seen_cpv.add(code)
            won_cpv.append(code)
    results["won_cpv_codes"] = won_cpv

    # Cache save
    if use_cache:
        from backend.services import cache_service
        cache_key = cache_service.make_cache_key("seap_history", cui_clean)
        await cache_service.set(cache_key, results, "seap_history")

    return results


async def _fetch_recent_open_notices(days_back: int, max_pages: int, use_cache: bool = True) -> list[dict]:
    """Descarca proceduri deschise SICAP (nefiltrate). Cache 6h per-fereastra, partajat intre firme."""
    if use_cache:
        from backend.services import cache_service
        ck = cache_service.make_cache_key("seap_cnotice_raw", str(days_back))
        cached = await cache_service.get(ck)
        if isinstance(cached, dict):
            return cached.get("notices", [])

    from datetime import UTC, datetime, timedelta
    start = (datetime.now(UTC) - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00.000Z")

    notices: list[dict] = []
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

        try:
            resp = await with_retry(_fetch, retries=1, backoff=[3], source_name="SEAP open tenders")
        except Exception as e:
            # Esec de pagina (rate-limit tranzitoriu) -> pastram ce am colectat deja, nu aruncam
            logger.warning(f"[seap] pagina {page} CNoticeList esuata: {e} — pastrez {len(notices)} rezultate")
            break
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
            notices.append({
                "title": it.get("contractTitle", ""),
                "authority": it.get("contractingAuthorityNameAndFN", ""),
                "cpv": cca.split(" - ", 1)[0].strip() if cca else "",
                "cpv_name": cca.split(" - ", 1)[1].strip() if " - " in cca else "",
                "value": it.get("estimatedValueRon"),
                "deadline": it.get("maxTenderReceiptDeadline") or it.get("minTenderReceiptDeadline") or "",
                "notice_no": it.get("noticeNo", ""),
                "procedure_id": it.get("procedureId"),
            })
        if page < max_pages - 1:
            await asyncio.sleep(REQUEST_DELAY)  # politicos intre pagini

    if use_cache and notices:
        from backend.services import cache_service
        ck = cache_service.make_cache_key("seap_cnotice_raw", str(days_back))
        await cache_service.set(ck, {"notices": notices}, "seap_cnotice_raw")
    return notices


async def search_open_tenders(
    caen_code: str,
    won_cpv_codes: list[str] | None = None,
    days_back: int = 30,
    max_pages: int = 2,
    max_results: int = 15,
    use_cache: bool = True,
) -> dict:
    """
    Angle A: licitatii/proceduri DESCHISE relevante pt firma.

    v2 — matching pe DOUA niveluri:
      - CPV-uri REALE castigate de firma (`won_cpv_codes`, din istoricul SEAP) = competente dovedite;
      - fallback pe maparea ORIENTATIVA CAEN->CPV la nivel de diviziune.
    Diviziunile reale + CAEN definesc setul de filtrare; clasa CPV (4 cifre) reala marcheaza
    oportunitatile `precise` (competenta dovedita), afisate primele.

    Descarcarea SICAP e cache-uita per-fereastra (6h) si partajata; filtrarea e locala/per-firma.
    Rezilient: {available: False} la eroare.
    """
    from backend.agents.tools.caen_cpv_map import caen_to_cpv_prefixes

    caen_prefixes = set(caen_to_cpv_prefixes(caen_code))
    real_divisions: set[str] = set()
    real_classes: set[str] = set()
    for raw in (won_cpv_codes or []):
        code = _cpv_code8(raw)
        if code:
            real_divisions.add(code[:2])
            real_classes.add(code[:4])

    filter_prefixes = real_divisions | caen_prefixes
    if not filter_prefixes:
        return {"available": False, "reason": "CAEN necunoscut si fara istoric CPV", "caen_code": str(caen_code)}

    try:
        notices = await _fetch_recent_open_notices(days_back, max_pages, use_cache)
    except Exception as e:
        logger.warning(f"[seap] search_open_tenders esuat: {e}")
        return {"available": False, "error": str(e), "caen_code": str(caen_code)}

    matched: list[dict] = []
    seen: set = set()
    for it in notices:
        code8 = _cpv_code8(it.get("cpv", ""))
        div = code8[:2]
        if not div or div not in filter_prefixes:
            continue
        k = it.get("notice_no") or (it.get("title"), it.get("authority"))
        if k in seen:
            continue
        seen.add(k)
        matched.append({**it, "precise": bool(code8[:4] and code8[:4] in real_classes)})

    matched.sort(key=lambda m: not m.get("precise"))  # competente dovedite primele
    matched = matched[:max_results]

    return {
        "available": True,
        "source": "SICAP",
        "source_url": "https://e-licitatie.ro",
        "caen_code": str(caen_code),
        "cpv_prefixes": sorted(filter_prefixes),
        "basis": "istoric_real" if real_divisions else "caen_orientativ",
        "days_back": days_back,
        "count": len(matched),
        "opportunities": matched,
        "note": ("Pe baza CPV-urilor reale castigate + sector" if real_divisions
                 else "Orientativ — mapare CAEN->CPV la nivel de diviziune"),
    }
