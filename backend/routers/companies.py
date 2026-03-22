import csv
import io

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.database import db

router = APIRouter()


@router.get("")
async def list_companies(
    search: str | None = None,
    county: str | None = None,
    caen: str | None = None,
    limit: int = Query(default=20, le=100),
    offset: int = 0,
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

    return {
        **dict(row),
        "reports": [dict(r) for r in reports],
    }
