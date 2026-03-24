"""
Job Logger — Logging complet per job in fisier dedicat.

Fiecare job de analiza primeste un fisier log separat in logs/
cu FIECARE pas executat: request-uri API, raspunsuri, timpi, erori,
completeness, prompt-uri AI, generare rapoarte.

Flux:
  1. La start job -> start_job_log(job_id) -> creeaza fisier + adauga sink loguru
  2. Pe parcurs -> get_job_logger(job_id).info/warning/error(...)
  3. La final -> finish_job_log(job_id) -> scrie rezumat + inchide sink

Log-urile pot fi citite cu orice text editor din: logs/job_{id}.log
"""

import sys
from pathlib import Path
from datetime import datetime, UTC

from loguru import logger

LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Consolidated summary log — one line per analysis, readable at session start
SUMMARY_LOG = LOGS_DIR / "ris_summary.log"

# Tracking: job_id -> loguru sink_id
_active_sinks: dict[str, int] = {}

# Tracking: job_id -> start time
_job_start_times: dict[str, datetime] = {}

# Tracking: job_id -> events list (for summary)
_job_events: dict[str, list[dict]] = {}

# Format pentru log-uri job (detaliat, cu timestamp)
JOB_LOG_FORMAT = (
    "[{time:YYYY-MM-DD HH:mm:ss.SSS}] "
    "{level: <8} | "
    "{message}"
)


def _get_log_path(job_id: str) -> Path:
    """Returneaza path-ul fisierului log pentru un job."""
    # Sanitize job_id (e UUID, dar prevenim path traversal)
    safe_id = "".join(c for c in job_id if c.isalnum() or c == "-")
    return LOGS_DIR / f"job_{safe_id}.log"


def start_job_log(job_id: str, analysis_type: str = "", cui: str = "", company_name: str = ""):
    """
    Incepe logging-ul pentru un job specific.
    Adauga un sink loguru care filtreaza doar mesajele pentru acest job.
    """
    log_path = _get_log_path(job_id)
    _job_start_times[job_id] = datetime.now(UTC)
    _job_events[job_id] = []

    # Adauga sink loguru care captureaza TOATE mesajele (vom filtra per job in cod)
    sink_id = logger.add(
        str(log_path),
        format=JOB_LOG_FORMAT,
        level="DEBUG",
        filter=lambda record: record.get("extra", {}).get("job_id") == job_id,
        encoding="utf-8",
        mode="w",  # Overwrite daca exista
    )
    _active_sinks[job_id] = sink_id

    # Header in log
    jl = get_job_logger(job_id)
    jl.info("=" * 70)
    jl.info(f"  JOB START: {job_id}")
    jl.info(f"  Analysis: {analysis_type}")
    jl.info(f"  CUI: {cui}")
    jl.info(f"  Company: {company_name}")
    jl.info(f"  Time: {_job_start_times[job_id].strftime('%Y-%m-%d %H:%M:%S')}")
    jl.info(f"  Log file: {log_path}")
    jl.info("=" * 70)

    return jl


def get_job_logger(job_id: str):
    """Returneaza un logger binduit la job_id specific."""
    return logger.bind(job_id=job_id)


def log_api_request(job_id: str, source: str, method: str, url: str, payload: str = ""):
    """Logheaza un request API extern."""
    jl = get_job_logger(job_id)
    jl.info(f"{source}_REQUEST | {method} {url}" + (f" | payload={payload[:200]}" if payload else ""))


def log_api_response(job_id: str, source: str, status_code: int, elapsed_ms: int,
                     data_summary: str = "", error: str = ""):
    """Logheaza un response API extern."""
    jl = get_job_logger(job_id)
    if error:
        jl.warning(f"{source}_RESPONSE | ERROR | {elapsed_ms}ms | {error}")
        _track_event(job_id, source, "FAIL", elapsed_ms, error)
    else:
        jl.info(f"{source}_RESPONSE | {status_code} OK | {elapsed_ms}ms | {data_summary[:200]}")
        _track_event(job_id, source, "OK", elapsed_ms)


def log_agent_start(job_id: str, agent_name: str):
    """Logheaza inceputul executiei unui agent."""
    jl = get_job_logger(job_id)
    jl.info("-" * 50)
    jl.info(f"AGENT_{agent_name.upper()} | START")
    jl.info("-" * 50)


def log_agent_end(job_id: str, agent_name: str, summary: str = ""):
    """Logheaza sfarsitul executiei unui agent."""
    jl = get_job_logger(job_id)
    jl.info(f"AGENT_{agent_name.upper()} | END | {summary}")
    jl.info("")


def log_source_result(job_id: str, source_name: str, found: bool, elapsed_ms: int,
                      fields_extracted: list[str] = None, error: str = ""):
    """Logheaza rezultatul unei surse de date."""
    jl = get_job_logger(job_id)
    status = "OK" if found else "FAIL"
    fields_str = ", ".join(fields_extracted) if fields_extracted else "none"

    if found:
        jl.info(f"  SOURCE | {source_name: <25} | {status} | {elapsed_ms}ms | fields=[{fields_str}]")
    else:
        reason = error or "no data"
        jl.warning(f"  SOURCE | {source_name: <25} | {status} | {elapsed_ms}ms | reason={reason}")

    _track_event(job_id, source_name, status, elapsed_ms, error)


def log_completeness(job_id: str, score: int, quality: str, passed: int, total: int,
                     gaps: list[dict] = None):
    """Logheaza rezultatul verificarii de completitudine."""
    jl = get_job_logger(job_id)
    jl.info("-" * 50)
    jl.info(f"COMPLETENESS | score={score}% | quality={quality} | {passed}/{total} checks")

    if gaps:
        for gap in gaps:
            severity = gap.get("severity", "?")
            field = gap.get("field", "?")
            reason = gap.get("reason", "?")
            jl.warning(f"  GAP [{severity}] | {field} | {reason}")
    else:
        jl.info("  No gaps — all checks passed!")
    jl.info("-" * 50)


def log_synthesis(job_id: str, section_key: str, provider: str, word_count: int,
                  elapsed_ms: int, success: bool, fallback: bool = False):
    """Logheaza generarea unei sectiuni de raport via AI."""
    jl = get_job_logger(job_id)
    status = "OK" if success else "FAIL"
    fb = " (FALLBACK)" if fallback else ""
    jl.info(
        f"  SYNTHESIS | {section_key: <25} | provider={provider}{fb} | "
        f"{status} | {word_count} words | {elapsed_ms}ms"
    )


def log_report_generation(job_id: str, formats: list[str], elapsed_ms: int):
    """Logheaza generarea rapoartelor."""
    jl = get_job_logger(job_id)
    jl.info(f"REPORT_GEN | formats={', '.join(formats)} | {elapsed_ms}ms")


def log_request(job_id: str, method: str, path: str, status_code: int, elapsed_ms: int):
    """Logheaza un request HTTP primit de backend (din frontend sau extern)."""
    jl = get_job_logger(job_id)
    jl.debug(f"HTTP | {method} {path} | {status_code} | {elapsed_ms}ms")


def _track_event(job_id: str, source: str, status: str, elapsed_ms: int, error: str = ""):
    """Inregistreaza un event pentru rezumatul final."""
    if job_id in _job_events:
        _job_events[job_id].append({
            "source": source,
            "status": status,
            "elapsed_ms": elapsed_ms,
            "error": error,
            "time": datetime.now(UTC).isoformat(),
        })


def finish_job_log(job_id: str, success: bool = True, error: str = "",
                   completeness_score: int = 0, risk_score: int = 0,
                   report_formats: list[str] = None):
    """
    Finalizeaza logging-ul pentru un job.
    Scrie rezumat complet + inchide sink-ul loguru.
    """
    jl = get_job_logger(job_id)
    start = _job_start_times.get(job_id)
    elapsed = (datetime.now(UTC) - start).total_seconds() if start else 0
    events = _job_events.get(job_id, [])

    # Rezumat surse
    ok_sources = [e for e in events if e["status"] == "OK"]
    fail_sources = [e for e in events if e["status"] == "FAIL"]

    jl.info("")
    jl.info("=" * 70)
    jl.info("  JOB SUMMARY")
    jl.info("=" * 70)
    jl.info(f"  Status: {'SUCCESS' if success else 'FAILED'}")
    jl.info(f"  Total time: {elapsed:.1f}s")
    jl.info(f"  Sources OK: {len(ok_sources)}")
    jl.info(f"  Sources FAIL: {len(fail_sources)}")
    jl.info(f"  Completeness: {completeness_score}%")
    jl.info(f"  Risk score: {risk_score}/100")
    jl.info(f"  Report formats: {', '.join(report_formats) if report_formats else 'none'}")

    if fail_sources:
        jl.info("")
        jl.info("  FAILED SOURCES:")
        for fs in fail_sources:
            jl.warning(f"    - {fs['source']}: {fs.get('error', 'unknown')}")

    if error:
        jl.error(f"  FATAL ERROR: {error}")

    jl.info("=" * 70)
    jl.info(f"  Log saved to: {_get_log_path(job_id)}")
    jl.info("=" * 70)

    # Append to consolidated summary (one-liner per analysis, for session review)
    try:
        cui_val = ""
        company_val = ""
        # Try to extract from job log header events
        log_path = _get_log_path(job_id)
        if log_path.exists():
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "CUI:" in line:
                        cui_val = line.split("CUI:")[-1].strip()
                    if "Company:" in line:
                        company_val = line.split("Company:")[-1].strip()
                    if company_val and cui_val:
                        break

        status_str = "DONE" if success else "FAILED"
        fail_names = ", ".join(fs["source"] for fs in fail_sources) if fail_sources else "none"
        formats_str = ", ".join(report_formats) if report_formats else "none"
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

        summary_line = (
            f"[{ts}] CUI={cui_val} | {company_val} | {status_str} | {elapsed:.0f}s | "
            f"Score={risk_score}/100 | Completeness={completeness_score}% | "
            f"Sources: {len(ok_sources)} OK, {len(fail_sources)} FAIL"
        )
        if fail_sources:
            summary_line += f" ({fail_names})"
        summary_line += f" | Formats: {formats_str}"
        if error:
            summary_line += f" | Error: {error[:100]}"

        with open(SUMMARY_LOG, "a", encoding="utf-8") as sf:
            sf.write(summary_line + "\n")
    except Exception:
        pass  # Summary log failure should never block job completion

    # Cleanup
    sink_id = _active_sinks.pop(job_id, None)
    if sink_id is not None:
        try:
            logger.remove(sink_id)
        except ValueError:
            pass

    _job_start_times.pop(job_id, None)
    _job_events.pop(job_id, None)


def get_log_file_path(job_id: str) -> Path | None:
    """Returneaza path-ul fisierului log pentru un job (daca exista)."""
    path = _get_log_path(job_id)
    return path if path.exists() else None
