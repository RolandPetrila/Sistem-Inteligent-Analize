import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from backend.database import db
from backend.config import settings

router = APIRouter()


@router.get("")
async def list_reports(
    report_type: str | None = None,
    company_id: str | None = None,
    limit: int = Query(default=20, le=100),
    offset: int = 0,
):
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
        # Check if one_pager exists on disk
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


@router.get("/{report_id}")
async def get_report(report_id: str):
    row = await db.fetch_one("SELECT * FROM reports WHERE id = ?", (report_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

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

    # Get sources
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


@router.get("/{report_id}/download/one_pager")
async def download_one_pager(report_id: str):
    """DF3: Download raport executiv 1-pager PDF."""
    row = await db.fetch_one("SELECT job_id FROM reports WHERE id = ?", (report_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

    one_pager_path = (Path(settings.outputs_dir) / row["job_id"] / "raport_executiv.pdf").resolve()
    outputs_root = Path(settings.outputs_dir).resolve()
    if not str(one_pager_path).startswith(str(outputs_root)):
        raise HTTPException(status_code=403, detail="Access denied")
    if not one_pager_path.exists():
        raise HTTPException(status_code=404, detail="1-Pager not generated for this report")

    return FileResponse(
        one_pager_path,
        media_type="application/pdf",
        filename="raport_executiv.pdf",
    )


@router.get("/{report_id}/download/{format}")
async def download_report(report_id: str, format: str):
    if format not in ("pdf", "docx", "excel", "html", "pptx"):
        raise HTTPException(status_code=400, detail="Invalid format")

    row = await db.fetch_one("SELECT * FROM reports WHERE id = ?", (report_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

    path_key = f"{format}_path"
    file_path = row.get(path_key)
    if not file_path:
        raise HTTPException(status_code=404, detail=f"Format {format} not available")

    full_path = Path(file_path).resolve()
    outputs_root = Path(settings.outputs_dir).resolve()
    if not str(full_path).startswith(str(outputs_root)):
        raise HTTPException(status_code=403, detail="Access denied")
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    media_types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "html": "text/html",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }

    return FileResponse(
        full_path,
        media_type=media_types.get(format, "application/octet-stream"),
        filename=full_path.name,
    )
