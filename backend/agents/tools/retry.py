"""
Shared retry utility for external API clients.
Exponential backoff with configurable retries.
"""

import asyncio
from typing import Callable, TypeVar

from loguru import logger

T = TypeVar("T")

DEFAULT_RETRIES = 2
DEFAULT_BACKOFF = [2, 5]  # seconds between retries


async def with_retry(
    fn: Callable,
    *args,
    retries: int = DEFAULT_RETRIES,
    backoff: list[int] | None = None,
    source_name: str = "API",
    **kwargs,
) -> T:
    """
    Executa fn cu retry si exponential backoff.
    Returneaza rezultatul sau raise ultima exceptie.
    """
    if backoff is None:
        backoff = DEFAULT_BACKOFF

    last_error = None
    for attempt in range(retries + 1):
        try:
            return await fn(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < retries:
                delay = backoff[min(attempt, len(backoff) - 1)]
                logger.warning(
                    f"[retry] {source_name} attempt {attempt + 1}/{retries + 1} failed: {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"[retry] {source_name} all {retries + 1} attempts failed: {e}")

    raise last_error
