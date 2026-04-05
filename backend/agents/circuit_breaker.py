"""
Circuit Breaker — Provider health tracking.
R2: Tracks provider failures and skips providers that fail 3+ times in 30 minutes.
Separated from orchestrator.py to avoid circular imports with agent_synthesis.py.
"""
from collections import defaultdict
import time

from loguru import logger

_provider_failures: dict[str, list[float]] = defaultdict(list)
_CIRCUIT_BREAKER_THRESHOLD = 3
_CIRCUIT_BREAKER_WINDOW = 1800  # 30 min


def is_provider_circuit_open(provider_name: str) -> bool:
    """Check if provider should be skipped due to repeated failures."""
    failures = _provider_failures[provider_name]
    now = time.time()
    _provider_failures[provider_name] = [f for f in failures if now - f < _CIRCUIT_BREAKER_WINDOW]
    return len(_provider_failures[provider_name]) >= _CIRCUIT_BREAKER_THRESHOLD


def record_provider_failure(provider_name: str):
    """Record a provider failure for circuit breaker tracking."""
    _provider_failures[provider_name].append(time.time())
    count = len(_provider_failures[provider_name])
    logger.warning(f"[circuit-breaker] {provider_name} failure recorded ({count}/{_CIRCUIT_BREAKER_THRESHOLD} in window)")


def reset_provider_circuit(provider_name: str):
    """Reset circuit breaker on successful provider call."""
    if provider_name in _provider_failures:
        _provider_failures[provider_name].clear()
