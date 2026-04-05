"""
Jina Reader Client — F7.1
Fetches URLs and returns clean Markdown content (no HTML boilerplate).
No API key required for public usage; set JINA_API_KEY for 1M tokens/day.
"""

import logging

from backend.config import settings
from backend.http_client import get_client

logger = logging.getLogger(__name__)

JINA_BASE = "https://r.jina.ai/"
_MAX_CONTENT_CHARS = 4000  # Trim to prevent oversized prompts


async def fetch_clean_content(url: str, timeout: int = 15) -> str | None:
    """
    Fetch a URL via Jina Reader and return clean Markdown text.
    Falls back to None on any error — caller uses raw Tavily content instead.
    """
    if not url or not url.startswith(("http://", "https://")):
        return None
    try:
        headers = {
            "Accept": "text/markdown",
            "X-With-Links-Summary": "false",
            "X-With-Images-Summary": "false",
        }
        jina_key = getattr(settings, "jina_api_key", "")
        if jina_key:
            headers["Authorization"] = f"Bearer {jina_key}"

        client = get_client()
        resp = await client.get(
            f"{JINA_BASE}{url}",
            headers=headers,
            timeout=timeout,
        )
        resp.raise_for_status()
        text = resp.text.strip()
        if not text or len(text) < 100:
            return None
        return text[:_MAX_CONTENT_CHARS]
    except Exception as e:
        logger.debug(f"[jina] fetch failed for {url}: {e}")
        return None


async def enrich_tavily_results(results: list[dict], max_urls: int = 3) -> list[dict]:
    """
    Replace raw content in Tavily results with clean Markdown from Jina Reader.
    Only processes the first `max_urls` results to limit latency.
    Returns enriched list (mutates content in-place on success).
    """
    import asyncio

    enriched = list(results)
    targets = [r for r in enriched if r.get("url") and r.get("score", 0) > 0.3][:max_urls]

    async def _enrich_one(result: dict) -> None:
        clean = await fetch_clean_content(result["url"])
        if clean:
            result["content_original"] = result.get("content", "")
            result["content"] = clean
            result["content_source"] = "jina_reader"
            logger.debug(f"[jina] enriched {result['url'][:60]} — {len(clean)} chars")

    await asyncio.gather(*[_enrich_one(r) for r in targets], return_exceptions=True)
    return enriched
