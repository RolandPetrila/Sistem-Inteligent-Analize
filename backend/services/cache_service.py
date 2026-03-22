"""
Cache service cu TTL per tip sursa.
Foloseste tabelul data_cache din SQLite.
9A: Hit/miss tracking per source.
"""

import json
import hashlib
from datetime import datetime

from loguru import logger
from backend.database import db


# 10A M10.2: Cache schema version — increment to auto-invalidate stale entries
CACHE_SCHEMA_VERSION = 1

# 10F M10.1: LRU eviction — maximum cache size in MB
MAX_CACHE_SIZE_MB = 100

# 9A: Hit/miss counters per source (in-memory, reset at restart)
_hit_miss: dict[str, dict[str, int]] = {}


def _track(source: str, hit: bool):
    """Track cache hit/miss per source."""
    if source not in _hit_miss:
        _hit_miss[source] = {"hits": 0, "misses": 0}
    _hit_miss[source]["hits" if hit else "misses"] += 1


# TTL in ore per tip sursa
TTL_HOURS = {
    "anaf": 12,
    "onrc": 168,       # 7 zile
    "seap_active": 2,
    "seap_history": 720,  # 30 zile
    "tavily": 6,
    "playwright": 12,
    "bnr": 24,
    "ins": 720,         # 30 zile
    "funds": 24,
}


def make_cache_key(source: str, identifier: str) -> str:
    """Genereaza un cache key unic."""
    h = hashlib.md5(identifier.encode()).hexdigest()[:12]
    return f"{source}_{h}"


async def get(key: str) -> dict | None:
    """Returneaza date din cache daca nu au expirat si au versiune curenta."""
    row = await db.fetch_one(
        "SELECT data, schema_version FROM data_cache "
        "WHERE cache_key = ? AND expires_at > datetime('now')",
        (key,),
    )
    if row and row["data"]:
        # 10A M10.2: Check schema version — auto-invalidate stale entries
        version = row.get("schema_version") or 0
        if version < CACHE_SCHEMA_VERSION:
            logger.debug(f"Cache STALE (v{version} < v{CACHE_SCHEMA_VERSION}): {key}")
            await db.execute("DELETE FROM data_cache WHERE cache_key = ?", (key,))
            return None
        try:
            data = json.loads(row["data"])
            logger.debug(f"Cache HIT: {key}")
            return data
        except (json.JSONDecodeError, TypeError):
            return None
    return None


async def set(key: str, data: dict, source: str, ttl_hours: int | None = None):
    """Salveaza date in cache cu TTL."""
    if ttl_hours is None:
        ttl_hours = TTL_HOURS.get(source, 6)

    await db.execute(
        "INSERT OR REPLACE INTO data_cache (cache_key, data, source, cached_at, expires_at, schema_version) "
        "VALUES (?, ?, ?, datetime('now'), datetime('now', ? || ' hours'), ?)",
        (key, json.dumps(data, ensure_ascii=False), source, str(ttl_hours), CACHE_SCHEMA_VERSION),
    )
    logger.debug(f"Cache SET: {key} (TTL: {ttl_hours}h)")
    # 10F M10.1: LRU eviction after insert
    await _enforce_size_limit()


async def _enforce_size_limit():
    """10F M10.1: LRU eviction — keep cache under MAX_CACHE_SIZE_MB."""
    size = await db.fetch_one("SELECT SUM(LENGTH(data)) as bytes FROM data_cache")
    total_bytes = size["bytes"] or 0
    max_bytes = MAX_CACHE_SIZE_MB * 1024 * 1024
    if total_bytes <= max_bytes:
        return
    # Delete oldest entries until under limit
    excess = total_bytes - max_bytes
    deleted = 0
    rows = await db.fetch_all(
        "SELECT cache_key, LENGTH(data) as size FROM data_cache ORDER BY cached_at ASC LIMIT 100"
    )
    for row in rows:
        if deleted >= excess:
            break
        await db.execute("DELETE FROM data_cache WHERE cache_key = ?", (row["cache_key"],))
        deleted += row["size"]
    logger.info(f"Cache LRU: evicted {deleted} bytes to stay under {MAX_CACHE_SIZE_MB}MB")


async def invalidate(pattern: str):
    """Invalideaza toate cheile care incep cu pattern."""
    await db.execute(
        "DELETE FROM data_cache WHERE cache_key LIKE ?",
        (f"{pattern}%",),
    )
    logger.debug(f"Cache INVALIDATED: {pattern}*")


async def cleanup_expired() -> int:
    """Sterge toate intrarile expirate. Returneaza numarul sters."""
    cursor = await db.execute(
        "DELETE FROM data_cache WHERE expires_at <= datetime('now')"
    )
    count = cursor.rowcount if hasattr(cursor, 'rowcount') else 0
    logger.debug(f"Cache: cleaned {count} expired entries")
    return count


async def get_stats() -> dict:
    """Statistici cache — total entries, per sursa, dimensiune estimata."""
    total = await db.fetch_one("SELECT COUNT(*) as c FROM data_cache")
    by_source = await db.fetch_all(
        "SELECT source, COUNT(*) as c FROM data_cache GROUP BY source ORDER BY c DESC"
    )
    expired = await db.fetch_one(
        "SELECT COUNT(*) as c FROM data_cache WHERE expires_at <= datetime('now')"
    )
    size = await db.fetch_one(
        "SELECT SUM(LENGTH(data)) as bytes FROM data_cache"
    )
    size_mb = round((size["bytes"] or 0) / (1024 * 1024), 2)
    # 9A: Hit/miss rates
    hit_miss_rates = {}
    for src, counts in _hit_miss.items():
        total_req = counts["hits"] + counts["misses"]
        hit_rate = round(counts["hits"] / total_req * 100, 1) if total_req > 0 else 0
        hit_miss_rates[src] = {"hits": counts["hits"], "misses": counts["misses"], "hit_rate_pct": hit_rate}

    return {
        "total_entries": total["c"] if total else 0,
        "expired_pending": expired["c"] if expired else 0,
        "size_mb": size_mb,
        "by_source": {r["source"]: r["c"] for r in by_source},
        "hit_miss": hit_miss_rates,
    }


async def get_or_fetch(
    key: str,
    source: str,
    fetch_coro,
    ttl_hours: int | None = None,
    force_refresh: bool = False,
) -> dict:
    """
    Returneaza din cache sau apeleaza fetch_coro si salveaza.
    Pattern principal pentru agenti.
    """
    if not force_refresh:
        cached = await get(key)
        if cached is not None:
            _track(source, hit=True)
            return cached

    _track(source, hit=False)
    data = await fetch_coro()
    if data:
        await set(key, data, source, ttl_hours)
    return data


async def invalidate_company(cui: str):
    """10F M10.4: Event-driven invalidation — clear all cache for a specific company."""
    patterns = [f"anaf_{hashlib.md5(cui.encode()).hexdigest()[:12]}",
                f"onrc_{hashlib.md5(cui.encode()).hexdigest()[:12]}",
                f"seap_{hashlib.md5(cui.encode()).hexdigest()[:12]}",
                f"tavily_{hashlib.md5(cui.encode()).hexdigest()[:12]}"]
    count = 0
    for pattern in patterns:
        await db.execute("DELETE FROM data_cache WHERE cache_key = ?", (pattern,))
        count += 1
    logger.info(f"Cache invalidated for CUI {cui[:3]}***: {count} patterns")
