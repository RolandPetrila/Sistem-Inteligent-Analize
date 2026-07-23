"""
Regresie: `.env` trebuie sa CASTIGE in fata variabilelor de mediu.

De ce exista acest fisier (2026-07-24, cauza masurata, nu presupusa):
serviciul Windows ruleaza sub contul `.\\ALIENWARE` — NU ca LocalSystem, cum
era scris in CLAUDE.md ca fapt verificat (`sc qc RIS-Backend` ->
SERVICE_START_NAME). Deci mosteneste blocul de mediu al userului, iar ordinea
implicita a pydantic-settings (env var > .env) facea ca orice variabila de
mediu omonima sa castige IN PRODUCTIE.

Masurat pe masina reala: 16 chei din `.env` au omonim in env vars User, dintre
care 4 divergeau. Una — `TELEGRAM_CHAT_ID=@ris_notif_bot`, adica @username-ul
BOTULUI — a facut ca nicio alerta de monitorizare sa nu fie livrata, tacut,
luni intregi (403 "the bot can't send messages to the bot").

Variabilele NU se sterg din Windows: sunt sistemul central de chei al masinii
(`~/.api-keys`), folosit de alte proiecte. Se schimba doar prioritatea, si doar
pentru RIS.
"""
import pytest

from backend.config import Settings


class TestDotenvBateEnvVar:
    def test_env_var_nu_mai_umbreste_dotenv(self, tmp_path, monkeypatch):
        """Cazul real: env var-ul avea @ris_notif_bot, .env avea id-ul corect."""
        env_file = tmp_path / ".env"
        env_file.write_text("TELEGRAM_CHAT_ID=6877691354\n", encoding="utf-8")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "@ris_notif_bot")

        s = Settings(_env_file=str(env_file))

        assert s.telegram_chat_id == "6877691354", (
            "variabila de mediu a umbrit .env — clasa de bug s-a intors"
        )

    def test_env_var_gol_nu_sterge_valoarea_din_dotenv(self, tmp_path, monkeypatch):
        """DEEPSEEK_API_KEY exista in env vars User cu valoare GOALA (masurat).

        Cu ordinea veche, cheia reala din .env era inlocuita cu "" in productie.
        """
        env_file = tmp_path / ".env"
        env_file.write_text("DEEPSEEK_API_KEY=cheie-reala-din-env-file\n", encoding="utf-8")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "")

        s = Settings(_env_file=str(env_file))

        assert s.deepseek_api_key == "cheie-reala-din-env-file"

    def test_env_var_ramane_sursa_cand_cheia_lipseste_din_dotenv(self, tmp_path, monkeypatch):
        """Fallback-ul nu se pierde: fara cheia in .env, mediul e in continuare citit."""
        env_file = tmp_path / ".env"
        env_file.write_text("TELEGRAM_CHAT_ID=6877691354\n", encoding="utf-8")
        monkeypatch.setenv("GROQ_API_KEY", "din-mediu")

        s = Settings(_env_file=str(env_file))

        assert s.groq_api_key == "din-mediu"

    def test_argumentul_explicit_bate_ambele(self, tmp_path, monkeypatch):
        """init_settings ramane pe primul loc — necesar pentru teste si scripturi."""
        env_file = tmp_path / ".env"
        env_file.write_text("TELEGRAM_CHAT_ID=din-fisier\n", encoding="utf-8")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "din-mediu")

        s = Settings(telegram_chat_id="explicit", _env_file=str(env_file))

        assert s.telegram_chat_id == "explicit"


class TestRisEnvNeatins:
    """`RIS_ENV` (setat de WinSW) e citit cu os.environ.get, nu prin Settings."""

    def test_ris_env_nu_e_camp_de_settings(self):
        assert "ris_env" not in Settings.model_fields, (
            "daca RIS_ENV devine camp de Settings, schimbarea de prioritate "
            "il poate face suprascriptibil din .env — reevalueaza"
        )

    def test_hard_fail_productie_citeste_tot_mediul(self, tmp_path, monkeypatch):
        """Garda de productie pt RIS_API_KEY depinde de os.environ, deci nu e afectata."""
        env_file = tmp_path / ".env"
        env_file.write_text("RIS_API_KEY=\n", encoding="utf-8")
        monkeypatch.setenv("RIS_ENV", "production")

        # app_secret_key valid, ca sa ajungem la garda pe care o testam
        # (cea pt APP_SECRET_KEY se evalueaza prima)
        with pytest.raises(RuntimeError, match="RIS_API_KEY"):
            Settings(
                _env_file=str(env_file),
                app_secret_key="x" * 40,
                ris_api_key="",
            )
