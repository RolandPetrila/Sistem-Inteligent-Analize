"""
Report service layer — logica de business extrasa din routers/reports.py (F9-3).
Ruterele raman thin wrappers peste aceste functii.
"""
import json
from pathlib import Path

from backend.config import settings
from backend.database import db


async def get_report_by_id(report_id: str) -> dict | None:
    """
    Returneaza un raport complet dupa ID, inclusiv surse si formate disponibile.
    Returns None daca raportul nu exista.
    """
    row = await db.fetch_one("SELECT * FROM reports WHERE id = ?", (report_id,))
    if not row:
        return None

    full_data = None
    if row["full_data"]:
        try:
            full_data = json.loads(row["full_data"])
        except (json.JSONDecodeError, TypeError):
            full_data = None

    formats = []
    for fmt in ["pdf", "docx", "excel", "html", "pptx"]:
        if row.get(f"{fmt}_path"):
            formats.append(fmt)

    sources = await db.fetch_all(
        "SELECT * FROM report_sources WHERE report_id = ? ORDER BY accessed_at",
        (report_id,),
    )

    return {
        "id": row["id"],
        "job_id": row["job_id"],
        "company_id": row["company_id"],
        "report_type": row["report_type"],
        "report_level": row["report_level"],
        "title": row["title"],
        "summary": row["summary"],
        "full_data": full_data,
        "risk_score": row["risk_score"],
        "created_at": row["created_at"],
        "formats_available": formats,
        "sources": [dict(s) for s in sources],
    }


async def list_reports(
    report_type: str | None = None,
    company_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """
    Returneaza o lista paginata de rapoarte cu filtre optionale.
    Output: {"reports": [...], "total": int}
    """
    conditions = []
    params: list = []

    if report_type:
        conditions.append("report_type = ?")
        params.append(report_type)
    if company_id:
        conditions.append("company_id = ?")
        params.append(company_id)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    total_row = await db.fetch_one(
        f"SELECT COUNT(*) as c FROM reports {where}", tuple(params)
    )
    total = total_row["c"] if total_row else 0

    rows = await db.fetch_all(
        f"SELECT * FROM reports {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        tuple(params + [limit, offset]),
    )

    reports = []
    for row in rows:
        formats = []
        for fmt in ["pdf", "docx", "excel", "html", "pptx"]:
            if row.get(f"{fmt}_path"):
                formats.append(fmt)
        one_pager = Path(settings.outputs_dir) / row["job_id"] / "raport_executiv.pdf"
        if one_pager.exists():
            formats.append("one_pager")
        reports.append({
            "id": row["id"],
            "job_id": row["job_id"],
            "company_id": row["company_id"],
            "report_type": row["report_type"],
            "report_level": row["report_level"],
            "title": row["title"],
            "summary": row["summary"],
            "risk_score": row["risk_score"],
            "created_at": row["created_at"],
            "formats_available": formats,
        })

    return {"reports": reports, "total": total}


ALLOWED_SECTIONS = {
    "company", "financial", "risk_score", "market", "swot",
    "early_warnings", "due_diligence", "benchmark", "relations",
    "company_network", "predictive_scores", "funding_programs",
}


async def get_report_data(report_id: str, section: str | None = None) -> dict | None:
    """
    Returneaza full_data JSON al unui raport, optional filtrat per sectiune.
    Returns None daca raportul nu exista.
    Raises ValueError daca sectiunea nu este permisa.
    """
    row = await db.fetch_one(
        "SELECT full_data FROM reports WHERE id = ?", (report_id,)
    )
    if not row:
        return None

    data = json.loads(row["full_data"]) if row.get("full_data") else {}

    if section and section not in ALLOWED_SECTIONS:
        raise ValueError(
            f"Sectiune invalida. Permise: {sorted(ALLOWED_SECTIONS)}"
        )

    if section:
        return {section: data.get(section)}

    return data
