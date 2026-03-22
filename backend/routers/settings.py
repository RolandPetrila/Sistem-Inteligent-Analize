"""
Settings API — citeste/scrie variabile .env din UI.
Cheile API sunt mascate la citire.
"""

from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from backend.config import settings

router = APIRouter()

ENV_PATH = Path(".env")

# Campuri expuse in UI (nu expunem APP_SECRET_KEY)
EDITABLE_FIELDS = [
    "GOOGLE_AI_API_KEY",
    "GROQ_API_KEY",
    "CEREBRAS_API_KEY",
    "TAVILY_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "GMAIL_USER",
    "GMAIL_APP_PASSWORD",
    "SYNTHESIS_MODE",
    "TAVILY_MONTHLY_QUOTA",
    "TAVILY_WARN_AT",
    "MAX_CONCURRENT_JOBS",
    "LOG_LEVEL",
]


def _mask(value: str) -> str:
    """Mascheaza o cheie API (arata doar ultimele 4 caractere)."""
    if not value or len(value) < 8:
        return "*" * len(value) if value else ""
    return "*" * (len(value) - 4) + value[-4:]


def _read_env() -> dict[str, str]:
    """Citeste .env file intr-un dict."""
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


def _write_env(env: dict[str, str]):
    """Scrie dict inapoi in .env, pastrand comentariile."""
    lines = []
    if ENV_PATH.exists():
        existing_lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
        written_keys = set()
        for line in existing_lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key = stripped.split("=", 1)[0].strip()
                if key in env:
                    lines.append(f"{key}={env[key]}")
                    written_keys.add(key)
                else:
                    lines.append(line)
            else:
                lines.append(line)
        # Adauga chei noi
        for key, value in env.items():
            if key not in written_keys:
                lines.append(f"{key}={value}")
    else:
        for key, value in env.items():
            lines.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


class SettingsResponse(BaseModel):
    fields: dict[str, str]
    synthesis_mode: str
    has_tavily: bool
    has_gemini: bool
    has_groq: bool
    has_cerebras: bool
    has_telegram: bool
    has_email: bool


class SettingsUpdate(BaseModel):
    fields: dict[str, str]


@router.get("", response_model=SettingsResponse)
async def get_settings():
    """Returneaza setarile curente (chei mascate)."""
    env = _read_env()
    masked: dict[str, str] = {}

    sensitive = {"GOOGLE_AI_API_KEY", "GROQ_API_KEY", "CEREBRAS_API_KEY", "TAVILY_API_KEY", "TELEGRAM_BOT_TOKEN", "GMAIL_APP_PASSWORD"}

    for field in EDITABLE_FIELDS:
        value = env.get(field, "")
        masked[field] = _mask(value) if field in sensitive else value

    return SettingsResponse(
        fields=masked,
        synthesis_mode=env.get("SYNTHESIS_MODE", "claude_code"),
        has_tavily=bool(env.get("TAVILY_API_KEY")),
        has_gemini=bool(env.get("GOOGLE_AI_API_KEY")),
        has_groq=bool(env.get("GROQ_API_KEY")),
        has_cerebras=bool(env.get("CEREBRAS_API_KEY")),
        has_telegram=bool(env.get("TELEGRAM_BOT_TOKEN") and env.get("TELEGRAM_CHAT_ID")),
        has_email=bool(env.get("GMAIL_USER") and env.get("GMAIL_APP_PASSWORD")),
    )


@router.put("")
async def update_settings(data: SettingsUpdate):
    """Actualizeaza setarile. Campurile cu valoare goala sau masked sunt ignorate."""
    env = _read_env()
    updated = []

    for key, value in data.fields.items():
        if key not in EDITABLE_FIELDS:
            continue
        # Skip masked values (nu suprascrie cu stelute)
        if value and not value.startswith("*"):
            env[key] = value
            updated.append(key)

    if updated:
        _write_env(env)

    return {"updated": updated, "count": len(updated)}


@router.post("/test-telegram")
async def test_telegram():
    """Trimite un mesaj test pe Telegram."""
    from backend.services.notification import send_telegram
    ok = await send_telegram("RIS - Test notificare Telegram OK")
    return {"success": ok}
