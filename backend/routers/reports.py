import json
import re
from datetime import date as _date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from backend.rate_limiter import rate_limit_downloads

from backend.database import db
from backend.config import settings
from backend.errors import RISError, ErrorCode

router = APIRouter()


@router.get("")
async def list_reports(
    report_type: str | None = None,
    company_id: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
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


@router.get("/{report_id}/download/one_pager", dependencies=[Depends(rate_limit_downloads)])
async def download_one_pager(report_id: str):
    """DF3: Download raport executiv 1-pager PDF."""
    row = await db.fetch_one("SELECT job_id FROM reports WHERE id = ?", (report_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

    one_pager_path = (Path(settings.outputs_dir) / row["job_id"] / "raport_executiv.pdf").resolve()
    outputs_root = Path(settings.outputs_dir).resolve()
    try:
        one_pager_path.relative_to(outputs_root)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    if not one_pager_path.exists():
        raise HTTPException(status_code=404, detail="1-Pager not generated for this report")

    return FileResponse(
        one_pager_path,
        media_type="application/pdf",
        filename="raport_executiv.pdf",
    )


@router.get("/{report_id}/download/{format}", dependencies=[Depends(rate_limit_downloads)])
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
    try:
        full_path.relative_to(outputs_root)
    except ValueError:
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

    from urllib.parse import quote
    safe_name = quote(full_path.name, safe=".")
    return FileResponse(
        full_path,
        media_type=media_types.get(format, "application/octet-stream"),
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"},
    )


@router.get("/{report_id}/data")
async def get_report_data(
    report_id: str,
    section: str | None = None,
):
    """FIX #34: Returneaza full_data JSON, optional filtrat per sectiune.
    Evita payload >500KB pe GET /{report_id} principal."""
    row = await db.fetch_one(
        "SELECT full_data FROM reports WHERE id = ?", (report_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    data = json.loads(row["full_data"]) if row.get("full_data") else {}
    if section:
        return {section: data.get(section)}
    return data


@router.get("/{report_id}/delta")
async def get_report_delta(report_id: str):
    """Returneaza delta (modificari) fata de analiza anterioara."""
    row = await db.fetch_one(
        "SELECT * FROM report_deltas WHERE report_id = ?", (report_id,)
    )
    if not row:
        return {
            "has_delta": False,
            "message": "Prima analiza pentru aceasta firma — fara date anterioare"
        }
    changes = []
    if row.get("changes_json"):
        try:
            changes = json.loads(row["changes_json"])
        except (json.JSONDecodeError, TypeError):
            changes = []
    return {
        "has_delta": True,
        "previous_report_id": row.get("previous_report_id"),
        "previous_score": row.get("previous_score"),
        "current_score": row.get("current_score"),
        "score_delta": (row.get("current_score") or 0) - (row.get("previous_score") or 0),
        "changes": changes,
    }


@router.get("/{report_id}/export/ics")
async def export_seap_calendar(report_id: str):
    """F3-5: Exporta licitatii SEAP din raport ca fisier .ics (iCalendar)."""
    import uuid as _uuid
    from fastapi.responses import Response as FastAPIResponse

    report = await db.fetch_one("SELECT full_data FROM reports WHERE id = ?", (report_id,))
    if not report:
        raise RISError(ErrorCode.NOT_FOUND, "Raport negasit")

    data = json.loads(report["full_data"] or "{}")
    tenders = data.get("market", {}).get("seap_tenders", [])
    if not tenders:
        raise RISError(ErrorCode.NOT_FOUND, "Nu exista licitatii in acest raport")

    ics_lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0",
        "PRODID:-//RIS//Licitatii SEAP//RO", "CALSCALE:GREGORIAN",
    ]
    events_added = 0
    for t in tenders:
        raw_deadline = str(t.get("deadline_date", ""))
        try:
            dt = _date.fromisoformat(raw_deadline[:10])
            deadline = dt.strftime("%Y%m%d")
        except (ValueError, TypeError):
            continue
        title = str(t.get("title", "Licitatie SEAP"))[:60]
        uid = t.get("id", str(_uuid.uuid4()))
        ics_lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}@ris-local",
            f"SUMMARY:{title}",
            f"DESCRIPTION:Valoare: {t.get('value', 'N/A')} RON\\nSursa: SEAP",
            f"DTSTART;VALUE=DATE:{deadline}",
            f"DTEND;VALUE=DATE:{deadline}",
            "STATUS:TENTATIVE",
            "END:VEVENT",
        ]
        events_added += 1

    if events_added == 0:
        raise RISError(ErrorCode.NOT_FOUND, "Nu exista licitatii cu data de deadline valida in acest raport")

    ics_lines.append("END:VCALENDAR")
    ics_content = "\r\n".join(ics_lines)
    return FastAPIResponse(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": f"attachment; filename=licitatii_{report_id[:8]}.ics"}
    )


class SendEmailRequest(BaseModel):
    to: str
    subject: str | None = None

    @field_validator("to")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Adresa email invalida")
        return v


@router.post("/{report_id}/send-email")
async def send_report_email(report_id: str, data: SendEmailRequest):
    """Send the report PDF as an email attachment."""
    row = await db.fetch_one("SELECT * FROM reports WHERE id = ?", (report_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

    pdf_path = row.get("pdf_path")
    if not pdf_path or not Path(pdf_path).exists():
        raise HTTPException(status_code=404, detail="PDF not available for this report")

    # Validate path stays inside outputs
    full_path = Path(pdf_path).resolve()
    outputs_root = Path(settings.outputs_dir).resolve()
    try:
        full_path.relative_to(outputs_root)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    subject = data.subject or f"Raport RIS — {row.get('title', 'Raport')}"

    body_html = (
        f"<h2>{subject}</h2>"
        f"<p>Raportul generat de Roland Intelligence System este atasat.</p>"
        f"<p><small>Generat: {row.get('created_at', 'N/A')}</small></p>"
    )

    from backend.services.notification import send_email
    ok = await send_email(to=data.to, subject=subject, body_html=body_html, attachments=[str(full_path)])
    if not ok:
        raise HTTPException(status_code=500, detail="Email sending failed. Check Gmail configuration in Settings.")

    return {"ok": True, "sent_to": data.to}
