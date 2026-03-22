"""
DOCX Generator — python-docx.
Genereaza document Word editabil din report_sections.
"""

from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

DISCLAIMER = (
    "Acest raport a fost generat automat folosind exclusiv date disponibile public "
    "din surse verificabile. Acuratetea datelor depinde de corectitudinea informatiilor "
    "din registrele publice accesate. Roland Intelligence System nu isi asuma "
    "responsabilitatea pentru decizii bazate exclusiv pe acest raport fara verificare "
    "independenta."
)


def _setup_styles(doc: Document):
    """Configureaza stilurile documentului."""
    style = doc.styles["Normal"]
    font = style.font
    font.name = "Calibri"
    font.size = Pt(11)
    font.color.rgb = RGBColor(40, 40, 40)

    for level, size in [(1, 18), (2, 14), (3, 12)]:
        h = doc.styles[f"Heading {level}"]
        h.font.name = "Calibri"
        h.font.size = Pt(size)
        h.font.color.rgb = RGBColor(99, 102, 241)
        h.font.bold = True


def generate_docx(report_sections: dict, meta: dict, output_path: str):
    """Genereaza DOCX din report_sections."""
    doc = Document()
    _setup_styles(doc)

    # Core properties (metadata)
    doc.core_properties.title = meta.get("title", "Raport RIS")
    doc.core_properties.author = "Roland Intelligence System"
    doc.core_properties.keywords = f"RIS, {meta.get('company_name', '')}, business intelligence"
    doc.core_properties.subject = meta.get("analysis_type", "Analiza")

    # Title page
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_para.add_run(meta.get("title", "Raport"))
    title_run.font.size = Pt(26)
    title_run.font.color.rgb = RGBColor(99, 102, 241)
    title_run.bold = True

    company = meta.get("company_name", "")
    if company:
        cp = doc.add_paragraph()
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cr = cp.add_run(company)
        cr.font.size = Pt(16)
        cr.font.color.rgb = RGBColor(80, 80, 80)

    info_para = doc.add_paragraph()
    info_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    info_run = info_para.add_run(
        f"Nivel: {meta.get('report_level', 'N/A')} | "
        f"Generat: {meta.get('generated_at', '')} | "
        f"Surse: {meta.get('sources_count', 0)}"
    )
    info_run.font.size = Pt(10)
    info_run.font.color.rgb = RGBColor(130, 130, 130)

    risk = meta.get("risk_score", "N/A")
    if risk != "N/A":
        risk_para = doc.add_paragraph()
        risk_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        risk_run = risk_para.add_run(f"Scor Risc: {risk}")
        risk_run.font.size = Pt(16)
        risk_run.bold = True
        color_map = {"Verde": RGBColor(34, 197, 94), "Galben": RGBColor(200, 150, 0), "Rosu": RGBColor(220, 50, 50)}
        risk_run.font.color.rgb = color_map.get(risk, RGBColor(100, 100, 100))

    doc.add_page_break()

    # 9D: Table of Contents
    toc_heading = doc.add_heading("Cuprins", level=1)
    # Insert Word TOC field (auto-updates on open in Word)
    toc_para = doc.add_paragraph()
    run = toc_para.add_run()
    fld_char_begin = OxmlElement("w:fldChar")
    fld_char_begin.set(qn("w:fldCharType"), "begin")
    run._r.append(fld_char_begin)
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = ' TOC \\o "1-2" \\h \\z \\u '
    run._r.append(instr_text)
    fld_char_separate = OxmlElement("w:fldChar")
    fld_char_separate.set(qn("w:fldCharType"), "separate")
    run._r.append(fld_char_separate)
    # Placeholder text — Word replaces on update
    placeholder_run = toc_para.add_run("(Apasati Ctrl+A apoi F9 pentru a actualiza cuprinsul)")
    placeholder_run.font.color.rgb = RGBColor(150, 150, 150)
    placeholder_run.font.size = Pt(9)
    placeholder_run.font.italic = True
    fld_char_end_run = toc_para.add_run()
    fld_char_end = OxmlElement("w:fldChar")
    fld_char_end.set(qn("w:fldCharType"), "end")
    fld_char_end_run._r.append(fld_char_end)

    doc.add_page_break()

    # Sections
    for key, section in report_sections.items():
        title = section.get("title", key)
        content = section.get("content", "")

        doc.add_heading(title, level=1)

        for paragraph in content.split("\n"):
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            if paragraph.startswith("**") or paragraph.startswith("##"):
                clean = paragraph.replace("**", "").replace("##", "").strip()
                doc.add_heading(clean, level=2)
            elif paragraph.startswith("- ") or paragraph.startswith("* "):
                doc.add_paragraph(paragraph[2:], style="List Bullet")
            else:
                p = doc.add_paragraph(paragraph)
                # Highlight trust labels
                if "[OFICIAL]" in paragraph:
                    for run in p.runs:
                        if "[OFICIAL]" in run.text:
                            run.font.color.rgb = RGBColor(0, 170, 0)
                elif "[ESTIMAT]" in paragraph:
                    for run in p.runs:
                        if "[ESTIMAT]" in run.text:
                            run.font.color.rgb = RGBColor(255, 136, 0)

        doc.add_paragraph()  # spacer

    # Sources
    sources = meta.get("sources", [])
    if sources:
        doc.add_page_break()
        doc.add_heading("Surse Utilizate", level=1)
        for src in sources:
            level = src.get("level", "?")
            name = src.get("name", "N/A")
            status = src.get("status", "N/A")
            doc.add_paragraph(f"[Nivel {level}] {name} — {status}", style="List Bullet")

    # Disclaimer
    doc.add_page_break()
    doc.add_heading("Disclaimer", level=2)
    disc_para = doc.add_paragraph(DISCLAIMER)
    disc_para.runs[0].font.size = Pt(8)
    disc_para.runs[0].font.italic = True
    disc_para.runs[0].font.color.rgb = RGBColor(150, 150, 150)

    doc.save(output_path)
