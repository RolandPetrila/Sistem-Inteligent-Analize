"""
DeepSeek R1 Client — F7.2
Financial reasoning specialist with chain-of-thought.
Requires DEEPSEEK_API_KEY in .env.
Obtain at: https://platform.deepseek.com/api_keys
"""

import logging

from backend.config import settings
from backend.http_client import get_client

logger = logging.getLogger(__name__)

_DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
_MODEL_REASONER = "deepseek-reasoner"
_MODEL_CHAT = "deepseek-chat"  # fallback (cheaper, faster)


def is_available() -> bool:
    """True if DeepSeek API key is configured."""
    return bool(getattr(settings, "deepseek_api_key", ""))


async def generate(
    prompt: str,
    *,
    model: str = _MODEL_REASONER,
    max_tokens: int = 4000,
    temperature: float = 0.3,
) -> str | None:
    """
    Generate text via DeepSeek API (OpenAI-compatible).
    Returns content string or None on failure.
    Automatically strips <think>...</think> reasoning block from R1 output.
    """
    api_key = getattr(settings, "deepseek_api_key", "")
    if not api_key:
        logger.debug("[deepseek] DEEPSEEK_API_KEY not set — skipping")
        return None

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }

    try:
        client = get_client()
        resp = await client.post(
            _DEEPSEEK_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=90,
        )
        resp.raise_for_status()
        data = resp.json()

        content = data["choices"][0]["message"]["content"]
        if not content:
            logger.warning("[deepseek] Empty response")
            return None

        # R1 wraps reasoning in <think>...</think> — strip it, keep final answer
        import re
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

        logger.debug(f"[deepseek] OK — {len(content.split())} words (model={model})")
        return content

    except Exception as e:
        err = str(e)
        # Sanitize any key= leakage in error messages
        import re as _re
        err = _re.sub(r"key=[A-Za-z0-9_-]+", "key=***REDACTED***", err)
        logger.warning(f"[deepseek] error: {err}")
        return None
