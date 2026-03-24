"""
Job Service — Logica de executie a job-urilor.
Porneste LangGraph, broadcast progress via WebSocket, update DB.
"""

import asyncio
import json
import ctypes
from datetime import datetime, date, UTC

from loguru import logger

from backend.database import db
from backend.agents.state import AnalysisState, get_agents_needed
from backend.agents.orchestrator import build_analysis_graph
from backend.services import cache_service
from backend.services.notification import notify_job_complete, notify_job_failed
from backend.services.job_logger import (
    start_job_log, finish_job_log, get_job_logger,
    log_completeness, log_report_generation,
)


# Windows sleep prevention
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def prevent_sleep():
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        )
    except Exception:
        pass


def allow_sleep():
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
    except Exception:
        pass


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


async def run_analysis_job(job_id: str, ws_manager=None):
    """
    Executa un job de analiza complet.
    Apelat din endpoint-ul start_job.
    """
    # Incarca job-ul din DB
    job = await db.fetch_one("SELECT * FROM jobs WHERE id = ?", (job_id,))
    if not job:
        logger.error(f"Job {job_id} not found")
        return

    analysis_type = job["type"]
    report_level = job["report_level"] or 2
    input_params = {}
    if job["input_data"]:
        try:
            input_params = json.loads(job["input_data"])
        except (json.JSONDecodeError, TypeError):
            pass

    # Determina agentii necesari
    agents_needed = get_agents_needed(analysis_type, report_level)

    logger.info(
        f"Starting job {job_id}: type={analysis_type}, level={report_level}, "
        f"agents={agents_needed}"
    )

    # Start job logging
    cui = input_params.get("cui", "")
    company_name_input = input_params.get("company_name", "")
    jl = start_job_log(job_id, analysis_type, cui, company_name_input)
    jl.info(f"Agents needed: {agents_needed}")
    jl.info(f"Report level: {report_level}")
    jl.info(f"Input params: {json.dumps(input_params, ensure_ascii=False)}")

    # Previne sleep
    prevent_sleep()

    # Update status
    now = datetime.now(UTC).isoformat()
    await db.execute(
        "UPDATE jobs SET status = 'RUNNING', started_at = ?, current_step = ? WHERE id = ?",
        (now, "Initializare agenti...", job_id),
    )
    await update_job_progress(job_id, 5, "Initializare agenti...", ws_manager=ws_manager)

    try:
        # Cleanup cache expirat
        await cache_service.cleanup_expired()

        # Construieste starea initiala
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
        }

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
            status = "OK" if src.get("data_found") else "FAIL"
            jl.info(f"  {src.get('source_name', '?'): <25} | {status} | {src.get('response_time_ms', 0)}ms")

        # Log errors
        if errors:
            jl.warning(f"ERRORS | {len(errors)} errors during execution")
            for err in errors:
                jl.warning(f"  [{err.get('agent', '?')}] {err.get('error', '?')}")

        # Salveaza rezultatele in DB
        report_id = None
        report_paths = final_state.get("report_paths", {})
        if verified_data:
            import uuid
            report_id = str(uuid.uuid4())

            # Extrage CUI si companie
            official = final_state.get("official_data", {})
            company_name = official.get("company_name", "")
            cui = official.get("cui", "")
            risk_score = verified_data.get("risk_score", {}).get("score")

            # Upsert company
            company_id = None
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
                "pdf_path, docx_path, html_path, excel_path, pptx_path) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?, ?, ?, ?)",
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
        if report_id and company_id:
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

        # Job completat
        await db.execute(
            "UPDATE jobs SET status = 'DONE', progress_percent = 100, "
            "completed_at = datetime('now'), current_step = 'Analiza finalizata' WHERE id = ?",
            (job_id,),
        )

        formats_available = list(report_paths.keys())
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

        # Notificari
        elapsed = (datetime.now(UTC) - datetime.fromisoformat(now)).total_seconds()
        await notify_job_complete(
            job_id=job_id,
            analysis_type=analysis_type,
            company_name=company_name if verified_data else "",
            risk_score=risk_score if verified_data else None,
            report_formats=formats_available,
            duration_seconds=int(elapsed),
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

    finally:
        allow_sleep()
