"""
Rate limiter simplu — per-IP, in-memory, fara dependinte externe.
Limiteaza endpoint-urile POST grele (job creation, batch).
"""

import time
from collections import defaultdict

from fastapi import HTTPException, Request


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
_download_limiter = RateLimiter(requests_per_minute=20)
_read_limiter = RateLimiter(requests_per_minute=60)
_analysis_limiter = RateLimiter(requests_per_minute=30)


def _get_client_ip(request: Request) -> str:
    """Respect X-Forwarded-For header for clients behind proxies."""
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit_jobs(request: Request):
    """Dependency: max 5 job creations per minute per IP."""
    ip = _get_client_ip(request)
    if not _job_limiter.check(ip):
        raise HTTPException(status_code=429, detail="Prea multe cereri. Asteapta 1 minut.")


async def rate_limit_batch(request: Request):
    """Dependency: max 2 batch uploads per minute per IP."""
    ip = _get_client_ip(request)
    if not _batch_limiter.check(ip):
        raise HTTPException(status_code=429, detail="Prea multe cereri batch. Asteapta 1 minut.")


async def rate_limit_downloads(request: Request):
    """Dependency: max 20 file downloads per minute per IP."""
    ip = _get_client_ip(request)
    if not _download_limiter.check(ip):
        raise HTTPException(status_code=429, detail="Prea multe descarcari. Asteapta 1 minut.")


async def rate_limit_read(request: Request):
    """Dependency: max 60 read requests per minute per IP (companies list, search)."""
    ip = _get_client_ip(request)
    if not _read_limiter.check(ip):
        raise HTTPException(status_code=429, detail="Prea multe cereri. Asteapta 1 minut.")


async def rate_limit_analysis(request: Request):
    """Dependency: max 30 analysis requests per minute per IP."""
    ip = _get_client_ip(request)
    if not _analysis_limiter.check(ip):
        raise HTTPException(status_code=429, detail="Prea multe cereri analiza. Asteapta 1 minut.")
