"""
Monitoring Service — Verifica periodic firmele monitorizate si trimite alerte.
8E: Smart severity, audit log, expanded delta detection.
10E: Severity throttling, alert escalation retry.
"""

import asyncio
import json
from datetime import datetime, UTC

from loguru import logger

from backend.database import db
from backend.agents.tools.anaf_client import get_anaf_data
from backend.services.notification import send_telegram


# Smart severity mapping (8E)
SEVERITY_MAP = {
    "inactiv_true": "RED",
    "inactiv_false": "GREEN",
    "stare_RADIAT": "RED",
    "stare_INACTIV": "RED",
    "stare_ACTIV": "GREEN",
    "tva_gained": "GREEN",
    "tva_lost": "YELLOW",
    "split_tva_on": "YELLOW",
    "split_tva_off": "GREEN",
}


def _determine_severity(change_type: str, old_val, new_val) -> str:
    """Determina severitatea schimbarii (8E)."""
    if change_type == "stare":
        if "RADIAT" in str(new_val).upper() or "INACTIV" in str(new_val).upper():
            return "RED"
        if "ACTIV" in str(new_val).upper():
            return "GREEN"
    elif change_type == "inactiv":
        return "RED" if new_val else "GREEN"
    elif change_type == "tva":
        return "YELLOW"
    elif change_type == "split_tva":
        return "YELLOW"
    return "INFO"


# Combinatii critice care escaladeaza severitatea
CRITICAL_COMBINATIONS = [
    ({"field": "Stare", "new_contains": "RADIAT"}, {"field": "Inactiv", "new": True}),
    ({"field": "Stare", "new_contains": "RADIAT"}, {"field": "TVA", "lost": True}),
    ({"field": "Inactiv", "new": True}, {"field": "TVA", "lost": True}),
]


def _determine_combined_severity(changes: list[dict]) -> str:
    """Verifica daca combinatia de schimbari justifica escaladare la CRITICAL."""
    if not changes:
        return "INFO"

    def _matches(change: dict, rule: dict) -> bool:
        if change.get("field") != rule.get("field"):
            return False
        if "new_contains" in rule:
            return rule["new_contains"] in str(change.get("new", "")).upper()
        if "new" in rule:
            return change.get("new") == rule["new"]
        if "lost" in rule and rule["lost"]:
            return change.get("new") is False or change.get("new") == "False"
        return True

    for combo_a, combo_b in CRITICAL_COMBINATIONS:
        a_match = any(_matches(c, combo_a) for c in changes)
        b_match = any(_matches(c, combo_b) for c in changes)
        if a_match and b_match:
            return "CRITICAL"

    severities = [c.get("severity", "INFO") for c in changes]
    if "RED" in severities:
        return "RED"
    if severities.count("YELLOW") >= 2:
        return "RED"  # 2+ yellow = escalate
    for s in ["YELLOW", "GREEN"]:
        if s in severities:
            return s
    return "INFO"


async def _log_audit(alert_id: str, cui: str, company_name: str,
                     change_type: str, old_val, new_val, severity: str):
    """Salveaza schimbarea in monitoring_audit (8E)."""
    try:
        await db.execute(
            "INSERT INTO monitoring_audit "
            "(alert_id, company_cui, company_name, change_type, old_value, new_value, severity) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (alert_id, cui, company_name, change_type, str(old_val), str(new_val), severity),
        )
    except Exception as e:
        logger.debug(f"[monitoring] Audit log failed (table may not exist): {e}")


async def _is_duplicate_alert(alert_id: str, change_type: str, new_val) -> bool:
    """9E: Dedup — verifica daca aceasta schimbare a fost deja raportata in ultimele 24h."""
    try:
        existing = await db.fetch_one(
            "SELECT id FROM monitoring_audit "
            "WHERE alert_id = ? AND change_type = ? AND new_value = ? "
            "AND triggered_at >= datetime('now', '-24 hours') "
            "ORDER BY triggered_at DESC LIMIT 1",
            (alert_id, change_type, str(new_val)),
        )
        return existing is not None
    except Exception:
        return False


async def _should_throttle(alert_id: str, severity: str) -> bool:
    """10E M9.1: Severity Throttling — RED=instant, YELLOW=max 1/6h, GREEN=daily digest."""
    if severity == "RED":
        return False  # Always send RED immediately

    # Check last notification time for this alert+severity level
    window = "'-6 hours'" if severity == "YELLOW" else "'-24 hours'"
    try:
        row = await db.fetch_one(
            f"SELECT id FROM monitoring_audit "
            f"WHERE alert_id = ? AND severity = ? "
            f"AND triggered_at >= datetime('now', {window}) "
            f"ORDER BY triggered_at DESC LIMIT 1",
            (alert_id, severity),
        )
        if row:
            logger.debug(f"[monitoring] Throttled {severity} alert for {alert_id}")
            return True
    except Exception as e:
        logger.debug(f"[monitoring] Throttle check error: {e}")
    return False


async def _send_telegram_with_retry(message: str, max_retries: int = 3) -> bool:
    """10E M9.2: Alert Escalation Retry — 3x exponential backoff on Telegram failure."""
    for attempt in range(max_retries):
        success = await send_telegram(message)
        if success:
            return True
        if attempt < max_retries - 1:
            wait = 2 ** (attempt + 1)  # 2s, 4s
            logger.warning(f"[monitoring] Telegram retry {attempt + 1}/{max_retries}, waiting {wait}s")
            await asyncio.sleep(wait)
    logger.error("[monitoring] Telegram delivery failed after all retries")
    return False


async def run_monitoring_check() -> list[dict]:
    """
    Verifica toate firmele cu monitorizare activa.
    8E: Expanded delta, smart severity, audit log.
    9E: Alert dedup (no repeat within 24h for same change).
    """
    alerts = await db.fetch_all(
        "SELECT m.id, m.company_id, m.telegram_notify, c.cui, c.name "
        "FROM monitoring_alerts m "
        "JOIN companies c ON m.company_id = c.id "
        "WHERE m.is_active = 1 AND c.cui IS NOT NULL"
    )

    results = []

    for alert in alerts:
        cui = alert["cui"]
        company_name = alert["name"]
        alert_id = alert["id"]

        try:
            current = await get_anaf_data(cui)
            if not current.get("found"):
                # B23 fix: CUI not found = firma radiata/dizolvata — trigger RED alert
                await db.execute(
                    "UPDATE monitoring_alerts SET last_checked_at = datetime('now') WHERE id = ?",
                    (alert_id,),
                )
                if alert.get("telegram_notify"):
                    msg = (
                        f"🔴 <b>ALERTA RIS [RED] — {company_name}</b>\n"
                        f"CUI: {cui}\n"
                        f"Firma NU mai apare in ANAF — posibil radiata/dizolvata!\n"
                        f"Verificat: {datetime.now(UTC).strftime('%d.%m.%Y %H:%M')}"
                    )
                    await _send_telegram_with_retry(msg)
                await _log_audit(alert_id, cui, company_name, "stare_firma", "activa", "NEGASIT ANAF", "RED")
                results.append({"cui": cui, "company": company_name, "changed": True,
                                "changes": [{"field": "stare_firma", "old": "activa",
                                             "new": "NEGASIT ANAF — posibil radiata", "severity": "RED"}],
                                "severity": "RED"})
                continue

            # Compara cu ultimul raport
            last_report = await db.fetch_one(
                "SELECT full_data FROM reports WHERE company_id = ? ORDER BY created_at DESC LIMIT 1",
                (alert["company_id"],),
            )

            changes = []
            max_severity = "INFO"

            if last_report and last_report["full_data"]:
                old_data = json.loads(last_report["full_data"])
                old_company = old_data.get("company", {})

                # Helper to extract old value
                def _old(key, default=""):
                    f = old_company.get(key, {})
                    return f.get("value", default) if isinstance(f, dict) else default

                # Verifica stare
                old_stare = _old("stare_inregistrare")
                new_stare = current.get("stare_inregistrare", "")
                if old_stare and new_stare and old_stare != new_stare:
                    if not await _is_duplicate_alert(alert_id, "stare", new_stare):
                        sev = _determine_severity("stare", old_stare, new_stare)
                        changes.append({"field": "Stare", "old": old_stare, "new": new_stare, "severity": sev})
                        await _log_audit(alert_id, cui, company_name, "stare", old_stare, new_stare, sev)

                # Verifica inactiv
                old_inactiv = _old("inactiv", False)
                new_inactiv = current.get("inactiv", False)
                if old_inactiv != new_inactiv:
                    if not await _is_duplicate_alert(alert_id, "inactiv", new_inactiv):
                        sev = _determine_severity("inactiv", old_inactiv, new_inactiv)
                        changes.append({"field": "Inactiv", "old": old_inactiv, "new": new_inactiv, "severity": sev})
                        await _log_audit(alert_id, cui, company_name, "inactiv", old_inactiv, new_inactiv, sev)

                # Verifica TVA
                old_tva = _old("platitor_tva")
                new_tva = current.get("platitor_tva")
                if old_tva is not None and new_tva is not None and old_tva != new_tva:
                    if not await _is_duplicate_alert(alert_id, "tva", new_tva):
                        sev = _determine_severity("tva", old_tva, new_tva)
                        changes.append({"field": "TVA", "old": old_tva, "new": new_tva, "severity": sev})
                        await _log_audit(alert_id, cui, company_name, "tva", old_tva, new_tva, sev)

                # 8E: Expanded delta — split TVA
                old_split = _old("split_tva", False)
                new_split = current.get("split_tva", False)
                if old_split != new_split:
                    if not await _is_duplicate_alert(alert_id, "split_tva", new_split):
                        sev = "YELLOW"
                        changes.append({"field": "Split TVA", "old": old_split, "new": new_split, "severity": sev})
                        await _log_audit(alert_id, cui, company_name, "split_tva", old_split, new_split, sev)

                # Determine max severity — including critical combinations
                max_severity = _determine_combined_severity(changes)

            # Update last_checked
            await db.execute(
                "UPDATE monitoring_alerts SET last_checked_at = datetime('now') WHERE id = ?",
                (alert_id,),
            )

            # 10E M9.1+M9.2: Send notification with throttling + retry
            if changes and alert["telegram_notify"]:
                throttled = await _should_throttle(alert_id, max_severity)
                if not throttled:
                    severity_icon = {"RED": "🔴", "YELLOW": "🟡", "GREEN": "🟢"}.get(max_severity, "ℹ️")
                    msg = (
                        f"{severity_icon} <b>ALERTA RIS [{max_severity}] — {company_name}</b>\n"
                        f"CUI: {cui}\n"
                        f"Schimbari detectate:\n"
                    )
                    for c in changes:
                        sev_icon = {"RED": "🔴", "YELLOW": "🟡", "GREEN": "🟢"}.get(c["severity"], "")
                        msg += f"  {sev_icon} {c['field']}: {c['old']} → {c['new']}\n"
                    msg += f"Verificat: {datetime.now(UTC).strftime('%d.%m.%Y %H:%M')}"
                    delivered = await _send_telegram_with_retry(msg)
                    logger.info(f"[monitoring] Alert [{max_severity}] {'sent' if delivered else 'FAILED'} for {company_name}")
                else:
                    logger.info(f"[monitoring] Alert [{max_severity}] throttled for {company_name}")

                # R2 Fix #1: Create in-app notification for monitoring alerts
                try:
                    from backend.routers.notifications import create_notification
                    await create_notification(
                        type="monitoring_alert",
                        title=f"Alerta [{max_severity}]: {company_name}",
                        message="; ".join(f"{c['field']}: {c['old']}→{c['new']}" for c in changes),
                        link=f"/company/{alert['company_id']}",
                        severity="error" if max_severity in ("RED", "CRITICAL") else "warning",
                    )
                except Exception as notif_err:
                    logger.debug(f"Notification create failed: {notif_err}")

            results.append({
                "cui": cui,
                "company": company_name,
                "changed": bool(changes),
                "changes": changes,
                "severity": max_severity,
            })

        except Exception as e:
            logger.warning(f"[monitoring] Error checking {cui}: {e}")
            results.append({"cui": cui, "changed": False, "error": str(e)})

    changed_count = sum(1 for r in results if r.get("changed"))
    logger.info(f"[monitoring] Checked {len(results)} companies, {changed_count} with changes")
    return results
