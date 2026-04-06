"""
OpenRouter Client — F7.6
Unified gateway for 100+ AI models via single OpenAI-compatible endpoint.
Requires OPENROUTER_API_KEY in .env.
Obtain at: https://openrouter.ai/ ($1 free credit on signup)
"""

import logging

from backend.config import settings
from backend.http_client import get_client

logger = logging.getLogger(__name__)

_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Free models available on OpenRouter (no credit needed):
FREE_MODELS = [
    "deepseek/deepseek-r1:free",
    "meta-llama/llama-4-scout:free",
    "qwen/qwen3-235b-a22b:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
]


def is_available() -> bool:
    """True if OpenRouter API key is configured."""
    return bool(getattr(settings, "openrouter_api_key", ""))


async def generate(
    prompt: str,
    *,
    model: str = "deepseek/deepseek-r1:free",
    max_tokens: int = 4000,
    temperature: float = 0.3,
) -> str | None:
    """
    Generate text via OpenRouter gateway (OpenAI-compatible).
    Defaults to free DeepSeek R1 model.
    Returns content string or None on failure.
    """
    api_key = getattr(settings, "openrouter_api_key", "")
    if not api_key:
        logger.debug("[openrouter] OPENROUTER_API_KEY not set — skipping")
        return None

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        client = get_client()
        resp = await client.post(
            _OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "http://localhost:8001",
                "X-Title": "RIS - Roland Intelligence System",
            },
            json=payload,
            timeout=90,
        )
        resp.raise_for_status()
        data = resp.json()

        content = data["choices"][0]["message"]["content"]
        if not content:
            logger.warning(f"[openrouter] Empty response from {model}")
            return None

        logger.debug(f"[openrouter] OK — {len(content.split())} words (model={model})")
        return content

    except Exception as e:
        logger.debug(f"[openrouter:{model}] error: {e}")
        return None
