"""
Singleton httpx.AsyncClient cu connection pool.
Refolosit de toate tools/*.py si services/*.py.
Se initializeaza in lifespan (main.py) si se inchide la shutdown.
"""

import httpx
import ipaddress
from urllib.parse import urlparse


_BLOCKED_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
]


def _validate_url_not_ssrf(url: str) -> None:
    """Block requests to private/internal IPs (SSRF prevention)."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return
        ip = ipaddress.ip_address(hostname)
        if any(ip in net for net in _BLOCKED_RANGES):
            raise ValueError(f"SSRF blocked: request to private IP {ip}")
    except ValueError as e:
        if "SSRF blocked" in str(e):
            raise
        # hostname is a domain name, not an IP — OK

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    """Returneaza clientul HTTP singleton. Creeaza lazy daca nu exista."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            follow_redirects=True,
        )
    return _client


async def startup():
    """Initializeaza clientul la startup server."""
    global _client
    _client = httpx.AsyncClient(
        timeout=httpx.Timeout(30.0, connect=10.0),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        follow_redirects=True,
    )


async def shutdown():
    """Inchide clientul la shutdown server."""
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


def get_pool_metrics() -> dict:
    """10F M10.3: HTTP Pool Metrics — expose connection pool stats."""
    if _client is None or _client.is_closed:
        return {"status": "closed", "active": 0, "idle": 0}
    pool = _client._transport._pool
    return {
        "status": "open",
        "max_connections": 20,
        "max_keepalive": 10,
        "pool_type": type(pool).__name__,
    }
