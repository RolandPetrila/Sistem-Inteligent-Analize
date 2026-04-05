"""
xAI Grok Client — F7.7
Real-time X/Twitter data for company social media mentions.
Requires XAI_API_KEY in .env.
Obtain at: https://console.x.ai/
WARNING: Prompts may be used for xAI training. Use only for public company data.
"""

import logging

from backend.config import settings
from backend.http_client import get_client

logger = logging.getLogger(__name__)

_XAI_URL = "https://api.x.ai/v1/chat/completions"
_MODEL = "grok-3"


def is_available() -> bool:
    """True if xAI API key is configured."""
    return bool(getattr(settings, "xai_api_key", ""))


async def search_company_social(
    company_name: str,
    *,
    days: int = 30,
) -> str | None:
    """
    Search recent X/Twitter mentions about a company via Grok Live Search.
    Returns narrative string or None.
    NOTE: Only use for public company data — prompts may be used for xAI training.
    """
    api_key = getattr(settings, "xai_api_key", "")
    if not api_key:
        logger.debug("[grok] XAI_API_KEY not set — skipping")
        return None

    payload = {
        "model": _MODEL,
        "messages": [
            {
                "role": "user",
                "content": (
                    f"Ce se discuta recent (ultimele {days} zile) pe X (Twitter) despre "
                    f"firma romaneasca '{company_name}'? "
                    f"Cauta stiri, controverse, anunturi, sentimentul pietei. "
                    f"Raspunde in romana cu surse."
                ),
            }
        ],
        "search_parameters": {
            "mode": "on",
            "sources": [{"type": "x"}, {"type": "web"}],
            "return_citations": True,
        },
    }

    try:
        client = get_client()
        resp = await client.post(
            _XAI_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        content = data["choices"][0]["message"]["content"]
        if not content:
            return None

        logger.debug(f"[grok] OK — {len(content)} chars")
        return content

    except Exception as e:
        logger.debug(f"[grok] search failed: {e}")
        return None
