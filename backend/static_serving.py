"""
Frontend static asset serving for Tailscale / production mode.

Extras din `main.py` (Gemini-audit follow-up). Daca `frontend/dist` exista,
monteaza:
- /assets/* (bundle JS/CSS cu content hash)
- /icons/*  (PWA icons)
- fisiere cunoscute la root (manifest, sw.js, favicon etc.)
- catch-all SPA routing → index.html
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

_ROOT_STATIC_FILES = (
    "manifest.webmanifest",
    "sw.js",
    "registerSW.js",
    "workbox-b51dd497.js",
    "favicon.ico",
    "robots.txt",
)


def mount_frontend_dist(app: FastAPI) -> None:
    """Monteaza routes statice + SPA catch-all pentru build-ul React."""
    dist_dir = Path(__file__).parent.parent / "frontend" / "dist"

    if not dist_dir.exists():
        logger.info("No frontend/dist — run 'cd frontend && npm run build' for Tailscale/PWA mode")
        return

    # /assets/*
    assets_dir = dist_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # /icons/*
    icons_dir = dist_dir / "icons"
    if icons_dir.exists():
        app.mount("/icons", StaticFiles(directory=str(icons_dir)), name="icons")

    # Root-level static files (manifest, sw, favicon etc.)
    for fname in _ROOT_STATIC_FILES:
        fpath = dist_dir / fname
        if fpath.exists():
            captured = str(fpath)

            @app.get(f"/{fname}", include_in_schema=False)
            async def _serve_root_file(_p: str = captured):
                return FileResponse(_p)

    # SPA catch-all — trebuie sa fie ULTIMUL route
    index_path = str(dist_dir / "index.html")

    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str = ""):
        return FileResponse(index_path)

    logger.info(f"Frontend build found — serving from {dist_dir}")
