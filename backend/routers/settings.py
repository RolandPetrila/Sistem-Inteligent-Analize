"""
Settings API — citeste/scrie variabile .env din UI.
Cheile API sunt mascate la citire.
"""

import shutil
import time
from pathlib import Path

from fastapi import APIRouter, Depends
from loguru import logger
from pydantic import BaseModel

from backend.config import settings
from backend.security import require_api_key

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


MAX_ENV_BACKUPS = 5


def _backup_env():
    """Create a timestamped backup of .env before writing. Keep max 5 backups."""
    if not ENV_PATH.exists():
        return
    try:
        ts = int(time.time())
        backup_path = ENV_PATH.parent / f".env.bak.{ts}"
        shutil.copy2(str(ENV_PATH), str(backup_path))
        logger.info(f"Settings: .env backed up to {backup_path.name}")

        # Cleanup old backups — keep only the newest MAX_ENV_BACKUPS
        backups = sorted(ENV_PATH.parent.glob(".env.bak.*"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in backups[MAX_ENV_BACKUPS:]:
            old.unlink()
            logger.debug(f"Settings: removed old backup {old.name}")
    except Exception as e:
        logger.warning(f"Settings: .env backup failed: {e}")


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


@router.get("", response_model=SettingsResponse, dependencies=[Depends(require_api_key)])
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


@router.put("", dependencies=[Depends(require_api_key)])
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
        _backup_env()
        _write_env(env)
        # C21 fix: Reload in-memory settings from updated .env
        _reload_settings(env, updated)

    return {"updated": updated, "count": len(updated)}


def _reload_settings(env: dict, updated_keys: list[str]):
    """C21: Reload in-memory settings for changed keys."""
    key_to_attr = {
        "GOOGLE_AI_API_KEY": "google_ai_api_key",
        "GROQ_API_KEY": "groq_api_key",
        "CEREBRAS_API_KEY": "cerebras_api_key",
        "TAVILY_API_KEY": "tavily_api_key",
        "TELEGRAM_BOT_TOKEN": "telegram_bot_token",
        "TELEGRAM_CHAT_ID": "telegram_chat_id",
        "GMAIL_USER": "gmail_user",
        "GMAIL_APP_PASSWORD": "gmail_app_password",
        "SYNTHESIS_MODE": "synthesis_mode",
        "TAVILY_MONTHLY_QUOTA": "tavily_monthly_quota",
        "TAVILY_WARN_AT": "tavily_warn_at",
        "MAX_CONCURRENT_JOBS": "max_concurrent_jobs",
        "LOG_LEVEL": "log_level",
    }
    for key in updated_keys:
        attr = key_to_attr.get(key)
        if attr and hasattr(settings, attr):
            new_val = env.get(key, "")
            # Convert to int for numeric fields
            if attr in ("tavily_monthly_quota", "tavily_warn_at", "max_concurrent_jobs"):
                try:
                    new_val = int(new_val)
                except (ValueError, TypeError):
                    continue
            object.__setattr__(settings, attr, new_val)


@router.post("/test-telegram")
async def test_telegram():
    """Trimite un mesaj test pe Telegram."""
    from backend.services.notification import send_telegram
    ok = await send_telegram("RIS - Test notificare Telegram OK")
    return {"success": ok}


TESTABLE_SERVICES = ["groq", "gemini", "tavily", "telegram"]


@router.post("/test/{service}")
async def test_service(service: str):
    """Test conectivitate individual per serviciu (groq, gemini, tavily, telegram)."""
    from backend.errors import ErrorCode, RISError

    if service not in TESTABLE_SERVICES:
        raise RISError(ErrorCode.VALIDATION_ERROR, f"Serviciu necunoscut: {service}. Valide: {', '.join(TESTABLE_SERVICES)}")

    try:
        if service == "tavily":
            from backend.agents.tools.tavily_client import TavilyClient
            client = TavilyClient()
            result = await client.search("test connectivity RIS", max_results=1)
            return {"ok": bool(result), "message": "Tavily OK" if result else "Tavily: niciun rezultat returnat"}

        elif service == "groq":
            from backend.http_client import get_client
            env = _read_env()
            groq_key = env.get("GROQ_API_KEY", "") or settings.groq_api_key
            if not groq_key:
                return {"ok": False, "message": "GROQ_API_KEY nu este configurat"}
            c = get_client()
            r = await c.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}"},
                json={"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": "1+1="}], "max_tokens": 5},
                timeout=10,
            )
            return {"ok": r.status_code == 200, "message": f"Groq HTTP {r.status_code}"}

        elif service == "gemini":
            from backend.http_client import get_client
            env = _read_env()
            gemini_key = env.get("GOOGLE_AI_API_KEY", "") or settings.google_ai_api_key
            if not gemini_key:
                return {"ok": False, "message": "GOOGLE_AI_API_KEY nu este configurat"}
            c = get_client()
            r = await c.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}",
                json={"contents": [{"parts": [{"text": "1+1="}]}]},
                timeout=10,
            )
            return {"ok": r.status_code == 200, "message": f"Gemini HTTP {r.status_code}"}

        elif service == "telegram":
            from backend.services.notification import send_telegram
            ok = await send_telegram("Test conexiune RIS — OK")
            return {"ok": ok, "message": "Telegram OK" if ok else "Telegram: eroare la trimitere"}

    except Exception as e:
        logger.warning(f"[settings] Test conexiune {service} esuat: {e}")
        return {"ok": False, "message": "Eroare la testarea conexiunii — verifica logs"}
