"""
BPI Client — Buletinul Procedurilor de Insolventa.
Verifica daca o firma apare in proceduri de insolventa.
Sursa primara: buletinul.ro | Fallback: Tavily search.
"""

from datetime import datetime

from loguru import logger
from backend.http_client import get_client


async def check_insolvency(cui: str) -> dict:
    """EP1: Verifica daca CUI apare in Buletinul Procedurilor de Insolventa."""
    cui_clean = str(cui).strip().replace("RO", "").replace("ro", "")
    checked_at = datetime.utcnow().isoformat()

    # Try direct buletinul.ro search first
    try:
        result = await _check_buletinul_ro(cui_clean)
        if result is not None:
            result["checked_at"] = checked_at
            return result
    except Exception as e:
        logger.debug(f"BPI direct check failed: {e}")

    # Fallback: Tavily search
    try:
        result = await _check_via_tavily(cui_clean)
        result["checked_at"] = checked_at
        return result
    except Exception as e:
        logger.warning(f"BPI Tavily fallback failed: {e}")

    return {
        "found": False,
        "source": "buletinul.ro",
        "error": "Verificare indisponibila",
        "checked_at": checked_at,
    }


async def _check_buletinul_ro(cui: str) -> dict | None:
    """Search buletinul.ro for insolvency records."""
    client = get_client()
    url = f"https://www.buletinul.ro/cautare?q={cui}"

    try:
        resp = await client.get(url, follow_redirects=True, timeout=10)
        if resp.status_code in (403, 429, 503):
            return None  # Site blocks — fall through to Tavily

        text = resp.text.lower()
        keywords = ["insolventa", "faliment", "dizolvare", "lichidare", "reorganizare"]
        found_keywords = [k for k in keywords if k in text]

        if found_keywords:
            status = found_keywords[0].capitalize()
            return {
                "found": True,
                "status": status,
                "details": f"Firma apare in BPI cu procedura: {', '.join(found_keywords)}",
                "source": "buletinul.ro",
            }

        return {
            "found": False,
            "status": None,
            "details": None,
            "source": "buletinul.ro",
        }
    except Exception:
        return None


async def _check_via_tavily(cui: str) -> dict:
    """Fallback: Search Tavily for insolvency info."""
    from backend.services import cache_service

    cache_key = f"bpi_tavily_{cui}"
    cached = await cache_service.get(cache_key)
    if cached:
        return cached

    from backend.agents.tools.tavily_client import search_tavily

    query = f"insolventa {cui} buletinul procedurilor insolventa"
    results = await search_tavily(query, max_results=3)

    found = False
    details = None
    status = None

    if isinstance(results, dict) and results.get("results"):
        for r in results["results"]:
            content = (r.get("content", "") + " " + r.get("title", "")).lower()
            keywords = ["insolventa", "faliment", "dizolvare", "lichidare", "reorganizare"]
            hits = [k for k in keywords if k in content]
            if hits and cui in (r.get("content", "") + r.get("title", "")):
                found = True
                status = hits[0].capitalize()
                details = r.get("content", "")[:200]
                break

    result = {
        "found": found,
        "status": status,
        "details": details,
        "source": "buletinul.ro (via Tavily)",
    }

    await cache_service.set(cache_key, result, "bpi", ttl_hours=24)
    return result
