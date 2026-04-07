"""
F8-1: Teste pentru job_service — SSRF, webhook, progress update.
Testeaza: _is_private_ip, update_job_progress, _send_webhook_if_configured.
"""
from unittest.mock import AsyncMock, patch

import pytest


class TestIsPrivateIp:
    """Teste pentru _is_private_ip — SSRF prevention (IP-uri directe)."""

    def _call(self, host: str) -> bool:
        from backend.services.job_service import _is_private_ip
        return _is_private_ip(host)

    def test_loopback_127_is_private(self):
        assert self._call("127.0.0.1") is True

    def test_192_168_is_private(self):
        assert self._call("192.168.1.1") is True

    def test_10_x_is_private(self):
        assert self._call("10.0.0.1") is True

    def test_172_16_is_private(self):
        assert self._call("172.16.0.1") is True

    def test_172_31_is_private(self):
        assert self._call("172.31.255.255") is True

    def test_public_8_8_8_8_not_private(self):
        assert self._call("8.8.8.8") is False

    def test_public_1_1_1_1_not_private(self):
        assert self._call("1.1.1.1") is False

    def test_unresolvable_host_blocked(self):
        # Hostname care nu se poate rezolva → fail-safe = blocked
        # Mock socket.gethostbyname sa arunce exceptie
        import socket
        from unittest.mock import patch
        with patch("backend.services.job_service.socket.gethostbyname", side_effect=socket.gaierror):
            assert self._call("nonexistent.invalid.domain.xyz") is True

    def test_ipv6_loopback_is_private(self):
        assert self._call("::1") is True


class TestUpdateJobProgress:
    """Teste pentru update_job_progress — DB update + WS broadcast."""

    @pytest.mark.asyncio
    async def test_update_with_no_ws_manager(self):
        """Fara ws_manager nu arunca exceptie."""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()

        with patch("backend.services.job_service.db", mock_db):
            from backend.services.job_service import update_job_progress
            await update_job_progress("test-job", 50, "Analiza ANAF", "RUNNING", None)

        mock_db.execute.assert_called_once()
        args = mock_db.execute.call_args[0]
        assert "UPDATE jobs SET" in args[0]

    @pytest.mark.asyncio
    async def test_update_broadcasts_to_ws(self):
        """Cu ws_manager, broadcasteaza progresul."""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_ws = AsyncMock()
        mock_ws.broadcast = AsyncMock()

        with patch("backend.services.job_service.db", mock_db):
            from backend.services.job_service import update_job_progress
            await update_job_progress("job-abc", 75, "Scoring", "RUNNING", mock_ws)

        mock_ws.broadcast.assert_called_once()
        job_id_arg, payload = mock_ws.broadcast.call_args[0]
        assert job_id_arg == "job-abc"
        assert payload["percent"] == 75
        assert payload["step"] == "Scoring"
        assert payload["status"] == "RUNNING"

    @pytest.mark.asyncio
    async def test_update_status_done(self):
        """Status DONE se propaga corect."""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()

        with patch("backend.services.job_service.db", mock_db):
            from backend.services.job_service import update_job_progress
            await update_job_progress("job-xyz", 100, "Complet", "DONE", None)

        call_args = mock_db.execute.call_args[0][1]
        # Parametrii SQL: (progress, step, status, job_id)
        assert call_args[0] == 100
        assert call_args[2] == "DONE"


class TestWebhookSend:
    """Teste pentru _send_webhook_if_configured — validari URL."""

    @pytest.mark.asyncio
    async def test_empty_webhook_url_skips(self):
        """Fara URL configurat, nu se face niciun request."""
        from backend.services.job_service import _send_webhook_if_configured

        with patch("backend.config.settings") as mock_s:
            mock_s.webhook_url = ""
            # Nu ridica exceptie
            await _send_webhook_if_configured("job-1", {})

    @pytest.mark.asyncio
    async def test_http_url_blocked(self):
        """URL non-HTTPS este blocat cu warning."""
        from backend.services.job_service import _send_webhook_if_configured

        with patch("backend.services.job_service.logger") as mock_log:
            # Importa settings real si suprascriem webhook_url
            from backend.config import settings
            original = settings.webhook_url
            settings.webhook_url = "http://hooks.example.com/ris"
            try:
                await _send_webhook_if_configured("job-1", {})
            finally:
                settings.webhook_url = original

        mock_log.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_private_ip_webhook_blocked(self):
        """URL cu IP privat este blocat."""
        from backend.config import settings
        from backend.services.job_service import _send_webhook_if_configured

        original = settings.webhook_url
        settings.webhook_url = "https://192.168.1.1/hook"
        try:
            with patch("backend.services.job_service.logger") as mock_log:
                await _send_webhook_if_configured("job-1", {})
                # Trebuie sa fie blocata cu warning
                assert mock_log.warning.called
        finally:
            settings.webhook_url = original
