"""
Settings API — citeste/scrie variabile .env din UI.
Cheile API sunt mascate la citire.
"""

import os
import shutil
import time
from pathlib import Path

from fastapi import APIRouter, Depends
from loguru import logger
from pydantic import BaseModel

from backend.agents.tools.connectivity import PING_REGISTRY, run_ping
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


def _env_backup_dir() -> Path:
    """F3: keep .env backups OUTSIDE the repo tree — they contain cleartext secrets."""
    base = os.environ.get("LOCALAPPDATA")
    root = (Path(base) / "RIS") if base else (Path.home() / ".ris")
    d = root / "env-backups"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _backup_env():
    """Create a timestamped backup of .env before writing, OUTSIDE the repo tree.
    Keep max MAX_ENV_BACKUPS. (F3: avoid cleartext secrets at rest in the project folder.)"""
    if not ENV_PATH.exists():
        return
    try:
        backup_dir = _env_backup_dir()
        ts = int(time.time())
        backup_path = backup_dir / f".env.bak.{ts}"
        shutil.copy2(str(ENV_PATH), str(backup_path))
        logger.info(f"Settings: .env backed up to {backup_path}")

        # Cleanup old backups — keep only the newest MAX_ENV_BACKUPS
        backups = sorted(backup_dir.glob(".env.bak.*"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in backups[MAX_ENV_BACKUPS:]:
            old.unlink()
            logger.debug(f"Settings: removed old backup {old.name}")

        # F3: clean up any legacy backups previously written into the repo root
        for legacy in ENV_PATH.parent.glob(".env.bak.*"):
            try:
                legacy.unlink()
                logger.debug(f"Settings: removed legacy in-repo backup {legacy.name}")
            except Exception:
                pass
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


@router.post("/test-telegram", dependencies=[Depends(require_api_key)])
async def test_telegram():
    """Trimite un mesaj test pe Telegram."""
    from backend.services.notification import send_telegram
    ok = await send_telegram("RIS - Test notificare Telegram OK")
    return {"success": ok}


TESTABLE_SERVICES = ["groq", "gemini", "mistral", "cerebras", "tavily", "telegram", "email", "webhook"]

# 15 surse externe fara endpoint dedicat (audit 2026-07-12) — dispatch generic prin
# PING_REGISTRY in loc de blocuri elif suplimentare (vezi connectivity.py pt motiv).
TESTABLE_SERVICES = TESTABLE_SERVICES + list(PING_REGISTRY.keys())


@router.post("/test/{service}", dependencies=[Depends(require_api_key)])
async def test_service(service: str):
    """Test conectivitate individual per serviciu (groq, gemini, tavily, telegram + 15 surse externe)."""
    from backend.errors import ErrorCode, RISError

    if service not in TESTABLE_SERVICES:
        raise RISError(ErrorCode.VALIDATION_ERROR, f"Serviciu necunoscut: {service}. Valide: {', '.join(TESTABLE_SERVICES)}")

    if service in PING_REGISTRY:
        return await run_ping(service)

    try:
        if service == "tavily":
            # Bug reparat 2026-07-17: importa `TavilyClient` (clasa INEXISTENTA) -> testul
            # raporta mereu FAIL desi Tavily FUNCTIONEAZA in joburi reale (pipeline-ul
            # foloseste functia modul `search`, nu o clasa). "Test care minte" — cazul clasic
            # din acest proiect. Interfata reala = tavily_client.search(query, max_results).
            from backend.agents.tools.tavily_client import search as tavily_search
            result = await tavily_search("test connectivity RIS", max_results=1)
            if result.get("error"):
                return {"ok": False, "message": f"Tavily: {result['error']}"}
            n = result.get("result_count", len(result.get("results", [])))
            return {"ok": n > 0, "message": f"Tavily OK ({n} rezultate)"}

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

        elif service in ("mistral", "cerebras"):
            # Refolosim config-ul din synthesis_providers.py (aceeasi sursa ca fallback-ul
            # real de sinteza) — evita sa reparam un model/URL hardcodat de 2 ori (asa a
            # ramas Cerebras nedetectat: niciun test manual nu exista pt acest provider).
            from backend.agents.synthesis_providers import SynthesisProvidersMixin
            from backend.http_client import get_client
            cfg = SynthesisProvidersMixin._PROVIDERS[service]
            api_key = getattr(settings, cfg["api_key_attr"], "")
            if not api_key:
                return {"ok": False, "message": f"{cfg['api_key_attr'].upper()} nu este configurat"}
            c = get_client()
            r = await c.post(
                cfg["url"],
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": cfg["model"], "messages": [{"role": "user", "content": "1+1="}], "max_tokens": 5},
                timeout=10,
            )
            return {"ok": r.status_code == 200, "message": f"{service.capitalize()} HTTP {r.status_code}"}

        elif service == "telegram":
            from backend.services.notification import send_telegram
            ok = await send_telegram("Test conexiune RIS — OK")
            return {"ok": ok, "message": "Telegram OK" if ok else "Telegram: eroare la trimitere"}

        elif service == "email":
            from backend.services.notification import send_email
            if not settings.gmail_user or not settings.gmail_app_password:
                return {"ok": False, "message": "GMAIL_USER / GMAIL_APP_PASSWORD nu sunt configurate"}
            ok = await send_email(
                to=settings.gmail_user,
                subject="RIS - Test conectivitate email",
                body_html="<p>Test conectivitate email RIS — mesaj minimal, fara raport real.</p>",
            )
            return {"ok": ok, "message": "Email OK" if ok else "Email: eroare la trimitere (verifica logs)"}

        elif service == "webhook":
            from backend.services.job_service import _send_webhook_if_configured
            result = await _send_webhook_if_configured("test-ping", {
                "company_name": "Firma Test SRL",
                "cui": "00000000",
                "risk_score": "Verde",
                "numeric_score": 100,
            })
            if result.get("sent"):
                return {"ok": True, "message": f"Webhook OK (HTTP {result.get('status_code')})"}
            return {"ok": False, "message": f"Webhook: {result.get('reason')}"}

    except Exception as e:
        logger.warning(f"[settings] Test conexiune {service} esuat: {e}")
        return {"ok": False, "message": "Eroare la testarea conexiunii — verifica logs"}
