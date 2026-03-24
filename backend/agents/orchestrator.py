"""
LangGraph orchestrator — State machine pentru executia agentilor.
Flux: Agent 1 -> [Agent 2 + 3 paralel] -> Agent 4 -> Agent 5 (Synthesis) -> Report Generator
8D: Timing metrics, error boundaries, adaptive routing.
10F M5.1: Request deduplication (in-flight tracking).
10F M5.3: Parallel Agent 2+3 via conditional_edges fan-out.
10F M5.4: State checkpoint recovery after each agent.
"""
import asyncio
import time

from langgraph.graph import StateGraph, START, END

from loguru import logger

from backend.agents.state import AnalysisState, get_agents_needed
from backend.agents.agent_official import official_agent
from backend.agents.agent_verification import verification_agent
from backend.agents.agent_synthesis import synthesis_agent
from backend.reports.generator import generate_all_reports
from backend.services.job_logger import (
    get_job_logger, log_agent_start, log_agent_end, log_source_result,
)


# --- 10F M5.1: Request Deduplication ---
# Track CUIs currently being analyzed to avoid duplicate work.
_in_flight: dict[str, asyncio.Event] = {}
_in_flight_results: dict[str, dict] = {}


async def deduplicate_job(cui: str) -> dict | None:
    """10F M5.1: If same CUI is already in-flight, wait and reuse result."""
    if cui in _in_flight:
        logger.info(f"[orchestrator] Dedup: CUI {cui} already in-flight, waiting...")
        await _in_flight[cui].wait()
        return _in_flight_results.get(cui)
    return None


def register_in_flight(cui: str):
    """10F M5.1: Mark CUI as in-flight before starting analysis."""
    _in_flight[cui] = asyncio.Event()


def complete_in_flight(cui: str, result: dict):
    """10F M5.1: Mark CUI as complete, store result, auto-cleanup after 60s."""
    _in_flight_results[cui] = result
    if cui in _in_flight:
        _in_flight[cui].set()
    # Auto-cleanup after 60s
    loop = asyncio.get_event_loop()
    loop.call_later(60, lambda: _in_flight.pop(cui, None))
    loop.call_later(60, lambda: _in_flight_results.pop(cui, None))


# --- 10F M5.4: State Checkpoint Recovery ---

async def _save_checkpoint(job_id: str, agent_name: str, state_data: dict):
    """10F M5.4: Save checkpoint after each agent for crash recovery."""
    import json
    from backend.database import db
    try:
        await db.execute(
            "INSERT OR REPLACE INTO job_checkpoints (job_id, agent_name, state_data, created_at) "
            "VALUES (?, ?, ?, datetime('now'))",
            (job_id, agent_name, json.dumps(state_data, ensure_ascii=False, default=str)),
        )
    except Exception as e:
        logger.warning(f"[orchestrator] Checkpoint save failed: {e}")


# --- Node functions with timing (8D) ---

async def run_official(state: AnalysisState) -> dict:
    """Ruleaza Agent 1 — Date Oficiale (with timing + 9A error boundary)."""
    t0 = time.time()
    try:
        result = await official_agent.run(state)
    except Exception as e:
        # 9A: Error boundary — Agent 1 fail returns minimal data, pipeline continues
        elapsed = time.time() - t0
        logger.error(f"[orchestrator] Agent 1 (Official) CRITICAL error boundary: {e} ({elapsed:.1f}s)")
        result = {
            "official_data": {"error": str(e), "timestamp": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat()},
            "sources": [],
            "errors": [{"agent": "official", "error": str(e)}],
        }
    elapsed = time.time() - t0
    # Store timing in state for diagnostics
    metrics = state.get("_agent_metrics", {})
    metrics["official"] = round(elapsed, 1)
    result["_agent_metrics"] = metrics
    logger.info(f"[orchestrator] Agent 1 (Official) completed in {elapsed:.1f}s")
    await _save_checkpoint(state.get("job_id", ""), "official", result)  # 10F M5.4
    return result


async def run_verification(state: AnalysisState) -> dict:
    """Ruleaza Agent 4 — Verification (with timing + 9A error boundary)."""
    t0 = time.time()
    job_id = state.get("job_id", "")
    log_agent_start(job_id, "verification")
    try:
        result = await verification_agent.run(state)
    except Exception as e:
        elapsed = time.time() - t0
        logger.error(f"[orchestrator] Agent 4 (Verification) error boundary: {e} ({elapsed:.1f}s)")
        log_agent_end(job_id, "verification", f"ERROR (boundary): {e}")
        result = {
            "verified_data": {"error": str(e), "risk_score": {"score": 50, "numeric_score": 50, "color": "GALBEN"}},
            "errors": [{"agent": "verification", "error": str(e)}],
        }
    vd = result.get("verified_data", {})
    completeness = vd.get("completeness", {})
    risk = vd.get("risk_score", {})
    elapsed = time.time() - t0
    metrics = state.get("_agent_metrics", {})
    metrics["verification"] = round(elapsed, 1)
    result["_agent_metrics"] = metrics
    log_agent_end(job_id, "verification",
        f"risk={risk.get('score', '?')}/100 | completeness={completeness.get('score', '?')}% | "
        f"gaps={completeness.get('gaps_count', '?')} | {elapsed:.1f}s")
    await _save_checkpoint(job_id, "verification", result)  # 10F M5.4
    return result


async def run_synthesis(state: AnalysisState) -> dict:
    """Ruleaza Agent 5 — Synthesis. CA4: completeness gate < 50%. 8D: timing."""
    t0 = time.time()
    job_id = state.get("job_id", "")
    log_agent_start(job_id, "synthesis")

    # 9B: Anomaly feedback loop — Agent 4 anomalies → synthesis forced analysis
    verified = state.get("verified_data", {})
    risk_score = verified.get("risk_score", {})
    anomalies = risk_score.get("anomalies", [])
    if anomalies:
        logger.info(f"[synthesis] ANOMALY FEEDBACK: {len(anomalies)} anomalii detectate → inject in prompt")
        verified.setdefault("_anomaly_alerts", []).extend(anomalies)
        state["verified_data"] = verified

    # CA4: Completeness gate — daca sub 50%, log WARNING + inject avertisment
    completeness = verified.get("completeness", {})
    score = completeness.get("score", 100)
    if isinstance(score, (int, float)) and score < 50:
        logger.warning(
            f"[synthesis] COMPLETENESS GATE: {score}% < 50% — date insuficiente! "
            f"Raportul va contine avertisment explicit."
        )
        verified.setdefault("_warnings", []).append(
            f"ATENTIE: Datele colectate sunt incomplete ({score}% completitudine). "
            f"Raportul poate contine sectiuni cu informatii limitate."
        )
        state["verified_data"] = verified

    try:
        result = await synthesis_agent.run(state)
    except Exception as e:
        elapsed = time.time() - t0
        logger.error(f"[orchestrator] Agent 5 (Synthesis) error boundary: {e} ({elapsed:.1f}s)")
        log_agent_end(job_id, "synthesis", f"ERROR (boundary): {e}")
        result = {
            "report_sections": {"executive_summary": f"Eroare generare raport: {e}. Date disponibile in format JSON."},
            "errors": [{"agent": "synthesis", "error": str(e)}],
        }
    sections = result.get("report_sections", {})
    elapsed = time.time() - t0
    metrics = state.get("_agent_metrics", {})
    metrics["synthesis"] = round(elapsed, 1)
    result["_agent_metrics"] = metrics
    log_agent_end(job_id, "synthesis", f"{len(sections)} sections | {elapsed:.1f}s")
    await _save_checkpoint(job_id, "synthesis", result)  # 10F M5.4
    return result


async def run_report_generator(state: AnalysisState) -> dict:
    """Genereaza rapoartele in toate formatele (with timing 8D)."""
    t0 = time.time()
    job_id = state.get("job_id", "")
    log_agent_start(job_id, "report_generator")
    report_sections = state.get("report_sections", {})
    verified_data = state.get("verified_data", {})
    job_id = state.get("job_id", "unknown")
    report_level = state.get("report_level", 2)
    analysis_type = state.get("analysis_type", "CUSTOM_REPORT")

    if not report_sections:
        logger.warning("[report] No sections to generate reports from")
        return {
            "report_paths": {},
            "current_step": "Generare rapoarte: nicio sectiune disponibila",
            "progress": 1.0,
        }

    paths = await generate_all_reports(
        job_id=job_id,
        report_sections=report_sections,
        verified_data=verified_data,
        report_level=report_level,
        analysis_type=analysis_type,
    )

    elapsed = time.time() - t0
    metrics = state.get("_agent_metrics", {})
    metrics["report_generator"] = round(elapsed, 1)

    logger.info(f"[report] Generated {len(paths)} formats in {elapsed:.1f}s: {list(paths.keys())}")
    log_agent_end(job_id, "report_generator", f"{len(paths)} formats | {elapsed:.1f}s")

    report_result = {
        "report_paths": paths,
        "_agent_metrics": metrics,
        "current_step": f"Rapoarte generate: {', '.join(paths.keys()).upper()}",
        "progress": 1.0,
    }
    await _save_checkpoint(job_id, "report_generator", report_result)  # 10F M5.4
    return report_result


async def run_web(state: AnalysisState) -> dict:
    """Agent 2 — Web Intelligence (Tavily search). 8D: error boundary."""
    from backend.agents.tools import tavily_client

    t0 = time.time()
    job_id = state.get("job_id", "")
    log_agent_start(job_id, "web")

    params = state.get("input_params", {})
    official = state.get("official_data") or {}
    company_name = official.get("company_name", params.get("cui", ""))

    if not company_name:
        log_agent_end(job_id, "web", "SKIPPED — no company name")
        return {"web_data": {}, "current_step": "Agent 2 (Web) — skip (no name)", "progress": 0.40}

    web_data = {}

    try:
        logger.info(f"[web] Searching web presence for: {company_name}")

        # Site oficial + prezenta online
        general = await tavily_client.search(
            query=f'"{company_name}" site oficial Romania contact',
            max_results=3,
        )
        if general.get("results"):
            web_data["online_presence"] = {
                "results": general["results"][:3],
                "answer": general.get("answer", ""),
                "source": "Tavily",
            }

        # Recenzii / reputatie
        reviews = await tavily_client.search(
            query=f'"{company_name}" recenzii pareri clienti',
            max_results=3,
        )
        if reviews.get("results"):
            web_data["reviews"] = {
                "results": reviews["results"][:3],
                "source": "Tavily",
            }

        # Stiri recente
        news = await tavily_client.search_company_info(
            company_name=company_name, info_type="news"
        )
        if news.get("results"):
            web_data["news"] = {
                "results": news["results"][:3],
                "source": "Tavily",
            }

        elapsed = time.time() - t0
        logger.info(f"[web] Found: {len(web_data)} categories in {elapsed:.1f}s")
        for cat in web_data:
            log_source_result(job_id, f"Tavily ({cat})", True, 0, [f"{len(web_data[cat].get('results', []))} results"])
        log_agent_end(job_id, "web", f"{len(web_data)} categories | {elapsed:.1f}s")
        metrics = state.get("_agent_metrics", {})
        metrics["web"] = round(elapsed, 1)
        web_result = {
            "web_data": web_data,
            "_agent_metrics": metrics,
            "current_step": f"Agent 2: {len(web_data)} categorii web gasite",
            "progress": 0.40,
        }
        await _save_checkpoint(job_id, "web", web_result)  # 10F M5.4
        return web_result

    except Exception as e:
        # 8D: Error boundary — Agent 2 fail does NOT stop the pipeline
        elapsed = time.time() - t0
        logger.warning(f"[web] Error boundary caught: {e} ({elapsed:.1f}s)")
        log_agent_end(job_id, "web", f"ERROR (boundary): {e}")
        return {"web_data": {}, "current_step": f"Agent 2 — eroare (continua): {e}", "progress": 0.40}


async def run_market(state: AnalysisState) -> dict:
    """Agent 3 — Market Research (SEAP). 8D: error boundary + timing."""
    from backend.agents.tools.seap_client import get_contracts_won

    t0 = time.time()
    job_id = state.get("job_id", "")
    log_agent_start(job_id, "market")

    params = state.get("input_params", {})
    cui = params.get("cui", "")
    cui_clean = cui.strip().replace("RO", "").replace("ro", "").replace(" ", "")
    if not cui_clean.isdigit():
        logger.info("[market] No valid CUI for SEAP search, skipping")
        log_agent_end(job_id, "market", "SKIPPED — no valid CUI")
        return {"market_data": {}, "current_step": "Agent 3 (Market) — skip (no CUI)", "progress": 0.40}

    try:
        logger.info(f"[market] Searching SEAP for CUI {cui_clean}")
        seap_data = await get_contracts_won(cui_clean)
        total = seap_data.get("total_contracts", 0)
        contracts = seap_data.get("contracts_count", 0)
        direct = seap_data.get("direct_count", 0)
        total_val = seap_data.get("total_value", 0)
        elapsed = time.time() - t0
        log_source_result(job_id, "SEAP (licitatii)", contracts > 0, 0,
            [f"{contracts} contracte", f"valoare={total_val}"])
        log_source_result(job_id, "SEAP (achizitii directe)", direct > 0, 0,
            [f"{direct} achizitii"])
        log_agent_end(job_id, "market", f"{total} contracte SEAP | {elapsed:.1f}s")
        metrics = state.get("_agent_metrics", {})
        metrics["market"] = round(elapsed, 1)
        market_result = {
            "market_data": {"seap": seap_data},
            "_agent_metrics": metrics,
            "current_step": f"Agent 3: {total} contracte SEAP gasite",
            "progress": 0.40,
        }
        await _save_checkpoint(job_id, "market", market_result)  # 10F M5.4
        return market_result
    except Exception as e:
        # 8D: Error boundary — Agent 3 fail does NOT stop the pipeline
        elapsed = time.time() - t0
        logger.warning(f"[market] Error boundary caught: {e} ({elapsed:.1f}s)")
        log_source_result(job_id, "SEAP", False, 0, error=str(e))
        log_agent_end(job_id, "market", f"ERROR (boundary): {e}")
        return {"market_data": {}, "current_step": f"Agent 3 — eroare (continua): {e}", "progress": 0.40}


# --- Routing ---

def route_after_official(state: AnalysisState) -> list[str]:
    """Decide ce agenti ruleaza dupa Agent 1.

    10F M5.3: Parallel Agent 2+3 — conditional_edges returns list → LangGraph fan-out.
    When both agent_web and agent_market are returned, LangGraph executes them
    in parallel. Both must complete before agent_verification runs (fan-in).
    """
    agents_needed = state.get("agents_needed", ["official"])

    needs_web = "web" in agents_needed
    needs_market = "market" in agents_needed

    # 10F M5.3: Returning multiple targets triggers LangGraph parallel fan-out
    targets = []
    if needs_web:
        targets.append("agent_web")
    if needs_market:
        targets.append("agent_market")

    if not targets:
        return ["agent_verification"]

    return targets


# --- Graph builder ---

def build_analysis_graph() -> StateGraph:
    """Construieste graful LangGraph complet."""
    graph = StateGraph(AnalysisState)

    # Noduri
    graph.add_node("agent_official", run_official)
    graph.add_node("agent_web", run_web)
    graph.add_node("agent_market", run_market)
    graph.add_node("agent_verification", run_verification)
    graph.add_node("agent_synthesis", run_synthesis)
    graph.add_node("report_generator", run_report_generator)

    # Edges
    graph.add_edge(START, "agent_official")

    # 10F M5.3: Parallel Agent 2+3 — conditional_edges returns list → LangGraph fan-out
    # Both agent_web and agent_market run concurrently; fan-in at agent_verification.
    graph.add_conditional_edges(
        "agent_official",
        route_after_official,
        ["agent_web", "agent_market", "agent_verification"],
    )

    graph.add_edge("agent_web", "agent_verification")   # fan-in leg 1
    graph.add_edge("agent_market", "agent_verification") # fan-in leg 2
    graph.add_edge("agent_verification", "agent_synthesis")
    graph.add_edge("agent_synthesis", "report_generator")
    graph.add_edge("report_generator", END)

    return graph.compile()
