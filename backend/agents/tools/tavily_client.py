"""
Tavily API wrapper cu quota tracking.
1000 requests/luna gratuit.
Avertizare la 80% consum.
"""

from datetime import datetime, date

from loguru import logger
from backend.http_client import get_client

from backend.config import settings
from backend.database import db


TAVILY_SEARCH_URL = "https://api.tavily.com/search"


async def _get_monthly_usage() -> int:
    """Returneaza numarul de query-uri Tavily din luna curenta."""
    row = await db.fetch_one(
        "SELECT COUNT(*) as c FROM data_cache "
        "WHERE source = 'tavily' AND cached_at >= date('now', 'start of month')"
    )
    return row["c"] if row else 0


async def _check_quota() -> tuple[bool, int]:
    """Verifica daca mai avem quota. Returneaza (ok, usage)."""
    usage = await _get_monthly_usage()
    if usage >= settings.tavily_monthly_quota:
        logger.warning(f"Tavily quota DEPASITA: {usage}/{settings.tavily_monthly_quota}")
        return False, usage
    if usage >= settings.tavily_warn_at:
        logger.warning(f"Tavily quota ATENTIE: {usage}/{settings.tavily_monthly_quota}")
    return True, usage


async def _log_usage(query: str, cache_key: str, data: dict):
    """D17 fix: Salveaza query-ul prin cache_service (LRU + stats + schema_version)."""
    from backend.services import cache_service
    await cache_service.set(cache_key, data, "tavily", ttl_hours=6)


async def search(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
) -> dict:
    """
    Cauta pe web prin Tavily API.
    Returneaza dict cu results, answer si query.
    """
    if not settings.tavily_api_key:
        return {
            "error": "TAVILY_API_KEY nu este configurat",
            "results": [],
            "query": query,
        }

    ok, usage = await _check_quota()
    if not ok:
        return {
            "error": f"Quota Tavily depasita ({usage}/{settings.tavily_monthly_quota})",
            "results": [],
            "query": query,
        }

    payload = {
        "api_key": settings.tavily_api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": search_depth,
        "include_answer": True,
    }
    if include_domains:
        payload["include_domains"] = include_domains
    if exclude_domains:
        payload["exclude_domains"] = exclude_domains

    client = get_client()
    logger.debug(f"Tavily search: {query[:80]}...")
    response = await client.post(TAVILY_SEARCH_URL, json=payload)
    response.raise_for_status()
    data = response.json()

    results = []
    for r in data.get("results", []):
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", ""),
            "score": r.get("score", 0),
        })

    output = {
        "query": query,
        "answer": data.get("answer", ""),
        "results": results,
        "result_count": len(results),
        "source": "Tavily",
    }

    # Log usage
    import hashlib
    cache_key = f"tavily_{hashlib.md5(query.encode()).hexdigest()}"
    await _log_usage(query, cache_key, output)

    logger.debug(f"Tavily: {len(results)} results for '{query[:50]}'")
    return output


async def search_site(query: str, site: str, max_results: int = 5) -> dict:
    """Cauta pe un site specific folosind Tavily."""
    return await search(
        query=f"site:{site} {query}",
        max_results=max_results,
        include_domains=[site],
    )


async def search_company_info(
    company_name: str,
    cui: str | None = None,
    info_type: str = "general",
) -> dict:
    """
    Cauta informatii despre o companie.
    info_type: general, financial, litigation, news, jobs
    """
    queries = {
        "general": f'"{company_name}" firma Romania',
        "financial": f'"{company_name}" cifra afaceri profit angajati',
        "litigation": f'site:portal.just.ro "{company_name}"' if company_name else f'site:portal.just.ro "{cui}"',
        "insolvency": f'site:bpi.ro "{cui or company_name}"',
        "news": f'"{company_name}" Romania',
        "jobs": f'"{company_name}" angajare job Romania',
    }

    query = queries.get(info_type, queries["general"])
    if cui and info_type == "general":
        query = f'"{company_name}" CUI {cui} Romania'

    # Domenii prioritare per tip
    domain_filters = {
        "financial": ["listafirme.ro", "topfirme.com", "risco.ro"],
        "litigation": ["portal.just.ro"],
        "insolvency": ["bpi.ro"],
        "news": ["economica.net", "ziare.com", "digi24.ro", "hotnews.ro"],
        "jobs": ["ejobs.ro", "bestjobs.ro", "hipo.ro"],
    }

    include = domain_filters.get(info_type)
    return await search(
        query=query,
        max_results=5,
        include_domains=include,
    )


async def get_quota_status() -> dict:
    """Returneaza statusul curent al cotei Tavily."""
    usage = await _get_monthly_usage()
    return {
        "used": usage,
        "quota": settings.tavily_monthly_quota,
        "remaining": max(0, settings.tavily_monthly_quota - usage),
        "warn_at": settings.tavily_warn_at,
        "percent_used": round(usage / settings.tavily_monthly_quota * 100, 1),
    }
