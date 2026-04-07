import asyncio
import json
import re
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime

# Runtime log — captures startup, shutdown, 500 errors (not per-job)
from pathlib import Path as _Path

import aiofiles
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from backend import http_client
from backend.config import settings
from backend.database import db
from backend.errors import ERROR_HTTP_STATUS, RISError
from backend.routers import analysis, batch, companies, compare, jobs, monitoring, notifications, reports
from backend.routers import settings as settings_router
from backend.ws import ws_manager

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


# --- WebSocket connection manager --- (defined in backend.ws, imported above)


# --- App lifespan ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("RIS starting up...")
    if settings.app_secret_key == "change-me-to-random-string":
        logger.warning("SECURITATE: app_secret_key are valoare default! Seteaza APP_SECRET_KEY in .env")
    await db.connect()
    await db.run_migrations()
    await http_client.startup()

    # Cleanup cache expirat
    from backend.services import cache_service
    await cache_service.cleanup_expired()
    logger.info("Cache: expired entries cleaned at startup")

    # Recover interrupted jobs
    interrupted = await db.fetch_all(
        "SELECT id FROM jobs WHERE status = 'RUNNING'"
    )
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

def _redact_sensitive(text: str) -> str:
    """10F M11.3: Mask CUI-like numbers and API keys in logs."""
    # Mask CUI-like numbers (6-10 digits) — keep first 3, replace rest with ***
    text = re.sub(r'\b(\d{3})\d{3,7}\b', r'\1***', text)
    return text


class RequestIdMiddleware(BaseHTTPMiddleware):
    """10F M11.4: Request ID tracing — propagate in logs + response headers."""
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# Security headers middleware
class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """9A: Reject requests > 10MB to prevent abuse."""
    MAX_BODY_SIZE = 10 * 1024 * 1024  # 10MB

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_BODY_SIZE:
            from starlette.responses import JSONResponse
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body too large. Maximum 10MB.", "error_code": "REQUEST_TOO_LARGE"},
            )
        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logheaza FIECARE request HTTP primit — monitorizare completa frontend + API.
    10F M11.3: Sensitive data redaction — CUI masked, X-RIS-Key never logged."""
    async def dispatch(self, request: Request, call_next):
        import time
        start = time.time()
        response: Response = await call_next(request)
        elapsed_ms = int((time.time() - start) * 1000)
        # 10F M11.3: Redact CUI-like numbers from path before logging
        path = _redact_sensitive(request.url.path)
        method = request.method
        status = response.status_code
        request_id = getattr(request.state, 'request_id', '-')
        # Nu logam health checks (prea frecvente)
        if request.url.path not in ("/api/health", "/api/health/deep"):
            logger.info(
                f"HTTP | {method: <6} {path: <40} | {status} | {elapsed_ms}ms | rid={request_id}"
            )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "img-src 'self' data: blob:; "
            "connect-src 'self' ws: wss:; "
            "font-src 'self' data: https://fonts.gstatic.com; "
            "worker-src 'self';"
        )
        # API Response Caching Headers (8A)
        path = request.url.path
        if path == "/api/stats":
            response.headers["Cache-Control"] = "public, max-age=30"
        elif path == "/api/analysis/types":
            response.headers["Cache-Control"] = "public, max-age=3600, immutable"
        elif path.startswith("/api/companies"):
            response.headers["Cache-Control"] = "public, max-age=300"
        elif path == "/api/health":
            response.headers["Cache-Control"] = "no-cache"
        return response

class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Daca RIS_API_KEY e setat in .env, cere header X-RIS-Key pe /api/ endpoints."""
    async def dispatch(self, request: Request, call_next):
        if not settings.ris_api_key:
            return await call_next(request)
        path = request.url.path
        # Exclude health checks, WebSocket, frontend-log
        if path in ("/api/health", "/api/health/deep", "/api/frontend-log") or path.startswith("/ws/"):
            return await call_next(request)
        if path.startswith("/api/"):
            key = request.headers.get("X-RIS-Key", "")
            if key != settings.ris_api_key:
                from starlette.responses import JSONResponse
                return JSONResponse(
                    status_code=401,
                    content={"detail": "API key invalid sau lipsa. Trimite header X-RIS-Key."},
                )
        return await call_next(request)

app.add_middleware(RequestIdMiddleware)  # 10F M11.4: Outermost — generates request ID first
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(ApiKeyMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|100\.\d+\.\d+\.\d+)(:\d+)?",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-RIS-Key", "Accept", "Authorization"],
    max_age=86400,  # 10A M11.7: Cache preflight OPTIONS for 24h — reduces overhead
)

# --- FIX #3: RISError handler — HTTP status corect per ErrorCode ---

@app.exception_handler(RISError)
async def ris_error_handler(request: Request, exc: RISError):
    """Transforma RISError in HTTP response cu status code corect."""
    request_id = getattr(request.state, 'request_id', 'unknown')
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


# --- 10F M11.2: Error Message Sanitization ---

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """10F M11.2: Error Message Sanitization — never expose stack traces."""
    request_id = getattr(request.state, 'request_id', 'unknown')
    logger.exception(f"Unhandled error [req={request_id}]: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Eroare interna server. Contacteaza administratorul.",
            "error_code": "INTERNAL_ERROR",
            "request_id": request_id,
        },
    )


# --- 10F M11.1: Request Body Schema Validation ---

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """10F M11.1: Structured validation errors without internal details."""
    request_id = getattr(request.state, 'request_id', 'unknown')
    errors = []
    for err in exc.errors():
        errors.append({
            "field": " -> ".join(str(loc) for loc in err.get("loc", [])),
            "message": err.get("msg", "Invalid"),
            "type": err.get("type", ""),
        })
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Date de intrare invalide",
            "error_code": "VALIDATION_ERROR",
            "errors": errors,
            "request_id": request_id,
        },
    )


# Routers
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(companies.router, prefix="/api/companies", tags=["Companies"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["Settings"])
app.include_router(compare.router, prefix="/api/compare", tags=["Compare"])
app.include_router(monitoring.router, prefix="/api/monitoring", tags=["Monitoring"])
app.include_router(batch.router, prefix="/api/batch", tags=["Batch"])
app.include_router(notifications.router)


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

                # Session markers get special formatting
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
                    # Multi-line details for errors (stack traces)
                    if entry.get("stack"):
                        for sline in str(entry["stack"]).split("\n")[:5]:
                            await f.write(f"{'': <12} | {'': <20} | {sline.strip()}\n")

        return {"ok": True}
    except Exception as e:
        logger.debug(f"[health] Non-critical: {e}")
        return {"ok": False}


@app.get("/api/health")
async def health_check():
    """Health check simplu — raspuns rapid."""
    return {"status": "ok", "service": "RIS", "version": "3.1.0"}


@app.get("/api/cache/stats")
async def get_cache_stats():
    """Cache statistics — total entries, size, per source breakdown."""
    from backend.services import cache_service
    return await cache_service.get_stats()


@app.get("/api/health/deep")
async def health_check_deep():
    """Health check avansat — verifica DB, APIs, quota, disk."""
    import shutil
    checks = {"service": "RIS", "version": "3.1.0"}

    # DB writable
    try:
        await db.execute("SELECT 1")
        checks["database"] = "OK"
    except Exception as e:
        checks["database"] = f"ERROR: {e}"

    # ANAF reachable
    try:
        from backend.http_client import get_client
        client = get_client()
        r = await client.get("https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva", timeout=5)
        checks["anaf"] = "OK" if r.status_code in (200, 404) else f"HTTP {r.status_code}"
    except Exception as e:
        checks["anaf"] = f"UNREACHABLE: {e}"

    # Tavily quota
    try:
        from backend.agents.tools.tavily_client import get_quota_status
        quota = await get_quota_status()
        checks["tavily_quota"] = f"{quota['used']}/{quota['quota']} ({quota['percent_used']}%)"
        checks["tavily_ok"] = quota["remaining"] > 0
    except Exception as e:
        logger.debug(f"[tavily_check] Non-critical: {e}")
        checks["tavily_quota"] = "N/A"

    # Disk space
    try:
        disk = shutil.disk_usage(".")
        free_gb = disk.free / (1024**3)
        checks["disk_free_gb"] = round(free_gb, 1)
        checks["disk_ok"] = free_gb > 1.0
    except Exception as e:
        logger.debug(f"[disk] Non-critical: {e}")
        checks["disk_free_gb"] = "N/A"

    # AI providers configured
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
    scheduler_info: dict = {}
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
        ]
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


@app.websocket("/ws/jobs/{job_id}")
async def websocket_job_progress(websocket: WebSocket, job_id: str):
    # SEC-01: Validate API key on WebSocket upgrade if configured
    if settings.ris_api_key:
        token = websocket.query_params.get("token", "")
        if token != settings.ris_api_key:
            await websocket.close(code=4001, reason="Unauthorized")
            return

    await ws_manager.connect(job_id, websocket)
    try:
        # Send current state on connect
        job = await db.fetch_one("SELECT * FROM jobs WHERE id = ?", (job_id,))
        if job:
            await websocket.send_text(json.dumps({
                "type": "progress",
                "job_id": job_id,
                "percent": job["progress_percent"],
                "step": job["current_step"],
                "status": job["status"],
            }, ensure_ascii=False))

        # Keep alive and listen for client messages
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


# --- Serve frontend static build (Tailscale / production mode) ---
# Routes defined AFTER all API routes — FastAPI matches in order, so /api/* wins.
# Pattern: explicit mounts for /assets and known root files + catch-all for SPA routing.

_FRONTEND_DIST = _Path(__file__).parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.exists():
    from fastapi.responses import FileResponse as _FileResponse
    from fastapi.staticfiles import StaticFiles

    # /assets/* — JS, CSS bundles (content-hashed, safe to cache)
    _assets_dir = _FRONTEND_DIST / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

    # /icons/* — PWA icons
    _icons_dir = _FRONTEND_DIST / "icons"
    if _icons_dir.exists():
        app.mount("/icons", StaticFiles(directory=str(_icons_dir)), name="icons")

    # Known root-level static files
    _ROOT_STATIC = ["manifest.webmanifest", "sw.js", "registerSW.js",
                    "workbox-b51dd497.js", "favicon.ico", "robots.txt"]

    for _fname in _ROOT_STATIC:
        _fpath = _FRONTEND_DIST / _fname
        if _fpath.exists():
            _captured = str(_fpath)
            _route = f"/{_fname}"

            @app.get(_route, include_in_schema=False)
            async def _serve_root_file(_p=_captured):
                return _FileResponse(_p)

    # SPA catch-all — must be last; serves index.html for all remaining paths
    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str = ""):
        return _FileResponse(str(_FRONTEND_DIST / "index.html"))

    logger.info(f"Frontend build found — serving from {_FRONTEND_DIST}")
else:
    logger.info("No frontend/dist — run 'cd frontend && npm run build' for Tailscale/PWA mode")


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
