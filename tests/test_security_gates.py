"""
HIGH #4 (audit 2026-07-13): RIS_API_KEY fail-open fara garda.

Teste CONTROLATE — construiesc `Settings`/`ApiKeyMiddleware` direct cu valori
explicite, NU ating .env-ul real si NU folosesc singleton-ul `settings` global
(care are RIS_API_KEY setat in acest mediu — testele astea verifica exact
scenariul opus, cheie goala, fara sa afecteze restul suitei).
"""
from unittest.mock import patch

import pytest
from fastapi import FastAPI

from backend.config import Settings
from backend.middlewares import ApiKeyMiddleware


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
