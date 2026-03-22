"""
Notification service — Telegram Bot API + Gmail SMTP.
Apelat automat la completarea/esuarea unui job.
"""

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

from loguru import logger
from backend.config import settings


async def send_telegram(message: str) -> bool:
    """Trimite mesaj pe Telegram via Bot API."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.debug("Telegram not configured, skipping notification")
        return False

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
            return True
        else:
            logger.warning(f"Telegram error: {response.status_code} {response.text[:200]}")
            return False
    except Exception as e:
        logger.warning(f"Telegram notification failed: {e}")
        return False


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
