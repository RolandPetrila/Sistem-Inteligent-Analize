"""
F8-1: Teste pentru cache_service — L1 in-memory, TTL, hit/miss, make_cache_key, cleanup.
Testeaza atat logica pura (fara DB) cat si operatii via mock DB.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMakeCacheKey:
    def test_returneaza_string(self):
        from backend.services.cache_service import make_cache_key
        key = make_cache_key("anaf", "12345678")
        assert isinstance(key, str)

    def test_format_prefix_sursa(self):
        from backend.services.cache_service import make_cache_key
        key = make_cache_key("anaf", "12345678")
        assert key.startswith("anaf_")

    def test_hash_12_caractere(self):
        from backend.services.cache_service import make_cache_key
        key = make_cache_key("anaf", "12345678")
        # Format: "sursa_HHHHHHHHHHHH" (prefix + underscore + 12 chars hash)
        parts = key.split("_", 1)
        assert len(parts) == 2
        assert len(parts[1]) == 12

    def test_chei_diferite_pentru_identificatori_diferiti(self):
        from backend.services.cache_service import make_cache_key
        key1 = make_cache_key("anaf", "12345678")
        key2 = make_cache_key("anaf", "87654321")
        assert key1 != key2

    def test_chei_diferite_pentru_surse_diferite(self):
        from backend.services.cache_service import make_cache_key
        key1 = make_cache_key("anaf", "12345678")
        key2 = make_cache_key("onrc", "12345678")
        assert key1 != key2

    def test_deterministic_acelasi_input_acelasi_output(self):
        from backend.services.cache_service import make_cache_key
        key1 = make_cache_key("tavily", "test_query")
        key2 = make_cache_key("tavily", "test_query")
        assert key1 == key2


class TestL1Cache:
    def test_get_put_basic(self):
        from backend.services.cache_service import _L1Cache
        cache = _L1Cache(max_size=10, ttl_seconds=300)
        cache.put("key1", {"data": "test"})
        result = cache.get("key1")
        assert result is not None
        assert result["data"] == "test"

    def test_get_cheia_inexistenta(self):
        from backend.services.cache_service import _L1Cache
        cache = _L1Cache(max_size=10, ttl_seconds=300)
        result = cache.get("cheia_nu_exista")
        assert result is None

    def test_evictie_lru_la_max_size(self):
        from backend.services.cache_service import _L1Cache
        cache = _L1Cache(max_size=3, ttl_seconds=300)
        cache.put("k1", {"v": 1})
        cache.put("k2", {"v": 2})
        cache.put("k3", {"v": 3})
        # k1 e cel mai vechi — va fi evictat la urmatoarea insertie
        cache.put("k4", {"v": 4})
        assert cache.get("k1") is None  # evictat
        assert cache.get("k4") is not None

    def test_invalidate(self):
        from backend.services.cache_service import _L1Cache
        cache = _L1Cache(max_size=10, ttl_seconds=300)
        cache.put("key_de_sters", {"data": "test"})
        cache.invalidate("key_de_sters")
        assert cache.get("key_de_sters") is None

    def test_clear(self):
        from backend.services.cache_service import _L1Cache
        cache = _L1Cache(max_size=10, ttl_seconds=300)
        cache.put("k1", {"v": 1})
        cache.put("k2", {"v": 2})
        cache.clear()
        assert cache.get("k1") is None
        assert cache.get("k2") is None

    def test_ttl_expirare(self):
        from backend.services.cache_service import _L1Cache
        cache = _L1Cache(max_size=10, ttl_seconds=0)  # TTL 0 = expira imediat
        cache.put("expira_key", {"data": "test"})
        # Dupa TTL=0, orice get trebuie sa returneze None (expirat)
        result = cache.get("expira_key")
        assert result is None

    def test_suprascriere_actualizeaza_valoarea(self):
        from backend.services.cache_service import _L1Cache
        cache = _L1Cache(max_size=10, ttl_seconds=300)
        cache.put("key1", {"v": 1})
        cache.put("key1", {"v": 2})
        result = cache.get("key1")
        assert result["v"] == 2

    def test_move_to_end_la_get(self):
        from backend.services.cache_service import _L1Cache
        cache = _L1Cache(max_size=3, ttl_seconds=300)
        cache.put("k1", {"v": 1})
        cache.put("k2", {"v": 2})
        cache.put("k3", {"v": 3})
        # Acceseaza k1 — devine recent, k2 va fi evictat
        cache.get("k1")
        cache.put("k4", {"v": 4})
        assert cache.get("k1") is not None  # recent accesat — nu evictat
        assert cache.get("k2") is None      # cel mai vechi neaccesat — evictat


class TestCacheServiceGet:
    @pytest.mark.asyncio
    async def test_get_l1_hit(self):
        from backend.services.cache_service import _l1, get
        # Pune direct in L1
        _l1.put("l1_test_key_001", {"source": "l1"})
        result = await get("l1_test_key_001")
        assert result is not None
        assert result["source"] == "l1"
        # Cleanup
        _l1.invalidate("l1_test_key_001")

    @pytest.mark.asyncio
    async def test_get_l2_miss_returneaza_none(self):
        # Cheia nu exista nici in L1 nici in DB
        with patch("backend.services.cache_service.db") as mock_db:
            mock_db.fetch_one = AsyncMock(return_value=None)
            from backend.services.cache_service import get
            result = await get("cheia_nu_exista_xyz_999")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_l2_hit_returneaza_date(self):
        import json
        data = {"info": "date test", "cui": "12345678"}
        with patch("backend.services.cache_service.db") as mock_db:
            # Simuleaza row din DB (cu versiune schema corecta)
            mock_row = {"data": json.dumps(data), "schema_version": 1}
            mock_db.fetch_one = AsyncMock(return_value=mock_row)
            from backend.services.cache_service import _l1, get
            _l1.invalidate("test_l2_key")  # asigura ca nu e in L1
            result = await get("test_l2_key")
            assert result is not None
            assert result["info"] == "date test"

    @pytest.mark.asyncio
    async def test_get_versiune_stale_returneaza_none(self):
        import json
        data = {"info": "stale data"}
        with patch("backend.services.cache_service.db") as mock_db:
            # Versiune 0 < CACHE_SCHEMA_VERSION (1) — stale
            mock_row = {"data": json.dumps(data), "schema_version": 0}
            mock_db.fetch_one = AsyncMock(return_value=mock_row)
            mock_db.execute = AsyncMock()
            from backend.services.cache_service import _l1, get
            _l1.invalidate("stale_key_test")
            result = await get("stale_key_test")
            assert result is None
            # Trebuie sa fi sters intrarea stale
            mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_json_invalid_returneaza_none(self):
        with patch("backend.services.cache_service.db") as mock_db:
            mock_row = {"data": "not_valid_json{{{", "schema_version": 1}
            mock_db.fetch_one = AsyncMock(return_value=mock_row)
            from backend.services.cache_service import _l1, get
            _l1.invalidate("invalid_json_key")
            result = await get("invalid_json_key")
            assert result is None


class TestCacheServiceSet:
    @pytest.mark.asyncio
    async def test_set_insereaza_in_l1_si_db(self):
        with patch("backend.services.cache_service.db") as mock_db:
            mock_db.execute = AsyncMock()
            mock_db.fetch_one = AsyncMock(return_value={"bytes": 0})
            mock_db.fetch_all = AsyncMock(return_value=[])
            from backend.services.cache_service import _l1, set
            await set("cache_set_test_001", {"val": 42}, source="anaf", ttl_hours=12)
            # Verifica L1 a fost actualizat
            assert _l1.get("cache_set_test_001") is not None
            # Verifica DB a fost apelat
            mock_db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_set_ttl_default_din_map(self):
        with patch("backend.services.cache_service.db") as mock_db:
            mock_db.execute = AsyncMock()
            mock_db.fetch_one = AsyncMock(return_value={"bytes": 0})
            mock_db.fetch_all = AsyncMock(return_value=[])
            from backend.services.cache_service import set
            # Sursa "onrc" are TTL 168 ore (din TTL_HOURS)
            await set("onrc_test_key", {"data": "test"}, source="onrc")
            # Verifica ca execute a fost apelat cu TTL-ul corect
            call_args = mock_db.execute.call_args[0][1]
            assert "168" in str(call_args)

    @pytest.mark.asyncio
    async def test_set_ttl_custom_override(self):
        with patch("backend.services.cache_service.db") as mock_db:
            mock_db.execute = AsyncMock()
            mock_db.fetch_one = AsyncMock(return_value={"bytes": 0})
            mock_db.fetch_all = AsyncMock(return_value=[])
            from backend.services.cache_service import set
            await set("custom_ttl_key", {"data": "test"}, source="anaf", ttl_hours=999)
            call_args = mock_db.execute.call_args[0][1]
            assert "999" in str(call_args)


class TestCacheServiceCleanup:
    @pytest.mark.asyncio
    async def test_cleanup_expired_returneaza_int(self):
        with patch("backend.services.cache_service.db") as mock_db:
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 3
            mock_db.execute = AsyncMock(return_value=mock_cursor)
            from backend.services.cache_service import cleanup_expired
            result = await cleanup_expired()
            assert isinstance(result, int)
            assert result == 3

    @pytest.mark.asyncio
    async def test_cleanup_expired_sterge_corect(self):
        with patch("backend.services.cache_service.db") as mock_db:
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 0
            mock_db.execute = AsyncMock(return_value=mock_cursor)
            from backend.services.cache_service import cleanup_expired
            await cleanup_expired()
            # Verifica ca s-a apelat DELETE cu expires_at
            call_args = mock_db.execute.call_args[0][0]
            assert "DELETE" in call_args.upper()
            assert "expires_at" in call_args


class TestCacheServiceInvalidate:
    @pytest.mark.asyncio
    async def test_invalidate_apeleaza_db(self):
        with patch("backend.services.cache_service.db") as mock_db:
            mock_db.execute = AsyncMock()
            from backend.services.cache_service import invalidate
            await invalidate("anaf_")
            mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_foloseste_like_pattern(self):
        with patch("backend.services.cache_service.db") as mock_db:
            mock_db.execute = AsyncMock()
            from backend.services.cache_service import invalidate
            await invalidate("test_pattern")
            call_args = mock_db.execute.call_args[0][1]
            # Pattern trebuie sa fie LIKE "test_pattern%"
            assert "test_pattern%" in str(call_args)


class TestTTLHours:
    def test_surse_principale_au_ttl_definit(self):
        from backend.services.cache_service import TTL_HOURS
        surse_necesare = ["anaf", "onrc", "seap_active", "seap_history", "tavily", "bnr", "ins"]
        for sursa in surse_necesare:
            assert sursa in TTL_HOURS, f"Sursa {sursa} nu are TTL definit"

    def test_onrc_are_ttl_mai_mare_ca_anaf(self):
        from backend.services.cache_service import TTL_HOURS
        # ONRC (7 zile) >> ANAF (12 ore) — date ONRC mai stabile
        assert TTL_HOURS["onrc"] > TTL_HOURS["anaf"]

    def test_toate_ttl_sunt_pozitive(self):
        from backend.services.cache_service import TTL_HOURS
        for sursa, ttl in TTL_HOURS.items():
            assert ttl > 0, f"TTL pentru {sursa} trebuie sa fie pozitiv"


class TestGetStats:
    @pytest.mark.asyncio
    async def test_get_stats_returneaza_structura_corecta(self):
        with patch("backend.services.cache_service.db") as mock_db:
            mock_db.fetch_one = AsyncMock(side_effect=[
                {"c": 10},           # total entries
                {"c": 2},            # expired
                {"bytes": 1024},     # size
            ])
            mock_db.fetch_all = AsyncMock(return_value=[
                {"source": "anaf", "c": 5},
                {"source": "onrc", "c": 5},
            ])
            from backend.services.cache_service import get_stats
            result = await get_stats()
            assert "total_entries" in result
            assert "expired_pending" in result
            assert "size_mb" in result
            assert "by_source" in result
            assert "hit_miss" in result

    @pytest.mark.asyncio
    async def test_get_stats_size_mb_corect(self):
        with patch("backend.services.cache_service.db") as mock_db:
            mock_db.fetch_one = AsyncMock(side_effect=[
                {"c": 5},
                {"c": 0},
                {"bytes": 1048576},  # exact 1MB
            ])
            mock_db.fetch_all = AsyncMock(return_value=[])
            from backend.services.cache_service import get_stats
            result = await get_stats()
            assert result["size_mb"] == 1.0
