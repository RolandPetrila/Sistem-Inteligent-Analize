"""
Notification service — Telegram Bot API + Gmail SMTP.
Apelat automat la completarea/esuarea unui job.
"""

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import aiosmtplib
from loguru import logger

from backend.config import settings


async def send_telegram_detailed(message: str) -> dict:
    """Trimite mesaj pe Telegram si returneaza MOTIVUL esecului, nu doar un bool.

    Exista pentru ca un esec de livrare trebuie sa fie observabil fara citirea
    logurilor: apelantul (monitoring) persista `error` pe alerta si il arata in UI.
    Absenta alertelor era pana acum indistincta de absenta schimbarilor de risc.

    Returneaza {"ok": bool, "error": str | None}.
    """
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.debug("Telegram not configured, skipping notification")
        return {"ok": False, "error": "Telegram neconfigurat (token sau chat_id lipsa)"}

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        from backend.http_client import get_client
        client = get_client()
        response = await client.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info("Telegram notification sent")
            return {"ok": True, "error": None}

        body = response.text[:200]
        # Cazul verificat live 2026-07-24: chat_id-ul pointeaza catre BOTUL INSUSI
        # (id numeric sau @username-ul lui) -> Telegram raspunde 403 cu acest text.
        # Il ridicam la ERROR cu instructiunea de reparare, pentru ca mesajul brut
        # ("Forbidden") nu spune utilizatorului ce sa schimbe.
        if response.status_code == 403 and "send messages to the bot" in body:
            logger.error(
                "[telegram] chat_id-ul configurat este BOTUL INSUSI, nu destinatarul. "
                "Scrie botului din contul tau, apoi ia `message.chat.id` din "
                "https://api.telegram.org/bot<TOKEN>/getUpdates si pune-l in TELEGRAM_CHAT_ID. "
                "ATENTIE: o variabila de mediu cu acelasi nume are prioritate fata de .env."
            )
            return {"ok": False, "error": "chat_id pointeaza catre bot, nu catre destinatar (403)"}

        logger.warning(f"Telegram error: {response.status_code} {body}")
        return {"ok": False, "error": f"HTTP {response.status_code}: {body}"}
    except Exception as e:
        logger.warning(f"Telegram notification failed: {e}")
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


async def send_telegram(message: str) -> bool:
    """Wrapper istoric peste `send_telegram_detailed` (apelantii care nu au nevoie de motiv)."""
    return (await send_telegram_detailed(message))["ok"]


async def send_email(
    to: str,
    subject: str,
    body_html: str,
    attachments: list[str] | None = None,
) -> bool:
    """Trimite email via Gmail SMTP cu aiosmtplib."""
    if not settings.gmail_user or not settings.gmail_app_password:
        logger.debug("Gmail not configured, skipping email")
        return False

    msg = MIMEMultipart()
    msg["From"] = settings.gmail_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    # Attachments
    if attachments:
        for filepath in attachments:
            path = Path(filepath)
            if not path.exists():
                continue
            part = MIMEBase("application", "octet-stream")
            part.set_payload(path.read_bytes())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={path.name}",
            )
            msg.attach(part)

    try:
        await aiosmtplib.send(
            msg,
            hostname="smtp.gmail.com",
            port=587,
            start_tls=True,
            username=settings.gmail_user,
            password=settings.gmail_app_password,
        )
        logger.info(f"Email sent to {to}")
        return True
    except Exception as e:
        logger.warning(f"Email send failed: {e}")
        return False


async def notify_job_complete(
    job_id: str,
    analysis_type: str,
    company_name: str,
    risk_score: str | None,
    report_formats: list[str],
    duration_seconds: int = 0,
):
    """Notificare automata la finalizarea unui job."""
    risk_text = f" | Risc: {risk_score}" if risk_score else ""
    formats_text = ", ".join(f.upper() for f in report_formats)

    telegram_msg = (
        f"<b>Analiza finalizata</b>\n"
        f"Tip: {analysis_type}\n"
        f"Firma: {company_name or 'N/A'}{risk_text}\n"
        f"Formate: {formats_text}\n"
        f"Durata: {duration_seconds}s\n"
        f"Job: <code>{job_id[:8]}</code>"
    )
    await send_telegram(telegram_msg)


async def notify_job_failed(job_id: str, error: str):
    """Notificare automata la esuarea unui job."""
    telegram_msg = (
        f"<b>Analiza esuata</b>\n"
        f"Job: <code>{job_id[:8]}</code>\n"
        f"Eroare: {error[:200]}"
    )
    await send_telegram(telegram_msg)
