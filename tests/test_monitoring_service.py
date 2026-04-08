"""
Teste pentru monitoring_service — _determine_severity, _determine_combined_severity, run_monitoring_check.
Pattern: import inline, mock DB via patch, @pytest.mark.asyncio pentru async.
"""
from unittest.mock import AsyncMock, patch

import pytest


class TestDetermineSeverity:
    def test_stare_radiat_returneaza_red(self):
        from backend.services.monitoring_service import _determine_severity
        result = _determine_severity("stare", "ACTIVA", "RADIAT")
        assert result == "RED"

    def test_stare_inactiv_returneaza_red(self):
        from backend.services.monitoring_service import _determine_severity
        result = _determine_severity("stare", "ACTIVA", "INACTIV")
        assert result == "RED"

    def test_stare_activ_returneaza_green(self):
        from backend.services.monitoring_service import _determine_severity
        result = _determine_severity("stare", "INACTIV", "ACTIVA")
        assert result == "GREEN"

    def test_inactiv_true_returneaza_red(self):
        from backend.services.monitoring_service import _determine_severity
        result = _determine_severity("inactiv", False, True)
        assert result == "RED"

    def test_inactiv_false_returneaza_green(self):
        from backend.services.monitoring_service import _determine_severity
        result = _determine_severity("inactiv", True, False)
        assert result == "GREEN"

    def test_tva_returneaza_yellow(self):
        from backend.services.monitoring_service import _determine_severity
        # change_type "tva" (nu "tva_platitor") conform cod sursa
        result = _determine_severity("tva", True, False)
        assert result == "YELLOW"

    def test_split_tva_returneaza_yellow(self):
        from backend.services.monitoring_service import _determine_severity
        result = _determine_severity("split_tva", False, True)
        assert result == "YELLOW"

    def test_tip_necunoscut_returneaza_info(self):
        from backend.services.monitoring_service import _determine_severity
        result = _determine_severity("tip_necunoscut", "vechi", "nou")
        assert result == "INFO"


class TestDetermineCombinedSeverity:
    def test_doua_red_flags_escaladeaza_la_critical(self):
        from backend.services.monitoring_service import _determine_combined_severity
        changes = [{"severity": "RED"}, {"severity": "RED"}]
        result = _determine_combined_severity(changes)
        assert result == "CRITICAL"

    def test_un_singur_red_returneaza_red(self):
        from backend.services.monitoring_service import _determine_combined_severity
        changes = [{"severity": "RED"}, {"severity": "GREEN"}]
        result = _determine_combined_severity(changes)
        assert result == "RED"

    def test_doar_green_returneaza_green(self):
        from backend.services.monitoring_service import _determine_combined_severity
        changes = [{"severity": "GREEN"}]
        result = _determine_combined_severity(changes)
        assert result == "GREEN"

    def test_lista_goala_returneaza_info(self):
        from backend.services.monitoring_service import _determine_combined_severity
        result = _determine_combined_severity([])
        assert result == "INFO"

    def test_doua_yellow_escaladeaza_la_red(self):
        from backend.services.monitoring_service import _determine_combined_severity
        changes = [{"severity": "YELLOW"}, {"severity": "YELLOW"}]
        result = _determine_combined_severity(changes)
        assert result == "RED"

    def test_un_yellow_returneaza_yellow(self):
        from backend.services.monitoring_service import _determine_combined_severity
        changes = [{"severity": "YELLOW"}]
        result = _determine_combined_severity(changes)
        assert result == "YELLOW"


class TestRunMonitoringCheck:
    @pytest.mark.asyncio
    async def test_returneaza_lista_cu_alerta_activa(self):
        """Verifica ca run_monitoring_check returneaza o lista cand exista alerte active."""
        fake_alert = {
            "id": "alert-1",
            "company_id": 1,
            "telegram_notify": 0,
            "cui": "12345678",
            "name": "Test SRL",
        }

        with patch("backend.services.monitoring_service.db") as mock_db, \
             patch("backend.services.monitoring_service.get_anaf_data") as mock_anaf:

            mock_db.fetch_all = AsyncMock(return_value=[fake_alert])
            mock_db.fetch_one = AsyncMock(return_value=None)
            mock_db.execute = AsyncMock()
            mock_anaf.return_value = {"found": True, "stare_inregistrare": "ACTIVA"}

            from backend.services.monitoring_service import run_monitoring_check
            results = await run_monitoring_check()

            assert isinstance(results, list)
            assert len(results) == 1
            assert results[0]["cui"] == "12345678"

    @pytest.mark.asyncio
    async def test_returneaza_lista_goala_fara_alerte(self):
        """Fara alerte active → lista goala."""
        with patch("backend.services.monitoring_service.db") as mock_db:
            mock_db.fetch_all = AsyncMock(return_value=[])

            from backend.services.monitoring_service import run_monitoring_check
            results = await run_monitoring_check()

            assert results == []

    @pytest.mark.asyncio
    async def test_firma_negasita_anaf_adauga_red_in_rezultat(self):
        """Daca ANAF nu gaseste firma → changed=True, severity=RED."""
        fake_alert = {
            "id": "alert-2",
            "company_id": 2,
            "telegram_notify": 0,
            "cui": "99999999",
            "name": "Firma Radiata SRL",
        }

        with patch("backend.services.monitoring_service.db") as mock_db, \
             patch("backend.services.monitoring_service.get_anaf_data") as mock_anaf, \
             patch("backend.services.monitoring_service._send_telegram_with_retry") as mock_tg:

            mock_db.fetch_all = AsyncMock(return_value=[fake_alert])
            mock_db.execute = AsyncMock()
            mock_anaf.return_value = {"found": False}
            mock_tg.return_value = True

            from backend.services.monitoring_service import run_monitoring_check
            results = await run_monitoring_check()

            assert results[0]["severity"] == "RED"
            assert results[0]["changed"] is True
