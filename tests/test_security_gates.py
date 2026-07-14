"""
HIGH #4 (audit 2026-07-13): RIS_API_KEY fail-open fara garda.

Teste CONTROLATE — construiesc `Settings`/`ApiKeyMiddleware` direct cu valori
explicite, NU ating .env-ul real si NU folosesc singleton-ul `settings` global
(care are RIS_API_KEY setat in acest mediu — testele astea verifica exact
scenariul opus, cheie goala, fara sa afecteze restul suitei).
"""
import contextlib
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI

from backend.config import Settings
from backend.middlewares import ApiKeyMiddleware


def _make_gated_client(stack: contextlib.ExitStack, host: str):
    """TestClient cu request.client.host controlat — pentru testarea gate-ului
    LOCALHOST-ONLY (aceleasi mock-uri ca fixture-ul `client` din test_routers.py,
    ca sa evitam efecte de import asupra restul suitei)."""
    from starlette.testclient import TestClient

    mock_db = stack.enter_context(patch("backend.database.db"))
    mock_db.connect = AsyncMock()
    mock_db.run_migrations = AsyncMock()
    mock_db.close = AsyncMock()
    mock_db.fetch_one = AsyncMock(return_value=None)
    mock_db.fetch_all = AsyncMock(return_value=[])
    mock_db.execute = AsyncMock()
    stack.enter_context(patch("backend.http_client.startup", new_callable=AsyncMock))
    stack.enter_context(patch("backend.http_client.shutdown", new_callable=AsyncMock))
    stack.enter_context(patch("backend.services.cache_service.cleanup_expired", new_callable=AsyncMock))
    stack.enter_context(patch("backend.services.scheduler.start_scheduler", new_callable=AsyncMock, return_value=AsyncMock()))
    stack.enter_context(patch("backend.services.scheduler.stop_scheduler", new_callable=AsyncMock))

    from backend.main import app
    return TestClient(app, client=(host, 12345))


class TestRisApiKeyBootGuard:
    """Settings.model_post_init — garda RIS_API_KEY (acelasi pattern ca APP_SECRET_KEY)."""

    def test_empty_key_warns_but_does_not_raise_in_dev(self):
        with patch.dict("os.environ", {}, clear=False), \
             patch("backend.config.logger") as mock_logger:
            import os
            os.environ.pop("RIS_ENV", None)
            settings = Settings(ris_api_key="")
        assert settings.ris_api_key == ""
        warning_calls = [c for c in mock_logger.warning.call_args_list if "RIS_API_KEY" in str(c)]
        assert warning_calls, "Asteptam un logger.warning mentionand RIS_API_KEY"

    def test_empty_key_hard_fails_in_production(self):
        with patch.dict("os.environ", {"RIS_ENV": "production"}, clear=False):
            with pytest.raises(RuntimeError, match="RIS_API_KEY"):
                Settings(ris_api_key="")

    def test_set_key_no_warning_no_raise(self):
        """Cazul curent (cheia E setata) — zero schimbare de comportament."""
        with patch.dict("os.environ", {}, clear=False), \
             patch("backend.config.logger") as mock_logger:
            import os
            os.environ.pop("RIS_ENV", None)
            settings = Settings(ris_api_key="o-cheie-reala-de-test-1234567890")
        assert settings.ris_api_key == "o-cheie-reala-de-test-1234567890"
        warning_calls = [c for c in mock_logger.warning.call_args_list if "RIS_API_KEY" in str(c)]
        assert not warning_calls, "Nu asteptam niciun warning cand cheia e setata"

    def test_set_key_no_raise_even_in_production(self):
        with patch.dict("os.environ", {"RIS_ENV": "production"}, clear=False):
            settings = Settings(ris_api_key="o-cheie-reala-de-test-1234567890")
        assert settings.ris_api_key == "o-cheie-reala-de-test-1234567890"


class TestApiKeyMiddlewareBootWarning:
    """ApiKeyMiddleware.__init__ — log unic la boot (nu per-request) cand fail-open."""

    def test_empty_key_logs_once_at_construction(self):
        app = FastAPI()
        with patch("backend.middlewares.settings") as mock_settings, \
             patch("backend.middlewares.logger") as mock_logger:
            mock_settings.ris_api_key = ""
            ApiKeyMiddleware(app)
        warning_calls = [c for c in mock_logger.warning.call_args_list if "DEZACTIVATA" in str(c)]
        assert len(warning_calls) == 1, "Asteptam exact un warning la constructie, nu per-request"

    def test_set_key_no_warning_at_construction(self):
        app = FastAPI()
        with patch("backend.middlewares.settings") as mock_settings, \
             patch("backend.middlewares.logger") as mock_logger:
            mock_settings.ris_api_key = "o-cheie-reala"
            ApiKeyMiddleware(app)
        mock_logger.warning.assert_not_called()


class TestUpdateRestartLoopbackGate:
    """B1 (audit 2026-07-13, quick-win securitate): /api/update + /api/restart
    LOCALHOST-ONLY, acelasi pattern ca /audit.html (main.py:_is_loopback_client).
    Defense-in-depth (restrange declansarea manuala a unui pull+build+restart ca
    SYSTEM la masina locala) — NU inchiderea unui RCE (ambele sunt deja sub
    ApiKeyMiddleware, dezactivata in teste de fixture-ul _no_api_key_in_tests)."""

    def test_update_blocked_for_non_loopback_host(self):
        with contextlib.ExitStack() as stack:
            client = _make_gated_client(stack, "100.80.18.55")
            resp = client.post("/api/update")
        assert resp.status_code == 404

    def test_update_allowed_for_loopback_host(self):
        with contextlib.ExitStack() as stack:
            client = _make_gated_client(stack, "127.0.0.1")
            with patch(
                "backend.services.updater.perform_update",
                new_callable=AsyncMock,
                return_value={"status": "ok"},
            ) as mock_update:
                resp = client.post("/api/update")
        assert resp.status_code == 200
        mock_update.assert_awaited_once_with(reason="manual")

    def test_restart_blocked_for_non_loopback_host(self):
        with contextlib.ExitStack() as stack:
            client = _make_gated_client(stack, "100.80.18.55")
            resp = client.post("/api/restart")
        assert resp.status_code == 404

    def test_restart_allowed_for_loopback_host(self):
        with contextlib.ExitStack() as stack:
            client = _make_gated_client(stack, "127.0.0.1")
            with patch(
                "backend.services.updater.restart_service",
                return_value={"status": "restarting"},
            ) as mock_restart:
                resp = client.post("/api/restart")
        assert resp.status_code == 200
        mock_restart.assert_called_once()
