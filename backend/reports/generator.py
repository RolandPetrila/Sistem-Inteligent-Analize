"""
Report Generator — Orchestrator pentru generarea tuturor formatelor.
Lazy imports: fpdf2/openpyxl/pptx/docx se importeaza DOAR cand genereaza efectiv.
8C: ZIP auto-pack all formats.
"""

import zipfile
from pathlib import Path
from datetime import datetime

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
        "generated_at": datetime.utcnow().strftime("%d.%m.%Y %H:%M"),
        "risk_score": risk_score.get("score", "N/A"),
        "numeric_score": risk_score.get("numeric_score"),
        "risk_recommendation": risk_score.get("recommendation", ""),
        "sources_count": len(sources_used),
        "sources": sources_used,
    }

    paths = {}

    # PDF (lazy import fpdf2)
    try:
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

        pdf_meta = _pdf_sanitize(meta)
        pdf_sections = _pdf_sanitize(report_sections)
        generate_pdf(pdf_sections, pdf_meta, str(pdf_path))
        paths["pdf"] = str(pdf_path)
        logger.info(f"PDF generated: {pdf_path}")
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")

    # DOCX (lazy import python-docx)
    try:
        from backend.reports.docx_generator import generate_docx
        docx_path = output_dir / "raport.docx"
        generate_docx(report_sections, meta, str(docx_path))
        paths["docx"] = str(docx_path)
        logger.info(f"DOCX generated: {docx_path}")
    except Exception as e:
        logger.error(f"DOCX generation failed: {e}")

    # HTML (lightweight, no heavy deps)
    try:
        from backend.reports.html_generator import generate_html
        html_path = output_dir / "raport.html"
        generate_html(report_sections, meta, verified_data, str(html_path))
        paths["html"] = str(html_path)
        logger.info(f"HTML generated: {html_path}")
    except Exception as e:
        logger.error(f"HTML generation failed: {e}")

    # Excel (lazy import openpyxl)
    try:
        from backend.reports.excel_generator import generate_excel
        excel_path = output_dir / "raport.xlsx"
        generate_excel(report_sections, meta, verified_data, str(excel_path))
        paths["excel"] = str(excel_path)
        logger.info(f"Excel generated: {excel_path}")
    except Exception as e:
        logger.error(f"Excel generation failed: {e}")

    # PPTX (lazy import python-pptx)
    try:
        from backend.reports.pptx_generator import generate_pptx
        pptx_path = output_dir / "raport.pptx"
        generate_pptx(report_sections, meta, verified_data, str(pptx_path))
        paths["pptx"] = str(pptx_path)
        logger.info(f"PPTX generated: {pptx_path}")
    except Exception as e:
        logger.error(f"PPTX generation failed: {e}")

    # 1-Pager Executiv (DF3 — lazy import fpdf2)
    try:
        from backend.reports.one_pager_generator import generate_one_pager
        one_pager_path = output_dir / "raport_executiv.pdf"
        generate_one_pager(verified_data, meta, str(one_pager_path))
        paths["one_pager"] = str(one_pager_path)
        logger.info(f"1-Pager generated: {one_pager_path}")
    except Exception as e:
        logger.error(f"1-Pager generation failed: {e}")

    # 8C: ZIP auto-pack all formats
    if len(paths) >= 2:
        try:
            cui_part = ""
            cui_field = company.get("cui", {})
            if isinstance(cui_field, dict):
                cui_part = cui_field.get("value", "")
            elif isinstance(cui_field, str):
                cui_part = cui_field
            date_part = datetime.utcnow().strftime("%Y-%m-%d")
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
