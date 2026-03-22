"""
Rate limiter simplu — per-IP, in-memory, fara dependinte externe.
Limiteaza endpoint-urile POST grele (job creation, batch).
"""

import time
from collections import defaultdict

from fastapi import Request, HTTPException


class RateLimiter:
    """Token bucket rate limiter per IP."""

    def __init__(self, requests_per_minute: int = 10):
        self.rpm = requests_per_minute
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _cleanup(self, ip: str, now: float):
        cutoff = now - 60
        self._requests[ip] = [t for t in self._requests[ip] if t > cutoff]

    def check(self, ip: str) -> bool:
        now = time.time()
        self._cleanup(ip, now)
        if len(self._requests[ip]) >= self.rpm:
            return False
        self._requests[ip].append(now)
        return True


# Rate limiters per use-case
_job_limiter = RateLimiter(requests_per_minute=5)
_batch_limiter = RateLimiter(requests_per_minute=2)


async def rate_limit_jobs(request: Request):
    """Dependency: max 5 job creations per minute per IP."""
    ip = request.client.host if request.client else "unknown"
    if not _job_limiter.check(ip):
        raise HTTPException(status_code=429, detail="Prea multe cereri. Asteapta 1 minut.")


async def rate_limit_batch(request: Request):
    """Dependency: max 2 batch uploads per minute per IP."""
    ip = request.client.host if request.client else "unknown"
    if not _batch_limiter.check(ip):
        raise HTTPException(status_code=429, detail="Prea multe cereri batch. Asteapta 1 minut.")
