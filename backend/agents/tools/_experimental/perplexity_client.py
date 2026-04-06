"""
Perplexity Sonar Client — F7.4
Real-time web search with cited sources for reputation section.
Requires PERPLEXITY_API_KEY in .env.
Obtain at: https://www.perplexity.ai/settings/api ($5 free credits on signup)
"""

import logging

from backend.config import settings
from backend.http_client import get_client

logger = logging.getLogger(__name__)

_PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
_MODEL_SONAR = "sonar"          # $1/1000 req
_MODEL_SONAR_PRO = "sonar-pro"  # $3/1000 req — deeper research


def is_available() -> bool:
    """True if Perplexity API key is configured."""
    return bool(getattr(settings, "perplexity_api_key", ""))


async def search_company_reputation(
    company_name: str,
    cui: str,
    *,
    model: str = _MODEL_SONAR,
    recency: str = "month",
) -> dict | None:
    """
    Search recent web information about a company with cited sources.
    Returns dict with 'content' (str) and 'citations' (list[str]) or None.
    """
    api_key = getattr(settings, "perplexity_api_key", "")
    if not api_key:
        logger.debug("[perplexity] PERPLEXITY_API_KEY not set — skipping")
        return None

    query = (
        f"Informatii recente despre firma romaneasca {company_name} (CUI {cui}): "
        f"litigii, insolventa, stiri negative sau pozitive, controverse, reputatie online. "
        f"Citeaza sursele. Raspunde in romana."
    )

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Esti un analist de business specializat pe firme romanesti. "
                           "Furnizeaza informatii factuale cu surse. Nu inventa date.",
            },
            {"role": "user", "content": query},
        ],
        "search_recency_filter": recency,
        "return_citations": True,
    }

    try:
        client = get_client()
        resp = await client.post(
            _PERPLEXITY_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        content = data["choices"][0]["message"]["content"]
        citations = data.get("citations", [])

        if not content:
            return None

        logger.debug(f"[perplexity] OK — {len(content)} chars, {len(citations)} citations")
        return {"content": content, "citations": citations, "model": model}

    except Exception as e:
        logger.debug(f"[perplexity] search failed: {e}")
        return None
