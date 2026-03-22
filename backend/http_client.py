"""
Singleton httpx.AsyncClient cu connection pool.
Refolosit de toate tools/*.py si services/*.py.
Se initializeaza in lifespan (main.py) si se inchide la shutdown.
"""

import httpx

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
