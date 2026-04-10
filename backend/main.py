import asyncio
import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path as _Path

import aiofiles
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger

from backend import http_client
from backend.config import settings
from backend.database import db
from backend.errors import ERROR_HTTP_STATUS, RISError
from backend.middlewares import register_middlewares
from backend.routers import (
    analysis,
    ask,
    batch,
    companies,
    compare,
    documents,
    jobs,
    monitoring,
    notifications,
    reports,
)
from backend.routers import settings as settings_router
from backend.static_serving import mount_frontend_dist
from backend.ws import ws_manager

# --- Runtime log sink — captures startup, shutdown, 500 errors (not per-job) ---
_LOGS_DIR = _Path("logs")
_LOGS_DIR.mkdir(exist_ok=True)
if settings.log_format == "json":
    logger.add(
        str(_LOGS_DIR / "ris_runtime.json"),
        serialize=True,
        level="WARNING",
        rotation="5 MB",
        retention="7 days",
        encoding="utf-8",
    )
else:
    logger.add(
        str(_LOGS_DIR / "ris_runtime.log"),
        format="[{time:YYYY-MM-DD HH:mm:ss}] {level: <8} | {message}",
        level="WARNING",
        rotation="5 MB",
        retention="7 days",
        encoding="utf-8",
    )


# --- App lifespan ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("RIS starting up...")
    await db.connect()
    await db.run_migrations()
    await http_client.startup()

    from backend.services import cache_service
    await cache_service.cleanup_expired()
    logger.info("Cache: expired entries cleaned at startup")

    # Recover interrupted jobs
    interrupted = await db.fetch_all("SELECT id FROM jobs WHERE status = 'RUNNING'")
    for job in interrupted:
        await db.execute(
            "UPDATE jobs SET status = 'PAUSED', "
            "current_step = 'Intrerupt - necesita reluare manuala' "
            "WHERE id = ?",
            (job["id"],),
        )
        logger.warning(f"Job {job['id']} marked as PAUSED (interrupted)")

    # ADV1: Scheduler monitoring automat
    from backend.services.scheduler import start_scheduler, stop_scheduler
    scheduler_task = await start_scheduler()

    logger.info(f"RIS ready on port {settings.backend_port}")
    yield
    await stop_scheduler(scheduler_task)
    await http_client.shutdown()
    await db.close()
    logger.info("RIS shut down")


# --- FastAPI app ---

app = FastAPI(
    title="Roland Intelligence System API",
    description="Business Intelligence cu date publice romanesti — ANAF, ONRC, SEAP, BNR",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

register_middlewares(app)


# --- Exception handlers ---

@app.exception_handler(RISError)
async def ris_error_handler(request: Request, exc: RISError):
    """Transforma RISError in HTTP response cu status code corect."""
    request_id = getattr(request.state, "request_id", "unknown")
    status_code = ERROR_HTTP_STATUS.get(exc.code, 500)
    logger.warning(f"RISError [{exc.code.value}] [req={request_id}]: {exc.message}")
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": exc.message,
            "error_code": exc.code.value,
            "request_id": request_id,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """10F M11.2: Error Message Sanitization — never expose stack traces."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception(f"Unhandled error [req={request_id}]: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Eroare interna server. Contacteaza administratorul.",
            "error_code": "INTERNAL_ERROR",
            "request_id": request_id,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """10F M11.1: Structured validation errors without internal details."""
    request_id = getattr(request.state, "request_id", "unknown")
    errors = [
        {
            "field": " -> ".join(str(loc) for loc in err.get("loc", [])),
            "message": err.get("msg", "Invalid"),
            "type": err.get("type", ""),
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Date de intrare invalide",
            "error_code": "VALIDATION_ERROR",
            "errors": errors,
            "request_id": request_id,
        },
    )


# --- Routers ---
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(companies.router, prefix="/api/companies", tags=["Companies"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["Settings"])
app.include_router(compare.router, prefix="/api/compare", tags=["Compare"])
app.include_router(monitoring.router, prefix="/api/monitoring", tags=["Monitoring"])
app.include_router(batch.router, prefix="/api/batch", tags=["Batch"])
app.include_router(notifications.router)
app.include_router(ask.router)  # B1: NLQ Ask RIS Chatbot
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])  # E3: Mistral OCR


# --- Frontend Log Endpoint ---

_FRONTEND_LOG = _Path("logs") / "ris_frontend.log"


@app.post("/api/frontend-log")
async def frontend_log(request: Request):
    """Receives frontend log entries (errors, actions, API calls, validations, session).
    Writes to logs/ris_frontend.log — consolidated file for session review."""
    try:
        body = await request.json()
        entries = body if isinstance(body, list) else [body]

        # H4: aiofiles async — evita blocarea event loop la logging intens
        async with aiofiles.open(_FRONTEND_LOG, "a", encoding="utf-8") as f:
            for entry in entries:
                ts = entry.get("ts", "")
                level = entry.get("level", "INFO")
                page = entry.get("page", "-")
                message = entry.get("message", "")
                details = entry.get("details", "")

                if level == "SESSION":
                    await f.write(f"\n{'=' * 60}\n")
                    await f.write(f"SESSION | {ts} | {message}\n")
                    if details:
                        await f.write(f"  {details}\n")
                    await f.write(f"{'=' * 60}\n\n")
                else:
                    line = f"[{ts}] {level: <8} | {page: <20} | {message}"
                    if details:
                        line += f" | {details}"
                    await f.write(line + "\n")
                    if entry.get("stack"):
                        for sline in str(entry["stack"]).split("\n")[:5]:
                            await f.write(f"{'': <12} | {'': <20} | {sline.strip()}\n")

        return {"ok": True}
    except Exception as e:
        logger.debug(f"[frontend-log] write error: {e}")
        return {"ok": False}


@app.get("/api/frontend-log/recent")
async def get_frontend_log(lines: int = 200):
    """Returns last N lines from ris_frontend.log for in-app log viewer."""
    try:
        if not _FRONTEND_LOG.exists():
            return {"lines": [], "total": 0}
        async with aiofiles.open(_FRONTEND_LOG, encoding="utf-8", errors="replace") as f:
            content = await f.read()
        all_lines = content.splitlines()
        tail = all_lines[-lines:] if len(all_lines) > lines else all_lines
        return {"lines": tail, "total": len(all_lines)}
    except Exception as e:
        logger.debug(f"[frontend-log] read error: {e}")
        return {"lines": [], "total": 0}


# --- Health / Stats / Metrics ---

@app.get("/api/health")
async def health_check():
    """Health check simplu — raspuns rapid."""
    return {"status": "ok", "service": "RIS", "version": "3.2.0"}


@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    """G7: Prometheus-compatible metrics endpoint. Util pentru Grafana Cloud / local monitoring."""
    try:
        from prometheus_client import (
            CONTENT_TYPE_LATEST,
            CollectorRegistry,
            Gauge,
            generate_latest,
        )
        from starlette.responses import Response

        registry = CollectorRegistry()
        info = Gauge("ris_info", "RIS application info", ["version"], registry=registry)
        info.labels(version="3.2.0").set(1)

        try:
            stats_row = await db.fetch_one("SELECT COUNT(*) as c FROM jobs")
            jobs_total = Gauge("ris_jobs_total", "Total jobs in DB", registry=registry)
            jobs_total.set(stats_row["c"] if stats_row else 0)
        except Exception:
            pass

        try:
            companies_row = await db.fetch_one("SELECT COUNT(*) as c FROM companies")
            companies_total = Gauge("ris_companies_total", "Total companies", registry=registry)
            companies_total.set(companies_row["c"] if companies_row else 0)
        except Exception:
            pass

        return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)
    except ImportError:
        return {"error": "prometheus-client not installed"}


@app.get("/api/cache/stats")
async def get_cache_stats():
    """Cache statistics — total entries, size, per source breakdown."""
    from backend.services import cache_service
    return await cache_service.get_stats()


@app.get("/api/health/deep")
async def health_check_deep():
    """Health check avansat — verifica DB, APIs, quota, disk."""
    import shutil
    checks: dict = {"service": "RIS", "version": "3.1.0"}

    try:
        await db.execute("SELECT 1")
        checks["database"] = "OK"
    except Exception as e:
        checks["database"] = f"ERROR: {e}"

    try:
        from backend.http_client import get_client
        client = get_client()
        r = await client.get(
            "https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva", timeout=5
        )
        checks["anaf"] = "OK" if r.status_code in (200, 404) else f"HTTP {r.status_code}"
    except Exception as e:
        checks["anaf"] = f"UNREACHABLE: {e}"

    try:
        from backend.agents.tools.tavily_client import get_quota_status
        quota = await get_quota_status()
        checks["tavily_quota"] = f"{quota['used']}/{quota['quota']} ({quota['percent_used']}%)"
        checks["tavily_ok"] = quota["remaining"] > 0
    except Exception as e:
        logger.debug(f"[tavily_check] Non-critical: {e}")
        checks["tavily_quota"] = "N/A"

    try:
        disk = shutil.disk_usage(".")
        free_gb = disk.free / (1024**3)
        checks["disk_free_gb"] = round(free_gb, 1)
        checks["disk_ok"] = free_gb > 1.0
    except Exception as e:
        logger.debug(f"[disk] Non-critical: {e}")
        checks["disk_free_gb"] = "N/A"

    checks["ai_providers"] = {
        "claude_cli": settings.synthesis_mode == "claude_code",
        "groq": bool(settings.groq_api_key),
        "mistral": bool(settings.mistral_api_key),
        "gemini": bool(settings.google_ai_api_key),
        "cerebras": bool(settings.cerebras_api_key),
    }
    checks["ai_providers_count"] = sum(1 for v in checks["ai_providers"].values() if v)

    # 10F M10.3: HTTP Pool Metrics
    checks["http_pool"] = http_client.get_pool_metrics()

    all_ok = (
        checks.get("database") == "OK"
        and "OK" in str(checks.get("anaf", ""))
        and checks.get("disk_ok", False)
    )
    checks["status"] = "healthy" if all_ok else "degraded"
    return checks


@app.get("/health/status", include_in_schema=False)
async def health_status_page():
    """F3-13: Status page publica — nu include date sensibile, fara autentificare."""
    db_ok = True
    try:
        await db.fetch_one("SELECT 1 as ok")
    except Exception as e:
        logger.warning(f"[health] DB check failed: {e}")
        db_ok = False

    recent_jobs = await db.fetch_all(
        "SELECT status, completed_at FROM jobs ORDER BY created_at DESC LIMIT 5"
    )

    from backend.services.scheduler import get_scheduler_status
    try:
        scheduler_info = await get_scheduler_status()
    except Exception as e:
        logger.warning(f"[health] Scheduler check failed: {e}")
        scheduler_info = {"status": "unknown"}

    return {
        "status": "ok" if db_ok else "degraded",
        "timestamp": datetime.now(UTC).isoformat(),
        "components": {
            "api": "ok",
            "database": "ok" if db_ok else "error",
            "scheduler": scheduler_info.get("status", "ok"),
        },
        "recent_jobs": [
            {"status": j["status"], "completed": j["completed_at"]}
            for j in recent_jobs
        ],
    }


_stats_cache: dict | None = None
_stats_cache_time: float = 0
_stats_lock = asyncio.Lock()


@app.get("/api/stats")
async def get_stats():
    """Statistici globale — cached 30 secunde."""
    import time
    global _stats_cache, _stats_cache_time

    async with _stats_lock:
        now = time.time()
        if _stats_cache and (now - _stats_cache_time) < 30:
            return _stats_cache

        total_jobs = await db.fetch_one("SELECT COUNT(*) as c FROM jobs")
        completed = await db.fetch_one("SELECT COUNT(*) as c FROM jobs WHERE status = 'DONE'")
        total_reports = await db.fetch_one("SELECT COUNT(*) as c FROM reports")
        total_companies = await db.fetch_one("SELECT COUNT(*) as c FROM companies")
        this_month = await db.fetch_one(
            "SELECT COUNT(*) as c FROM jobs WHERE created_at >= date('now', 'start of month')"
        )
        _stats_cache = {
            "total_jobs": total_jobs["c"] if total_jobs else 0,
            "completed_jobs": completed["c"] if completed else 0,
            "total_reports": total_reports["c"] if total_reports else 0,
            "total_companies": total_companies["c"] if total_companies else 0,
            "jobs_this_month": this_month["c"] if this_month else 0,
        }
        _stats_cache_time = now
        return _stats_cache


@app.get("/api/stats/trend")
async def get_stats_trend():
    """Analize per luna ultimele 6 luni — pentru grafic Dashboard."""
    rows = await db.fetch_all(
        "SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count "
        "FROM jobs WHERE created_at >= date('now', '-6 months') "
        "GROUP BY month ORDER BY month"
    )
    return {"trend": [{"month": r["month"], "count": r["count"]} for r in rows]}


# --- WebSocket ---

@app.websocket("/ws/jobs/{job_id}")
async def websocket_job_progress(websocket: WebSocket, job_id: str):
    # SEC-01: First-message auth — token nu apare in query params (URL/logs)
    await websocket.accept()
    if settings.ris_api_key:
        try:
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
            msg = json.loads(raw)
            if msg.get("type") != "auth" or msg.get("token") != settings.ris_api_key:
                await websocket.close(code=4001, reason="Unauthorized")
                return
        except (TimeoutError, json.JSONDecodeError, Exception):
            await websocket.close(code=4001, reason="Unauthorized")
            return

    await ws_manager.connect(job_id, websocket, already_accepted=True)
    try:
        job = await db.fetch_one(
            "SELECT id, status, progress_percent, current_step FROM jobs WHERE id = ?",
            (job_id,),
        )
        if job:
            await websocket.send_text(json.dumps({
                "type": "progress",
                "job_id": job_id,
                "percent": job["progress_percent"],
                "step": job["current_step"],
                "status": job["status"],
            }, ensure_ascii=False))

        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        ws_manager.disconnect(job_id, websocket)
    except Exception as e:
        logger.debug(f"[ws_recv] Non-critical: {e}")
        ws_manager.disconnect(job_id, websocket)


# --- Frontend static serving (must be after all API routes) ---
mount_frontend_dist(app)


if __name__ == "__main__":
    import os

    import uvicorn
    is_dev = os.environ.get("RIS_ENV", "development") == "development"
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=settings.backend_port,
        reload=is_dev,
    )
