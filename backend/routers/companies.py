
import json
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from loguru import logger
from pydantic import BaseModel  # noqa: F401 — used by ChatRequest

from backend.config import settings
from backend.database import db
from backend.errors import ErrorCode, RISError
from backend.rate_limiter import rate_limit_read

router = APIRouter()


@router.get("/favorites")
async def list_favorites():
    """Return only companies marked as favorite."""
    try:
        rows = await db.fetch_all(
            "SELECT id, cui, name, caen_code, county, is_active, is_favorite, last_analyzed_at, risk_score, tag, note FROM companies WHERE is_favorite = 1 ORDER BY last_analyzed_at DESC LIMIT 500"
        )
        return {"companies": [dict(r) for r in rows], "total": len(rows)}
    except Exception as e:
        logger.debug(f"[companies] is_favorite column: {e}")
        return {"companies": [], "total": 0}


@router.get("/stats/risk-movers")
async def risk_movers():
    """Companies with the biggest score drops in the last 30 days."""
    try:
        rows = await db.fetch_all(
            """
            WITH ranked AS (
                SELECT
                    company_id,
                    numeric_score,
                    recorded_at,
                    ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY recorded_at DESC) AS rn_new,
                    ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY recorded_at ASC) AS rn_old
                FROM score_history
                WHERE recorded_at >= datetime('now', '-30 days')
            ),
            latest AS (
                SELECT company_id, numeric_score AS new_score
                FROM ranked WHERE rn_new = 1
            ),
            oldest AS (
                SELECT company_id, numeric_score AS old_score
                FROM ranked WHERE rn_old = 1
            )
            SELECT
                l.company_id,
                c.name AS company_name,
                c.cui,
                o.old_score,
                l.new_score,
                (l.new_score - o.old_score) AS delta
            FROM latest l
            JOIN oldest o ON l.company_id = o.company_id
            LEFT JOIN companies c ON l.company_id = c.id
            WHERE l.new_score != o.old_score
            ORDER BY delta ASC
            LIMIT 10
            """
        )
        return {"movers": [dict(r) for r in rows]}
    except Exception as e:
        logger.debug(f"risk-movers query failed (expected if no data): {e}")
        return {"movers": []}


@router.get("/search/fts")
async def search_companies_fts(
    q: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(20, ge=1, le=50),
):
    """FTS5 full-text search pe firme — mai rapid si ranked vs LIKE."""
    try:
        rows = await db.fetch_all(
            """SELECT c.id, c.name, c.cui, c.caen_code, c.county, c.city,
                      c.last_analyzed_at, c.analysis_count
               FROM companies_fts fts
               JOIN companies c ON c.cui = fts.cui
               WHERE companies_fts MATCH ?
               ORDER BY rank
               LIMIT ?""",
            (f"{q}*", limit),
        )
        return rows
    except Exception as e:
        logger.warning(f"[companies] FTS5 search failed, fallback to LIKE: {e}")
        rows = await db.fetch_all(
            "SELECT id, name, cui, caen_code, county, city FROM companies WHERE name LIKE ? LIMIT ?",
            (f"%{q}%", limit),
        )
        return rows


@router.post("/import")
async def import_companies_csv(file: UploadFile = File(...)):
    """F3-7: Import companii din CSV cu coloane cui, name. INSERT OR IGNORE — nu suprascrie date existente."""
    import uuid as _uuid

    from backend.agents.tools.cui_validator import validate_cui

    content = await file.read()
    lines = content.decode("utf-8", errors="replace").splitlines()
    if not lines:
        raise RISError(ErrorCode.VALIDATION_ERROR, "Fisier CSV gol")

    header = [h.lower().strip().strip('"') for h in lines[0].split(",")]
    cui_idx = next((i for i, h in enumerate(header) if "cui" in h), 0)
    name_idx = next(
        (i for i, h in enumerate(header) if any(k in h for k in ["name", "denu", "firma", "compan", "nume"])),
        1
    )

    data_lines = [l for l in lines[1:] if l.strip()]
    if len(data_lines) > 5000:
        raise RISError(ErrorCode.VALIDATION_ERROR, "CSV prea mare — maxim 5000 randuri per import")

    imported, skipped = 0, 0
    for line in data_lines:
        parts = line.split(",")
        if len(parts) <= max(cui_idx, name_idx):
            skipped += 1
            continue
        cui = parts[cui_idx].strip().strip('"')
        name = parts[name_idx].strip().strip('"') if name_idx < len(parts) else ""
        val = validate_cui(cui)
        if not val.get("valid"):
            skipped += 1
            continue
        await db.execute(
            "INSERT OR IGNORE INTO companies(id, cui, name, created_at, updated_at) "
            "VALUES (?,?,?,datetime('now'),datetime('now'))",
            (_uuid.uuid4().hex, cui, name or f"Firma {cui}")
        )
        imported += 1

    return {"imported": imported, "skipped": skipped}


VALID_SORT_COLS = {
    "last_analyzed": "last_analyzed_at DESC",
    "score_desc": "CAST(COALESCE(last_risk_score_numeric, 0) AS INTEGER) DESC",
    "score_asc": "CAST(COALESCE(last_risk_score_numeric, 0) AS INTEGER) ASC",
    "name_asc": "name ASC",
    "name_desc": "name DESC",
    "analysis_count": "analysis_count DESC",
}

VALID_RISK_SCORES = {"Verde", "Galben", "Rosu"}


@router.get("", dependencies=[Depends(rate_limit_read)])
async def list_companies(
    search: str | None = None,
    county: str | None = None,
    caen: str | None = None,
    risk_score: str | None = None,
    sort: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    conditions = []
    params: list = []

    if search:
        conditions.append("(name LIKE ? OR cui LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    if county:
        conditions.append("county = ?")
        params.append(county)
    if caen:
        conditions.append("caen_code = ?")
        params.append(caen)
    if risk_score and risk_score in VALID_RISK_SCORES:
        conditions.append("risk_score = ?")
        params.append(risk_score)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    order_by = VALID_SORT_COLS.get(sort or "last_analyzed", "last_analyzed_at DESC")

    total_row = await db.fetch_one(
        f"SELECT COUNT(*) as c FROM companies {where}", tuple(params)
    )
    total = total_row["c"] if total_row else 0

    rows = await db.fetch_all(
        f"SELECT id, cui, name, caen_code, county, is_active, is_favorite, last_analyzed_at, risk_score, tag, note FROM companies {where} ORDER BY {order_by} LIMIT ? OFFSET ?",
        tuple(params + [limit, offset]),
    )

    return {"companies": [dict(r) for r in rows], "total": total}


async def _stream_companies_csv():
    """F7-2: Generator streaming CSV — evita fetch_all() in memorie pentru liste mari."""
    header = "CUI,Denumire,CAEN Cod,CAEN Descriere,Judet,Oras,Nr Analize,Prima Analiza,Ultima Analiza\n"
    yield header
    offset = 0
    chunk_size = 500
    while True:
        rows = await db.fetch_all(
            "SELECT cui, name, caen_code, caen_description, county, city, "
            "analysis_count, first_analyzed_at, last_analyzed_at "
            f"FROM companies ORDER BY name LIMIT {chunk_size} OFFSET {offset}"
        )
        if not rows:
            break
        for row in rows:
            r = dict(row)
            # Escape commas in text fields using semicolon
            def _esc(v):
                return str(v or "").replace(",", ";").replace("\n", " ")
            yield (
                f"{_esc(r.get('cui'))},{_esc(r.get('name'))},{_esc(r.get('caen_code'))},"
                f"{_esc(r.get('caen_description'))},{_esc(r.get('county'))},{_esc(r.get('city'))},"
                f"{r.get('analysis_count', 0)},{_esc(r.get('first_analyzed_at'))},"
                f"{_esc(r.get('last_analyzed_at'))}\n"
            )
        offset += chunk_size


@router.get("/export/csv")
async def export_companies_csv():
    """DF7: Export toate companiile in format CSV (CRM-ready).
    F7-2: Streaming response — nu incarca toata lista in memorie."""
    return StreamingResponse(
        _stream_companies_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=companii_ris.csv"},
    )


# --- Tags (F3-3) ---
@router.get("/{company_id}/tags")
async def get_company_tags(company_id: str):
    tags = await db.fetch_all(
        "SELECT tag, created_at FROM company_tags WHERE company_id = ? ORDER BY created_at DESC",
        (company_id,),
    )
    return {"tags": [r["tag"] for r in tags]}


@router.post("/{company_id}/tags")
async def add_company_tag(company_id: str, body: dict):
    tag = str(body.get("tag", "")).strip()[:30]
    if not tag:
        raise RISError(ErrorCode.VALIDATION_ERROR, "Tag gol")
    await db.execute(
        "INSERT OR IGNORE INTO company_tags(company_id, tag) VALUES (?, ?)",
        (company_id, tag),
    )
    return {"ok": True}


@router.delete("/{company_id}/tags/{tag}")
async def remove_company_tag(company_id: str, tag: str):
    await db.execute(
        "DELETE FROM company_tags WHERE company_id = ? AND tag = ?",
        (company_id, tag),
    )
    return {"ok": True}


# --- Note (F3-3) ---
@router.get("/{company_id}/note")
async def get_company_note(company_id: str):
    row = await db.fetch_one(
        "SELECT note, updated_at FROM company_notes WHERE company_id = ?",
        (company_id,),
    )
    return {
        "note": row["note"] if row else "",
        "updated_at": row["updated_at"] if row else None,
    }


@router.put("/{company_id}/note")
async def upsert_company_note(company_id: str, body: dict):
    note = str(body.get("note", ""))[:2000]
    existing = await db.fetch_one(
        "SELECT id FROM company_notes WHERE company_id = ?", (company_id,)
    )
    if existing:
        await db.execute(
            "UPDATE company_notes SET note = ?, updated_at = datetime('now') WHERE company_id = ?",
            (note, company_id),
        )
    else:
        await db.execute(
            "INSERT INTO company_notes(company_id, note) VALUES (?, ?)",
            (company_id, note),
        )
    return {"ok": True}


@router.get("/{company_id}")
async def get_company(company_id: str):
    row = await db.fetch_one("SELECT id, cui, name, caen_code, county, is_active, is_favorite, last_analyzed_at, risk_score, tag, note FROM companies WHERE id = ?", (company_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Company not found")

    # F5.1: Parallel queries — reports + score_history în paralel
    import asyncio as _asyncio
    reports, score_history = await _asyncio.gather(
        db.fetch_all(
            "SELECT id, report_type, report_level, title, summary, risk_score, created_at "
            "FROM reports WHERE company_id = ? ORDER BY created_at DESC",
            (company_id,),
        ),
        db.fetch_all(
            "SELECT numeric_score, dimensions, recorded_at "
            "FROM score_history WHERE company_id = ? ORDER BY recorded_at DESC LIMIT 10",
            (company_id,),
        ),
    )

    return {
        **dict(row),
        "reports": [dict(r) for r in reports],
        "score_history": [dict(s) for s in score_history],
    }


@router.put("/{company_id}/favorite")
async def toggle_favorite(company_id: str):
    """Toggle is_favorite on a company. Creates column if missing."""
    row = await db.fetch_one("SELECT id FROM companies WHERE id = ?", (company_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Company not found")

    try:
        current = await db.fetch_one(
            "SELECT is_favorite FROM companies WHERE id = ?", (company_id,)
        )
        new_val = 0 if current and current.get("is_favorite") else 1
    except Exception as e:
        logger.debug(f"[companies] toggle favorite: {e}")
        # Column does not exist yet — create it then set to 1
        try:
            await db.execute("ALTER TABLE companies ADD COLUMN is_favorite INTEGER DEFAULT 0")
        except Exception as e2:
            logger.debug(f"[companies] migration: {e2}")
        new_val = 1

    await db.execute("UPDATE companies SET is_favorite = ? WHERE id = ?", (new_val, company_id))
    return {"ok": True, "is_favorite": bool(new_val)}


@router.post("/{company_id}/auto-reanalyze")
async def toggle_auto_reanalyze(company_id: str):
    """F6-6: Toggle auto_reanalyze flag pe companie.
    Scheduler-ul va re-analiza automat la intervalul configurat (default 30 zile)."""
    row = await db.fetch_one("SELECT id FROM companies WHERE id = ?", (company_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Company not found")

    # Ensure columns exist (idempotent ALTER TABLE)
    for alter_sql in [
        "ALTER TABLE companies ADD COLUMN auto_reanalyze INTEGER DEFAULT 0",
        "ALTER TABLE companies ADD COLUMN reanalyze_interval_days INTEGER DEFAULT 30",
    ]:
        try:
            await db.execute(alter_sql)
        except Exception:
            pass  # Column already exists

    current = await db.fetch_one(
        "SELECT auto_reanalyze FROM companies WHERE id = ?", (company_id,)
    )
    new_val = 0 if current and current.get("auto_reanalyze") else 1
    await db.execute(
        "UPDATE companies SET auto_reanalyze = ? WHERE id = ?", (new_val, company_id)
    )
    logger.info(f"[companies] auto_reanalyze={bool(new_val)} pentru company_id={company_id}")
    return {"ok": True, "auto_reanalyze": bool(new_val)}


@router.get("/{company_id}/timeline")
async def company_timeline(company_id: str):
    """Chronological list of events: reports, score changes, monitoring alerts."""
    row = await db.fetch_one("SELECT id FROM companies WHERE id = ?", (company_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Company not found")

    # H5: Single UNION query — eliminam 3 round-trips DB
    TIMELINE_SQL = """
        SELECT 'report' as type,
               id as ref_id,
               title as title,
               report_type || ' | Risc: ' || COALESCE(CAST(risk_score AS TEXT), 'N/A') as detail,
               created_at as event_date,
               '/reports/' || id as link
        FROM reports WHERE company_id = ? AND created_at IS NOT NULL
        UNION ALL
        SELECT 'score' as type,
               CAST(id AS TEXT) as ref_id,
               'Scor actualizat: ' || CAST(numeric_score AS TEXT) || '/100' as title,
               '' as detail,
               recorded_at as event_date,
               '' as link
        FROM score_history WHERE company_id = ? AND recorded_at IS NOT NULL
        UNION ALL
        SELECT 'alert' as type,
               CAST(id AS TEXT) as ref_id,
               'Alertă [' || severity || ']' as title,
               message as detail,
               created_at as event_date,
               '' as link
        FROM monitoring_audit WHERE company_id = ? AND created_at IS NOT NULL
        ORDER BY event_date DESC
        LIMIT 50
    """
    try:
        rows = await db.fetch_all(TIMELINE_SQL, (company_id, company_id, company_id))
        events = [
            {
                "type": r["type"],
                "title": r["title"] or "",
                "detail": r["detail"] or "",
                "date": r["event_date"] or "",
                "link": r["link"] or "",
            }
            for r in rows
        ]
    except Exception as e:
        logger.debug(f"[companies] timeline UNION error: {e}")
        events = []
    return {"events": events}


@router.get("/{company_id}/score-trend")
async def get_score_trend(
    company_id: int,
    limit: int = Query(20, ge=1, le=100),
):
    """Score trend cu LAG window function — delta per analiza."""
    rows = await db.fetch_all(
        """SELECT
               recorded_at,
               numeric_score as score,
               numeric_score - LAG(numeric_score) OVER (ORDER BY recorded_at) as delta
           FROM score_history
           WHERE company_id = ?
           ORDER BY recorded_at DESC
           LIMIT ?""",
        (company_id, limit),
    )
    return rows


@router.get("/{cui}/predictive")
async def get_predictive_scores(cui: str):
    """F2-5: Calculeaza scoruri predictive financiare Altman/Piotroski/Beneish/Zmijewski.
    Foloseste cel mai recent raport disponibil pentru CUI-ul dat."""
    from datetime import UTC, datetime

    from backend.agents.verification.scoring import calculate_all_predictive_scores

    # Gaseste cel mai recent raport pentru CUI
    report = await db.fetch_one(
        """
        SELECT r.full_data FROM reports r
        JOIN companies c ON c.id = r.company_id
        WHERE c.cui = ?
        ORDER BY r.created_at DESC
        LIMIT 1
        """,
        (cui,),
    )

    if not report or not report["full_data"]:
        raise HTTPException(status_code=404, detail=f"Nu exista raport pentru CUI {cui}")

    try:
        verified_data = json.loads(report["full_data"])
    except Exception:
        raise HTTPException(status_code=500, detail="Date raport invalide")

    scores = calculate_all_predictive_scores(verified_data)
    scores["cui"] = cui
    scores["computed_at"] = datetime.now(UTC).isoformat()

    return scores


# ---------------------------------------------------------------------------
# F6-7: Raport Evolutie Multi-An (aceeasi firma, mai multe rapoarte)
# ---------------------------------------------------------------------------

def _extract_ca_from_full(data: dict):
    """Extrage CA din full_data al unui raport."""
    fin = data.get("financial", {})
    ca = fin.get("cifra_afaceri", {})
    if isinstance(ca, dict):
        return ca.get("value")
    return None


def _extract_profit_from_full(data: dict):
    fin = data.get("financial", {})
    p = fin.get("profit_net", {})
    if isinstance(p, dict):
        return p.get("value")
    return None


def _extract_angajati_from_full(data: dict):
    fin = data.get("financial", {})
    e = fin.get("numar_angajati", {})
    if isinstance(e, dict):
        return e.get("value")
    return None


def _extract_risk_score_from_full(data: dict):
    rs = data.get("risk_score", {})
    if isinstance(rs, dict):
        return rs.get("numeric_score")
    return None


@router.get("/{cui}/timeline-report")
async def get_company_timeline_report(
    cui: str,
    max_reports: int = Query(default=5, ge=2, le=10),
):
    """F6-7: Returneaza evolutia multi-an a aceleiasi firme (ultimele N rapoarte).
    Extrage CA, Profit, Angajati, Scor Risc din fiecare raport si calculeaza trendurii."""
    company_row = await db.fetch_one(
        "SELECT id, name FROM companies WHERE cui = ? LIMIT 1", (cui,)
    )
    if not company_row:
        raise HTTPException(status_code=404, detail=f"Firma cu CUI {cui} nu a fost gasita")

    company_id = company_row["id"]
    company_name = company_row["name"]

    rows = await db.fetch_all(
        "SELECT full_data, created_at FROM reports "
        "WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
        (company_id, max_reports),
    )

    if not rows:
        raise HTTPException(status_code=404, detail="Nu exista rapoarte pentru aceasta firma")

    years = []
    ca_values = []
    profit_values = []
    risk_values = []

    for row in reversed(rows):  # cel mai vechi primul
        data: dict = {}
        try:
            data = json.loads(row["full_data"]) if row["full_data"] else {}
        except (json.JSONDecodeError, TypeError):
            data = {}

        analyzed_at = row["created_at"] or ""
        year_label = analyzed_at[:4] if analyzed_at else "?"
        ca = _extract_ca_from_full(data)
        profit = _extract_profit_from_full(data)
        angajati = _extract_angajati_from_full(data)
        risk = _extract_risk_score_from_full(data)

        years.append({
            "year": year_label,
            "ca": ca,
            "profit": profit,
            "angajati": angajati,
            "risk_score": risk,
            "analyzed_at": analyzed_at,
        })
        ca_values.append(ca)
        profit_values.append(profit)
        risk_values.append(risk)

    def _pct_growth(vals: list) -> float | None:
        valids = [v for v in vals if v is not None]
        if len(valids) < 2 or valids[0] == 0:
            return None
        return round(((valids[-1] - valids[0]) / abs(valids[0])) * 100, 1)

    def _trend_label(vals: list) -> str:
        valids = [v for v in vals if v is not None]
        if len(valids) < 2:
            return "DATE INSUFICIENTE"
        first, last = valids[0], valids[-1]
        pct = ((last - first) / abs(first)) * 100 if first != 0 else (last - first)
        if pct > 5:
            return "IN CRESTERE"
        elif pct < -5:
            return "IN SCADERE"
        return "STABIL"

    def _risk_trend_label(vals: list) -> str:
        valids = [v for v in vals if v is not None]
        if len(valids) < 2:
            return "DATE INSUFICIENTE"
        delta = valids[-1] - valids[0]
        if delta > 5:
            return "IN IMBUNATATIRE"
        elif delta < -5:
            return "IN DETERIORARE"
        return "STABIL"

    return {
        "cui": cui,
        "company_name": company_name,
        "reports_count": len(rows),
        "years": years,
        "trends": {
            "ca_growth_pct": _pct_growth(ca_values),
            "profit_trend": _trend_label(profit_values),
            "risk_trend": _risk_trend_label(risk_values),
        },
    }


@router.get("/{cui}/timeline-report/pdf")
async def download_company_timeline_pdf(
    cui: str,
    max_reports: int = Query(default=5, ge=2, le=10),
):
    """F6-7: Genereaza si descarca PDF cu evolutia multi-an a aceleiasi firme."""
    from backend.reports.timeline_generator import generate_timeline_pdf

    timeline_data = await get_company_timeline_report(cui=cui, max_reports=max_reports)

    outputs_root = os.path.abspath(settings.outputs_dir)
    os.makedirs(outputs_root, exist_ok=True)

    tmp_path = os.path.join(outputs_root, f"timeline_{uuid.uuid4().hex}.pdf")
    try:
        generate_timeline_pdf(timeline_data, tmp_path)
        return FileResponse(
            tmp_path,
            media_type="application/pdf",
            filename=f"evolutie_{cui}.pdf",
        )
    except Exception:
        logger.exception(f"[timeline_pdf] eroare generare pentru CUI {cui}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise HTTPException(status_code=500, detail="Eroare internă generare PDF evolutie")


# ─── RAG Chat with Company ────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str
    report_id: str | None = None


@router.post("/{company_id}/chat", dependencies=[Depends(rate_limit_read)])
async def chat_with_company(company_id: str, req: ChatRequest):
    """
    RAG Chat — raspunde la intrebari despre o companie folosind datele din ultimul raport.
    Flux: incarca full_data din reports → injecteaza in prompt → genereaza via Groq/Gemini.
    """
    question = (req.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Intrebarea nu poate fi goala")
    if len(question) > 500:
        raise HTTPException(status_code=400, detail="Intrebarea depaseste 500 caractere")

    company = await db.fetch_one(
        "SELECT id, cui, name, caen_code FROM companies WHERE id = ?",
        (company_id,),
    )
    if not company:
        raise HTTPException(status_code=404, detail="Compania nu a fost gasita")

    if req.report_id:
        report = await db.fetch_one(
            "SELECT id, full_data, title, created_at FROM reports WHERE id = ? AND company_id = ?",
            (req.report_id, company_id),
        )
    else:
        report = await db.fetch_one(
            """
            SELECT id, full_data, title, created_at
            FROM reports
            WHERE company_id = ?
              AND full_data IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (company_id,),
        )

    if not report or not report["full_data"]:
        raise HTTPException(
            status_code=404,
            detail="Nu exista raport generat pentru aceasta companie. Ruleaza mai intai o analiza.",
        )

    try:
        full_data = json.loads(report["full_data"])
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=500, detail="Date raport corupte")

    company_name = company["name"]
    context_parts = []

    # Sectiunile narative din raport
    for section_key, section_data in (full_data.get("report_sections") or {}).items():
        if isinstance(section_data, dict) and section_data.get("content"):
            title = section_data.get("title", section_key)
            content = section_data["content"][:800]
            context_parts.append(f"## {title}\n{content}")

    # Date cheie verificate
    verified = full_data.get("verified_data") or {}
    risk_score = verified.get("risk_score", {})
    if risk_score:
        context_parts.append(
            f"## Scor Risc\n"
            f"Scor: {risk_score.get('score', 'N/A')}/100 | "
            f"Culoare: {risk_score.get('color', 'N/A')} | "
            f"Factori: {', '.join(str(f[0]) for f in (risk_score.get('risk_factors') or [])[:3])}"
        )

    early_warnings = verified.get("early_warnings") or []
    if early_warnings:
        warnings_text = "; ".join(
            w.get("signal", "") for w in early_warnings[:3] if isinstance(w, dict)
        )
        if warnings_text:
            context_parts.append(f"## Early Warnings\n{warnings_text}")

    financial = verified.get("financial") or {}
    ca = financial.get("cifra_afaceri", {})
    ca_val = ca.get("value") if isinstance(ca, dict) else None
    if ca_val:
        context_parts.append(f"## Date Financiare Cheie\nCA: {ca_val:,.0f} RON")

    context_text = "\n\n".join(context_parts) or (
        f"Compania {company_name} (CUI: {company['cui']}) — date insuficiente in cache."
    )
    if len(context_text) > 12000:
        context_text = context_text[:12000] + "\n\n[... context trunchiat ...]"

    prompt = (
        f"Esti un analist de business intelligence care a analizat compania {company_name}.\n"
        f"Ai acces la urmatoarele date extrase din raportul generat:\n\n"
        f"{context_text}\n\n"
        f"---\n"
        f"Intrebarea utilizatorului: {question}\n\n"
        f"Raspunde in romana, concis si bazat EXCLUSIV pe datele de mai sus. "
        f"Daca datele nu sunt suficiente pentru a raspunde, spune explicit ce informatii lipsesc. "
        f"Nu inventa cifre sau fapte care nu sunt in context."
    )

    answer = None
    provider_used = "unknown"

    if settings.groq_api_key:
        try:
            from backend.http_client import get_client
            client = get_client()
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                json={
                    "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 600,
                    "temperature": 0.3,
                },
                timeout=20.0,
            )
            resp.raise_for_status()
            answer = resp.json()["choices"][0]["message"]["content"].strip()
            provider_used = "groq"
        except Exception as e:
            logger.warning(f"[chat] Groq failed: {e}")

    if not answer and settings.gemini_api_key:
        try:
            from backend.http_client import get_client
            client = get_client()
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
                f"?key={settings.gemini_api_key}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": 600, "temperature": 0.3},
                },
                timeout=20.0,
            )
            resp.raise_for_status()
            candidates = resp.json().get("candidates", [])
            if candidates:
                answer = candidates[0]["content"]["parts"][0]["text"].strip()
                provider_used = "gemini"
        except Exception as e:
            logger.warning(f"[chat] Gemini failed: {e}")

    if not answer:
        answer = (
            "Serviciul de chat este temporar indisponibil. "
            "Toti providerii AI au esuat. Incearca din nou in cateva momente."
        )
        provider_used = "fallback"

    logger.info(f"[chat] {company_name[:30]} | provider={provider_used} | q={question[:50]}")

    return {
        "question": question,
        "answer": answer,
        "provider": provider_used,
        "report_id": report["id"],
        "report_title": report["title"] or company_name,
        "company_name": company_name,
    }
