"""
HTML Generator — Single-file HTML report cu dark theme + Chart.js grafice.
"""

import html as html_lib
import json as json_lib

DISCLAIMER = (
    "Acest raport a fost generat automat folosind exclusiv date disponibile public "
    "din surse verificabile. Acuratetea datelor depinde de corectitudinea informatiilor "
    "din registrele publice accesate. Roland Intelligence System nu isi asuma "
    "responsabilitatea pentru decizii bazate exclusiv pe acest raport fara verificare "
    "independenta."
)


def _escape(text: str) -> str:
    return html_lib.escape(text)


def _render_content(content: str) -> str:
    lines = []
    in_list = False
    for line in content.split("\n"):
        line = line.strip()
        is_list_item = line.startswith("- ") or line.startswith("* ")
        # C11 fix: Close <ul> when transitioning out of list
        if in_list and not is_list_item:
            lines.append("</ul>")
            in_list = False
        if not line:
            lines.append("<br>")
        elif line.startswith("## ") or line.startswith("**"):
            clean = line.replace("**", "").replace("## ", "")
            lines.append(f'<h3 class="subsection">{_escape(clean)}</h3>')
        elif is_list_item:
            if not in_list:
                lines.append('<ul class="list-disc ml-6 space-y-1">')
                in_list = True
            lines.append(f'<li>{_escape(line[2:])}</li>')
        else:
            escaped = _escape(line)
            escaped = escaped.replace("[OFICIAL]", '<span class="trust-oficial">[OFICIAL]</span>')
            escaped = escaped.replace("[VERIFICAT]", '<span class="trust-verificat">[VERIFICAT]</span>')
            escaped = escaped.replace("[ESTIMAT]", '<span class="trust-estimat">[ESTIMAT]</span>')
            escaped = escaped.replace("[INDISPONIBIL]", '<span class="trust-indisponibil">[INDISPONIBIL]</span>')
            lines.append(f"<p>{escaped}</p>")
    if in_list:
        lines.append("</ul>")
    return "\n".join(lines)


def _build_charts_html(verified_data: dict, risk_score: dict) -> str:
    """Genereaza sectiunea de grafice Chart.js din verified_data."""
    charts = []

    # Extrage trend financiar
    financial = verified_data.get("financial", {})
    trend_field = financial.get("trend_financiar", {})
    trend_val = trend_field.get("value") if isinstance(trend_field, dict) else None

    if isinstance(trend_val, dict) and trend_val:
        # Grafic 1: CA
        ca_data = trend_val.get("cifra_afaceri_neta", {})
        if ca_data and ca_data.get("values"):
            labels = [str(v["year"]) for v in ca_data["values"]]
            values = [v["value"] for v in ca_data["values"]]
            charts.append(_chart_bar("chartCA", "Evolutie Cifra de Afaceri (RON)", labels, values, "#6366f1"))

        # Grafic 2: Profit
        profit_data = trend_val.get("profit_net", {})
        if not profit_data or not profit_data.get("values"):
            profit_data = trend_val.get("cifra_afaceri_neta", {})  # fallback
        if profit_data and profit_data.get("values") and profit_data is not ca_data:
            labels = [str(v["year"]) for v in profit_data["values"]]
            values = [v["value"] for v in profit_data["values"]]
            colors = ["#22c55e" if v >= 0 else "#ef4444" for v in values]
            charts.append(_chart_bar("chartProfit", f"Evolutie {profit_data.get('name', 'Profit')} (RON)", labels, values, colors))

        # Grafic 3: Angajati
        emp_data = trend_val.get("numar_mediu_salariati", {})
        if emp_data and emp_data.get("values"):
            labels = [str(v["year"]) for v in emp_data["values"]]
            values = [v["value"] for v in emp_data["values"]]
            charts.append(_chart_bar("chartEmp", "Numar Mediu Angajati", labels, values, "#a78bfa"))

    # Grafic 4: Radar dimensiuni risc
    dimensions = risk_score.get("dimensions", {})
    if dimensions:
        labels = [d.capitalize() for d in dimensions.keys()]
        values = [d.get("score", 0) for d in dimensions.values()]
        charts.append(_chart_radar("chartRisk", "Profil Risc (0-100)", labels, values))

    if not charts:
        return ""

    return f'''
    <section id="charts" class="report-section">
        <h2>Grafice si Indicatori</h2>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:24px;margin-top:20px">
            {"".join(charts)}
        </div>
    </section>'''


def _chart_bar(canvas_id: str, title: str, labels: list, values: list, color) -> str:
    labels_json = json_lib.dumps(labels)
    values_json = json_lib.dumps(values)
    if isinstance(color, list):
        bg_color = json_lib.dumps(color)
    else:
        bg_color = json_lib.dumps(color)
    return f'''
    <div style="background:#16213e;border-radius:12px;padding:16px">
        <canvas id="{canvas_id}" height="200"></canvas>
        <script>
        new Chart(document.getElementById('{canvas_id}'),{{
            type:'bar',
            data:{{labels:{labels_json},datasets:[{{label:'{_escape(title)}',data:{values_json},
                backgroundColor:{bg_color if isinstance(color,list) else f'"{color}88"'},
                borderColor:{bg_color if isinstance(color,list) else f'"{color}"'},borderWidth:1}}]}},
            options:{{responsive:true,plugins:{{legend:{{display:false}},title:{{display:true,text:'{_escape(title)}',color:'#e2e8f0',font:{{size:13}}}}}},
                scales:{{y:{{ticks:{{color:'#94a3b8'}},grid:{{color:'#2a3a5c'}}}},x:{{ticks:{{color:'#94a3b8'}},grid:{{display:false}}}}}}}}
        }});
        </script>
    </div>'''


def _chart_radar(canvas_id: str, title: str, labels: list, values: list) -> str:
    labels_json = json_lib.dumps(labels)
    values_json = json_lib.dumps(values)
    return f'''
    <div style="background:#16213e;border-radius:12px;padding:16px">
        <canvas id="{canvas_id}" height="200"></canvas>
        <script>
        new Chart(document.getElementById('{canvas_id}'),{{
            type:'radar',
            data:{{labels:{labels_json},datasets:[{{label:'Scor',data:{values_json},
                backgroundColor:'#6366f130',borderColor:'#6366f1',pointBackgroundColor:'#6366f1',pointBorderColor:'#fff'}}]}},
            options:{{responsive:true,plugins:{{legend:{{display:false}},title:{{display:true,text:'{_escape(title)}',color:'#e2e8f0',font:{{size:13}}}}}},
                scales:{{r:{{min:0,max:100,ticks:{{color:'#94a3b8',backdropColor:'transparent'}},grid:{{color:'#2a3a5c'}},pointLabels:{{color:'#cbd5e1',font:{{size:11}}}}}}}}}}
        }});
        </script>
    </div>'''


def generate_html(report_sections: dict, meta: dict, verified_data: dict, output_path: str):
    """Genereaza HTML single-file din report_sections + verified_data."""
    company = _escape(meta.get("company_name", "N/A"))
    title = _escape(meta.get("title", "Raport"))
    generated = _escape(meta.get("generated_at", ""))
    risk = meta.get("risk_score", "N/A")
    numeric = meta.get("numeric_score")
    risk_rec = _escape(meta.get("risk_recommendation", ""))
    level = meta.get("report_level", 2)
    sources = meta.get("sources", [])

    risk_color = {"Verde": "#22c55e", "Galben": "#eab308", "Rosu": "#ef4444"}.get(risk, "#888")

    risk_display = f"Risc: {risk}"
    if numeric is not None:
        risk_display += f" ({numeric}/100)"

    # Build sections HTML
    nav_items = '<a href="#charts" class="nav-link">Grafice</a>\n'
    sections_html = ""
    for key, section in report_sections.items():
        sec_title = _escape(section.get("title", key))
        content_html = _render_content(section.get("content", ""))
        nav_items += f'<a href="#{key}" class="nav-link">{sec_title}</a>\n'
        sections_html += f'''
        <section id="{key}" class="report-section">
            <h2>{sec_title}</h2>
            <div class="section-content">{content_html}</div>
        </section>'''

    # Charts
    risk_score_data = verified_data.get("risk_score", {})
    charts_html = _build_charts_html(verified_data, risk_score_data)

    # Completeness section
    completeness = verified_data.get("completeness", {})
    completeness_html = ""
    if completeness:
        c_score = completeness.get("score", 0)
        c_level = completeness.get("quality_level", "N/A")
        c_color = "#22c55e" if c_score >= 90 else "#eab308" if c_score >= 70 else "#ef4444"
        gaps = completeness.get("gaps", [])

        completeness_html = f'''
        <section id="completeness" class="report-section">
            <h2>Diagnostic Completitudine Raport</h2>
            <div style="text-align:center;margin:20px 0">
                <span style="font-size:2em;font-weight:700;color:{c_color}">{c_score}%</span>
                <span style="color:#94a3b8;margin-left:12px">({c_level})</span>
                <div style="color:#94a3b8;font-size:0.85em;margin-top:4px">
                    {completeness.get("passed", 0)}/{completeness.get("total_checks", 0)} verificari trecute
                </div>
            </div>'''

        if gaps:
            completeness_html += '<div style="margin-top:16px"><h3 style="color:#ef4444;margin-bottom:12px">Date lipsa</h3>'
            for gap in gaps:
                sev_color = "#ef4444" if gap.get("severity") == "HIGH" else "#eab308"
                completeness_html += (
                    f'<div style="padding:8px 12px;margin-bottom:6px;background:#16213e;border-radius:6px;'
                    f'border-left:3px solid {sev_color}">'
                    f'<span style="color:{sev_color};font-weight:600">[{_escape(gap.get("severity", ""))}]</span> '
                    f'<span style="color:#e2e8f0">{_escape(gap.get("field", ""))}</span> '
                    f'<span style="color:#64748b;font-size:0.85em">— {_escape(gap.get("reason", ""))}</span>'
                    f'</div>\n'
                )
            completeness_html += '</div>'
        completeness_html += '</section>'

        nav_items += '<a href="#completeness" class="nav-link">Diagnostic</a>\n'

    # Diagnostics section (per-source from agent_official)
    diag = verified_data.get("diagnostics") if "diagnostics" in verified_data else None
    if not diag:
        # Cauta in official_data daca a fost propagat
        official_diag = meta.get("diagnostics", {})
        if official_diag:
            diag = official_diag

    # Sources HTML
    sources_html = ""
    for src in sources:
        lvl = src.get("level", "?")
        name = _escape(src.get("name", ""))
        status = src.get("status", "OK")
        s_color = "#22c55e" if status == "OK" else "#ef4444" if status in ("ERROR", "TIMEOUT") else "#eab308"
        sources_html += f'<div class="source-item"><span class="source-level">N{lvl}</span> {name} <span class="source-status" style="color:{s_color}">{status}</span></div>\n'

    html_content = f'''<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — {company}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#1a1a2e;color:#e2e8f0;line-height:1.7}}
.container{{max-width:960px;margin:0 auto;padding:40px 20px}}
.header{{text-align:center;padding:60px 0 40px;border-bottom:2px solid #6366f1}}
.header h1{{font-size:2em;color:#6366f1;margin-bottom:8px}}
.header .company{{font-size:1.4em;color:#a5b4fc;margin-bottom:16px}}
.header .meta{{color:#94a3b8;font-size:0.85em}}
.risk-badge{{display:inline-block;padding:8px 24px;border-radius:8px;font-weight:700;font-size:1.1em;margin-top:16px;background:{risk_color}20;color:{risk_color};border:1px solid {risk_color}40}}
.nav{{position:sticky;top:0;background:#16213e;padding:12px 0;border-bottom:1px solid #2a3a5c;z-index:10;display:flex;gap:4px;flex-wrap:wrap;justify-content:center}}
.nav-link{{color:#94a3b8;text-decoration:none;padding:6px 14px;border-radius:6px;font-size:0.8em;transition:all .2s}}
.nav-link:hover{{background:#6366f120;color:#a5b4fc}}
.report-section{{padding:40px 0;border-bottom:1px solid #2a3a5c}}
.report-section h2{{color:#6366f1;font-size:1.5em;margin-bottom:20px;padding-bottom:8px;border-bottom:2px solid #6366f140}}
.section-content p{{margin-bottom:10px;color:#cbd5e1}}
.section-content h3.subsection{{color:#818cf8;font-size:1.1em;margin:20px 0 8px}}
.section-content li{{margin-left:24px;margin-bottom:4px;color:#cbd5e1}}
.trust-oficial{{color:#00AA00;font-weight:600}}
.trust-verificat{{color:#0066CC;font-weight:600}}
.trust-estimat{{color:#FF8800;font-weight:600}}
.trust-indisponibil{{color:#888;font-weight:600}}
.sources{{padding:40px 0}}
.sources h2{{color:#6366f1;margin-bottom:16px}}
.source-item{{padding:6px 12px;margin-bottom:4px;background:#16213e;border-radius:6px;font-size:0.85em}}
.source-level{{display:inline-block;width:28px;font-weight:700;color:#6366f1}}
.source-status{{float:right;color:#22c55e;font-size:0.85em}}
.disclaimer{{padding:40px 0;border-top:1px solid #2a3a5c;color:#64748b;font-size:0.75em;font-style:italic}}
.footer{{text-align:center;padding:20px 0;color:#475569;font-size:0.7em}}
.watermark{{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%) rotate(-45deg);font-size:6em;font-weight:900;color:rgba(255,255,255,0.03);pointer-events:none;z-index:0;white-space:nowrap;letter-spacing:0.1em}}
@media print{{.watermark{{color:rgba(0,0,0,0.05)}}body{{background:#fff;color:#333}}.container{{max-width:100%;padding:10px}}.header{{padding:20px 0}}.report-section h2{{color:#4338ca}}.nav{{display:none}}.risk-badge{{border:1px solid #333}}canvas{{max-height:200px!important}}}}
@media (max-width:768px){{.container{{padding:16px 12px}}.header{{padding:30px 0 20px}}.header h1{{font-size:1.4em}}.header .company{{font-size:1.1em}}.report-section{{padding:20px 0}}.report-section h2{{font-size:1.2em}}canvas{{max-height:250px!important}}.nav{{gap:2px;padding:8px 4px}}.nav-link{{padding:4px 8px;font-size:0.7em}}.source-status{{float:none;display:block;margin-top:2px}}}}
@media (max-width:480px){{.container{{padding:10px 8px}}.header h1{{font-size:1.1em}}.header .company{{font-size:0.95em}}.risk-badge{{font-size:0.9em;padding:6px 16px}}.section-content p{{font-size:0.9em}}}}
</style>
</head>
<body>
<div class="watermark">CONFIDENTIAL</div>
<div class="container">
    <div class="header">
        <h1>{title}</h1>
        <div class="company">{company}</div>
        <div class="meta">Nivel {level} | Generat: {generated} | {len(sources)} surse</div>
        <div class="risk-badge">{risk_display}</div>
        {f'<p style="margin-top:8px;color:#94a3b8;font-size:0.85em">{risk_rec}</p>' if risk_rec else ''}
    </div>
    <nav class="nav">{nav_items}</nav>
    {charts_html}
    {sections_html}
    {completeness_html}
    <div class="sources">
        <h2>Surse Utilizate</h2>
        {sources_html}
    </div>
    <div class="disclaimer">{_escape(DISCLAIMER)}</div>
    <div class="footer">Roland Intelligence System v1.1</div>
</div>
</body>
</html>'''

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
