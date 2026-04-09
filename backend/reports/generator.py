"""
Report Generator — Orchestrator pentru generarea tuturor formatelor.
Lazy imports: fpdf2/openpyxl/pptx/docx se importeaza DOAR cand genereaza efectiv.
8C: ZIP auto-pack all formats.
G1: asyncio.to_thread — elibereaza event loop pentru generari CPU-bound (PDF/DOCX/Excel/PPTX).
     Toate formatele grele ruleaza concurent in thread pool (max 4 simultan).
"""

import asyncio
import zipfile
from datetime import UTC, datetime
from functools import partial
from pathlib import Path

from loguru import logger

from backend.config import settings


def _sanitize(text: str) -> str:
    """Lazy-loaded sanitize from pdf_generator."""
    from backend.reports.pdf_generator import _sanitize as _pdf_sanitize
    return _pdf_sanitize(text)


async def _run_format_async(name: str, fn, *args, **kwargs) -> bool:
    """G1: DRY helper — run sync format generator in thread pool, elibereaza event loop."""
    try:
        await asyncio.to_thread(partial(fn, *args, **kwargs))
        logger.info(f"[reports] {name} generated OK")
        return True
    except Exception as e:
        logger.error(f"[reports] {name} generation failed: {e}")
        return False


async def generate_all_reports(
    job_id: str,
    report_sections: dict,
    verified_data: dict,
    report_level: int,
    analysis_type: str,
    lang: str = "ro",
) -> dict:
    """
    Genereaza toate formatele de raport concurent in thread pool.
    Returneaza dict cu path-urile fisierelor generate.
    lang: "ro" (default) sau "en" — G5: i18n pentru etichete PDF/HTML.
    """
    output_dir = Path(settings.outputs_dir) / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Metadata comuna
    company = verified_data.get("company", {})
    company_name = ""
    denumire = company.get("denumire", {})
    if isinstance(denumire, dict):
        company_name = denumire.get("value", "")
    elif isinstance(denumire, str):
        company_name = denumire

    risk_score = verified_data.get("risk_score", {})
    sources_used = verified_data.get("sources_used", [])

    # A1: Număr raport unic RIS-YYYY-XXXX
    from backend.database import db as _db
    report_number = await _db.get_next_report_number()

    meta = {
        "title": f"Raport {analysis_type.replace('_', ' ').title()}",
        "company_name": company_name or "N/A",
        "report_level": report_level,
        "analysis_type": analysis_type,
        "generated_at": datetime.now(UTC).strftime("%d.%m.%Y %H:%M"),
        "risk_score": risk_score.get("score", "N/A"),
        "numeric_score": risk_score.get("numeric_score"),
        "risk_recommendation": risk_score.get("recommendation", ""),
        "sources_count": len(sources_used),
        "sources": sources_used,
        "report_number": report_number,
    }

    # G1: Pre-sanitize pentru PDF (closure → sanitize inainte de thread pool)
    from backend.reports.pdf_generator import _sanitize as pdf_sanitize_fn

    def _pdf_sanitize(obj):
        if isinstance(obj, str):
            return pdf_sanitize_fn(obj)
        if isinstance(obj, dict):
            return {_pdf_sanitize(k): _pdf_sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_pdf_sanitize(i) for i in obj]
        return obj

    from backend.reports.docx_generator import generate_docx
    from backend.reports.excel_generator import generate_excel
    from backend.reports.html_generator import generate_html
    from backend.reports.one_pager_generator import generate_one_pager
    from backend.reports.pdf_generator import generate_pdf
    from backend.reports.pptx_generator import generate_pptx

    pdf_path = output_dir / "raport.pdf"
    docx_path = output_dir / "raport.docx"
    html_path = output_dir / "raport.html"
    excel_path = output_dir / "raport.xlsx"
    pptx_path = output_dir / "raport.pptx"
    one_pager_path = output_dir / "raport_executiv.pdf"

    sanitized_sections = _pdf_sanitize(report_sections)
    sanitized_meta = _pdf_sanitize(meta)

    # G1+G5: Ruleaza toate formatele CPU-bound concurent in thread pool; pasa lang pentru i18n
    await asyncio.gather(
        _run_format_async("PDF", generate_pdf, sanitized_sections, sanitized_meta, str(pdf_path), verified_data=verified_data, lang=lang),
        _run_format_async("DOCX", generate_docx, report_sections, meta, str(docx_path), verified_data=verified_data),
        _run_format_async("HTML", generate_html, report_sections, meta, verified_data, str(html_path), lang=lang),
        _run_format_async("Excel", generate_excel, report_sections, meta, verified_data, str(excel_path)),
        _run_format_async("PPTX", generate_pptx, report_sections, meta, verified_data, str(pptx_path)),
        _run_format_async("1-Pager", generate_one_pager, verified_data, meta, str(one_pager_path)),
        return_exceptions=True,
    )

    paths = {}
    for fmt_name, path_obj in [
        ("pdf", pdf_path), ("docx", docx_path), ("html", html_path),
        ("excel", excel_path), ("pptx", pptx_path), ("one_pager", one_pager_path),
    ]:
        if path_obj.exists():
            paths[fmt_name] = str(path_obj)

    # 8C: ZIP auto-pack all formats
    if len(paths) >= 2:
        try:
            cui_part = ""
            cui_field = company.get("cui", {})
            if isinstance(cui_field, dict):
                cui_part = cui_field.get("value", "")
            elif isinstance(cui_field, str):
                cui_part = cui_field
            date_part = datetime.now(UTC).strftime("%Y-%m-%d")
            zip_name = f"raport_{cui_part}_{date_part}.zip" if cui_part else f"raport_{date_part}.zip"
            zip_path = output_dir / zip_name
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for fmt, fpath in paths.items():
                    p = Path(fpath)
                    if p.exists():
                        zf.write(p, p.name)
            paths["zip"] = str(zip_path)
            logger.info(f"ZIP pack generated: {zip_path} ({len(paths)-1} formats)")
        except Exception as e:
            logger.error(f"ZIP pack failed: {e}")

    # A1: Include report_number in returned dict for persistence
    paths["report_number"] = report_number
    return paths
