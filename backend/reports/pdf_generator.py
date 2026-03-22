"""
PDF Generator -fpdf2 (zero dependinte native Windows).
Genereaza PDF profesional din report_sections.
"""

from fpdf import FPDF

DISCLAIMER = (
    "Acest raport a fost generat automat folosind exclusiv date disponibile public "
    "din surse verificabile. Acuratetea datelor depinde de corectitudinea informatiilor "
    "din registrele publice accesate. Roland Intelligence System nu isi asuma "
    "responsabilitatea pentru decizii bazate exclusiv pe acest raport fara verificare "
    "independenta."
)


def _sanitize(text: str) -> str:
    """Encode text to latin-1 safe characters for Helvetica font."""
    # Replacements for common chars outside latin-1
    replacements = {
        "\u0218": "S", "\u0219": "s",  # Ș, ș
        "\u021a": "T", "\u021b": "t",  # Ț, ț
        "\u2014": "-", "\u2013": "-",  # em dash, en dash
        "\u2018": "'", "\u2019": "'",  # smart quotes
        "\u201c": '"', "\u201d": '"',
        "\u2026": "...",               # ellipsis
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    # Encode to latin-1, replacing any remaining unsupported chars
    return text.encode("latin-1", errors="replace").decode("latin-1")


class RISPdf(FPDF):
    def __init__(self, meta: dict, watermark: str = "CONFIDENTIAL"):
        super().__init__()
        self.meta = meta
        self.watermark = watermark
        self.section_pages: list[tuple[str, int]] = []  # (title, page_no) for TOC
        self.set_auto_page_break(auto=True, margin=25)

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, "Roland Intelligence System", align="L")
        self.cell(0, 6, self.meta.get("generated_at", ""), align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(99, 102, 241)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)
        # 9D: Diagonal watermark — very light gray so content remains readable
        if self.watermark:
            prev_font = (self.font_family, self.font_style, self.font_size_pt)
            self.set_font("Helvetica", "B", 48)
            self.set_text_color(230, 230, 230)
            with self.rotation(45, self.w / 2, self.h / 2):
                self.text(25, self.h / 2 + 10, self.watermark)
            self.set_font(*prev_font)

    def footer(self):
        self.set_y(-20)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 5, f"CONFIDENTIAL | Pagina {self.page_no()}/{{nb}}", align="C")


def generate_pdf(report_sections: dict, meta: dict, output_path: str):
    """Genereaza PDF din report_sections. 9D: watermark + TOC."""
    # meta and report_sections should already be sanitized by caller
    pdf = RISPdf(meta)
    pdf.alias_nb_pages()
    pdf.add_page()

    # Title page
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(99, 102, 241)
    pdf.ln(30)
    pdf.cell(0, 15, meta.get("title", "Raport"), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 16)
    pdf.set_text_color(60, 60, 60)
    company = meta.get("company_name", "")
    if company:
        pdf.cell(0, 10, company, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(10)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 8, f"Nivel raport: {meta.get('report_level', 'N/A')}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Generat: {meta.get('generated_at', '')}", align="C", new_x="LMARGIN", new_y="NEXT")

    risk = meta.get("risk_score", "N/A")
    numeric = meta.get("numeric_score")
    if risk != "N/A":
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 14)
        color_map = {"Verde": (34, 197, 94), "Galben": (234, 179, 8), "Rosu": (239, 68, 68)}
        r, g, b = color_map.get(risk, (150, 150, 150))
        pdf.set_text_color(r, g, b)
        score_text = f"Scor Risc: {risk}"
        if numeric is not None:
            score_text += f" ({numeric}/100)"
        pdf.cell(0, 10, score_text, align="C", new_x="LMARGIN", new_y="NEXT")

    # 9D: Table of Contents page
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(99, 102, 241)
    pdf.cell(0, 12, "Cuprins", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(99, 102, 241)
    pdf.line(10, pdf.get_y(), 80, pdf.get_y())
    pdf.ln(8)

    toc_start_page = pdf.page_no() + 1  # next page after TOC
    section_titles = []
    for key, section in report_sections.items():
        section_titles.append(section.get("title", key))

    # Pre-calculate: each section starts on a new page, so page = toc_start_page + index
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(60, 60, 60)
    for idx, title in enumerate(section_titles):
        page_num = toc_start_page + idx
        # TOC entry: title ........... page
        dots = "." * max(2, 60 - len(title))
        pdf.cell(0, 8, f"  {title} {dots} {page_num}", new_x="LMARGIN", new_y="NEXT")

    # Sources + Disclaimer entries
    extra_pages = toc_start_page + len(section_titles)
    sources = meta.get("sources", [])
    if sources:
        pdf.cell(0, 8, f"  Surse Utilizate {'.' * 40} {extra_pages}", new_x="LMARGIN", new_y="NEXT")
        extra_pages += 1
    pdf.cell(0, 8, f"  Disclaimer {'.' * 45} {extra_pages}", new_x="LMARGIN", new_y="NEXT")

    # Sections
    for key, section in report_sections.items():
        pdf.add_page()
        title = section.get("title", key)
        content = section.get("content", "")

        # PDF bookmark for this section (clickable outline entry)
        pdf.start_section(title, level=0)

        # Section title
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(99, 102, 241)
        pdf.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(99, 102, 241)
        pdf.line(10, pdf.get_y(), 80, pdf.get_y())
        pdf.ln(6)

        # Section content
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)

        for paragraph in content.split("\n"):
            paragraph = paragraph.strip()
            if not paragraph:
                pdf.ln(3)
                continue
            # Truncate very long words to prevent overflow
            words = paragraph.split()
            paragraph = " ".join(w[:60] for w in words)
            # Skip lines that are too short to render or are raw JSON
            if paragraph.startswith("{") or paragraph.startswith("["):
                continue

            try:
                # Bold headers (lines starting with ** or ##)
                if paragraph.startswith("**") or paragraph.startswith("##"):
                    clean = paragraph.replace("**", "").replace("##", "").strip()
                    pdf.set_font("Helvetica", "B", 11)
                    pdf.set_text_color(60, 60, 60)
                    pdf.multi_cell(0, 6, clean)
                    pdf.set_font("Helvetica", "", 10)
                    pdf.set_text_color(40, 40, 40)
                else:
                    pdf.multi_cell(0, 5.5, paragraph)
            except Exception:
                # Skip paragraphs that cause rendering errors
                pass

    # Sources page
    sources = meta.get("sources", [])
    if sources:
        pdf.add_page()
        pdf.start_section("Surse Utilizate", level=0)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(99, 102, 241)
        pdf.cell(0, 10, "Surse Utilizate", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(60, 60, 60)
        for src in sources:
            level = src.get("level", "?")
            name = src.get("name", "N/A")
            status = src.get("status", "N/A")
            pdf.cell(0, 5.5, f"[Nivel {level}] {name} -{status}", new_x="LMARGIN", new_y="NEXT")

    # Disclaimer
    pdf.add_page()
    pdf.start_section("Disclaimer", level=0)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, "Disclaimer", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(130, 130, 130)
    pdf.multi_cell(0, 4.5, DISCLAIMER)

    pdf.output(output_path)
