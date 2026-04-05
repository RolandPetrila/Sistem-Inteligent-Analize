"""
DF8: Batch Analysis — Upload CSV cu CUI-uri, analiza in serie, ZIP cu rapoarte.
Progress persistent in DB (nu in-memory).
"""

import asyncio
import csv
import io
import json
import uuid
import zipfile
from datetime import datetime, date, UTC
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from loguru import logger

from backend.database import db
from backend.config import settings
from backend.agents.tools.cui_validator import validate_cui
from backend.rate_limiter import rate_limit_batch
from backend.errors import RISError, ErrorCode

router = APIRouter()

# 10F M8.3: Parallel Analysis — max CUI-uri procesate simultan intr-un batch
MAX_PARALLEL_BATCH = 2


async def _get_batch_progress(batch_id: str) -> dict:
    """Citeste batch progress din DB (input_data JSON)."""
    row = await db.fetch_one("SELECT input_data FROM jobs WHERE id = ?", (batch_id,))
    if not row or not row["input_data"]:
        return {}
    try:
        data = json.loads(row["input_data"])
        return data.get("batch_progress", {})
    except (json.JSONDecodeError, TypeError):
        return {}


async def _update_batch_progress(batch_id: str, progress: dict):
    """Salveaza batch progress in DB (input_data JSON)."""
    row = await db.fetch_one("SELECT input_data FROM jobs WHERE id = ?", (batch_id,))
    if not row:
        return
    try:
        data = json.loads(row["input_data"]) if row["input_data"] else {}
    except (json.JSONDecodeError, TypeError):
        data = {}
    data["batch_progress"] = progress
    await db.execute(
        "UPDATE jobs SET input_data = ? WHERE id = ?",
        (json.dumps(data, ensure_ascii=False), batch_id),
    )


@router.post("", dependencies=[Depends(rate_limit_batch)])
async def create_batch(
    file: UploadFile = File(...),
    analysis_type: str = Query(default="COMPANY_PROFILE"),
    report_level: int = Query(default=2, ge=1, le=3),
    refresh: bool = Query(default=False, description="Skip cache, fetch fresh data"),  # 10F M8.5
):
    """Upload CSV cu CUI-uri si porneste batch analysis."""
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Fisierul trebuie sa fie CSV")

    content = await file.read()
    text = content.decode("utf-8-sig", errors="replace")

    # 10E M8.2: CSV Pre-validation — parse, validate, report issues BEFORE starting
    raw_lines = []
    invalid_lines = []
    reader = csv.reader(io.StringIO(text))
    for line_num, row in enumerate(reader, 1):
        if not row:
            continue
        raw_val = row[0].strip()
        # Strip RO prefix, spaces
        val = raw_val.upper().replace("RO", "").replace(" ", "")
        if not val:
            continue
        if not val.isdigit() or not (2 <= len(val) <= 10):
            invalid_lines.append({"line": line_num, "value": raw_val, "reason": "Format invalid"})
            continue
        validation = validate_cui(val)
        if not validation["valid"]:
            invalid_lines.append({"line": line_num, "value": raw_val, "reason": validation.get("error", "CUI invalid")})
            continue
        raw_lines.append(val)

    if not raw_lines:
        raise HTTPException(status_code=400, detail="Niciun CUI valid gasit in CSV")

    # Detect duplicates before dedup
    seen = {}
    duplicates = []
    for cui in raw_lines:
        if cui in seen:
            duplicates.append(cui)
        else:
            seen[cui] = True
    cuis = list(seen.keys())

    if len(cuis) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 CUI-uri per batch")

    # B21 fix: Auto-timeout stuck batches (RUNNING > 4 hours) before checking limit
    four_hours_ago = (datetime.now(UTC).timestamp() - 4 * 3600)
    stuck = await db.fetch_all(
        "SELECT id FROM jobs WHERE type LIKE 'BATCH_%' AND status = 'RUNNING' AND started_at IS NOT NULL"
    )
    for row in stuck:
        try:
            started = await db.fetch_one("SELECT started_at FROM jobs WHERE id = ?", (row["id"],))
            if started and started["started_at"]:
                started_ts = datetime.fromisoformat(started["started_at"]).timestamp()
                if started_ts < four_hours_ago:
                    await db.execute(
                        "UPDATE jobs SET status = 'ERROR', error_message = 'Timeout: batch blocat > 4h' WHERE id = ?",
                        (row["id"],),
                    )
                    logger.warning(f"[batch] Auto-timeout stuck batch {row['id'][:8]}")
        except Exception as e:
            logger.debug(f"[batch] Timeout check failed: {e}")

    # 10F M8.4: Batch Queue — max 2 concurrent batches
    active = await db.fetch_one(
        "SELECT COUNT(*) as c FROM jobs WHERE type LIKE 'BATCH_%' AND status = 'RUNNING'"
    )
    if active and active["c"] >= 2:
        raise RISError(ErrorCode.RATE_LIMITED, "Maximum 2 batch-uri active simultan. Asteapta finalizarea.")

    batch_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    # Salveaza batch in DB cu progress initial
    input_data = {
        "cuis": cuis,
        "analysis_type": analysis_type,
        "refresh": refresh,  # 10F M8.5: Fresh Data Option
        "batch_progress": {
            "total": len(cuis),
            "completed": 0,
            "failed": 0,
            "current_cui": "",
        },
    }
    await db.execute(
        """INSERT INTO jobs (id, type, status, input_data, report_level, created_at, current_step)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            batch_id,
            f"BATCH_{analysis_type}",
            "PENDING",
            json.dumps(input_data, ensure_ascii=False),
            report_level,
            now,
            f"Batch creat: {len(cuis)} firme",
        ),
    )

    # Porneste executia in background
    from backend.main import ws_manager
    asyncio.create_task(_run_batch(batch_id, cuis, analysis_type, report_level, ws_manager, refresh=refresh))

    # 10E M8.2: Include validation warnings in response
    validation_warnings = {}
    if duplicates:
        validation_warnings["duplicates_removed"] = list(set(duplicates))
    if invalid_lines:
        validation_warnings["invalid_lines"] = invalid_lines[:10]  # Max 10

    return {
        "batch_id": batch_id,
        "total_cuis": len(cuis),
        "cuis": cuis,
        "status": "started",
        **({"warnings": validation_warnings} if validation_warnings else {}),
    }


@router.get("/{batch_id}")
async def get_batch_status(batch_id: str):
    """Status batch analysis — citeste din DB (persistent)."""
    row = await db.fetch_one("SELECT * FROM jobs WHERE id = ?", (batch_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Batch not found")

    progress = await _get_batch_progress(batch_id)

    return {
        "batch_id": batch_id,
        "status": row["status"],
        "progress_percent": row["progress_percent"] or 0,
        "current_step": row["current_step"],
        "total": progress.get("total", 0),
        "completed": progress.get("completed", 0),
        "failed": progress.get("failed", 0),
        "current_cui": progress.get("current_cui", ""),
    }


@router.post("/{batch_id}/resume")
async def resume_batch(batch_id: str):
    """9E: Resume a failed/paused batch — re-runs only failed CUIs."""
    row = await db.fetch_one("SELECT * FROM jobs WHERE id = ?", (batch_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Batch not found")

    if row["status"] not in ("DONE", "ERROR", "PAUSED"):
        raise HTTPException(status_code=400, detail=f"Batch status is {row['status']}, cannot resume")

    progress = await _get_batch_progress(batch_id)
    results = progress.get("results", [])
    failed_cuis = [r["cui"] for r in results if r.get("status") == "FAILED"]

    if not failed_cuis:
        return {"batch_id": batch_id, "message": "No failed CUIs to retry", "resumed": 0}

    # Parse original settings
    try:
        input_data = json.loads(row["input_data"]) if row["input_data"] else {}
    except (json.JSONDecodeError, TypeError):
        input_data = {}

    analysis_type = input_data.get("analysis_type", "COMPANY_PROFILE")
    report_level = row["report_level"] or 2

    # Reset batch status
    await db.execute(
        "UPDATE jobs SET status = 'RUNNING', current_step = ? WHERE id = ?",
        (f"Resuming: {len(failed_cuis)} CUI-uri esuate", batch_id),
    )

    # 10F M8.5: Preserve refresh flag from original batch
    refresh = input_data.get("refresh", False)

    from backend.main import ws_manager
    asyncio.create_task(_run_batch(batch_id, failed_cuis, analysis_type, report_level, ws_manager, refresh=refresh))

    return {
        "batch_id": batch_id,
        "resumed": len(failed_cuis),
        "cuis": failed_cuis,
        "status": "resuming",
    }


@router.get("/{batch_id}/download")
async def download_batch_zip(batch_id: str):
    """Download ZIP cu toate rapoartele din batch."""
    zip_path = (Path(settings.outputs_dir) / batch_id / "batch_rapoarte.zip").resolve()
    outputs_root = Path(settings.outputs_dir).resolve()
    if not str(zip_path).startswith(str(outputs_root)):
        raise HTTPException(status_code=403, detail="Access denied")
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="ZIP not ready or batch not completed")

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"batch_{batch_id[:8]}.zip",
    )


async def _extract_batch_summary_row(result: dict) -> list:
    """8D: Extrage date sumar din raportul sub-job pentru Rich Summary CSV."""
    cui = result["cui"]
    status = result["status"]
    error = result.get("error", "")

    if status != "OK":
        return [cui, "", "", "", "", "", "", "", "", status, error]

    try:
        report = await db.fetch_one(
            "SELECT full_data, risk_score FROM reports WHERE job_id = ? LIMIT 1",
            (result["job_id"],),
        )
        if not report or not report["full_data"]:
            return [cui, "", "", "", "", "", "", "", "", status, ""]

        data = json.loads(report["full_data"])
        company = data.get("company", {})
        financial = data.get("financial", {})

        def _v(field):
            if isinstance(field, dict):
                return field.get("value", "")
            return field or ""

        denumire = _v(company.get("denumire", {}))
        caen = _v(company.get("caen_code", {}))
        # D15 fix: Include CAEN description
        caen_desc = _v(company.get("caen_description", {}))
        ca = _v(financial.get("cifra_afaceri", {}))
        pn = _v(financial.get("profit_net", {}))
        ang = _v(financial.get("numar_angajati", {}))
        risk = data.get("risk_score", {})
        score = risk.get("numeric_score", "")
        color = risk.get("score", "")

        return [cui, denumire, caen, caen_desc, ca, pn, ang, score, color, status, ""]
    except Exception as e:
        logger.warning(f"[batch] CSV row build: {e}")
        return [cui, "", "", "", "", "", "", "", "", status, ""]


async def _analyze_one_cui(
    sem: asyncio.Semaphore,
    cui: str,
    analysis_type: str,
    report_level: int,
    refresh: bool,
) -> dict:
    """10F M8.3: Analizeaza un singur CUI cu semaphore rate limiting si retry logic."""
    from backend.services.job_service import run_analysis_job

    async with sem:
        sub_job_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        input_params = {"cui": cui, "refresh": refresh}  # 10F M8.5: Fresh Data Option

        await db.execute(
            """INSERT INTO jobs (id, type, status, input_data, report_level, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (sub_job_id, analysis_type, "PENDING", json.dumps(input_params), report_level, now),
        )

        # 8D: Retry logic — max 2 retries with backoff
        max_retries = 2
        last_error = ""
        for attempt in range(1 + max_retries):
            try:
                await run_analysis_job(sub_job_id, ws_manager=None)
                return {"cui": cui, "job_id": sub_job_id, "status": "OK"}
            except Exception as e:
                last_error = str(e)[:200]
                if attempt < max_retries:
                    logger.warning(f"[batch] CUI {cui} attempt {attempt+1} failed: {e}, retrying...")
                    await asyncio.sleep(3 * (attempt + 1))
                    # Reset job status for retry
                    await db.execute(
                        "UPDATE jobs SET status = 'PENDING', error_message = NULL WHERE id = ?",
                        (sub_job_id,),
                    )

        logger.warning(f"[batch] CUI {cui} failed after {max_retries+1} attempts: {last_error}")
        return {"cui": cui, "job_id": sub_job_id, "status": "FAILED", "error": last_error}


async def _run_batch(
    batch_id: str,
    cuis: list[str],
    analysis_type: str,
    report_level: int,
    ws_manager,
    refresh: bool = False,  # 10F M8.5: Fresh Data Option
):
    """Executa analiza pentru CUI-uri in paralel (chunks). Progress persistent in DB."""
    # C13 fix: Top-level try/except so batch doesn't stay RUNNING on unexpected errors
    try:
        await _run_batch_inner(batch_id, cuis, analysis_type, report_level, ws_manager, refresh=refresh)
    except Exception as e:
        logger.error(f"[batch] {batch_id[:8]}: Top-level error: {e}")
        await db.execute(
            "UPDATE jobs SET status = 'ERROR', error_message = ?, completed_at = ? WHERE id = ?",
            (f"Eroare neasteptata: {str(e)[:200]}", datetime.now(UTC).isoformat(), batch_id),
        )


async def _run_batch_inner(
    batch_id: str,
    cuis: list[str],
    analysis_type: str,
    report_level: int,
    ws_manager,
    refresh: bool = False,
):
    """Inner batch execution — called by _run_batch with error protection."""
    total = len(cuis)
    batch_dir = Path(settings.outputs_dir) / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)

    await db.execute(
        "UPDATE jobs SET status = 'RUNNING', started_at = ? WHERE id = ?",
        (datetime.now(UTC).isoformat(), batch_id),
    )

    # C14 fix: Load existing results from progress (for resume scenarios)
    existing_progress = await _get_batch_progress(batch_id)
    existing_results = existing_progress.get("results", [])
    completed = sum(1 for r in existing_results if r.get("status") == "OK")
    failed = sum(1 for r in existing_results if r.get("status") == "FAILED")
    results = list(existing_results)

    # 10F M8.3: Parallel Analysis — process CUIs in chunks of MAX_PARALLEL_BATCH
    sem = asyncio.Semaphore(MAX_PARALLEL_BATCH)

    for chunk_start in range(0, total, MAX_PARALLEL_BATCH):
        chunk = cuis[chunk_start:chunk_start + MAX_PARALLEL_BATCH]
        chunk_end = min(chunk_start + len(chunk), total)

        logger.info(f"[batch] {batch_id[:8]}: Processing chunk {chunk_start+1}-{chunk_end}/{total} — CUIs {chunk}")

        progress_pct = int((chunk_start / total) * 100)

        # 10E M8.1: State checkpoint — save last successful CUI index for crash recovery
        await _update_batch_progress(batch_id, {
            "total": total,
            "completed": completed,
            "failed": failed,
            "current_cui": ", ".join(chunk),
            "last_index": chunk_start,
            "results": results,
        })
        await db.execute(
            "UPDATE jobs SET progress_percent = ?, current_step = ? WHERE id = ?",
            (progress_pct, f"Analiza {chunk_start+1}-{chunk_end}/{total}: CUI {', '.join(chunk)}", batch_id),
        )
        if ws_manager:
            await ws_manager.broadcast(batch_id, {
                "type": "progress",
                "job_id": batch_id,
                "percent": progress_pct,
                "step": f"Analiza {chunk_start+1}-{chunk_end}/{total}: CUI {', '.join(chunk)}",
                "status": "RUNNING",
            })

        # 10F M8.3: Fire all CUIs in chunk in parallel via asyncio.gather
        # B20 fix: return_exceptions=True so one failure doesn't crash entire batch
        chunk_results = await asyncio.gather(
            *[
                _analyze_one_cui(sem, cui, analysis_type, report_level, refresh)
                for cui in chunk
            ],
            return_exceptions=True,
        )

        for idx, result in enumerate(chunk_results):
            if isinstance(result, BaseException):
                # B20: Unhandled exception from gather — treat as failed
                failed_cui = chunk[idx] if idx < len(chunk) else "unknown"
                results.append({"cui": failed_cui, "job_id": "", "status": "FAILED", "error": str(result)[:200]})
                failed += 1
            else:
                results.append(result)
                if result["status"] == "OK":
                    completed += 1
                else:
                    failed += 1

    # Genereaza ZIP cu toate rapoartele
    zip_path = batch_dir / "batch_rapoarte.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for result in results:
            if result["status"] != "OK":
                continue
            sub_dir = Path(settings.outputs_dir) / result["job_id"]
            if sub_dir.exists():
                for file in sub_dir.iterdir():
                    if file.is_file():
                        arcname = f"{result['cui']}/{file.name}"
                        zf.write(file, arcname)

        # 8D: Rich Summary CSV — include CA, profit, risk score, CAEN
        summary = io.StringIO()
        writer = csv.writer(summary)
        # D15 fix: Added CAEN Descriere column
        writer.writerow(["CUI", "Denumire", "CAEN", "CAEN Descriere", "CA", "Profit Net", "Angajati",
                         "Scor Risc", "Culoare Risc", "Status", "Error"])
        for r in results:
            # Extract data from sub-job report if available
            row_data = await _extract_batch_summary_row(r)
            writer.writerow(row_data)
        zf.writestr("_sumar_batch.csv", summary.getvalue())

    # Update final progress in DB
    await _update_batch_progress(batch_id, {
        "total": total,
        "completed": completed,
        "failed": failed,
        "current_cui": "",
        "results": results,
    })

    await db.execute(
        "UPDATE jobs SET status = 'DONE', progress_percent = 100, "
        "current_step = ?, completed_at = ? WHERE id = ?",
        (f"Batch complet: {completed} OK, {failed} erori din {total}", datetime.now(UTC).isoformat(), batch_id),
    )

    if ws_manager:
        await ws_manager.broadcast(batch_id, {
            "type": "progress",
            "job_id": batch_id,
            "percent": 100,
            "step": f"Batch complet: {completed}/{total}",
            "status": "DONE",
        })

    logger.info(f"[batch] {batch_id[:8]}: Done — {completed} OK, {failed} failed, ZIP: {zip_path}")
