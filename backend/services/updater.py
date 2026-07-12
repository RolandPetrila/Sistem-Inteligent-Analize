"""
Updater local — echivalentul „Vercel local" pentru RIS (app self-hosted, fara cloud).

Verifica git remote periodic; daca sunt commit-uri noi + tree curat + build reusit,
face `git pull --ff-only` + rebuild frontend + restart serviciu (proces DETASAT, ca sa
supravietuiasca stop-ului). Utilizatorul da doar refresh in PWA.

Safeguards:
  - nu trage peste modificari locale necomise (tree murdar -> abort);
  - `--ff-only` (fara merge-uri surpriza);
  - build verificat INAINTE de restart; la build esuat -> rollback la commit-ul anterior + rebuild;
  - stare cache-uita pentru /api/version (fara a lovi reteaua la fiecare request);
  - dezactivabil prin AUTO_UPDATE_ENABLED=false in .env.
"""

import subprocess
import sys
import time
from pathlib import Path

from loguru import logger

PROJECT_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_DIR / "frontend"
WINSW_EXE = PROJECT_DIR / "tools" / "RIS-Backend.exe"

_running_version: dict | None = None
_state: dict = {
    "local": None, "remote": None, "update_available": False,
    "behind": 0, "last_check": None, "updating": False, "last_result": None,
}


def _git(*args, timeout: int = 90) -> tuple[int, str]:
    # -c safe.directory=* : serviciul ruleaza ca NT AUTHORITY/SYSTEM, repo-ul e al userului ->
    # git refuza ("dubious ownership") fara aceasta exceptie (self-contained, fara config global).
    try:
        r = subprocess.run(
            ["git", "-c", "safe.directory=*", *args], cwd=str(PROJECT_DIR),
            capture_output=True, text=True, timeout=timeout,
        )
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:
        return 1, str(e)


def get_running_version() -> dict:
    """Versiunea codului care ruleaza ACUM (git SHA + data). Cache-uita — nu se schimba pana la restart."""
    global _running_version
    if _running_version is not None:
        return _running_version
    code, sha = _git("rev-parse", "--short", "HEAD", timeout=10)
    _, date = _git("log", "-1", "--format=%cd", "--date=short", timeout=10)
    _, branch = _git("rev-parse", "--abbrev-ref", "HEAD", timeout=10)
    ok = code == 0
    _running_version = {
        "sha": sha if ok else "unknown",
        "date": date if ok else "",
        "branch": branch or "?",
        "build": f"{date}-{sha}" if ok else "dev",
    }
    return _running_version


def get_state() -> dict:
    return dict(_state)


def _tree_clean() -> bool:
    """Tree curat pentru cod de APLICATIE. Ignora .claude/ (config local Claude, irelevant pt build)."""
    code, out = _git("status", "--porcelain", timeout=15)
    if code != 0:
        return False
    dirty = [ln for ln in out.splitlines() if ln.strip() and ".claude/" not in ln]
    return not dirty


async def check_remote() -> dict:
    """git fetch + compara local vs origin/<branch>. Actualizeaza starea cache. NU modifica nimic."""
    import asyncio

    def _sync() -> dict:
        branch = get_running_version()["branch"]
        _git("fetch", "--quiet", "origin", branch, timeout=60)
        _, local = _git("rev-parse", "HEAD", timeout=10)
        code_r, remote = _git("rev-parse", f"origin/{branch}", timeout=10)
        behind = 0
        if code_r == 0:
            code_c, cnt = _git("rev-list", "--count", f"HEAD..origin/{branch}", timeout=15)
            behind = int(cnt) if code_c == 0 and cnt.isdigit() else 0
        return {"local": local[:8], "remote": remote[:8] if code_r == 0 else None, "behind": behind}

    try:
        res = await asyncio.to_thread(_sync)
    except Exception as e:
        logger.warning(f"[updater] check_remote esuat: {e}")
        return dict(_state)
    _state.update(res)
    _state["update_available"] = res["behind"] > 0
    _state["last_check"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return dict(_state)


async def perform_update(reason: str = "manual") -> dict:
    """Pull + build + restart cu safeguards. git/npm sunt blocante -> rulate in thread."""
    import asyncio

    if _state.get("updating"):
        return {"ok": False, "error": "update deja in curs"}
    _state["updating"] = True
    try:
        result = await asyncio.to_thread(_perform_update_sync, reason)
        _state["last_result"] = result
        return result
    finally:
        _state["updating"] = False


def _perform_update_sync(reason: str) -> dict:
    logger.info(f"[updater] START ({reason})")
    if not _tree_clean():
        logger.warning("[updater] tree murdar (modificari locale necomise) -> abort")
        return {"ok": False, "error": "tree murdar - modificari locale necomise, update sarit"}

    _, pre_sha = _git("rev-parse", "HEAD", timeout=10)
    branch = get_running_version()["branch"]

    code, out = _git("pull", "--ff-only", "origin", branch, timeout=180)
    if code != 0:
        logger.error(f"[updater] pull esuat: {out[:200]}")
        return {"ok": False, "error": f"pull esuat: {out[:200]}"}

    _, post_sha = _git("rev-parse", "HEAD", timeout=10)
    if post_sha == pre_sha:
        logger.info("[updater] deja la zi (nimic de tras)")
        return {"ok": True, "changed": False, "note": "deja la zi"}

    logger.info(f"[updater] pull OK {pre_sha[:8]} -> {post_sha[:8]}. Build frontend...")
    b = subprocess.run("npm run build", shell=True, cwd=str(FRONTEND_DIR),
                       capture_output=True, text=True, timeout=600)
    if b.returncode != 0:
        logger.error(f"[updater] BUILD ESUAT -> rollback la {pre_sha[:8]}. stderr: {b.stderr[-300:]}")
        _git("reset", "--hard", pre_sha, timeout=30)
        subprocess.run("npm run build", shell=True, cwd=str(FRONTEND_DIR),
                       capture_output=True, text=True, timeout=600)  # restaureaza dist vechi
        return {"ok": False, "error": "build esuat - rollback aplicat, versiunea veche pastrata"}

    logger.info(f"[updater] build OK. Restart serviciu (detasat) pentru {post_sha[:8]}")
    _spawn_detached_restart()
    return {"ok": True, "changed": True, "from": pre_sha[:8], "to": post_sha[:8], "note": "restart in curs"}


def _spawn_detached_restart() -> None:
    """Proces DETASAT care repornaste serviciul dupa o scurta pauza (supravietuieste stop-ului WinSW)."""
    if sys.platform != "win32":
        logger.warning("[updater] restart automat suportat doar pe Windows")
        return
    if not WINSW_EXE.exists():
        logger.error(f"[updater] WinSW lipsa: {WINSW_EXE} — restart manual necesar")
        return
    breakaway = getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0x01000000)
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | breakaway
    cmd = f'timeout /t 4 /nobreak >nul & "{WINSW_EXE}" restart'
    try:
        subprocess.Popen(
            ["cmd", "/c", cmd], creationflags=flags, close_fds=True,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        logger.error(f"[updater] spawn restart esuat: {e}")
