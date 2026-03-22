"""
DF3: Raport Executiv 1-Pager — PDF compact pe o singura pagina.
Contine: scor risc, top 3 puncte tari, top 3 riscuri, recomandare, due diligence checklist.
"""

from fpdf import FPDF
from backend.reports.pdf_generator import _sanitize

DISCLAIMER_SHORT = (
    "Raport generat automat din surse publice. Verificare independenta recomandata."
)


class OnePagerPdf(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=False)


def generate_one_pager(verified_data: dict, meta: dict, output_path: str):
    """Genereaza PDF 1-pager executiv din verified_data."""
    pdf = OnePagerPdf()
    pdf.add_page()

    company_name = _sanitize(meta.get("company_name", "N/A"))
    risk_score = verified_data.get("risk_score", {})
    score_color = risk_score.get("score", "N/A")
    numeric = risk_score.get("numeric_score", 0)
    recommendation = risk_score.get("recommendation", "")
    dimensions = risk_score.get("dimensions", {})
    factors = risk_score.get("factors", [])
    due_diligence = verified_data.get("due_diligence", [])
    early_warnings = verified_data.get("early_warnings", [])

    color_map = {
        "Verde": (34, 197, 94),
        "Galben": (234, 179, 8),
        "Rosu": (239, 68, 68),
    }

    # --- Header bar ---
    pdf.set_fill_color(26, 26, 46)  # dark theme
    pdf.rect(0, 0, 210, 28, "F")
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(10, 6)
    pdf.cell(0, 10, company_name[:50], new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(180, 180, 200)
    pdf.set_x(10)
    cui = meta.get("company_name", "")
    generated = _sanitize(meta.get("generated_at", ""))
    pdf.cell(0, 5, f"Raport Executiv | {generated} | Roland Intelligence System")

    # --- Score box (right side of header) ---
    r, g, b = color_map.get(score_color, (150, 150, 150))
    pdf.set_fill_color(r, g, b)
    pdf.rect(155, 3, 48, 22, "F")
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(155, 4)
    pdf.cell(48, 12, f"{numeric}/100", align="C")
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_xy(155, 16)
    pdf.cell(48, 6, f"RISC {score_color.upper()}", align="C")

    y = 32

    # --- Recomandare ---
    pdf.set_xy(10, y)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(r, g, b)
    # C8 fix: N/A or missing score → "INSUFICIENT DATE" instead of "NERECOMANDAT"
    if score_color in ("Verde", "Galben", "Rosu"):
        recom_short = "RECOMANDAT" if score_color == "Verde" else "PRUDENTA" if score_color == "Galben" else "NERECOMANDAT"
    else:
        recom_short = "INSUFICIENT DATE"
    pdf.cell(0, 6, f"Recomandare: {recom_short}")
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(80, 80, 80)
    pdf.set_xy(10, y + 6)
    pdf.cell(0, 4, _sanitize(recommendation[:120]))
    y += 14

    # --- Dimensiuni scor (bara compacta) ---
    pdf.set_xy(10, y)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 5, "SCOR PE DIMENSIUNI")
    y += 6

    dim_labels = {
        "financiar": "Financiar",
        "juridic": "Juridic",
        "fiscal": "Fiscal",
        "operational": "Operational",
        "reputational": "Reputational",
        "piata": "Piata",
    }
    bar_width = 90
    for dim_key, dim_label in dim_labels.items():
        dim = dimensions.get(dim_key, {})
        score = dim.get("score", 0)
        weight = dim.get("weight", 0)

        pdf.set_xy(10, y)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(28, 4, f"{dim_label} ({weight}%)")

        # Background bar
        pdf.set_fill_color(230, 230, 230)
        pdf.rect(40, y, bar_width, 3.5, "F")

        # Score bar
        if score >= 70:
            pdf.set_fill_color(34, 197, 94)
        elif score >= 40:
            pdf.set_fill_color(234, 179, 8)
        else:
            pdf.set_fill_color(239, 68, 68)
        bar_len = max(1, score * bar_width / 100)
        pdf.rect(40, y, bar_len, 3.5, "F")

        pdf.set_xy(132, y)
        pdf.set_font("Helvetica", "B", 7)
        pdf.cell(10, 4, str(int(score)))
        y += 5

    y += 2

    # --- Due Diligence Checklist (left column) ---
    col1_x = 10
    col2_x = 108
    dd_y = y

    pdf.set_xy(col1_x, dd_y)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 5, "DUE DILIGENCE CHECKLIST")
    dd_y += 6

    for item in due_diligence[:10]:
        status = item.get("status", "?")
        name = _sanitize(item.get("name", ""))
        severity = item.get("severity", "info")

        if status == "DA":
            marker = "[OK]"
            pdf.set_text_color(34, 197, 94)
        elif status == "NU":
            marker = "[X]"
            if severity == "critical":
                pdf.set_text_color(239, 68, 68)
            else:
                pdf.set_text_color(234, 179, 8)
        else:
            marker = "[?]"
            pdf.set_text_color(150, 150, 150)

        pdf.set_xy(col1_x, dd_y)
        pdf.set_font("Helvetica", "B", 7)
        pdf.cell(8, 3.5, marker)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(80, 3.5, name[:40])
        dd_y += 4.2

    # --- Top 3 riscuri + top 3 puncte tari (right column) ---
    right_y = y

    pdf.set_xy(col2_x, right_y)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 5, "TOP RISCURI")
    right_y += 6

    # Top risks from factors
    risk_items = [f for f in factors if f[1] in ("HIGH", "MEDIUM")][:3]
    if not risk_items:
        risk_items = factors[:3]

    for i, (text, severity) in enumerate(risk_items):
        pdf.set_xy(col2_x, right_y)
        pdf.set_font("Helvetica", "", 7)
        if severity == "HIGH":
            pdf.set_text_color(239, 68, 68)
        elif severity == "MEDIUM":
            pdf.set_text_color(234, 179, 8)
        else:
            pdf.set_text_color(150, 150, 150)
        pdf.cell(4, 3.5, f"{i+1}.")
        pdf.set_text_color(60, 60, 60)
        pdf.cell(88, 3.5, _sanitize(text[:55]))
        right_y += 4.2

    if not risk_items:
        pdf.set_xy(col2_x, right_y)
        pdf.set_font("Helvetica", "I", 7)
        pdf.set_text_color(34, 197, 94)
        pdf.cell(0, 3.5, "Niciun risc major identificat")
        right_y += 4.2

    right_y += 3

    # Top 3 puncte tari (derivate din dimensiuni cu scor mare)
    pdf.set_xy(col2_x, right_y)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 5, "PUNCTE TARI")
    right_y += 6

    strengths = sorted(
        [(dim_labels.get(k, k), v.get("score", 0)) for k, v in dimensions.items()],
        key=lambda x: -x[1],
    )[:3]

    for i, (dim_name, dim_score) in enumerate(strengths):
        pdf.set_xy(col2_x, right_y)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(34, 197, 94)
        pdf.cell(4, 3.5, f"{i+1}.")
        pdf.set_text_color(60, 60, 60)
        pdf.cell(88, 3.5, f"{dim_name}: {int(dim_score)}/100")
        right_y += 4.2

    # --- Early Warnings (daca exista) ---
    ew_y = max(dd_y, right_y) + 4
    if early_warnings:
        pdf.set_xy(10, ew_y)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(239, 68, 68)
        pdf.cell(0, 5, f"SEMNALE DE ALARMA ({len(early_warnings)})")
        ew_y += 6

        for ew in early_warnings[:3]:
            pdf.set_xy(10, ew_y)
            pdf.set_font("Helvetica", "", 7)
            sev = ew.get("severity", "")
            if sev == "HIGH":
                pdf.set_text_color(239, 68, 68)
            else:
                pdf.set_text_color(234, 179, 8)
            signal = _sanitize(ew.get("signal", ""))
            detail = _sanitize(ew.get("detail", ""))
            pdf.cell(0, 3.5, f"[{sev}] {signal}: {detail[:80]}")
            ew_y += 4.2

    # --- CAEN info (daca exista) ---
    caen_info = verified_data.get("caen_context", {})
    if caen_info and caen_info.get("available"):
        caen_y = ew_y + 3
        pdf.set_xy(10, caen_y)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(0, 5, "CONTEXT SECTOR")
        caen_y += 6
        pdf.set_xy(10, caen_y)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(80, 80, 80)
        caen_code = caen_info.get("caen_code", "")
        caen_desc = _sanitize(caen_info.get("caen_description", ""))
        nr_firme = caen_info.get("nr_firme_caen", "N/A")
        pdf.cell(0, 3.5, f"CAEN {caen_code}: {caen_desc} | Firme active pe CAEN: {nr_firme}")

    # --- Footer disclaimer ---
    pdf.set_xy(10, 280)
    pdf.set_font("Helvetica", "I", 6)
    pdf.set_text_color(160, 160, 160)
    pdf.cell(0, 3, _sanitize(DISCLAIMER_SHORT), align="C")

    pdf.output(output_path)
