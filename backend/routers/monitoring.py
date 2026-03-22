"""
Monitoring API — CRUD pentru alerte de monitorizare firme.
10E: Monitoring health endpoint.
"""

import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database import db
from loguru import logger

router = APIRouter()


class MonitoringCreate(BaseModel):
    company_id: str
    alert_type: str = "all"
    check_frequency: str = "weekly"
    telegram_notify: bool = True


@router.get("")
async def list_monitoring_alerts():
    """Lista toate alertele de monitorizare active."""
    rows = await db.fetch_all(
        "SELECT m.*, c.name as company_name, c.cui "
        "FROM monitoring_alerts m "
        "LEFT JOIN companies c ON m.company_id = c.id "
        "ORDER BY m.is_active DESC"
    )
    return {"alerts": [dict(r) for r in rows], "total": len(rows)}


@router.post("")
async def create_monitoring_alert(data: MonitoringCreate):
    """Creeaza o alerta de monitorizare noua."""
    # Verifica ca firma exista
    company = await db.fetch_one("SELECT id, name FROM companies WHERE id = ?", (data.company_id,))
    if not company:
        raise HTTPException(status_code=404, detail="Firma nu exista in baza de date. Ruleaza o analiza mai intai.")

    # Verifica daca exista deja
    existing = await db.fetch_one(
        "SELECT id FROM monitoring_alerts WHERE company_id = ? AND is_active = 1",
        (data.company_id,),
    )
    if existing:
        raise HTTPException(status_code=400, detail="Monitorizare deja activa pentru aceasta firma")

    alert_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO monitoring_alerts (id, company_id, alert_type, is_active, "
        "check_frequency, telegram_notify) VALUES (?, ?, ?, 1, ?, ?)",
        (alert_id, data.company_id, data.alert_type, data.check_frequency, data.telegram_notify),
    )
    return {"id": alert_id, "status": "created", "company": company["name"]}


@router.put("/{alert_id}/toggle")
async def toggle_monitoring(alert_id: str):
    """Activeaza/dezactiveaza o alerta."""
    row = await db.fetch_one("SELECT * FROM monitoring_alerts WHERE id = ?", (alert_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Alerta nu exista")

    new_status = not row["is_active"]
    await db.execute(
        "UPDATE monitoring_alerts SET is_active = ? WHERE id = ?",
        (new_status, alert_id),
    )
    return {"id": alert_id, "is_active": new_status}


@router.delete("/{alert_id}")
async def delete_monitoring(alert_id: str):
    """Sterge o alerta de monitorizare."""
    row = await db.fetch_one("SELECT id FROM monitoring_alerts WHERE id = ?", (alert_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Alerta nu exista")

    await db.execute("DELETE FROM monitoring_alerts WHERE id = ?", (alert_id,))
    return {"status": "deleted", "id": alert_id}


@router.post("/check-now")
async def check_all_now():
    """Ruleaza verificare manuala pentru toate alertele active."""
    from backend.services.monitoring_service import run_monitoring_check
    results = await run_monitoring_check()
    return {"checked": len(results), "alerts_triggered": sum(1 for r in results if r.get("changed"))}


@router.get("/health")
async def monitoring_health():
    """10E M9.4: Monitoring health — last check per alert, failed count, next scheduled."""
    alerts = await db.fetch_all(
        "SELECT m.id, m.is_active, m.last_checked_at, m.check_frequency, "
        "c.name as company_name, c.cui "
        "FROM monitoring_alerts m "
        "LEFT JOIN companies c ON m.company_id = c.id "
        "WHERE m.is_active = 1"
    )

    # Get failed alert count (last 24h) from audit log
    failed_count = 0
    try:
        row = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM monitoring_audit "
            "WHERE severity = 'RED' AND created_at >= datetime('now', '-24 hours')"
        )
        failed_count = row["cnt"] if row else 0
    except Exception:
        pass

    # Get scheduler last run from scheduler_state
    scheduler_last_run = None
    try:
        sched_row = await db.fetch_one(
            "SELECT last_run, last_status FROM scheduler_state WHERE key = 'monitoring'"
        )
        if sched_row:
            scheduler_last_run = sched_row["last_run"]
    except Exception:
        pass

    alert_details = []
    for a in alerts:
        alert_details.append({
            "id": a["id"],
            "company": a["company_name"],
            "cui": a["cui"],
            "last_checked": a["last_checked_at"],
            "frequency": a["check_frequency"],
        })

    return {
        "active_alerts": len(alerts),
        "red_alerts_24h": failed_count,
        "scheduler_last_run": scheduler_last_run,
        "alerts": alert_details,
    }
