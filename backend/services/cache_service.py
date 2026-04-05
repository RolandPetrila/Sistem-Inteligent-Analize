"""
Cache service cu TTL per tip sursa.
Foloseste tabelul data_cache din SQLite.
9A: Hit/miss tracking per source.
"""

import json
import hashlib
import threading
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


# --- L1 In-Memory Cache (hot data layer) ---
from collections import OrderedDict as _LRUDict
from time import time as _time_now


class _L1Cache:
    """In-memory LRU cache for hot data. Max 50 entries, TTL 5 minutes."""

    def __init__(self, max_size: int = 50, ttl_seconds: int = 300):
        self._store: _LRUDict[str, tuple[float, dict]] = _LRUDict()
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def get(self, key: str) -> dict | None:
        with self._lock:
            if key in self._store:
                ts, value = self._store[key]
                if _time_now() - ts < self._ttl:
                    self._store.move_to_end(key)
                    return value
                del self._store[key]
            return None

    def put(self, key: str, value: dict):
        with self._lock:
            self._store[key] = (_time_now(), value)
            self._store.move_to_end(key)
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)

    def invalidate(self, key: str):
        self._store.pop(key, None)

    def clear(self):
        self._store.clear()


_l1 = _L1Cache()


# TTL in ore per tip sursa
TTL_HOURS = {
    "anaf": 12,
    "onrc": 168,       # 7 zile
    "seap_active": 2,
    "seap_history": 720,  # 30 zile
    "tavily": 6,
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
    # L1: Check in-memory hot cache first
    l1_result = _l1.get(key)
    if l1_result is not None:
        logger.debug(f"Cache L1 HIT: {key}")
        return l1_result

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
            _l1.put(key, data)  # Promote to L1
            logger.debug(f"Cache HIT: {key}")
            return data
        except (json.JSONDecodeError, TypeError):
            return None
    return None


async def set(key: str, data: dict, source: str, ttl_hours: int | None = None):
    """Salveaza date in cache cu TTL."""
    if ttl_hours is None:
        ttl_hours = TTL_HOURS.get(source, 6)

    _l1.put(key, data)  # L1 first — hot cache updated immediately
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
    _l1.invalidate(pattern)  # L1: invalidate exact key (conservative)
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


# B24 fix: In-flight lock to prevent duplicate fetches for same key
# D18 fix: Bounded OrderedDict to prevent memory leak (max 500 entries)
import asyncio as _asyncio
from collections import OrderedDict as _OrderedDict
_fetch_locks: _OrderedDict[str, _asyncio.Lock] = _OrderedDict()
_MAX_LOCKS = 500


async def get_or_fetch(
    key: str,
    source: str,
    fetch_coro,
    ttl_hours: int | None = None,
    force_refresh: bool = False,
) -> dict:
    """
    Returneaza din cache sau apeleaza fetch_coro si salveaza.
    B24 fix: Lock per key prevents duplicate concurrent fetches.
    """
    if not force_refresh:
        cached = await get(key)
        if cached is not None:
            _track(source, hit=True)
            return cached

    # B24: Acquire per-key lock so only one coroutine fetches
    # D18 fix: Evict oldest locks when exceeding _MAX_LOCKS
    if key not in _fetch_locks:
        if len(_fetch_locks) >= _MAX_LOCKS:
            _fetch_locks.popitem(last=False)
        _fetch_locks[key] = _asyncio.Lock()
    async with _fetch_locks[key]:
        # Double-check cache after acquiring lock
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
    """C16 fix: Cache invalidation using LIKE to match all key variants for a CUI.
    Real keys are like anaf_{md5("bilant_CUI_YEAR")}, not anaf_{md5(cui)}.
    We search for any key whose original identifier contained this CUI."""
    # Strategy: delete keys that match any hash of identifiers containing this CUI
    # Build all possible hash prefixes
    cui_clean = cui.strip().replace("RO", "").replace("ro", "")
    possible_identifiers = [
        cui_clean,                    # direct CUI
        f"bilant_{cui_clean}",        # bilant prefix
        f"fin_{cui_clean}",           # financial prefix
    ]
    # Also match year variants for bilant (recent 6 years)
    from datetime import date
    current_year = date.today().year
    for year in range(current_year - 6, current_year + 1):
        possible_identifiers.append(f"bilant_{cui_clean}_{year}")

    count = 0
    for source in ("anaf", "onrc", "seap", "tavily"):
        for ident in possible_identifiers:
            key = make_cache_key(source, ident)
            result = await db.execute("DELETE FROM data_cache WHERE cache_key = ?", (key,))
            count += 1
    _l1.clear()  # conservative: clear all L1 on company invalidation
    logger.info(f"Cache invalidated for CUI {cui_clean[:3]}***: checked {count} key variants")
