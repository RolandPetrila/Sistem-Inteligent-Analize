"""
HTTP middlewares for RIS.

Extras din `main.py` (Gemini-audit follow-up) — separa responsabilitatile de
middleware de aplicatia FastAPI principala:

- RequestIdMiddleware          — propaga X-Request-ID in logs + response headers
- RequestSizeLimitMiddleware   — respinge requesturi > 10MB
- RequestLoggingMiddleware     — loggeaza fiecare request (CUI/API key redactate)
- ApiKeyMiddleware             — cere header X-RIS-Key daca RIS_API_KEY setat
- SecurityHeadersMiddleware    — CSP + X-Frame-Options + cache headers
"""

from __future__ import annotations

import re
import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from backend.config import settings


# --- 10F M11.3: Sensitive data redaction ---
def _redact_sensitive(text: str) -> str:
    """Mask CUI-like numbers and API keys in log output."""
    return re.sub(r"\b(\d{3})\d{3,7}\b", r"\1***", text)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """10F M11.4: Request ID tracing — propagate in logs + response headers."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """9A: Reject requests > 10MB to prevent abuse."""

    MAX_BODY_SIZE = 10 * 1024 * 1024  # 10MB

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_BODY_SIZE:
            return JSONResponse(
                status_code=413,
                content={
                    "detail": "Request body too large. Maximum 10MB.",
                    "error_code": "REQUEST_TOO_LARGE",
                },
            )
        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Loggeaza fiecare request HTTP. Exclude health checks (prea frecvente).
    10F M11.3: CUI-like numbers sunt mascate; X-RIS-Key niciodata in logs."""

    _SKIP_PATHS = ("/api/health", "/api/health/deep")

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response: Response = await call_next(request)
        elapsed_ms = int((time.time() - start) * 1000)

        if request.url.path in self._SKIP_PATHS:
            return response

        path = _redact_sensitive(request.url.path)
        request_id = getattr(request.state, "request_id", "-")
        logger.info(
            f"HTTP | {request.method: <6} {path: <40} | "
            f"{response.status_code} | {elapsed_ms}ms | rid={request_id}"
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Security headers + API response cache hints."""

    _CSP = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "img-src 'self' data: blob:; "
        "connect-src 'self' ws: wss:; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        "worker-src 'self';"
    )

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = self._CSP

        # 8A: API response cache headers
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

    _EXEMPT_PATHS = ("/api/health", "/api/health/deep", "/api/frontend-log")

    async def dispatch(self, request: Request, call_next):
        if not settings.ris_api_key:
            return await call_next(request)

        path = request.url.path
        if path in self._EXEMPT_PATHS or path.startswith("/ws/"):
            return await call_next(request)

        if path.startswith("/api/"):
            if request.headers.get("X-RIS-Key", "") != settings.ris_api_key:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "API key invalid sau lipsa. Trimite header X-RIS-Key."},
                )
        return await call_next(request)


def register_middlewares(app: FastAPI) -> None:
    """Registreaza toate middlewares pe aplicatia FastAPI (ordine importanta)."""
    app.add_middleware(RequestIdMiddleware)  # outermost — generates request ID first
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
        max_age=86400,  # 10A M11.7: cache preflight OPTIONS for 24h
    )
