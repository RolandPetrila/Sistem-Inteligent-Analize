import asyncio
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from backend.database import db
from backend.rate_limiter import rate_limit_jobs
from backend.models import (
    JobCreate, JobResponse, JobListResponse, JobStatus
)
from backend.services.job_service import run_analysis_job

router = APIRouter()


@router.get("/diagnostics/latest")
async def get_latest_diagnostics():
    """CA6: Returneaza diagnosticul ultimului job completat."""
    row = await db.fetch_one(
        "SELECT id FROM jobs WHERE status = 'DONE' ORDER BY completed_at DESC LIMIT 1"
    )
    if not row:
        return {"error": "Niciun job completat", "diagnostics": None}

    from backend.routers.jobs import get_job_diagnostics
    return await get_job_diagnostics(row["id"])


@router.post("", response_model=JobResponse, dependencies=[Depends(rate_limit_jobs)])
async def create_job(data: JobCreate):
    job_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    await db.execute(
        """INSERT INTO jobs (id, type, status, input_data, report_level, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            job_id,
            data.analysis_type.value,
            JobStatus.PENDING.value,
            json.dumps(data.input_params, ensure_ascii=False),
            data.report_level.value,
            now,
        ),
    )
    return JobResponse(
        id=job_id,
        type=data.analysis_type.value,
        status=JobStatus.PENDING,
        report_level=data.report_level.value,
        input_data=data.input_params,
        created_at=now,
    )


@router.get("", response_model=JobListResponse)
async def list_jobs(
    status: str | None = None,
    limit: int = Query(default=20, le=100),
    offset: int = 0,
):
    where = ""
    params: list = []
    if status:
        where = "WHERE status = ?"
        params.append(status)

    total_row = await db.fetch_one(
        f"SELECT COUNT(*) as c FROM jobs {where}", tuple(params)
    )
    total = total_row["c"] if total_row else 0

    rows = await db.fetch_all(
        f"SELECT * FROM jobs {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        tuple(params + [limit, offset]),
    )

    jobs = []
    for row in rows:
        input_data = None
        if row["input_data"]:
            try:
                input_data = json.loads(row["input_data"])
            except (json.JSONDecodeError, TypeError):
                input_data = None
        jobs.append(
            JobResponse(
                id=row["id"],
                type=row["type"],
                status=row["status"],
                report_level=row["report_level"],
                input_data=input_data,
                created_at=row["created_at"] or "",
                started_at=row["started_at"],
                completed_at=row["completed_at"],
                error_message=row["error_message"],
                progress_percent=row["progress_percent"] or 0,
                current_step=row["current_step"],
            )
        )
    return JobListResponse(jobs=jobs, total=total)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    row = await db.fetch_one("SELECT * FROM jobs WHERE id = ?", (job_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")

    input_data = None
    if row["input_data"]:
        try:
            input_data = json.loads(row["input_data"])
        except (json.JSONDecodeError, TypeError):
            input_data = None

    return JobResponse(
        id=row["id"],
        type=row["type"],
        status=row["status"],
        report_level=row["report_level"],
        input_data=input_data,
        created_at=row["created_at"] or "",
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        error_message=row["error_message"],
        progress_percent=row["progress_percent"] or 0,
        current_step=row["current_step"],
    )


@router.post("/{job_id}/start")
async def start_job(job_id: str):
    row = await db.fetch_one("SELECT * FROM jobs WHERE id = ?", (job_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    if row["status"] not in (JobStatus.PENDING.value, JobStatus.PAUSED.value):
        raise HTTPException(status_code=400, detail=f"Cannot start job with status {row['status']}")

    # Import ws_manager from main
    from backend.main import ws_manager

    # Porneste executia in background
    asyncio.create_task(run_analysis_job(job_id, ws_manager=ws_manager))
    return {"status": "started", "job_id": job_id}


@router.get("/{job_id}/diagnostics")
async def get_job_diagnostics(job_id: str):
    """CA6: Returneaza diagnosticul completitudine si surse pentru un job."""
    row = await db.fetch_one("SELECT * FROM jobs WHERE id = ?", (job_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")

    # Cauta raportul asociat
    report = await db.fetch_one(
        "SELECT full_data FROM reports WHERE job_id = ? ORDER BY created_at DESC LIMIT 1",
        (job_id,),
    )

    diagnostics = {"job_id": job_id, "status": row["status"]}

    if report and report["full_data"]:
        try:
            full = json.loads(report["full_data"])
            diagnostics["completeness"] = full.get("completeness", {})
            diagnostics["risk_score"] = full.get("risk_score", {})

            # Extract official diagnostics if available
            company = full.get("company", {})
            if isinstance(company, dict):
                diag = company.get("diagnostics", {})
                if isinstance(diag, dict) and diag.get("value"):
                    diagnostics["source_diagnostics"] = diag["value"]
                elif isinstance(diag, dict):
                    diagnostics["source_diagnostics"] = diag
        except (json.JSONDecodeError, TypeError):
            diagnostics["parse_error"] = "Could not parse report data"

    # Check for job log file
    import os
    log_path = os.path.join("logs", f"job_{job_id}.log")
    if os.path.exists(log_path):
        diagnostics["log_file"] = log_path
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            diagnostics["log_lines"] = len(lines)
            # Last 20 lines as summary
            diagnostics["log_tail"] = [l.rstrip() for l in lines[-20:]]
        except Exception as e:
            logger.debug(f"[diagnostics] Log read failed: {e}")

    return diagnostics


@router.post("/{job_id}/retry-source/{source}")
async def retry_single_source(job_id: str, source: str):
    """CA7: Re-ruleaza o singura sursa esuata fara re-analiza completa."""
    row = await db.fetch_one("SELECT * FROM jobs WHERE id = ?", (job_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")

    input_data = {}
    if row["input_data"]:
        try:
            input_data = json.loads(row["input_data"])
        except (json.JSONDecodeError, TypeError):
            pass

    cui = input_data.get("cui", "").strip().replace("RO", "").replace("ro", "")

    # Map source names to fetch functions
    VALID_SOURCES = {
        "anaf": "ANAF TVA/Stare",
        "openapi": "openapi.ro ONRC",
        "bilant": "ANAF Bilant",
        "bnr": "BNR cursuri",
        "seap": "SEAP licitatii",
    }

    source_lower = source.lower().strip()
    if source_lower not in VALID_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Sursa necunoscuta: {source}. Surse valide: {list(VALID_SOURCES.keys())}",
        )

    if source_lower in ("anaf", "openapi", "bilant", "seap") and not cui:
        raise HTTPException(status_code=400, detail="CUI necesar pentru aceasta sursa")

    try:
        result = {}
        if source_lower == "anaf":
            from backend.agents.tools.anaf_client import get_anaf_data
            result = await get_anaf_data(cui)
        elif source_lower == "openapi":
            from backend.agents.tools.openapi_client import get_company_onrc
            result = await get_company_onrc(cui)
        elif source_lower == "bilant":
            from backend.agents.tools.anaf_bilant_client import get_bilant_multi_year
            result = await get_bilant_multi_year(cui)
        elif source_lower == "bnr":
            from backend.agents.tools.bnr_client import get_exchange_rates
            result = await get_exchange_rates()
        elif source_lower == "seap":
            from backend.agents.tools.seap_client import get_contracts_won
            result = await get_contracts_won(cui, use_cache=False)

        return {
            "job_id": job_id,
            "source": source_lower,
            "source_description": VALID_SOURCES[source_lower],
            "success": True,
            "data": result,
        }

    except Exception as e:
        # C19 fix: Sanitize error — don't leak raw exception details to client
        safe_error = str(e)[:100].split("\n")[0]  # First line, max 100 chars
        return {
            "job_id": job_id,
            "source": source_lower,
            "success": False,
            "error": f"Eroare la interogarea sursei: {safe_error}",
        }


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    row = await db.fetch_one("SELECT * FROM jobs WHERE id = ?", (job_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")

    # C20 fix: Don't allow canceling already-completed jobs
    if row["status"] in ("DONE", "ERROR", "FAILED"):
        raise HTTPException(status_code=400, detail=f"Job deja finalizat (status: {row['status']})")

    await db.execute(
        "UPDATE jobs SET status = ?, error_message = ? WHERE id = ?",
        (JobStatus.FAILED.value, "Anulat de utilizator", job_id),
    )
    return {"status": "cancelled", "job_id": job_id}
