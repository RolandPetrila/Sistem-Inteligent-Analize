"""
Timeline Generator — Raport Evolutie Multi-An pentru aceeasi firma.
Genereaza un PDF simplu cu tabel cronologic: CA, Profit, Angajati, Scor Risc.
Foloseste fpdf2 (acelasi pattern ca pdf_generator.py, zero dependinte native Windows).
"""

import unicodedata
from datetime import UTC, datetime

from fpdf import FPDF
from loguru import logger

from backend.config import settings

# Reuse char fallback map din pdf_generator pentru compatibilitate latin-1
CHAR_FALLBACK = {
    "\u0218": "S", "\u0219": "s",
    "\u021a": "T", "\u021b": "t",
    "\u2014": "-", "\u2013": "-",
    "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"',
    "\u201e": '"', "\u201f": '"',
    "\u2026": "...",
    "\u20ac": "EUR",
    "\u2022": "*",
    "\u00b0": "deg",
    "\u00a0": " ",
    "\u200b": "",
    "\u0102": "A", "\u0103": "a",
    "\u00c2": "A", "\u00e2": "a",
    "\u00ce": "I", "\u00ee": "i",
}


def _sanitize(text: str) -> str:
    """Encode text to latin-1 safe characters for Helvetica font."""
    for orig, repl in CHAR_FALLBACK.items():
        text = text.replace(orig, repl)
    normalized = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _fmt_ron(value) -> str:
    """Formateaza valoare numerica in RON cu separatori de mii."""
    if value is None:
        return "N/A"
    try:
        num = float(value)
        if abs(num) >= 1_000_000:
            return f"{num / 1_000_000:.2f}M"
        elif abs(num) >= 1_000:
            return f"{num:,.0f}"
        else:
            return f"{num:.0f}"
    except (TypeError, ValueError):
        return "N/A"


def _trend_label(values: list) -> str:
    """Calculeaza trendul dintr-o lista de valori (ignorand None)."""
    valid = [v for v in values if v is not None]
    if len(valid) < 2:
        return "INSUFICIENT"
    first, last = valid[0], valid[-1]
    if first == 0:
        return "IN CRESTERE" if last > 0 else "STABIL"
    pct = ((last - first) / abs(first)) * 100
    if pct > 5:
        return f"IN CRESTERE (+{pct:.1f}%)"
    elif pct < -5:
        return f"IN SCADERE ({pct:.1f}%)"
    else:
        return "STABIL"


def _score_trend_label(values: list) -> str:
    """Eticheta pentru trendul scorului de risc."""
    valid = [v for v in values if v is not None]
    if len(valid) < 2:
        return "INSUFICIENT DATE"
    delta = valid[-1] - valid[0]
    if delta > 5:
        return "IN IMBUNATATIRE"
    elif delta < -5:
        return "IN DETERIORARE"
    else:
        return "STABIL"


class TimelinePdf(FPDF):
    def __init__(self, company_name: str, cui: str):
        super().__init__()
        self.company_name = company_name
        self.cui = cui
        self.watermark_text = settings.pdf_watermark if settings.pdf_watermark_enabled else ""
        self.set_auto_page_break(auto=True, margin=25)

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, "Roland Intelligence System — Evolutie Multi-An", align="L")
        now = datetime.now(UTC).strftime("%d.%m.%Y %H:%M")
        self.cell(0, 6, now, align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(99, 102, 241)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)
        if self.watermark_text:
            prev_font = (self.font_family, self.font_style, self.font_size_pt)
            self.set_font("Helvetica", "B", 48)
            self.set_text_color(230, 230, 230)
            with self.rotation(45, self.w / 2, self.h / 2):
                self.text(25, self.h / 2 + 10, self.watermark_text)
            self.set_font(*prev_font)

    def footer(self):
        self.set_y(-20)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(150, 150, 150)
        label = self.watermark_text if self.watermark_text else "CONFIDENTIAL"
        self.cell(0, 5, f"{label} | Pagina {self.page_no()}/{{nb}}", align="C")


def generate_timeline_pdf(timeline_data: dict, output_path: str) -> None:
    """
    Genereaza PDF raport evolutie multi-an pentru o firma.

    Args:
        timeline_data: dict returnat de endpoint-ul /api/companies/{cui}/timeline-report
        output_path: calea completa unde se salveaza fisierul PDF

    Structura timeline_data:
    {
        "cui": str,
        "company_name": str,
        "years": [{"year": int, "ca": float|None, "profit": float|None,
                   "angajati": int|None, "risk_score": float|None, "analyzed_at": str}, ...],
        "trends": {"ca_growth_pct": float|None, "profit_trend": str, "risk_trend": str}
    }
    """
    company_name = timeline_data.get("company_name", "Firma necunoscuta")
    cui = timeline_data.get("cui", "N/A")
    years_data = timeline_data.get("years", [])
    trends = timeline_data.get("trends", {})

    pdf = TimelinePdf(company_name=company_name, cui=cui)
    pdf.alias_nb_pages()
    pdf.add_page()

    # --- Titlu ---
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(99, 102, 241)
    pdf.ln(20)
    pdf.multi_cell(0, 12, _sanitize("Evolutie Multi-An"), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 16)
    pdf.set_text_color(60, 60, 60)
    pdf.multi_cell(0, 10, _sanitize(company_name), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 8, _sanitize(f"CUI: {cui}"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, _sanitize(f"Perioda analizata: {len(years_data)} rapoarte"), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(15)

    # --- Tabel evolutie ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(99, 102, 241)
    pdf.cell(0, 10, "Tabel Evolutie Indicatori", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(99, 102, 241)
    pdf.line(10, pdf.get_y(), 80, pdf.get_y())
    pdf.ln(6)

    if years_data:
        # Header tabel
        col_widths = [28, 42, 38, 28, 30]  # An | CA | Profit | Angajati | Scor
        headers = ["An", "CA (RON)", "Profit (RON)", "Angajati", "Scor Risc"]

        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(99, 102, 241)
        pdf.set_text_color(255, 255, 255)
        for i, (h, w) in enumerate(zip(headers, col_widths)):
            pdf.cell(w, 8, h, border=1, fill=True, align="C")
        pdf.ln()

        # Randuri tabel
        pdf.set_font("Helvetica", "", 9)
        for idx, row in enumerate(years_data):
            # Fundal alternant usor
            if idx % 2 == 0:
                pdf.set_fill_color(248, 248, 255)
            else:
                pdf.set_fill_color(255, 255, 255)

            year = str(row.get("year", "—"))
            ca = _fmt_ron(row.get("ca"))
            profit_val = row.get("profit")
            profit_str = _fmt_ron(profit_val)

            angajati = row.get("angajati")
            angajati_str = str(int(angajati)) if angajati is not None else "N/A"

            risk = row.get("risk_score")
            risk_str = f"{int(risk)}/100" if risk is not None else "N/A"

            # Colorare profit (rosu daca negativ)
            if profit_val is not None and float(profit_val) < 0:
                pdf.set_text_color(239, 68, 68)
            else:
                pdf.set_text_color(40, 40, 40)

            pdf.cell(col_widths[0], 7, year, border=1, fill=True, align="C")
            pdf.set_text_color(40, 40, 40)
            pdf.cell(col_widths[1], 7, ca, border=1, fill=True, align="R")

            if profit_val is not None and float(profit_val) < 0:
                pdf.set_text_color(239, 68, 68)
            pdf.cell(col_widths[2], 7, profit_str, border=1, fill=True, align="R")
            pdf.set_text_color(40, 40, 40)

            pdf.cell(col_widths[3], 7, angajati_str, border=1, fill=True, align="C")

            # Colorare scor risc
            if risk is not None:
                if float(risk) >= 70:
                    pdf.set_text_color(34, 197, 94)
                elif float(risk) >= 40:
                    pdf.set_text_color(234, 179, 8)
                else:
                    pdf.set_text_color(239, 68, 68)
            pdf.cell(col_widths[4], 7, risk_str, border=1, fill=True, align="C")
            pdf.set_text_color(40, 40, 40)
            pdf.ln()

        pdf.ln(8)
    else:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 8, "Nu exista date disponibile pentru evolutie.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # --- Concluzii trendurii ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(99, 102, 241)
    pdf.cell(0, 10, "Concluzii si Trendurii", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(99, 102, 241)
    pdf.line(10, pdf.get_y(), 80, pdf.get_y())
    pdf.ln(6)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 40, 40)

    ca_growth = trends.get("ca_growth_pct")
    profit_trend = trends.get("profit_trend", "N/A")
    risk_trend = trends.get("risk_trend", "N/A")

    conclusion_lines = []
    if ca_growth is not None:
        sign = "+" if ca_growth >= 0 else ""
        conclusion_lines.append(f"Trend Cifra de Afaceri: {sign}{ca_growth:.1f}% pe perioada analizata")
    else:
        conclusion_lines.append("Trend Cifra de Afaceri: DATE INSUFICIENTE")

    conclusion_lines.append(f"Trend Profit Net: {_sanitize(profit_trend)}")
    conclusion_lines.append(f"Scor Risc: {_sanitize(risk_trend)}")

    for line in conclusion_lines:
        pdf.cell(20, 7, "*")
        pdf.multi_cell(0, 7, _sanitize(line), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)

    # --- Disclaimer ---
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(150, 150, 150)
    disclaimer = (
        "Raport generat automat de Roland Intelligence System pe baza analizelor efectuate. "
        "Datele reflecta informatii din momentul fiecarei analize, nu date financiare oficiale ANAF. "
        "Nu se asuma responsabilitatea pentru decizii bazate exclusiv pe acest raport."
    )
    pdf.multi_cell(0, 4.5, _sanitize(disclaimer), new_x="LMARGIN", new_y="NEXT")

    try:
        pdf.output(output_path)
        logger.info(f"[timeline_pdf] generat: {output_path}")
    except Exception as e:
        logger.error(f"[timeline_pdf] eroare la generare: {e}")
        raise
