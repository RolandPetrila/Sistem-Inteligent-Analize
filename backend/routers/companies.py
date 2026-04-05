import csv
import io

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from loguru import logger

from backend.database import db

router = APIRouter()


@router.get("/favorites")
async def list_favorites():
    """Return only companies marked as favorite."""
    try:
        rows = await db.fetch_all(
            "SELECT * FROM companies WHERE is_favorite = 1 ORDER BY last_analyzed_at DESC"
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


@router.get("")
async def list_companies(
    search: str | None = None,
    county: str | None = None,
    caen: str | None = None,
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

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    total_row = await db.fetch_one(
        f"SELECT COUNT(*) as c FROM companies {where}", tuple(params)
    )
    total = total_row["c"] if total_row else 0

    rows = await db.fetch_all(
        f"SELECT * FROM companies {where} ORDER BY last_analyzed_at DESC LIMIT ? OFFSET ?",
        tuple(params + [limit, offset]),
    )

    return {"companies": [dict(r) for r in rows], "total": total}


@router.get("/export/csv")
async def export_companies_csv():
    """DF7: Export toate companiile in format CSV (CRM-ready)."""
    rows = await db.fetch_all(
        "SELECT cui, name, caen_code, caen_description, county, city, "
        "analysis_count, first_analyzed_at, last_analyzed_at "
        "FROM companies ORDER BY name"
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "CUI", "Denumire", "CAEN Cod", "CAEN Descriere",
        "Judet", "Oras", "Nr Analize", "Prima Analiza", "Ultima Analiza",
    ])
    for row in rows:
        r = dict(row)
        writer.writerow([
            r.get("cui", ""),
            r.get("name", ""),
            r.get("caen_code", ""),
            r.get("caen_description", ""),
            r.get("county", ""),
            r.get("city", ""),
            r.get("analysis_count", 0),
            r.get("first_analyzed_at", ""),
            r.get("last_analyzed_at", ""),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=companii_ris.csv"},
    )


@router.get("/{company_id}")
async def get_company(company_id: str):
    row = await db.fetch_one("SELECT * FROM companies WHERE id = ?", (company_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Company not found")

    # Get reports for this company
    reports = await db.fetch_all(
        "SELECT id, report_type, report_level, title, summary, risk_score, created_at "
        "FROM reports WHERE company_id = ? ORDER BY created_at DESC",
        (company_id,),
    )

    # N4: Get score history for trend display
    score_history = await db.fetch_all(
        "SELECT numeric_score, dimensions, recorded_at "
        "FROM score_history WHERE company_id = ? ORDER BY recorded_at DESC LIMIT 10",
        (company_id,),
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


@router.get("/{company_id}/timeline")
async def company_timeline(company_id: str):
    """Chronological list of events: reports, score changes, monitoring alerts."""
    row = await db.fetch_one("SELECT id FROM companies WHERE id = ?", (company_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Company not found")

    events: list[dict] = []

    # Reports generated
    reports = await db.fetch_all(
        "SELECT id, title, report_type, risk_score, created_at "
        "FROM reports WHERE company_id = ? ORDER BY created_at DESC LIMIT 20",
        (company_id,),
    )
    for r in reports:
        events.append({
            "type": "report",
            "title": r.get("title", "Raport"),
            "detail": f"Tip: {r.get('report_type', 'N/A')} | Risc: {r.get('risk_score', 'N/A')}",
            "date": r.get("created_at", ""),
            "link": f"/reports/{r['id']}",
        })

    # Score changes
    scores = await db.fetch_all(
        "SELECT numeric_score, recorded_at "
        "FROM score_history WHERE company_id = ? ORDER BY recorded_at DESC LIMIT 20",
        (company_id,),
    )
    for s in scores:
        events.append({
            "type": "score",
            "title": f"Scor actualizat: {s.get('numeric_score', 'N/A')}/100",
            "detail": "",
            "date": s.get("recorded_at", ""),
            "link": "",
        })

    # Monitoring alerts
    try:
        alerts = await db.fetch_all(
            "SELECT message, severity, created_at "
            "FROM monitoring_audit WHERE company_id = ? ORDER BY created_at DESC LIMIT 20",
            (company_id,),
        )
        for a in alerts:
            events.append({
                "type": "alert",
                "title": f"Alerta [{a.get('severity', 'INFO')}]",
                "detail": a.get("message", ""),
                "date": a.get("created_at", ""),
                "link": "",
            })
    except Exception as e:
        logger.debug(f"[companies] monitoring check: {e}")

    # Sort by date descending
    events.sort(key=lambda e: e.get("date", ""), reverse=True)
    return {"timeline": events[:50]}


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
