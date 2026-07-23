"""
Regresie pentru clasa de bug "canal de livrare gatat pe preferinta altui canal"
(gasita 2026-07-24, extinderea findingului A-NEW-4 din auditul extern).

Pana la acest fix, in `run_monitoring_check` TOT blocul de reactie la o schimbare
era inauntrul lui `if changes and alert["telegram_notify"]:`. Consecinte reale:

  1. cine oprea Telegram (`telegram_notify=0`) pierdea SI notificarea in-app —
     schimbarea de risc disparea complet, tacut;
  2. sincronizarea `companies.is_active = 0` la detectarea unei firme RADIATE
     (integritate de date, nu notificare) era gatata si ea pe Telegram, ba chiar
     si pe throttling;
  3. ramura cea mai SEVERA — firma disparuta din ANAF — nu crea NICIO notificare
     in-app, nici macar cu Telegram pornit;
  4. rezultatul livrarii se logha, dar nu se persista nicaieri, deci un esec de
     livrare era invizibil in UI (absenta alertelor = absenta schimbarilor).

DOVADA DE NON-VACUITATE (obligatorie prin regulile proiectului): fiecare test de
mai jos PICA pe codul de dinainte de fix — verificat prin recuplarea temporara a
gate-ului vechi. Un test care trece si inainte, si dupa, nu dovedeste nimic.
"""
import json
from unittest.mock import AsyncMock, patch

import pytest

# Firma pe care ANAF o gaseste, dar care a intrat in insolventa fata de ultimul
# raport -> garanteaza `changes` nevid, fara sa depinda de praguri financiare.
_OLD_DATA_NEINSOLVENT = {
    "company": {},
    "risk": {"bpi_insolventa": {"value": {"found": False}}},
    "financial": {"cifra_afaceri": {"value": 100000}},
}


def _patches(alert, anaf_result, old_data=None):
    """Contextul comun de mock-uri; returneaza lista de context manageri."""
    return [
        patch("backend.services.monitoring_service.db"),
        patch("backend.services.monitoring_service.get_anaf_data"),
        patch("backend.services.monitoring_service._is_duplicate_alert"),
        patch("backend.services.monitoring_service._log_audit"),
        patch("backend.services.monitoring_service._should_throttle"),
        patch("backend.routers.notifications.create_notification"),
        patch("backend.agents.tools.bpi_client.check_insolvency"),
        patch("backend.agents.tools.anaf_bilant_client.get_bilant"),
    ]


async def _run(alert, anaf_result, old_data, telegram_ok=True, telegram_error=None):
    """Ruleaza run_monitoring_check cu mock-urile standard.

    Returneaza (results, mock_create_notification, mock_db).
    """
    with patch("backend.services.monitoring_service.db") as mock_db, \
         patch("backend.services.monitoring_service.get_anaf_data") as mock_anaf, \
         patch("backend.services.monitoring_service._is_duplicate_alert") as mock_dup, \
         patch("backend.services.monitoring_service._log_audit") as mock_log, \
         patch("backend.services.monitoring_service._should_throttle") as mock_thr, \
         patch("backend.routers.notifications.create_notification") as mock_notif, \
         patch("backend.services.monitoring_service.send_telegram_detailed") as mock_tg, \
         patch("backend.agents.tools.bpi_client.check_insolvency") as mock_bpi, \
         patch("backend.agents.tools.anaf_bilant_client.get_bilant") as mock_bil:

        mock_db.fetch_all = AsyncMock(return_value=[alert])
        mock_db.fetch_one = AsyncMock(
            return_value={"full_data": json.dumps(old_data)} if old_data else None
        )
        mock_db.execute = AsyncMock()
        mock_anaf.return_value = anaf_result
        mock_dup.return_value = False
        mock_log.return_value = None
        mock_thr.return_value = False
        mock_notif.return_value = None
        mock_tg.return_value = {"ok": telegram_ok, "error": telegram_error}
        mock_bpi.return_value = {"found": True, "status": "Faliment"}
        mock_bil.return_value = {"found": False}

        from backend.services.monitoring_service import run_monitoring_check
        results = await run_monitoring_check()
        return results, mock_notif, mock_db


class TestInAppNotificationIndependentDeTelegram:
    """N-1: canalul in-app nu depinde de preferinta Telegram."""

    @pytest.mark.asyncio
    async def test_notificare_in_app_creata_si_cu_telegram_oprit(self):
        """PICA pe codul vechi: create_notification era in `if ... telegram_notify`."""
        alert = {"id": "a1", "company_id": "c1", "telegram_notify": 0,
                 "cui": "12345678", "name": "Fara Telegram SRL"}

        results, mock_notif, _ = await _run(
            alert, {"found": True}, _OLD_DATA_NEINSOLVENT
        )

        assert results[0]["changed"] is True, results
        assert mock_notif.await_count == 1, (
            "Cu Telegram oprit, schimbarea de risc nu a produs nicio notificare in-app"
        )
        kwargs = mock_notif.await_args.kwargs
        assert kwargs["type"] == "monitoring_alert"
        assert "Fara Telegram SRL" in kwargs["title"]
        assert kwargs["link"] == "/company/c1"

    @pytest.mark.asyncio
    async def test_notificare_in_app_creata_si_cu_telegram_pornit(self):
        """Comportamentul existent nu regreseaza."""
        alert = {"id": "a2", "company_id": "c2", "telegram_notify": 1,
                 "cui": "12345678", "name": "Cu Telegram SRL"}

        _, mock_notif, _ = await _run(alert, {"found": True}, _OLD_DATA_NEINSOLVENT)

        assert mock_notif.await_count == 1

    @pytest.mark.asyncio
    async def test_firma_disparuta_din_anaf_produce_notificare_in_app(self):
        """PICA pe codul vechi: ramura RED 'negasit ANAF' nu crea NICIO notificare.

        E cea mai severa alerta din sistem (posibil radiata/dizolvata).
        """
        alert = {"id": "a3", "company_id": "c3", "telegram_notify": 0,
                 "cui": "99999999", "name": "Firma Radiata SRL"}

        results, mock_notif, _ = await _run(alert, {"found": False}, None)

        assert results[0]["severity"] == "RED"
        assert mock_notif.await_count == 1, (
            "Firma disparuta din ANAF nu a produs notificare in-app"
        )
        assert mock_notif.await_args.kwargs["severity"] == "error"


class TestIntegritateDateIndependentaDeNotificari:
    """Sincronizarea is_active e integritate de date, nu notificare."""

    @pytest.mark.asyncio
    async def test_is_active_sincronizat_si_cu_telegram_oprit(self):
        """PICA pe codul vechi: UPDATE-ul era gatat pe telegram_notify SI pe throttling."""
        alert = {"id": "a4", "company_id": "c4", "telegram_notify": 0,
                 "cui": "12345678", "name": "Radiata SRL"}
        # cheia reala citita de cod e `stare_inregistrare`, nu `stare`
        old_data = {
            "company": {"stare_inregistrare": {"value": "ACTIVA"}},
            "risk": {"bpi_insolventa": {"value": {"found": True}}},
            "financial": {},
        }

        results, _, mock_db = await _run(
            alert, {"found": True, "stare_inregistrare": "RADIAT"}, old_data
        )

        assert any(c["field"] == "Stare" for c in results[0]["changes"]), results[0]["changes"]
        sql_calls = [c.args[0] for c in mock_db.execute.await_args_list if c.args]
        assert any("is_active = 0" in s for s in sql_calls), (
            f"companies.is_active nu a fost sincronizat cu Telegram oprit: {sql_calls}"
        )


class TestVizibilitateaEsecuriiDeLivrare:
    """1c: rezultatul livrarii se persista, nu doar se logheaza."""

    @pytest.mark.asyncio
    async def test_esecul_de_livrare_e_persistat_cu_motiv(self):
        """PICA pe codul vechi: `delivered` era doar logat, nicaieri persistat."""
        alert = {"id": "a5", "company_id": "c5", "telegram_notify": 1,
                 "cui": "12345678", "name": "Livrare Esuata SRL"}

        _, _, mock_db = await _run(
            alert, {"found": True}, _OLD_DATA_NEINSOLVENT,
            telegram_ok=False,
            telegram_error="chat_id pointeaza catre bot, nu catre destinatar (403)",
        )

        delivery_calls = [
            c for c in mock_db.execute.await_args_list
            if c.args and "last_delivery_status" in c.args[0]
        ]
        assert delivery_calls, "starea livrarii nu a fost persistata pe alerta"
        params = delivery_calls[0].args[1]
        assert params[0] == "failed"
        assert "chat_id" in params[1]
        assert params[2] == "a5"

    @pytest.mark.asyncio
    async def test_livrarea_reusita_e_persistata_fara_eroare(self):
        alert = {"id": "a6", "company_id": "c6", "telegram_notify": 1,
                 "cui": "12345678", "name": "Livrare OK SRL"}

        _, _, mock_db = await _run(alert, {"found": True}, _OLD_DATA_NEINSOLVENT)

        delivery_calls = [
            c for c in mock_db.execute.await_args_list
            if c.args and "last_delivery_status" in c.args[0]
        ]
        assert delivery_calls
        params = delivery_calls[0].args[1]
        assert params[0] == "delivered"
        assert params[1] is None


class TestGardaChatIdLaPornire:
    """1d: config-ul semnaleaza la pornire un chat_id care pointeaza catre bot."""

    @staticmethod
    def _warns(chat_id: str) -> bool:
        from unittest.mock import patch as _patch

        from backend.config import Settings
        with _patch("backend.config.logger") as mock_log:
            Settings(
                telegram_bot_token="8522792443:AAtest",
                telegram_chat_id=chat_id,
                _env_file=None,
            )
            msgs = [str(c.args[0]) for c in mock_log.warning.call_args_list if c.args]
        return any("BOTUL INSUSI" in m for m in msgs)

    def test_username_de_bot_e_semnalat(self):
        """Cazul real gasit in productie 2026-07-24."""
        assert self._warns("@ris_notif_bot") is True

    def test_id_numeric_de_bot_e_semnalat(self):
        assert self._warns("8522792443") is True

    def test_chat_id_corect_nu_e_semnalat(self):
        assert self._warns("6877691354") is False

    def test_canal_legitim_nu_e_fals_pozitiv(self):
        """Un canal/grup real cu @username nu trebuie sa declanseze garda."""
        assert self._warns("@canalul_meu_de_alerte") is False
