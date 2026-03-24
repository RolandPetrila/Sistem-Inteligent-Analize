"""
ADV1: Scheduler — Ruleaza monitoring + backup automat la intervale fixe.
Foloseste asyncio.create_task cu sleep loop (lightweight, fara dependinte externe).
10A M9.3: Checkpoint persistence in DB — survive restart without window gaps.
"""

import asyncio
from datetime import datetime, date, UTC

from loguru import logger

from backend.config import settings

# Intervale (secunde)
MONITORING_INTERVAL = 6 * 3600  # 6 ore (verifica de 4 ori pe zi)
BACKUP_INTERVAL = 24 * 3600     # 24 ore (o data pe zi)
CACHE_CLEANUP_INTERVAL = 12 * 3600  # 12 ore

_running = True


# --- 10A M9.3: Checkpoint persistence ---

async def _get_checkpoint(key: str) -> float:
    """Read last_run timestamp from DB. Returns 0.0 if not found."""
    try:
        from backend.database import db
        row = await db.fetch_one(
            "SELECT last_run FROM scheduler_state WHERE key = ?", (key,)
        )
        if row and row["last_run"]:
            dt = datetime.fromisoformat(row["last_run"])
            return dt.timestamp()
    except Exception:
        pass
    return 0.0


async def _save_checkpoint(key: str, status: str = "OK"):
    """Persist last_run timestamp to DB."""
    try:
        from backend.database import db
        now = datetime.now(UTC).isoformat()
        await db.execute(
            "INSERT OR REPLACE INTO scheduler_state (key, last_run, run_count, last_status) "
            "VALUES (?, ?, COALESCE((SELECT run_count FROM scheduler_state WHERE key = ?), 0) + 1, ?)",
            (key, now, key, status),
        )
    except Exception as e:
        logger.debug(f"[scheduler] Checkpoint save failed for {key}: {e}")


async def start_scheduler() -> asyncio.Task:
    """Porneste scheduler-ul in background. Returneaza task-ul pentru cleanup."""
    global _running
    _running = True
    task = asyncio.create_task(_scheduler_loop())
    logger.info("[scheduler] Started — monitoring every 6h, backup every 24h, cache cleanup every 12h")
    return task


async def stop_scheduler(task: asyncio.Task):
    """Opreste scheduler-ul graceful."""
    global _running
    _running = False
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("[scheduler] Stopped")


async def _scheduler_loop():
    """Loop principal — ruleaza monitoring, backup si cache cleanup la intervale fixe."""
    # 10A M9.3: Load last_run from DB checkpoints (survive restart)
    last_monitoring = await _get_checkpoint("monitoring")
    last_backup = await _get_checkpoint("backup")
    last_cache_cleanup = await _get_checkpoint("cache_cleanup")

    # Asteapta 30s dupa startup (sa fie totul initializat)
    await asyncio.sleep(30)

    while _running:
        now = datetime.now(UTC).timestamp()

        # Monitoring check
        if now - last_monitoring >= MONITORING_INTERVAL:
            await _run_monitoring_safe()
            last_monitoring = now
            await _save_checkpoint("monitoring")

        # DB backup
        if now - last_backup >= BACKUP_INTERVAL:
            await _run_backup_safe()
            last_backup = now
            await _save_checkpoint("backup")

        # Cache cleanup (8A)
        if now - last_cache_cleanup >= CACHE_CLEANUP_INTERVAL:
            await _run_cache_cleanup_safe()
            last_cache_cleanup = now
            await _save_checkpoint("cache_cleanup")

        # Sleep 60s intre verificari
        await asyncio.sleep(60)


async def _run_monitoring_safe():
    """Ruleaza monitoring check cu error handling."""
    try:
        from backend.services.monitoring_service import run_monitoring_check
        from backend.database import db

        # Verifica daca sunt alerte active
        count = await db.fetch_one(
            "SELECT COUNT(*) as c FROM monitoring_alerts WHERE is_active = 1"
        )
        if not count or count["c"] == 0:
            return

        logger.info(f"[scheduler] Running monitoring check ({count['c']} active alerts)")
        results = await run_monitoring_check()
        changed = sum(1 for r in results if r.get("changed"))
        logger.info(f"[scheduler] Monitoring done: {len(results)} checked, {changed} changes")

    except Exception as e:
        logger.error(f"[scheduler] Monitoring error: {e}")


async def _run_cache_cleanup_safe():
    """Curata cache-ul expirat periodic (8A)."""
    try:
        from backend.services import cache_service
        count = await cache_service.cleanup_expired()
        logger.info(f"[scheduler] Cache cleanup: {count} expired entries removed")
    except Exception as e:
        logger.error(f"[scheduler] Cache cleanup error: {e}")


async def _run_backup_safe():
    """ADV3: Backup automat SQLite — foloseste sqlite3.backup() pentru consistenta."""
    try:
        import sqlite3
        from pathlib import Path

        db_path = Path(settings.database_path)
        if not db_path.exists():
            return

        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)

        # Format: ris_2026-03-21.db
        date_str = datetime.now().strftime("%Y-%m-%d")
        backup_path = backup_dir / f"ris_{date_str}.db"

        # Nu suprascrie backup din aceeasi zi
        if backup_path.exists():
            return

        # sqlite3.backup() — safe chiar daca DB e in uz (WAL mode)
        src = sqlite3.connect(str(db_path))
        dst = sqlite3.connect(str(backup_path))
        src.backup(dst)
        dst.close()
        src.close()
        logger.info(f"[scheduler] DB backup created: {backup_path}")

        # Rotatie: pastreaza ultimele 7 zile
        backups = sorted(backup_dir.glob("ris_*.db"), reverse=True)
        for old in backups[7:]:
            old.unlink()
            logger.debug(f"[scheduler] Old backup removed: {old}")

    except Exception as e:
        logger.error(f"[scheduler] Backup error: {e}")
