"""
BPI Client — Buletinul Procedurilor de Insolventa.
Verifica daca o firma apare in proceduri de insolventa.
Sursa primara: buletinul.ro | Fallback: Tavily search.
"""

import re
from datetime import datetime, UTC

from loguru import logger
from backend.http_client import get_client

# BPI-01: Procedural markers — keyword must appear near one of these
# to distinguish real insolvency from company names containing keywords
_PROCEDURAL_MARKERS = [
    "procedura", "debitor", "publicat", "sedinta", "judecator",
    "tribunal", "sentinta", "cerere", "hotarare", "termen",
    "administrator judiciar", "lichidator judiciar", "creditor",
    "legea 85", "legii 85", "radiat", "dosar",
]

_INSOLVENCY_KEYWORDS = ["insolventa", "faliment", "dizolvare", "lichidare", "reorganizare"]


def _normalize_cui(cui: str) -> str:
    """BPI-03: Normalize CUI — strip RO prefix, whitespace, leading zeros."""
    return re.sub(r"^[Rr][Oo]\s*", "", str(cui).strip())


def _keyword_has_procedural_context(keyword: str, context: str) -> bool:
    """BPI-01: Check if keyword appears in procedural context, not just company name."""
    kw_pos = context.find(keyword)
    if kw_pos == -1:
        return False
    # Look for procedural markers within 200 chars of keyword
    kw_start = max(0, kw_pos - 200)
    kw_end = min(len(context), kw_pos + len(keyword) + 200)
    kw_context = context[kw_start:kw_end]
    return any(marker in kw_context for marker in _PROCEDURAL_MARKERS)


async def check_insolvency(cui: str) -> dict:
    """EP1: Verifica daca CUI apare in Buletinul Procedurilor de Insolventa."""
    cui_clean = _normalize_cui(cui)
    checked_at = datetime.now(UTC).isoformat()

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

        cui_pos = text.find(cui)
        if cui_pos == -1:
            return {
                "found": False,
                "status": None,
                "details": None,
                "source": "buletinul.ro",
            }

        # Extract context window around CUI
        ctx_start = max(0, cui_pos - 500)
        ctx_end = min(len(text), cui_pos + 500)
        context = text[ctx_start:ctx_end]

        # BPI-01: Require procedural context, not just keyword presence
        confirmed_keywords = [
            k for k in _INSOLVENCY_KEYWORDS
            if k in context and _keyword_has_procedural_context(k, context)
        ]

        if confirmed_keywords:
            status = confirmed_keywords[0].capitalize()
            return {
                "found": True,
                "status": status,
                "details": f"Firma apare in BPI cu procedura: {', '.join(confirmed_keywords)}",
                "source": "buletinul.ro",
            }

        return {
            "found": False,
            "status": None,
            "details": None,
            "source": "buletinul.ro",
        }
    except Exception as e:
        # BPI-04: Log instead of silent pass
        logger.debug(f"BPI buletinul.ro error: {e}")
        return None


async def _check_via_tavily(cui: str) -> dict:
    """Fallback: Search Tavily for insolvency info."""
    from backend.services import cache_service

    cache_key = f"bpi_tavily_{cui}"
    cached = await cache_service.get(cache_key)
    if cached:
        return cached

    from backend.agents.tools.tavily_client import search as tavily_search

    # BPI-03: Use normalized CUI in query
    query = f"insolventa {cui} buletinul procedurilor insolventa"
    results = await tavily_search(query, max_results=3)

    found = False
    details = None
    status = None

    if isinstance(results, dict) and results.get("results"):
        for r in results["results"]:
            content = (r.get("content", "") + " " + r.get("title", "")).lower()
            hits = [k for k in _INSOLVENCY_KEYWORDS if k in content]
            # BPI-02: Case-insensitive CUI match (strip RO prefix from content too)
            raw_content = r.get("content", "") + " " + r.get("title", "")
            content_cui_normalized = re.sub(r"[Rr][Oo]\s*", "", raw_content)
            if hits and cui in content_cui_normalized:
                # BPI-01: Also require procedural context in Tavily results
                if any(_keyword_has_procedural_context(k, content) for k in hits):
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
