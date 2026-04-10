"""
Job Service — Logica de executie a job-urilor.
Porneste LangGraph, broadcast progress via WebSocket, update DB.
"""

import ctypes
import json
import socket
from datetime import UTC, datetime
from ipaddress import AddressValueError, ip_address
from urllib.parse import urlparse

from loguru import logger

from backend.agents.orchestrator import build_analysis_graph
from backend.agents.state import AnalysisState, get_agents_needed
from backend.database import db
from backend.services import cache_service
from backend.services.job_logger import (
    finish_job_log,
    log_completeness,
    log_report_generation,
    start_job_log,
)
from backend.services.notification import notify_job_complete, notify_job_failed

# Windows sleep prevention
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def prevent_sleep():
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        )
    except Exception as e:
        logger.debug(f"[job_service] sleep prevention: {e}")


def allow_sleep():
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
    except Exception as e:
        logger.debug(f"[job_service] sleep prevention: {e}")


async def update_job_progress(
    job_id: str,
    progress: int,
    step: str,
    status: str = "RUNNING",
    ws_manager=None,
):
    """Update progress in DB + broadcast via WebSocket."""
    await db.execute(
        "UPDATE jobs SET progress_percent = ?, current_step = ?, status = ? WHERE id = ?",
        (progress, step, status, job_id),
    )
    if ws_manager:
        await ws_manager.broadcast(job_id, {
            "type": "progress",
            "job_id": job_id,
            "percent": progress,
            "step": step,
            "status": status,
        })


def _is_private_ip(hostname: str) -> bool:
    """Verifica daca un hostname se rezolva la un IP privat/loopback/rezervat."""
    try:
        ip = ip_address(hostname)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except (AddressValueError, ValueError, TypeError):
        pass
    try:
        resolved = socket.gethostbyname(hostname)
        ip = ip_address(resolved)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except Exception:
        return True  # fail-safe: block if can't resolve


async def _send_webhook_if_configured(job_id: str, report_data: dict):
    """F3-1: Trimite POST webhook la URL configurat dupa finalizarea unui job."""
    from backend.config import settings
    webhook_url = settings.webhook_url
    if not webhook_url:
        return
    parsed = urlparse(webhook_url)
    if parsed.scheme != "https" or not parsed.hostname:
        logger.warning(f"[webhook] URL invalid sau non-HTTPS: {webhook_url[:50]}")
        return
    if _is_private_ip(parsed.hostname):
        logger.warning("[webhook] Webhook URL blocat — IP privat/localhost detectat")
        return
    payload = {
        "event": "analysis_completed",
        "job_id": job_id,
        "company_name": report_data.get("company_name"),
        "cui": report_data.get("cui"),
        "risk_score": report_data.get("risk_score"),
        "numeric_score": report_data.get("numeric_score"),
        "completed_at": datetime.now(UTC).isoformat(),
    }
    try:
        from backend.http_client import get_client
        c = get_client()
        await c.post(webhook_url, json=payload, timeout=5)
        logger.info(f"[webhook] Trimis OK pentru job {job_id}")
    except Exception as e:
        logger.warning(f"[webhook] Esuat: {e}")


async def _prepare_job_state(job_id: str, ws_manager=None) -> tuple[dict, "AnalysisState", object]:
    """
    Incarca job din DB, determina agentii, construieste initial_state.
    Returns: (job_dict_with_parsed_params, initial_state, job_logger)
    Raises: ValueError daca job nu exista.
    Side effects: seteaza status RUNNING in DB, trimite WS progress 5%.
    """
    job = await db.fetch_one(
        "SELECT id, type, status, input_data, report_level, created_at, "
        "started_at, completed_at, error_message, progress_percent, "
        "current_step, checkpoint_data "
        "FROM jobs WHERE id = ?",
        (job_id,),
    )
    if not job:
        raise ValueError(f"Job {job_id} not found")

    analysis_type = job["type"]
    report_level = job["report_level"] or 2
    input_params: dict = {}
    if job["input_data"]:
        try:
            input_params = json.loads(job["input_data"])
        except (json.JSONDecodeError, TypeError):
            pass

    agents_needed = get_agents_needed(analysis_type, report_level)

    logger.info(
        f"Starting job {job_id}: type={analysis_type}, level={report_level}, "
        f"agents={agents_needed}"
    )

    cui = input_params.get("cui", "")
    company_name_input = input_params.get("company_name", "")
    jl = start_job_log(job_id, analysis_type, cui, company_name_input)
    jl.info(f"Agents needed: {agents_needed}")
    jl.info(f"Report level: {report_level}")
    jl.info(f"Input params: {json.dumps(input_params, ensure_ascii=False)}")

    now = datetime.now(UTC).isoformat()
    await db.execute(
        "UPDATE jobs SET status = 'RUNNING', started_at = ?, current_step = ? WHERE id = ?",
        (now, "Initializare agenti...", job_id),
    )
    await update_job_progress(job_id, 5, "Initializare agenti...", ws_manager=ws_manager)

    initial_state: AnalysisState = {
        "job_id": job_id,
        "analysis_type": analysis_type,
        "report_level": report_level,
        "input_params": input_params,
        "official_data": None,
        "web_data": None,
        "market_data": None,
        "verified_data": None,
        "report_sections": None,
        "report_paths": None,
        "errors": [],
        "sources": [],
        "progress": 0.0,
        "current_step": "Start",
        "agents_needed": agents_needed,
        # FIX #5: pass ws_manager through state to avoid circular import in orchestrator
        "_ws_manager": ws_manager,
        "_agent_metrics": {},
    }

    # Returnam si job dict extins cu campuri parsate (util pentru caller)
    job_info = dict(job)
    job_info["_input_params"] = input_params
    job_info["_now"] = now

    return job_info, initial_state, jl


async def _save_job_results(
    job_id: str,
    final_state: dict,
    verified_data: dict,
    sources: list,
    report_paths: dict,
    analysis_type: str,
    report_level: int,
) -> tuple[str | None, str | None]:
    """
    Salveaza rezultatele analizei in DB (reports, companies, report_sources, delta, score_history).
    Returns: (report_id, company_id) — pot fi None daca verified_data e gol.
    """
    import uuid

    report_id = None
    company_id = None
    cui = ""
    company_name = ""
    risk_score = None

    if not verified_data:
        return report_id, company_id

    report_id = str(uuid.uuid4())

    official = final_state.get("official_data", {})
    company_name = official.get("company_name", "")
    cui = official.get("cui", "")
    risk_score = verified_data.get("risk_score", {}).get("score")

    # Upsert company
    if cui or company_name:
        company_id = str(uuid.uuid4())
        existing = await db.fetch_one(
            "SELECT id FROM companies WHERE cui = ?", (cui,)
        ) if cui else None

        if existing:
            company_id = existing["id"]
            await db.execute(
                "UPDATE companies SET last_analyzed_at = datetime('now'), "
                "analysis_count = analysis_count + 1 WHERE id = ?",
                (company_id,),
            )
        else:
            await db.execute(
                "INSERT INTO companies (id, cui, name, county, first_analyzed_at, "
                "last_analyzed_at, analysis_count) VALUES (?, ?, ?, ?, datetime('now'), "
                "datetime('now'), 1)",
                (company_id, cui or None, company_name or "N/A", None),
            )

    # Salveaza raportul
    title = f"{analysis_type} — {company_name or cui or 'Analiza'}"
    summary = verified_data.get("risk_score", {}).get("recommendation", "")

    await db.execute(
        "INSERT INTO reports (id, job_id, company_id, report_type, report_level, "
        "title, summary, full_data, risk_score, created_at, "
        "pdf_path, docx_path, html_path, excel_path, pptx_path, report_number) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?, ?, ?, ?, ?)",
        (
            report_id, job_id, company_id, analysis_type, report_level,
            title, summary,
            json.dumps(verified_data, ensure_ascii=False, default=str),
            risk_score,
            report_paths.get("pdf"),
            report_paths.get("docx"),
            report_paths.get("html"),
            report_paths.get("excel"),
            report_paths.get("pptx"),
            report_paths.get("report_number"),
        ),
    )

    # Salveaza sursele
    for source in sources:
        await db.execute(
            "INSERT INTO report_sources (report_id, source_name, source_url, "
            "status, data_found, response_time_ms) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                report_id,
                source.get("source_name", ""),
                source.get("source_url", ""),
                source.get("status", ""),
                source.get("data_found", False),
                source.get("response_time_ms", 0),
            ),
        )

    # Delta report (compara cu raport anterior pt aceeasi firma)
    if company_id:
        try:
            from backend.services.delta_service import compute_delta, save_delta
            delta = await compute_delta(company_id, verified_data)
            if delta:
                delta_summary = json.dumps(delta, ensure_ascii=False, default=str)
                await save_delta(report_id, delta["previous_report_id"], delta_summary)
                verified_data["delta"] = delta
                await db.execute(
                    "UPDATE reports SET full_data = ? WHERE id = ?",
                    (json.dumps(verified_data, ensure_ascii=False, default=str), report_id),
                )
        except Exception as e:
            logger.warning(f"Delta computation failed: {e}")

    # 8E: Score history — stocheaza scor in DB pentru delta scoring temporal
    if company_id and verified_data.get("risk_score"):
        try:
            rs = verified_data["risk_score"]
            await db.execute(
                "INSERT INTO score_history (company_id, cui, numeric_score, dimensions, factors) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    company_id,
                    cui or "",
                    rs.get("numeric_score"),
                    json.dumps(rs.get("dimensions", {}), ensure_ascii=False),
                    json.dumps(rs.get("factors", []), ensure_ascii=False),
                ),
            )
        except Exception as e:
            logger.debug(f"Score history save failed (table may not exist): {e}")

    return report_id, company_id


async def _finalize_job(
    job_id: str,
    report_id: str | None,
    company_id: str | None,
    verified_data: dict,
    report_paths: dict,
    sources: list,
    analysis_type: str,
    now: str,
    completeness: dict,
    jl,
    ws_manager=None,
) -> None:
    """
    Update status DONE, trimite WS job_complete, log-uri, notificari, webhook.
    """
    # Variabile derivate (safe pentru cazul cand verified_data e gol)
    risk_score = verified_data.get("risk_score", {}).get("score") if verified_data else None
    company_name = ""
    cui = ""
    if verified_data:
        # Extragem company_name/cui din verified_data daca exista (fost salvat de _save_job_results)
        rs_data = verified_data.get("risk_score", {})
        company_name = verified_data.get("company_name", "")
        cui = verified_data.get("cui", "")
        risk_score = rs_data.get("score")

    formats_available = list(report_paths.keys())

    # Job completat — update DB
    await db.execute(
        "UPDATE jobs SET status = 'DONE', progress_percent = 100, "
        "completed_at = datetime('now'), current_step = 'Analiza finalizata' WHERE id = ?",
        (job_id,),
    )

    # WS broadcast
    if ws_manager:
        await ws_manager.broadcast(job_id, {
            "type": "job_complete",
            "job_id": job_id,
            "report_id": report_id,
            "formats": formats_available,
            "sources_total": len(sources),
            "sources_ok": sum(1 for s in sources if s.get("data_found")),
        })

    logger.info(f"Job {job_id} completed successfully. Report: {report_id}")

    # Log report generation
    log_report_generation(job_id, formats_available, int(
        (datetime.now(UTC) - datetime.fromisoformat(now)).total_seconds() * 1000
    ))

    # Finish job log
    finish_job_log(
        job_id,
        success=True,
        completeness_score=completeness.get("score", 0) if completeness else 0,
        risk_score=risk_score or 0,
        report_formats=formats_available,
    )

    # Notificari externe (Telegram/Email)
    elapsed = (datetime.now(UTC) - datetime.fromisoformat(now)).total_seconds()
    await notify_job_complete(
        job_id=job_id,
        analysis_type=analysis_type,
        company_name=company_name,
        risk_score=risk_score,
        report_formats=formats_available,
        duration_seconds=int(elapsed),
    )

    # F3-1: Webhook outbound la finalizare job
    try:
        _numeric_score = verified_data.get("risk_score", {}).get("numeric_score") if verified_data else None
        await _send_webhook_if_configured(job_id, {
            "company_name": company_name,
            "cui": cui,
            "risk_score": risk_score,
            "numeric_score": _numeric_score,
        })
    except Exception as _wh_err:
        logger.debug(f"[webhook] Non-critical: {_wh_err}")

    # R2 Fix #1: Create in-app notification on job complete
    try:
        from backend.routers.notifications import create_notification
        _score = risk_score
        _sev = "success" if _score and _score >= 70 else "warning" if _score and _score >= 40 else "error"
        await create_notification(
            type="job_complete",
            title=f"Analiza finalizata: {company_name or cui or 'N/A'}",
            message=f"Scor risc: {_score or 'N/A'}. {len(formats_available)} formate disponibile.",
            link=f"/report/{report_id}" if report_id else f"/analysis/{job_id}",
            severity=_sev,
        )
    except Exception as notif_err:
        logger.debug(f"Notification create failed (non-critical): {notif_err}")


async def run_analysis_job(job_id: str, ws_manager=None):
    """
    Executa un job de analiza complet.
    Apelat din endpoint-ul start_job.
    Orchestreaza: _prepare_job_state → LangGraph → _save_job_results → _finalize_job.
    """
    # F0-3: Extrage logica de init in subfunctie
    try:
        job_info, initial_state, jl = await _prepare_job_state(job_id, ws_manager)
    except ValueError:
        logger.error(f"Job {job_id} not found")
        return

    analysis_type = initial_state["analysis_type"]
    report_level = initial_state["report_level"]
    input_params = job_info["_input_params"]
    now = job_info["_now"]

    # Previne sleep
    prevent_sleep()

    try:
        # Cleanup cache expirat
        await cache_service.cleanup_expired()

        # Construieste si executa graful
        graph = build_analysis_graph()

        await update_job_progress(
            job_id, 10, "Agent 1: Extragere date oficiale...", ws_manager=ws_manager
        )

        # Executie LangGraph
        jl.info("LANGGRAPH | START | executing analysis graph...")
        final_state = await graph.ainvoke(initial_state)
        jl.info("LANGGRAPH | END | graph execution complete")

        # Extrage rezultatele
        verified_data = final_state.get("verified_data", {})
        errors = final_state.get("errors", [])
        sources = final_state.get("sources", [])

        # F2-15: Injecteaza key_takeaways in verified_data
        key_takeaways = final_state.get("key_takeaways", "")
        if key_takeaways and isinstance(verified_data, dict):
            verified_data["key_takeaways"] = key_takeaways

        # Log completeness
        completeness = verified_data.get("completeness", {}) if verified_data else {}
        if completeness:
            log_completeness(
                job_id,
                score=completeness.get("score", 0),
                quality=completeness.get("quality_level", "N/A"),
                passed=completeness.get("passed", 0),
                total=completeness.get("total_checks", 0),
                gaps=completeness.get("gaps"),
            )

        # Log sources summary
        jl.info(f"SOURCES | total={len(sources)} | ok={sum(1 for s in sources if s.get('data_found'))} | fail={sum(1 for s in sources if not s.get('data_found'))}")
        for src in sources:
            src_status = "OK" if src.get("data_found") else "FAIL"
            jl.info(f"  {src.get('source_name', '?'): <25} | {src_status} | {src.get('response_time_ms', 0)}ms")

        # Log errors
        if errors:
            jl.warning(f"ERRORS | {len(errors)} errors during execution")
            for err in errors:
                jl.warning(f"  [{err.get('agent', '?')}] {err.get('error', '?')}")

        # F0-3: Salveaza rezultatele in DB
        report_paths = final_state.get("report_paths", {})
        report_id, company_id = await _save_job_results(
            job_id=job_id,
            final_state=final_state,
            verified_data=verified_data,
            sources=sources,
            report_paths=report_paths,
            analysis_type=analysis_type,
            report_level=report_level,
        )

        # F0-3: Finalizeaza job (notificari, WS, logging)
        await _finalize_job(
            job_id=job_id,
            report_id=report_id,
            company_id=company_id,
            verified_data=verified_data,
            report_paths=report_paths,
            sources=sources,
            analysis_type=analysis_type,
            now=now,
            completeness=completeness,
            jl=jl,
            ws_manager=ws_manager,
        )

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        finish_job_log(job_id, success=False, error=str(e))
        await db.execute(
            "UPDATE jobs SET status = 'FAILED', error_message = ?, "
            "current_step = 'Eroare fatala' WHERE id = ?",
            (str(e), job_id),
        )
        if ws_manager:
            await ws_manager.broadcast(job_id, {
                "type": "job_failed",
                "job_id": job_id,
                "error": str(e),
                "retry_available": True,
            })
        await notify_job_failed(job_id, str(e))

        # R2 Fix #1: Create in-app notification on job failure
        try:
            from backend.routers.notifications import create_notification
            await create_notification(
                type="job_failed",
                title=f"Analiza esuata: {input_params.get('cui', 'N/A')}",
                message=str(e)[:200],
                link=f"/analysis/{job_id}",
                severity="error",
            )
        except Exception as notif_err:
            logger.debug(f"[job_service] notification: {notif_err}")

    finally:
        allow_sleep()
