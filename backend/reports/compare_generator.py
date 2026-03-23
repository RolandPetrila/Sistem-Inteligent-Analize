"""
E9: Compare PDF Generator — Raport comparativ 2 firme side-by-side.
"""

from fpdf import FPDF
from backend.reports.pdf_generator import _sanitize


class ComparePdf(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=25)

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, "Roland Intelligence System — Raport Comparativ", align="L")
        self.ln(3)
        self.set_draw_color(99, 102, 241)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)
        # Watermark
        prev = (self.font_family, self.font_style, self.font_size_pt)
        self.set_font("Helvetica", "B", 48)
        self.set_text_color(230, 230, 230)
        with self.rotation(45, self.w / 2, self.h / 2):
            self.text(25, self.h / 2 + 10, "CONFIDENTIAL")
        self.set_font(*prev)

    def footer(self):
        self.set_y(-20)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 5, f"CONFIDENTIAL | Pagina {self.page_no()}/{{nb}}", align="C")


def generate_compare_pdf(company_a: dict, company_b: dict, output_path: str):
    """Generate a comparative PDF for 2 companies."""
    pdf = ComparePdf()
    pdf.alias_nb_pages()

    name_a = _sanitize(str(company_a.get("denumire", company_a.get("cui", "Firma A"))))
    name_b = _sanitize(str(company_b.get("denumire", company_b.get("cui", "Firma B"))))

    # --- Page 1: Title ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(99, 102, 241)
    pdf.ln(25)
    pdf.cell(0, 14, "Raport Comparativ", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 10, f"{name_a}  vs  {name_b}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(120, 120, 120)
    an = company_a.get("an_financiar", "N/A")
    pdf.cell(0, 8, f"Date financiare: {an}", align="C", new_x="LMARGIN", new_y="NEXT")

    # --- Page 2: Comparison Table ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(99, 102, 241)
    pdf.cell(0, 12, "Tabel Comparativ", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(99, 102, 241)
    pdf.line(10, pdf.get_y(), 80, pdf.get_y())
    pdf.ln(6)

    # Table header
    col_w = [50, 60, 60]
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(99, 102, 241)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(col_w[0], 7, "Indicator", border=1, fill=True)
    pdf.cell(col_w[1], 7, name_a[:25], border=1, align="C", fill=True)
    pdf.cell(col_w[2], 7, name_b[:25], border=1, align="C", fill=True, new_x="LMARGIN", new_y="NEXT")

    # Data rows
    indicators = [
        ("CUI", "cui", "cui"),
        ("Stare", "stare", "stare"),
        ("Cifra Afaceri (RON)", "cifra_afaceri", "cifra_afaceri"),
        ("Profit Net (RON)", "profit_net", "profit_net"),
        ("Nr Angajati", "angajati", "angajati"),
        ("Capitaluri Proprii", "capitaluri", "capitaluri"),
        ("Scor Risc", "scor_risc", "scor_risc"),
        ("CAEN", "caen_code", "caen_code"),
        ("Platitor TVA", "platitor_tva", "platitor_tva"),
        ("Inactiv", "inactiv", "inactiv"),
    ]

    pdf.set_font("Helvetica", "", 9)
    for label, key_a, key_b in indicators:
        val_a = company_a.get(key_a)
        val_b = company_b.get(key_b)

        def _fmt(v):
            if v is None:
                return "N/A"
            if isinstance(v, bool):
                return "Da" if v else "Nu"
            if isinstance(v, (int, float)) and abs(v) >= 1000:
                return f"{v:,.0f}"
            return str(v)

        pdf.set_text_color(40, 40, 40)
        pdf.cell(col_w[0], 6, _sanitize(label), border=1)

        # Color winner green
        va, vb = val_a, val_b
        a_better = False
        b_better = False
        if key_a in ("cifra_afaceri", "profit_net", "angajati", "capitaluri", "scor_risc"):
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                a_better = va > vb
                b_better = vb > va

        if a_better:
            pdf.set_text_color(34, 197, 94)
        else:
            pdf.set_text_color(40, 40, 40)
        pdf.cell(col_w[1], 6, _sanitize(_fmt(va)), border=1, align="R")

        if b_better:
            pdf.set_text_color(34, 197, 94)
        else:
            pdf.set_text_color(40, 40, 40)
        pdf.cell(col_w[2], 6, _sanitize(_fmt(vb)), border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    # --- Page 3: Visual comparison bars ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(99, 102, 241)
    pdf.cell(0, 12, "Comparatie Vizuala", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(99, 102, 241)
    pdf.line(10, pdf.get_y(), 80, pdf.get_y())
    pdf.ln(8)

    bar_metrics = [
        ("Cifra Afaceri", "cifra_afaceri"),
        ("Profit Net", "profit_net"),
        ("Angajati", "angajati"),
        ("Scor Risc", "scor_risc"),
    ]

    for label, key in bar_metrics:
        va = company_a.get(key)
        vb = company_b.get(key)
        if va is None and vb is None:
            continue

        va = va or 0
        vb = vb or 0
        max_val = max(abs(va), abs(vb), 1)

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(0, 7, _sanitize(label), new_x="LMARGIN", new_y="NEXT")

        # Bar A
        bar_width_a = max(2, abs(va) / max_val * 120)
        pdf.set_fill_color(99, 102, 241)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(99, 102, 241)
        pdf.cell(30, 5, name_a[:15])
        pdf.cell(bar_width_a, 5, "", fill=True)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(40, 5, f"  {va:,.0f}" if isinstance(va, (int, float)) else f"  {va}", new_x="LMARGIN", new_y="NEXT")

        # Bar B
        bar_width_b = max(2, abs(vb) / max_val * 120)
        pdf.set_fill_color(34, 197, 94)
        pdf.set_text_color(34, 197, 94)
        pdf.cell(30, 5, name_b[:15])
        pdf.cell(bar_width_b, 5, "", fill=True)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(40, 5, f"  {vb:,.0f}" if isinstance(vb, (int, float)) else f"  {vb}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # --- Page 4: Conclusions ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(99, 102, 241)
    pdf.cell(0, 12, "Concluzii", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(99, 102, 241)
    pdf.line(10, pdf.get_y(), 80, pdf.get_y())
    pdf.ln(6)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 40, 40)

    conclusions = []
    a_wins = 0
    b_wins = 0
    for label, key in [("Cifra Afaceri", "cifra_afaceri"), ("Profit Net", "profit_net"),
                       ("Angajati", "angajati"), ("Scor Risc", "scor_risc")]:
        va = company_a.get(key)
        vb = company_b.get(key)
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            if va != 0 or vb != 0:
                base = max(abs(va), abs(vb), 1)
                pct_diff = abs(va - vb) / base * 100
                pct_str = f" ({pct_diff:.0f}% diferenta)" if pct_diff > 1 else ""
            else:
                pct_str = ""
            if va > vb:
                conclusions.append(f"{label}: {name_a} este superior ({va:,.0f} vs {vb:,.0f}){pct_str}")
                a_wins += 1
            elif vb > va:
                conclusions.append(f"{label}: {name_b} este superior ({vb:,.0f} vs {va:,.0f}){pct_str}")
                b_wins += 1
            else:
                conclusions.append(f"{label}: Egalitate ({va:,.0f})")

    for c in conclusions:
        pdf.multi_cell(0, 6, _sanitize(f"- {c}"))
        pdf.ln(1)

    # F18: Narrative summary
    if conclusions:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(99, 102, 241)
        pdf.cell(0, 8, "Rezumat", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        if a_wins > b_wins:
            narrative = f"{name_a} prezinta performante superioare in {a_wins} din {len(conclusions)} indicatori analizati."
        elif b_wins > a_wins:
            narrative = f"{name_b} prezinta performante superioare in {b_wins} din {len(conclusions)} indicatori analizati."
        else:
            narrative = f"Cele doua firme au performante similare ({a_wins} indicatori fiecare)."
        pdf.multi_cell(0, 6, _sanitize(narrative))

    if not conclusions:
        pdf.multi_cell(0, 6, "Date insuficiente pentru concluzii comparative.")

    pdf.output(output_path)
