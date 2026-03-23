import secrets as _secrets

from pydantic_settings import BaseSettings
from pathlib import Path


def _default_secret_key() -> str:
    """D19: Generate random secret key if not set in .env."""
    return _secrets.token_urlsafe(32)


class Settings(BaseSettings):
    # AI Providers
    google_ai_api_key: str = ""
    groq_api_key: str = ""
    cerebras_api_key: str = ""
    synthesis_mode: str = "claude_code"  # "claude_code" | "autonomous"

    # Web Search
    tavily_api_key: str = ""

    # ONRC (openapi.ro)
    openapi_ro_key: str = ""

    # Mistral AI
    mistral_api_key: str = ""
    tavily_monthly_quota: int = 1000
    tavily_warn_at: int = 800

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

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    def model_post_init(self, __context) -> None:
        # D19: Auto-generate secret key if not set or still default
        if not self.app_secret_key or self.app_secret_key == "change-me-to-random-string":
            import sys
            self.app_secret_key = _default_secret_key()
            print(
                "[WARNING] APP_SECRET_KEY nu e setat in .env — s-a generat automat. "
                "Setati APP_SECRET_KEY in .env pentru persistenta intre restart-uri.",
                file=sys.stderr,
            )

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
