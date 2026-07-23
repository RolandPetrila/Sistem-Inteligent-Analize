import os
import secrets as _secrets
import stat
from pathlib import Path

from loguru import logger
from pydantic import model_validator
from pydantic_settings import BaseSettings

_SECRET_KEY_FILE = Path("data") / ".secret_key"
_DEFAULT_PLACEHOLDER = "change-me-to-random-string"


def _load_or_create_secret_key() -> tuple[str, bool]:
    """Load persisted secret key from data/.secret_key or create one.

    Returns (key, was_created). Persisting the key ensures JWT/cookie
    sessions survive across process restarts when APP_SECRET_KEY is not
    explicitly set in .env.
    """
    try:
        if _SECRET_KEY_FILE.exists():
            key = _SECRET_KEY_FILE.read_text(encoding="utf-8").strip()
            if key and key != _DEFAULT_PLACEHOLDER and len(key) >= 32:
                return key, False
    except OSError as e:
        logger.warning(f"[config] Could not read {_SECRET_KEY_FILE}: {e}")

    # Create a fresh key and persist it
    key = _secrets.token_urlsafe(32)
    try:
        _SECRET_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        _SECRET_KEY_FILE.write_text(key, encoding="utf-8")
        # Best-effort restrict permissions (noop on Windows but safe)
        try:
            os.chmod(_SECRET_KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
    except OSError as e:
        logger.warning(f"[config] Could not persist secret key to {_SECRET_KEY_FILE}: {e}")
    return key, True


class Settings(BaseSettings):
    # AI Providers
    google_ai_api_key: str = ""
    groq_api_key: str = ""
    cerebras_api_key: str = ""
    synthesis_mode: str = "claude_code"  # "claude_code" | "autonomous"
    # Cale ABSOLUTA optionala catre claude.exe (CLAUDE_CLI_PATH in .env). De ce exista:
    # serviciul Windows RIS-Backend porneste ca SYSTEM, iar SCM (Service Control Manager)
    # CACHEAZA blocul de mediu (inclusiv PATH) la BOOT-ul masinii — nu la pornirea
    # serviciului. Daca Claude CLI e instalat/mutat DUPA ultimul reboot, procesul
    # serviciului NU vede noul PATH pana la urmatorul reboot, desi orice shell nou
    # deschis dupa instalare il gaseste instant (shell-urile citesc PATH-ul curent,
    # nu cel cachet de SCM la boot) — nu e o problema de istoric/ordine, e o
    # constrangere reala a Windows SCM. Un reboot ar repara temporar, dar problema
    # revine tacut la orice viitoare schimbare de PATH. Gol = foloseste "claude" din
    # PATH (comportament implicit, neschimbat).
    claude_cli_path: str = ""

    # Sinteza Claude Opus — reglabile din .env FARA cod. Masurat live 2026-07-17 pe prompt
    # real de productie (~46k caractere, MEGA IMAGE): --effort max = 252s/sectiune (1128
    # cuvinte), --effort high = 143s/sectiune (1044 cuvinte, calitate ~identica). Timeout-ul
    # vechi hardcodat de 180s taia MEREU Claude -> fallback tacut pe Groq/Cerebras (Claude
    # nu scria nimic). NB: numele e `synthesis_effort` (SYNTHESIS_EFFORT), NU `claude_effort` —
    # ar coliziona cu env var-ul CLAUDE_EFFORT folosit de Claude Code CLI insusi.
    synthesis_effort: str = "max"          # SYNTHESIS_EFFORT: max | high | medium | low
    synthesis_claude_timeout: int = 360    # SYNTHESIS_CLAUDE_TIMEOUT: secunde per apel Claude (252 masurat + marja)
    synthesis_total_timeout: int = 2400    # SYNTHESIS_TOTAL_TIMEOUT: plafon global sinteza (plasa de siguranta; execute() se auto-termina inainte)

    # Web Search
    tavily_api_key: str = ""

    # ONRC (openapi.ro)
    openapi_ro_key: str = ""

    # Mistral AI
    mistral_api_key: str = ""
    tavily_monthly_quota: int = 1000
    tavily_warn_at: int = 800

    # F7 — AI API Extensions
    jina_api_key: str = ""           # https://jina.ai/reader/ (optional, free without key)
    deepseek_api_key: str = ""       # https://platform.deepseek.com/api_keys
    cohere_api_key: str = ""         # https://dashboard.cohere.com/
    brave_api_key: str = ""          # https://api.search.brave.com/register (2000 req/luna gratuit)
    xai_api_key: str = ""            # https://console.x.ai/ (credit $25 — not permanent free)
    openrouter_api_key: str = ""     # https://openrouter.ai/ (50 req/zi :free models)
    # R6 — Truly free permanent AI providers
    github_token: str = ""           # https://github.com/settings/tokens (50-150 req/zi, GPT-4.1 + Llama 4)
    fireworks_api_key: str = ""      # https://fireworks.ai/ (10 RPM permanent free, Llama 4 Scout/Maverick)
    sambanova_api_key: str = ""      # https://cloud.sambanova.ai/ (Llama 405B GRATUIT — unic)

    # R8 — Maps & Geocoding
    google_cloud_api_key: str = ""   # Google Maps Places API (billing activ pe proiect GCloud)

    # Notifications
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Email
    gmail_user: str = ""
    gmail_app_password: str = ""

    # API Key (optional — if set, all /api/ endpoints require X-RIS-Key header)
    ris_api_key: str = ""

    # App — D19: auto-generate random key if not explicitly set
    app_secret_key: str = ""
    database_path: str = "./data/ris.db"
    checkpoint_db_path: str = "./data/checkpoints.db"
    outputs_dir: str = "./outputs/"
    log_level: str = "INFO"
    backend_port: int = 8001
    frontend_port: int = 5173

    # Rate limiting
    max_concurrent_jobs: int = 2
    request_delay_gov: int = 2
    request_delay_web: int = 3

    # Batch processing
    batch_max_parallel: int = 2
    batch_max_cuis: int = 50
    batch_timeout_hours: int = 4

    # Webhook outbound
    webhook_url: str = ""  # WEBHOOK_URL in .env — URL HTTPS la care se trimite POST la finalizare job

    # Compare & dedup
    compare_rate_delay_s: int = 2
    dedup_cleanup_s: int = 600

    # Logging
    log_format: str = "text"  # "text" sau "json" — LOG_FORMAT in .env

    # PDF
    pdf_watermark: str = "CONFIDENTIAL"  # PDF_WATERMARK in .env
    pdf_watermark_enabled: bool = True   # PDF_WATERMARK_ENABLED in .env (false = fara watermark)

    # Auto-update local (updater.py) — verifica git remote periodic + pull/build/restart automat
    auto_update_enabled: bool = True     # AUTO_UPDATE_ENABLED in .env (false = dezactiveaza)
    auto_update_interval_min: int = 10   # AUTO_UPDATE_INTERVAL_MIN in .env

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    def model_post_init(self, __context) -> None:
        # D19 + Gemini-P0: Persist auto-generated secret key so sessions survive restarts.
        if not self.app_secret_key or self.app_secret_key == _DEFAULT_PLACEHOLDER:
            # Production hard-fail: refuse to run with missing/default key
            if os.environ.get("RIS_ENV", "").lower() == "production":
                raise RuntimeError(
                    "SECURITATE: APP_SECRET_KEY lipseste sau e valoarea default in .env. "
                    "Seteaza APP_SECRET_KEY cu o valoare random (min 32 chars) inainte de "
                    "pornire in RIS_ENV=production."
                )
            key, created = _load_or_create_secret_key()
            self.app_secret_key = key
            if created:
                logger.warning(
                    f"APP_SECRET_KEY nu e setat in .env — s-a generat si persistat in "
                    f"{_SECRET_KEY_FILE}. Pentru productie, seteaza APP_SECRET_KEY in .env."
                )

        # HIGH #4 (audit 2026-07-13): RIS_API_KEY fail-open fara garda — daca e
        # goala, ApiKeyMiddleware lasa TOATE /api/* neautentificate silentios.
        # Acelasi pattern ca APP_SECRET_KEY: hard-fail DOAR in RIS_ENV=production.
        # Spre deosebire de APP_SECRET_KEY, aceasta cheie NU se auto-genereaza
        # (clientii — frontend/.env — trebuie sa cunoasca valoarea ca sa o trimita),
        # deci WARNING-ul e neconditionat (nu doar la "created" prima data).
        if not self.ris_api_key:
            if os.environ.get("RIS_ENV", "").lower() == "production":
                raise RuntimeError(
                    "SECURITATE: RIS_API_KEY lipseste in .env. Toate endpoint-urile "
                    "/api/* ar ramane neautentificate. Seteaza RIS_API_KEY inainte de "
                    "pornire in RIS_ENV=production."
                )
            logger.warning(
                "SECURITATE: RIS_API_KEY nu e setat in .env — TOATE endpoint-urile "
                "/api/* sunt NEAUTENTIFICATE (oricine acceseaza serviciul poate apela "
                "orice API). Seteaza RIS_API_KEY in .env pentru a activa autentificarea."
            )

    @model_validator(mode="after")
    def validate_telegram_target(self) -> "Settings":
        """TELEGRAM_CHAT_ID trebuie sa fie DESTINATARUL, nu botul insusi.

        Caz real (2026-07-24): `TELEGRAM_CHAT_ID=@ris_notif_bot` — @username-ul
        botului. Telegram raspunde 403 "the bot can't send messages to the bot",
        deci nicio alerta de monitorizare nu se livra, tacut, luni intregi.
        Verificarea e locala (fara apel de retea la pornire).
        """
        chat = str(self.telegram_chat_id or "").strip()
        token = str(self.telegram_bot_token or "")
        if not chat or not token:
            return self

        bot_id = token.split(":", 1)[0]
        looks_like_bot = chat == bot_id or (chat.startswith("@") and chat.lower().endswith("bot"))
        if looks_like_bot:
            logger.warning(
                f"TELEGRAM_CHAT_ID ({chat}) pare sa fie BOTUL INSUSI, nu destinatarul — "
                "Telegram va raspunde 403 si NICIO alerta nu va fi livrata. "
                "Scrie botului din contul tau, apoi ia `message.chat.id` din getUpdates. "
                "ATENTIE: o variabila de mediu cu acelasi nume are prioritate fata de .env."
            )
        return self

    @model_validator(mode="after")
    def validate_critical_keys(self) -> "Settings":
        if not self.tavily_api_key:
            import warnings
            warnings.warn("TAVILY_API_KEY lipseste — cautarea web va fi dezactivata", stacklevel=2)
        if not self.groq_api_key and not self.google_ai_api_key and not getattr(self, 'anthropic_api_key', ''):
            import warnings
            warnings.warn("Niciun AI provider configurat (GROQ_API_KEY, GOOGLE_AI_API_KEY) — synthesis va esua", stacklevel=2)
        return self

    @property
    def db_path(self) -> Path:
        return Path(self.database_path)

    @property
    def checkpoint_path(self) -> Path:
        return Path(self.checkpoint_db_path)

    @property
    def output_path(self) -> Path:
        return Path(self.outputs_dir)


settings = Settings()
