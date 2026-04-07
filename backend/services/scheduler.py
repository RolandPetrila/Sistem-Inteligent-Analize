"""
ADV1: Scheduler — Ruleaza monitoring + backup automat la intervale fixe.
Foloseste asyncio.create_task cu sleep loop (lightweight, fara dependinte externe).
10A M9.3: Checkpoint persistence in DB — survive restart without window gaps.
"""

import asyncio
from datetime import UTC, datetime

from loguru import logger

from backend.config import settings

# Intervale (secunde)
MONITORING_INTERVAL = 6 * 3600  # 6 ore (verifica de 4 ori pe zi)
BACKUP_INTERVAL = 24 * 3600     # 24 ore (o data pe zi)
CACHE_CLEANUP_INTERVAL = 12 * 3600  # 12 ore
AUTO_REANALYZE_INTERVAL = 6 * 3600  # 6 ore (verifica ce firme trebuie re-analizate)

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
    except Exception as e:
        logger.debug(f"[scheduler] sleep prevention: {e}")
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


_task: asyncio.Task | None = None


async def get_scheduler_status() -> dict:
    """Returneaza statusul curent al scheduler-ului (pentru health/status endpoint)."""
    return {
        "status": "ok" if _task is not None and not _task.done() else "stopped",
        "running": _task is not None and not _task.done(),
    }


async def start_scheduler() -> asyncio.Task:
    """Porneste scheduler-ul in background. Returneaza task-ul pentru cleanup."""
    global _running, _task
    _running = True
    _task = asyncio.create_task(_scheduler_loop())
    logger.info("[scheduler] Started — monitoring every 6h, backup every 24h, cache cleanup every 12h, auto-reanalyze every 6h")
    return _task


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
    """Loop principal — ruleaza monitoring, backup, cache cleanup si auto-reanalyze la intervale fixe."""
    # 10A M9.3: Load last_run from DB checkpoints (survive restart)
    last_monitoring = await _get_checkpoint("monitoring")
    last_backup = await _get_checkpoint("backup")
    last_cache_cleanup = await _get_checkpoint("cache_cleanup")
    last_auto_reanalyze = await _get_checkpoint("auto_reanalyze")

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

        # F6-6: Auto re-analyze companies cu auto_reanalyze=1
        if now - last_auto_reanalyze >= AUTO_REANALYZE_INTERVAL:
            await _auto_reanalyze_job()
            last_auto_reanalyze = now
            await _save_checkpoint("auto_reanalyze")

        # Sleep 60s intre verificari
        await asyncio.sleep(60)


async def _run_monitoring_safe():
    """Ruleaza monitoring check cu error handling."""
    try:
        from backend.database import db
        from backend.services.monitoring_service import run_monitoring_check

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


async def _auto_reanalyze_job():
    """F6-6: Re-analizeaza automat companiile cu auto_reanalyze=1 care depasesc intervalul.
    Creeaza un nou job pentru fiecare firma eligibila si il porneste imediat.
    """
    try:
        import json
        import uuid

        from backend.database import db

        # Ensure columns exist (idempotent — poate fi primul run)
        for alter_sql in [
            "ALTER TABLE companies ADD COLUMN auto_reanalyze INTEGER DEFAULT 0",
            "ALTER TABLE companies ADD COLUMN reanalyze_interval_days INTEGER DEFAULT 30",
        ]:
            try:
                await db.execute(alter_sql)
            except Exception:
                pass  # Column already exists

        # Selecteaza firmele eligibile:
        # - auto_reanalyze = 1
        # - last_analyzed_at < now - reanalyze_interval_days
        rows = await db.fetch_all(
            """
            SELECT c.id, c.cui, c.name, c.caen_code,
                   COALESCE(c.reanalyze_interval_days, 30) as interval_days,
                   c.last_analyzed_at
            FROM companies c
            WHERE c.auto_reanalyze = 1
              AND (
                c.last_analyzed_at IS NULL
                OR datetime(c.last_analyzed_at, '+' || COALESCE(c.reanalyze_interval_days, 30) || ' days') <= datetime('now')
              )
            LIMIT 10
            """
        )

        if not rows:
            logger.debug("[scheduler] auto-reanalyze: nicio firma eligibila")
            return

        logger.info(f"[scheduler] auto-reanalyze: {len(rows)} firme eligibile")

        for row in rows:
            company_id = row["id"]
            cui = row["cui"]
            name = row["name"] or f"Firma {cui}"

            if not cui:
                logger.debug(f"[scheduler] auto-reanalyze: skip company {company_id} (fara CUI)")
                continue

            try:
                job_id = str(uuid.uuid4())
                input_params = {"cui": cui, "company_name": name}

                # Creeaza job in DB
                await db.execute(
                    "INSERT INTO jobs (id, type, status, report_level, input_data, created_at) "
                    "VALUES (?, ?, 'PENDING', 2, ?, datetime('now'))",
                    (job_id, "FULL_COMPANY_PROFILE", json.dumps(input_params, ensure_ascii=False)),
                )

                # Porneste job-ul in background (fara WS — scheduler nu are conexiune WS)
                from backend.services.job_service import run_analysis_job
                asyncio.create_task(run_analysis_job(job_id, ws_manager=None))

                logger.info(f"[scheduler] auto-reanalyze: job {job_id} creat pentru {name} (CUI {cui})")

            except Exception as e:
                logger.error(f"[scheduler] auto-reanalyze: eroare la crearea job pentru {cui}: {e}")

    except Exception as e:
        logger.error(f"[scheduler] auto-reanalyze job error: {e}")


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
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        backup_path = backup_dir / f"ris_{date_str}.db"

        # Nu suprascrie backup din aceeasi zi
        if backup_path.exists():
            return

        # WAL checkpoint before backup — ensures WAL is flushed into main DB
        import aiosqlite
        async with aiosqlite.connect(str(db_path)) as conn:
            await conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            logger.info("[scheduler] WAL checkpoint completed")

        # sqlite3.backup() — safe chiar daca DB e in uz (WAL mode)
        src = sqlite3.connect(str(db_path))
        dst = sqlite3.connect(str(backup_path))
        src.backup(dst)
        dst.close()
        src.close()
        logger.info(f"[scheduler] DB backup created: {backup_path}")

        # Incremental VACUUM — recupereaza spatiu dupa DELETE-uri (non-blocking)
        async with aiosqlite.connect(str(db_path)) as conn:
            await conn.execute("PRAGMA incremental_vacuum(100)")
            logger.debug("[scheduler] Incremental vacuum completed")

        # Rotatie: pastreaza ultimele 7 zile
        backups = sorted(backup_dir.glob("ris_*.db"), reverse=True)
        for old in backups[7:]:
            old.unlink()
            logger.debug(f"[scheduler] Old backup removed: {old}")

    except Exception as e:
        logger.error(f"[scheduler] Backup error: {e}")
