"""
Brave Search Client — F7.4 (inlocuieste Perplexity)
Web search cu index propriu (non-Google/Bing) pentru sectiunea de reputatie.
2000 req/luna GRATUIT, fara card de credit.
Obtine key la: https://api.search.brave.com/register
"""

import logging

from backend.config import settings
from backend.http_client import get_client

logger = logging.getLogger(__name__)

_BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"
_MAX_RESULTS = 5


def is_available() -> bool:
    """True if Brave Search API key is configured."""
    return bool(getattr(settings, "brave_api_key", ""))


async def search_company_reputation(
    company_name: str,
    cui: str,
    *,
    freshness: str = "pm",  # pm = past month, py = past year, pw = past week
) -> dict | None:
    """
    Cauta informatii recente despre o firma via Brave Search.
    Returneaza dict cu 'results' (list) si 'summary' (str) sau None.
    Brave are index propriu — ofera rezultate diferite de Tavily (Google-based).
    """
    api_key = getattr(settings, "brave_api_key", "")
    if not api_key:
        logger.debug("[brave] BRAVE_API_KEY not set — skipping")
        return None

    # Doua query-uri: reputatie generala + stiri negative/litigii
    queries = [
        f'"{company_name}" litigii insolventa stiri',
        f'"{company_name}" CUI {cui} reputatie',
    ]

    all_results = []
    for query in queries:
        try:
            client = get_client()
            resp = await client.get(
                _BRAVE_URL,
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": api_key,
                },
                params={
                    "q": query,
                    "count": _MAX_RESULTS,
                    "freshness": freshness,
                    "search_lang": "ro",
                    "country": "RO",
                    "text_decorations": False,
                    "spellcheck": False,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            web_results = data.get("web", {}).get("results", [])
            for r in web_results:
                all_results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "description": r.get("description", ""),
                    "age": r.get("age", ""),
                })

        except Exception as e:
            logger.debug(f"[brave] query failed: {e}")

    if not all_results:
        return None

    # Deduplica dupa URL
    seen = set()
    unique = []
    for r in all_results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)

    # Construieste un sumar text pentru agent_synthesis
    summary_lines = []
    for r in unique[:_MAX_RESULTS]:
        line = f"- [{r['title']}]({r['url']})"
        if r.get("description"):
            line += f": {r['description'][:150]}"
        if r.get("age"):
            line += f" ({r['age']})"
        summary_lines.append(line)

    summary = "\n".join(summary_lines)

    logger.debug(f"[brave] OK — {len(unique)} rezultate pentru {company_name}")
    return {
        "results": unique,
        "summary": summary,
        "source": "brave_search",
        "queries": queries,
    }
