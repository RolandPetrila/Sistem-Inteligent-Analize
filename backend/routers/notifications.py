"""Notification center — in-app notifications for jobs, alerts, system events."""
import uuid
from fastapi import APIRouter
from backend.database import db

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(unread_only: bool = False, limit: int = 20):
    query = "SELECT * FROM notifications"
    if unread_only:
        query += " WHERE read_at IS NULL"
    query += " ORDER BY created_at DESC LIMIT ?"
    rows = await db.fetch_all(query, (limit,))
    unread = await db.fetch_one("SELECT COUNT(*) as c FROM notifications WHERE read_at IS NULL")
    return {"notifications": rows, "unread_count": unread["c"] if unread else 0}


@router.put("/{notification_id}/read")
async def mark_read(notification_id: str):
    await db.execute("UPDATE notifications SET read_at = datetime('now') WHERE id = ?", (notification_id,))
    return {"ok": True}


@router.put("/read-all")
async def mark_all_read():
    await db.execute("UPDATE notifications SET read_at = datetime('now') WHERE read_at IS NULL")
    return {"ok": True}


async def create_notification(type: str, title: str, message: str = "", link: str = "", severity: str = "info"):
    """Helper to create a notification from any service."""
    nid = uuid.uuid4().hex[:16]
    await db.execute(
        "INSERT INTO notifications (id, type, title, message, link, severity) VALUES (?, ?, ?, ?, ?, ?)",
        (nid, type, title, message, link, severity),
    )
    return nid
