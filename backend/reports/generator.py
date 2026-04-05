"""
Report Generator — Orchestrator pentru generarea tuturor formatelor.
Lazy imports: fpdf2/openpyxl/pptx/docx se importeaza DOAR cand genereaza efectiv.
8C: ZIP auto-pack all formats.
"""

import zipfile
from pathlib import Path
from datetime import datetime, date, UTC

from loguru import logger

from backend.config import settings


def _sanitize(text: str) -> str:
    """Lazy-loaded sanitize from pdf_generator."""
    from backend.reports.pdf_generator import _sanitize as _pdf_sanitize
    return _pdf_sanitize(text)


async def generate_all_reports(
    job_id: str,
    report_sections: dict,
    verified_data: dict,
    report_level: int,
    analysis_type: str,
) -> dict:
    """
    Genereaza toate formatele de raport.
    Returneaza dict cu path-urile fisierelor generate.
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
    }

    paths = {}

    def _run_format(name: str, generator_fn, *args, **kwargs) -> str | None:
        """F6.3: DRY helper — run a format generator, log success/failure."""
        try:
            result = generator_fn(*args, **kwargs)
            logger.info(f"[reports] {name} generated OK")
            return result
        except Exception as e:
            logger.error(f"[reports] {name} generation failed: {e}")
            return None

    # PDF (lazy import fpdf2)
    from backend.reports.pdf_generator import generate_pdf, _sanitize as pdf_sanitize_fn
    pdf_path = output_dir / "raport.pdf"

    def _pdf_sanitize(obj):
        if isinstance(obj, str):
            return pdf_sanitize_fn(obj)
        if isinstance(obj, dict):
            return {_pdf_sanitize(k): _pdf_sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_pdf_sanitize(i) for i in obj]
        return obj

    r = _run_format("PDF", generate_pdf, _pdf_sanitize(report_sections), _pdf_sanitize(meta), str(pdf_path), verified_data=verified_data)
    if r is not False:
        if pdf_path.exists():
            paths["pdf"] = str(pdf_path)

    # DOCX (lazy import python-docx)
    from backend.reports.docx_generator import generate_docx
    docx_path = output_dir / "raport.docx"
    r = _run_format("DOCX", generate_docx, report_sections, meta, str(docx_path), verified_data=verified_data)
    if docx_path.exists():
        paths["docx"] = str(docx_path)

    # HTML (lightweight, no heavy deps)
    from backend.reports.html_generator import generate_html
    html_path = output_dir / "raport.html"
    r = _run_format("HTML", generate_html, report_sections, meta, verified_data, str(html_path))
    if html_path.exists():
        paths["html"] = str(html_path)

    # Excel (lazy import openpyxl)
    from backend.reports.excel_generator import generate_excel
    excel_path = output_dir / "raport.xlsx"
    r = _run_format("Excel", generate_excel, report_sections, meta, verified_data, str(excel_path))
    if excel_path.exists():
        paths["excel"] = str(excel_path)

    # PPTX (lazy import python-pptx)
    from backend.reports.pptx_generator import generate_pptx
    pptx_path = output_dir / "raport.pptx"
    r = _run_format("PPTX", generate_pptx, report_sections, meta, verified_data, str(pptx_path))
    if pptx_path.exists():
        paths["pptx"] = str(pptx_path)

    # 1-Pager Executiv (DF3 — lazy import fpdf2)
    from backend.reports.one_pager_generator import generate_one_pager
    one_pager_path = output_dir / "raport_executiv.pdf"
    r = _run_format("1-Pager", generate_one_pager, verified_data, meta, str(one_pager_path))
    if one_pager_path.exists():
        paths["one_pager"] = str(one_pager_path)

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

    return paths
