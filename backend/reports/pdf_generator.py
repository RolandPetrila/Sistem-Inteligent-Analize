"""
PDF Generator -fpdf2 (zero dependinte native Windows).
Genereaza PDF profesional din report_sections.
F21: Markdown table rendering via fpdf2 native cells.
"""

import re
import unicodedata

from fpdf import FPDF
from loguru import logger

from backend.config import settings

DISCLAIMER = (
    "Acest raport a fost generat automat folosind exclusiv date disponibile public "
    "din surse verificabile. Acuratetea datelor depinde de corectitudinea informatiilor "
    "din registrele publice accesate. Roland Intelligence System nu isi asuma "
    "responsabilitatea pentru decizii bazate exclusiv pe acest raport fara verificare "
    "independenta."
)


CHAR_FALLBACK = {
    "\u0218": "S", "\u0219": "s",  # Ș, ș (Romanian)
    "\u021a": "T", "\u021b": "t",  # Ț, ț (Romanian)
    "\u2014": "-",                  # em dash
    "\u2013": "-",                  # en dash
    "\u2018": "'", "\u2019": "'",  # left/right single smart quotes
    "\u201c": '"', "\u201d": '"',  # left/right double smart quotes
    "\u201e": '"', "\u201f": '"',  # low-9 double quote (Romanian „)
    "\u2026": "...",               # ellipsis
    "\u20ac": "EUR",               # euro sign
    "\u2022": "*",                 # bullet
    "\u00b0": "deg",               # degree sign
    "\u2103": "C",                 # degree Celsius
    "\u2109": "F",                 # degree Fahrenheit
    "\u2122": "(TM)",              # trademark
    "\u00a9": "(C)",               # copyright
    "\u00ae": "(R)",               # registered
    "\u00ab": "<<", "\u00bb": ">>",  # guillemets
    "\u2039": "<", "\u203a": ">",    # single guillemets
    "\u2010": "-", "\u2011": "-",    # hyphen, non-breaking hyphen
    "\u2012": "-",                   # figure dash
    "\u2015": "--",                  # horizontal bar
    "\u00a0": " ",                   # non-breaking space
    "\u2002": " ", "\u2003": " ",    # en space, em space
    "\u200b": "",                    # zero-width space
    "\u00d7": "x",                   # multiplication sign
    "\u00f7": "/",                   # division sign
    "\u2264": "<=", "\u2265": ">=",  # less/greater than or equal
    "\u2260": "!=",                  # not equal
    "\u221e": "INF",                 # infinity
    "\u2030": "o/oo",               # per mille
    "\u00bc": "1/4", "\u00bd": "1/2", "\u00be": "3/4",  # fractions
    "\u0102": "A", "\u0103": "a",  # A/a with breve (Romanian)
    "\u00c2": "A", "\u00e2": "a",  # A/a with circumflex (latin-1 has these but just in case)
    "\u00ce": "I", "\u00ee": "i",  # I/i with circumflex
}


def _sanitize(text: str) -> str:
    """Encode text to latin-1 safe characters for Helvetica font.
    Uses NFKD normalization for proper diacritics decomposition, then explicit
    fallback map for special characters that NFKD cannot handle."""
    # Step 1: Explicit replacements for known special chars
    for orig, repl in CHAR_FALLBACK.items():
        text = text.replace(orig, repl)
    # Step 2: NFKD normalization — decomposes accented chars (e.g. e + combining accent)
    # then strip combining marks (category M) to get ASCII base letter
    normalized = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    # Step 3: Final encode to latin-1, replacing any remaining unsupported chars
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _render_pdf_table(pdf, rows: list[list[str]], has_header: bool):
    """F21: Render a markdown table as fpdf2 cells.
    PDF-01/PDF-02: Use multi_cell for long text, warn on truncation."""
    from loguru import logger

    if not rows:
        return
    num_cols = max(len(r) for r in rows)
    if num_cols == 0:
        return
    # Calculate column widths proportionally (total usable width ~190mm)
    col_width = 190 / num_cols
    # PDF-01: Max chars per cell based on column width (approx 2.5 chars per mm)
    max_chars = max(int(col_width * 2.5), 20)

    start = 0
    if has_header and len(rows) >= 1:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(99, 102, 241)
        pdf.set_text_color(255, 255, 255)
        for j, cell in enumerate(rows[0]):
            sanitized = _sanitize(cell)
            if len(sanitized) > max_chars:
                logger.debug(f"PDF table header cell truncated: '{sanitized[:30]}...' ({len(sanitized)} > {max_chars})")
                sanitized = sanitized[:max_chars - 1] + "\u2026"
            pdf.cell(col_width, 7, sanitized, border=1, fill=True,
                     align="C" if j > 0 else "L")
        pdf.ln()
        start = 1

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(40, 40, 40)
    for row in rows[start:]:
        for j, cell in enumerate(row):
            sanitized = _sanitize(cell)
            if len(sanitized) > max_chars:
                logger.debug(f"PDF table cell truncated: '{sanitized[:30]}...' ({len(sanitized)} > {max_chars})")
                sanitized = sanitized[:max_chars - 1] + "\u2026"
            pdf.cell(col_width, 6, sanitized, border=1,
                     align="C" if j > 0 else "L")
        pdf.ln()
    pdf.ln(4)  # PDF-04: Increased spacing after table
    pdf.set_font("Helvetica", "", 10)


def _add_section_header(pdf, title: str):
    """Render a section header: bold, accent color, underline."""
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(99, 102, 241)
    pdf.multi_cell(0, 7, _sanitize(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 40, 40)


def _render_markdown_text(pdf, text: str, line_height: float = 6.0):
    """Render text with basic markdown: **bold**, # headings, - bullets.
    FIX #18: Helper suplimentar — nu inlocuieste procesarea existenta."""
    lines = text.split("\n") if text else []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            pdf.ln(3)
            continue

        # H1/H2 headings
        if stripped.startswith("## "):
            _add_section_header(pdf, stripped[3:])
            continue
        elif stripped.startswith("# "):
            _add_section_header(pdf, stripped[2:])
            continue

        # Bullet points
        if stripped.startswith(("- ", "* ", "• ")):
            content = stripped[2:]
            # Strip **bold** markers (fpdf2 nu suporta inline bold)
            content = re.sub(r'\*\*(.+?)\*\*', r'\1', content)
            pdf.set_x(pdf.get_x() + 5)
            try:
                pdf.multi_cell(0, line_height, _sanitize(f"* {content}"), new_x="LMARGIN", new_y="NEXT")
            except Exception as e:
                logger.debug(f"[pdf] bullet render failed: {e}")
            continue

        # Normal paragraph — strip **bold** si *italic* markers
        clean_line = re.sub(r'\*\*(.+?)\*\*', r'\1', stripped)
        clean_line = re.sub(r'\*(.+?)\*', r'\1', clean_line)
        try:
            pdf.multi_cell(0, line_height, _sanitize(clean_line), new_x="LMARGIN", new_y="NEXT")
        except Exception as e:
            logger.debug(f"[pdf] markdown line render failed: {e}")


class RISPdf(FPDF):
    def __init__(self, meta: dict, watermark: str = "CONFIDENTIAL", lang: str = "ro"):
        super().__init__()
        self.meta = meta
        self.watermark = watermark
        self.lang = lang
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
        from backend.reports.i18n import t as _t
        self.set_y(-20)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(150, 150, 150)
        watermark_label = self.watermark if self.watermark else _t("confidential", self.lang)
        page_label = _t("page", self.lang)
        self.cell(0, 5, f"{watermark_label} | {page_label} {self.page_no()}/{{nb}}", align="C")


def _fmt_pdf_num(v) -> str:
    if isinstance(v, int | float):
        return f"{v:,.0f}"
    return str(v) if v is not None else "-"


def _pdf_names(items) -> list[str]:
    res = []
    for it in items or []:
        if isinstance(it, dict):
            res.append(str(it.get("nume") or it.get("name") or it.get("denumire") or it))
        else:
            res.append(str(it))
    return res


def _add_rich_fields_pdf(pdf, verified_data: dict):
    """Render previously-dropped rich fields into the PDF: predictive scores,
    benchmark, actionariat/relations, AEGRM guarantees, historical OSINT, funding."""
    pred = verified_data.get("predictive_scores", {})
    bench = verified_data.get("benchmark", {})
    has_pred = isinstance(pred, dict) and pred.get("summary")
    has_bench = isinstance(bench, dict) and bench.get("available") and bench.get("comparisons")

    # ---- Page 1: Predictive + Benchmark ----
    if has_pred or has_bench:
        pdf.add_page()
        pdf.start_section("Analiza Predictiva si Benchmark", level=0)
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(99, 102, 241)
        pdf.cell(0, 12, _sanitize("Analiza Predictiva si Benchmark"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(99, 102, 241)
        pdf.line(10, pdf.get_y(), 80, pdf.get_y())
        pdf.ln(6)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)

        if has_pred:
            _add_section_header(pdf, "Scoruri Predictive Faliment")
            altman = pred.get("altman_z", {}) or {}
            piotroski = pred.get("piotroski_f", {}) or {}
            beneish = pred.get("beneish_m", {}) or {}
            zmijewski = pred.get("zmijewski_x", {}) or {}
            zmi_state = "Distres" if zmijewski.get("distress") else ("OK" if zmijewski.get("available") else "Indisponibil")
            for ln_ in [
                f"Altman Z'': {altman.get('z_score', 'N/A')} ({altman.get('zone', 'INDISPONIBIL')})",
                f"Piotroski F: {piotroski.get('f_score', 'N/A')}/{piotroski.get('max_possible', 9)} ({piotroski.get('grade', 'N/A')})",
                f"Beneish M: {beneish.get('m_score', 'N/A')} ({beneish.get('risk', 'INDISPONIBIL')})",
                f"Zmijewski X: {zmijewski.get('x_score', 'N/A')} ({zmi_state})",
            ]:
                pdf.multi_cell(0, 6, _sanitize(ln_), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 10)
            pdf.multi_cell(0, 6, _sanitize(f"Concluzie: {pred.get('summary', '')} ({pred.get('distress_signals', 0)} semnale)"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            pdf.ln(4)

        if has_bench:
            _add_section_header(pdf, f"Benchmark Sector CAEN {bench.get('caen_code', '')}")
            rows = [["Indicator", "Firma", "Media sector", "Pozitie"]]
            for c in bench["comparisons"]:
                rows.append([
                    str(c.get("metric", "")),
                    _fmt_pdf_num(c.get("firma")),
                    _fmt_pdf_num(c.get("media_sector")),
                    str(c.get("pozitie", "")),
                ])
            _render_pdf_table(pdf, rows, has_header=True)

    # ---- Page 2: Actionariat + Garantii/Istoric + Finantare ----
    act = verified_data.get("actionariat", {})
    rel = verified_data.get("relations", {})
    risk = verified_data.get("risk", {})
    aegrm_field = risk.get("aegrm_guarantees", {}) if isinstance(risk, dict) else {}
    aegrm = aegrm_field.get("value") if isinstance(aegrm_field, dict) else None
    hist = verified_data.get("historical_flags", [])
    funding = verified_data.get("funding_programs", {})

    act_ok = isinstance(act, dict) and act.get("available")
    rel_flags = rel.get("flags", []) if isinstance(rel, dict) else []
    aegrm_ok = isinstance(aegrm, dict) and aegrm.get("has_data")
    hist_ok = isinstance(hist, list) and bool(hist)
    fund_ok = isinstance(funding, dict) and funding.get("eligible")

    if act_ok or rel_flags or aegrm_ok or hist_ok or fund_ok:
        pdf.add_page()
        pdf.start_section("Actionariat, Garantii si Finantare", level=0)
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(99, 102, 241)
        pdf.cell(0, 12, _sanitize("Actionariat, Garantii si Finantare"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(99, 102, 241)
        pdf.line(10, pdf.get_y(), 80, pdf.get_y())
        pdf.ln(6)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)

        if act_ok or rel_flags:
            _add_section_header(pdf, "Actionariat si Relatii")
            if act_ok:
                cap = act.get("capital_social")
                stare = act.get("stare", "")
                if cap or stare:
                    extra = f" | Stare: {stare}" if stare else ""
                    pdf.multi_cell(0, 6, _sanitize(f"Capital social: {_fmt_pdf_num(cap)}{extra}"), new_x="LMARGIN", new_y="NEXT")
                for label, items in (("Asociati", act.get("asociati")), ("Administratori", act.get("administratori"))):
                    names = _pdf_names(items)
                    if names:
                        pdf.set_font("Helvetica", "B", 10)
                        pdf.multi_cell(0, 6, _sanitize(f"{label}:"), new_x="LMARGIN", new_y="NEXT")
                        pdf.set_font("Helvetica", "", 10)
                        for n in names:
                            pdf.multi_cell(0, 5.5, _sanitize(f"  * {n}"), new_x="LMARGIN", new_y="NEXT")
            for fl in rel_flags:
                pdf.multi_cell(0, 5.5, _sanitize(f"[{fl.get('severity', 'INFO')}] {fl.get('type', '')}: {fl.get('detail', '')}"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

        if aegrm_ok or hist_ok:
            _add_section_header(pdf, "Garantii si Istoric (OSINT)")
            if aegrm_ok:
                pdf.multi_cell(0, 6, _sanitize(f"Garantii reale mobiliare (AEGRM): {aegrm.get('count', 0)}"), new_x="LMARGIN", new_y="NEXT")
                guarantees = aegrm.get("guarantees") or aegrm.get("results") or []
                if isinstance(guarantees, list):
                    for g in guarantees[:8]:
                        txt = (g.get("descriere") or g.get("creditor") or g.get("title") or str(g)) if isinstance(g, dict) else str(g)
                        pdf.multi_cell(0, 5.5, _sanitize(f"  * {str(txt)[:200]}"), new_x="LMARGIN", new_y="NEXT")
            if hist_ok:
                for fl in hist:
                    if isinstance(fl, dict):
                        # osint_client emits {type(slug), label(human), severity, snippet};
                        # prefer the human label + snippet, fall back to other shapes.
                        label = fl.get("label") or fl.get("type") or fl.get("title") or "Semnal"
                        detail = fl.get("snippet") or fl.get("detail") or fl.get("description") or ""
                        date_raw = fl.get("date") or fl.get("data") or ""
                        pdf.multi_cell(0, 5.5, _sanitize(f"- {label} {date_raw}: {detail}"[:200]), new_x="LMARGIN", new_y="NEXT")
                    else:
                        pdf.multi_cell(0, 5.5, _sanitize(f"- {fl}"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

        if fund_ok:
            _add_section_header(pdf, "Programe de Finantare Eligibile")
            if funding.get("summary"):
                pdf.multi_cell(0, 6, _sanitize(str(funding["summary"])), new_x="LMARGIN", new_y="NEXT")
                pdf.ln(1)
            rows = [["Program", "Suma max (EUR)", "Termen"]]
            for p in funding["eligible"]:
                suma = p.get("suma_max_eur", 0)
                suma_str = f"{suma:,.0f}" if isinstance(suma, int | float) and suma else "-"
                rows.append([str(p.get("nume", "")), suma_str, str(p.get("termen", "") or "-")])
            _render_pdf_table(pdf, rows, has_header=True)


def generate_pdf(report_sections: dict, meta: dict, output_path: str, verified_data: dict = None, lang: str = "ro"):
    """Genereaza PDF din report_sections. 9D: watermark + TOC. B15: due_diligence + early_warnings. G5: i18n lang."""
    verified_data = verified_data or {}
    # F3-12: Watermark personalizabil din settings (.env PDF_WATERMARK / PDF_WATERMARK_ENABLED)
    watermark_text = settings.pdf_watermark if settings.pdf_watermark_enabled else ""
    pdf = RISPdf(meta, watermark=watermark_text, lang=lang)
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
    from backend.reports.i18n import t as _t
    pdf.cell(0, 8, f"{_t('report_level', lang)}: {meta.get('report_level', 'N/A')}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"{_t('generated_at', lang)}: {meta.get('generated_at', '')}", align="C", new_x="LMARGIN", new_y="NEXT")
    if meta.get("report_number"):
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(160, 160, 160)
        pdf.cell(0, 7, f"{_t('report_number', lang)}: {meta['report_number']}", align="C", new_x="LMARGIN", new_y="NEXT")

    risk = meta.get("risk_score", "N/A")
    numeric = meta.get("numeric_score")
    if risk != "N/A":
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 14)
        color_map = {"Verde": (34, 197, 94), "Galben": (234, 179, 8), "Rosu": (239, 68, 68)}
        r, g, b = color_map.get(risk, (150, 150, 150))
        pdf.set_text_color(r, g, b)
        score_text = f"{_t('risk_score', lang)}: {risk}"
        if numeric is not None:
            score_text += f" ({numeric}/100)"
        pdf.cell(0, 10, score_text, align="C", new_x="LMARGIN", new_y="NEXT")

    # C6 fix: Use fpdf2 built-in TOC with correct page numbers (auto-tracked via start_section)
    def _render_toc(pdf_obj, outline):
        pdf_obj.set_font("Helvetica", "B", 16)
        pdf_obj.set_text_color(99, 102, 241)
        pdf_obj.cell(0, 12, "Cuprins", new_x="LMARGIN", new_y="NEXT")
        pdf_obj.set_draw_color(99, 102, 241)
        pdf_obj.line(10, pdf_obj.get_y(), 80, pdf_obj.get_y())
        pdf_obj.ln(8)
        pdf_obj.set_font("Helvetica", "", 11)
        pdf_obj.set_text_color(60, 60, 60)
        for entry in outline:
            title = entry.name[:55]
            page_num = entry.page_number
            dots = "." * max(2, 58 - len(title))
            pdf_obj.cell(0, 8, f"  {title} {dots} {page_num}", new_x="LMARGIN", new_y="NEXT")

    pdf.insert_toc_placeholder(_render_toc, pages=1)

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

        # F21: Pre-parse content to detect markdown tables
        lines = content.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # F21: Detect markdown table block
            if line.startswith("|") and line.endswith("|") and line.count("|") >= 3:
                table_rows = []
                has_header = False
                while i < len(lines):
                    tl = lines[i].strip()
                    if not (tl.startswith("|") and tl.endswith("|")):
                        break
                    if re.match(r'^\|[\s\-:|]+\|$', tl):
                        has_header = True
                        i += 1
                        continue
                    cells = [c.strip() for c in tl.strip("|").split("|")]
                    table_rows.append(cells)
                    i += 1
                _render_pdf_table(pdf, table_rows, has_header)
                continue

            i += 1

            if not line:
                pdf.ln(3)
                continue
            # C9 fix: Break very long words with hyphens instead of truncating
            words = line.split()
            line = " ".join(w[:55] + "-" + w[55:110] if len(w) > 60 else w for w in words)
            # Skip raw JSON
            if line.startswith("{") or line.startswith("["):
                continue

            try:
                if line.startswith("**") or line.startswith("##"):
                    clean = line.replace("**", "").replace("##", "").strip()
                    pdf.set_font("Helvetica", "B", 11)
                    pdf.set_text_color(60, 60, 60)
                    pdf.multi_cell(0, 6, _sanitize(clean))
                    pdf.set_font("Helvetica", "", 10)
                    pdf.set_text_color(40, 40, 40)
                else:
                    pdf.multi_cell(0, 5.5, _sanitize(line))
            except Exception as e:
                logger.debug(f"[pdf] font fallback: {e}")
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(180, 180, 180)
                pdf.cell(0, 4, "[paragraf nerandat]", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(40, 40, 40)

    # E6: Financial Ratios Table
    ratios = verified_data.get("risk_score", {}).get("financial_ratios", [])
    if ratios:
        pdf.add_page()
        pdf.start_section("Ratii Financiare", level=0)
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(99, 102, 241)
        pdf.cell(0, 12, "Ratii Financiare", new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(99, 102, 241)
        pdf.line(10, pdf.get_y(), 80, pdf.get_y())
        pdf.ln(6)

        # Table header
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(99, 102, 241)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(55, 7, "Indicator", border=1, fill=True)
        pdf.cell(30, 7, "Valoare", border=1, align="C", fill=True)
        pdf.cell(20, 7, "Unitate", border=1, align="C", fill=True)
        pdf.cell(75, 7, "Interpretare", border=1, align="C", fill=True, new_x="LMARGIN", new_y="NEXT")

        # Rows
        pdf.set_font("Helvetica", "", 9)
        for ratio in ratios:
            name = _sanitize(str(ratio.get("name", "")))
            val = ratio.get("value", 0)
            unit = ratio.get("unit", "")
            interp = _sanitize(str(ratio.get("interpretation", "")))

            # Value formatting
            if unit == "RON":
                val_str = f"{val:,.0f}"
            else:
                val_str = f"{val}"

            # Color-code interpretation
            if interp in ("Excelent", "Bun", "Solid", "Conservator"):
                pdf.set_text_color(34, 197, 94)
            elif interp in ("Moderat", "Fragil"):
                pdf.set_text_color(234, 179, 8)
            elif interp in ("Slab", "Negativ", "Ridicat", "Periculos", "Subcapitalizat", "Pierdere"):
                pdf.set_text_color(239, 68, 68)
            else:
                pdf.set_text_color(40, 40, 40)

            pdf.cell(55, 6, name, border=1)
            pdf.cell(30, 6, val_str, border=1, align="R")
            pdf.cell(20, 6, unit, border=1, align="C")
            pdf.cell(75, 6, interp, border=1, align="C", new_x="LMARGIN", new_y="NEXT")

        pdf.set_text_color(40, 40, 40)

    # B15: Due Diligence Checklist from verified_data
    due_diligence = verified_data.get("due_diligence", {})
    dd_checklist = []
    if isinstance(due_diligence, dict):
        dd_checklist = due_diligence.get("checklist", [])
    elif isinstance(due_diligence, list):
        dd_checklist = due_diligence
    if dd_checklist:
        pdf.add_page()
        pdf.start_section("Due Diligence Checklist", level=0)
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(99, 102, 241)
        pdf.cell(0, 12, "Due Diligence Checklist", new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(99, 102, 241)
        pdf.line(10, pdf.get_y(), 80, pdf.get_y())
        pdf.ln(6)
        pdf.set_font("Helvetica", "", 10)
        for item in dd_checklist[:15]:
            if isinstance(item, dict):
                name = _sanitize(str(item.get("name", "N/A")))
                status = item.get("status", "N/A")
                icon = "DA" if status in ("DA", True) else "NU" if status in ("NU", False) else "N/A"
                color = (34, 197, 94) if icon == "DA" else (239, 68, 68) if icon == "NU" else (150, 150, 150)
                pdf.set_text_color(*color)
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(15, 6, f"[{icon}]")
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(40, 40, 40)
                pdf.cell(0, 6, name, new_x="LMARGIN", new_y="NEXT")

    # B15: Early Warning Signals from verified_data
    early_warnings = verified_data.get("early_warnings", [])
    if isinstance(early_warnings, list) and early_warnings:
        pdf.add_page()
        pdf.start_section("Semnale de Alarma", level=0)
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(99, 102, 241)
        pdf.cell(0, 12, "Semnale de Alarma (Early Warnings)", new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(99, 102, 241)
        pdf.line(10, pdf.get_y(), 80, pdf.get_y())
        pdf.ln(6)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        for ew in early_warnings[:10]:
            if isinstance(ew, dict):
                signal = _sanitize(str(ew.get("signal", ew.get("message", "N/A"))))
                severity = ew.get("severity", "MEDIUM")
                color = (239, 68, 68) if severity == "HIGH" else (234, 179, 8) if severity == "MEDIUM" else (150, 150, 150)
                pdf.set_text_color(*color)
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(0, 6, f"[{severity}] {signal}", new_x="LMARGIN", new_y="NEXT")
                detail = ew.get("detail", "")
                if detail:
                    pdf.set_font("Helvetica", "", 9)
                    pdf.set_text_color(80, 80, 80)
                    pdf.multi_cell(0, 5, _sanitize(str(detail)))
                    pdf.ln(2)
            elif isinstance(ew, str):
                pdf.set_text_color(234, 179, 8)
                pdf.cell(0, 6, _sanitize(f"- {ew}"), new_x="LMARGIN", new_y="NEXT")

    # Rich fields previously dropped: predictive, benchmark, actionariat, AEGRM, historical, funding
    _add_rich_fields_pdf(pdf, verified_data)

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
