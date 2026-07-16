"""
HTML Generator — Single-file HTML report cu dark theme + Chart.js grafice.
"""

import html as html_lib
import json as json_lib

from backend.reports.rich_fields import build_rich_fields_model

DISCLAIMER = (
    "Acest raport a fost generat automat folosind exclusiv date disponibile public "
    "din surse verificabile. Acuratetea datelor depinde de corectitudinea informatiilor "
    "din registrele publice accesate. Roland Intelligence System nu isi asuma "
    "responsabilitatea pentru decizii bazate exclusiv pe acest raport fara verificare "
    "independenta."
)


def _escape(text: str) -> str:
    return html_lib.escape(text)


def _render_inline(text: str) -> str:
    """F3: Convert **bold** to <strong> and escape HTML."""
    import re
    escaped = _escape(text)
    escaped = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', escaped)
    escaped = escaped.replace("[OFICIAL]", '<span class="trust-oficial">[OFICIAL]</span>')
    escaped = escaped.replace("[VERIFICAT]", '<span class="trust-verificat">[VERIFICAT]</span>')
    escaped = escaped.replace("[ESTIMAT]", '<span class="trust-estimat">[ESTIMAT]</span>')
    escaped = escaped.replace("[INDISPONIBIL]", '<span class="trust-indisponibil">[INDISPONIBIL]</span>')
    return escaped


def _render_content(content: str) -> str:
    import re
    lines = []
    in_ul = False
    in_ol = False
    in_table = False
    table_rows: list[list[str]] = []
    table_header = False

    for line in content.split("\n"):
        line = line.strip()
        is_ul_item = line.startswith("- ") or line.startswith("* ")
        is_ol_item = bool(re.match(r'^\d+\.\s', line))
        is_table_row = line.startswith("|") and line.endswith("|") and line.count("|") >= 3
        # HTML-05: Require at least one '-' per column to be a valid separator
        is_table_sep = bool(re.match(r'^\|(\s*:?-+:?\s*\|)+$', line))

        # Close open lists/table when transitioning
        if in_ul and not is_ul_item:
            lines.append("</ul>")
            in_ul = False
        if in_ol and not is_ol_item:
            lines.append("</ol>")
            in_ol = False
        if in_table and not is_table_row and not is_table_sep:
            lines.append(_build_table(table_rows, table_header))
            in_table = False
            table_rows = []
            table_header = False

        if not line:
            lines.append("<br>")
        elif is_table_sep:
            # HTML-01: Header separator valid only right after first row
            # (separator after 2+ data rows = misplaced, ignore header flag)
            if len(table_rows) <= 1:
                table_header = True
        elif is_table_row:
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not in_table:
                in_table = True
            table_rows.append(cells)
        elif line.startswith("### ") or line.startswith("## "):
            clean = line.lstrip("#").strip()
            lines.append(f'<h3 class="subsection">{_escape(clean)}</h3>')
        elif line.startswith("**") and line.endswith("**") and len(line) > 4:
            clean = line[2:-2]
            lines.append(f'<h3 class="subsection">{_escape(clean)}</h3>')
        elif is_ul_item:
            if not in_ul:
                lines.append('<ul class="list-disc ml-6 space-y-1">')
                in_ul = True
            lines.append(f'<li>{_render_inline(line[2:])}</li>')
        elif is_ol_item:
            if not in_ol:
                lines.append('<ol class="list-decimal ml-6 space-y-1">')
                in_ol = True
            text = re.sub(r'^\d+\.\s', '', line)
            lines.append(f'<li>{_render_inline(text)}</li>')
        else:
            lines.append(f"<p>{_render_inline(line)}</p>")

    if in_ul:
        lines.append("</ul>")
    if in_ol:
        lines.append("</ol>")
    if in_table:
        lines.append(_build_table(table_rows, table_header))
    return "\n".join(lines)


def _build_table(rows: list[list[str]], has_header: bool) -> str:
    """F2: Build HTML <table> from parsed markdown table rows."""
    if not rows:
        return ""
    # HTML-03: Normalize column count — pad short rows with empty cells
    max_cols = max(len(r) for r in rows)
    rows = [r + [""] * (max_cols - len(r)) for r in rows]

    html_parts = ['<table class="ris-table">']
    start = 0
    if has_header and len(rows) >= 1:
        html_parts.append("<thead><tr>")
        for cell in rows[0]:
            html_parts.append(f"<th>{_render_inline(cell)}</th>")
        html_parts.append("</tr></thead>")
        start = 1
    html_parts.append("<tbody>")
    for row in rows[start:]:
        html_parts.append("<tr>")
        for cell in row:
            html_parts.append(f"<td>{_render_inline(cell)}</td>")
        html_parts.append("</tr>")
    html_parts.append("</tbody></table>")
    return "\n".join(html_parts)


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


def _build_sparkline_html(verified_data: dict) -> str:
    """E2: Sparkline trend CA — mini Chart.js line chart."""
    financial = verified_data.get("financial", {})
    trend_field = financial.get("trend_financiar", {})
    trend_val = trend_field.get("value") if isinstance(trend_field, dict) else None
    if not isinstance(trend_val, dict):
        return ""

    ca_data = trend_val.get("cifra_afaceri_neta", {})
    if not ca_data or not ca_data.get("values") or len(ca_data["values"]) < 2:
        return ""

    labels = json_lib.dumps([str(v["year"]) for v in ca_data["values"]])
    values = json_lib.dumps([v["value"] for v in ca_data["values"]])
    growth = ca_data.get("growth_percent")
    growth_str = f' (<span style="color:{("#22c55e" if growth > 0 else "#ef4444")}">{("+" if growth > 0 else "")}{growth:.1f}%</span>)' if growth is not None else ""

    return f'''
    <section id="sparkline" class="report-section">
        <h2>Trend Cifra de Afaceri{growth_str}</h2>
        <div style="background:#16213e;border-radius:12px;padding:16px;max-width:450px">
            <canvas id="sparkCA" height="100"></canvas>
            <script>
            new Chart(document.getElementById('sparkCA'),{{
                type:'line',
                data:{{labels:{labels},datasets:[{{data:{values},
                    borderColor:'#6366f1',backgroundColor:'#6366f120',fill:true,tension:0.3,pointRadius:3,pointBackgroundColor:'#a5b4fc'}}]}},
                options:{{responsive:true,plugins:{{legend:{{display:false}}}},
                    scales:{{y:{{ticks:{{color:'#94a3b8'}},grid:{{color:'#2a3a5c'}}}},x:{{ticks:{{color:'#94a3b8'}},grid:{{display:false}}}}}}}}
            }});
            </script>
        </div>
    </section>'''


def _build_executive_summary(verified_data: dict, meta: dict) -> str:
    """N3: Executive Summary — 3 lines with key KPIs at the top of the report."""
    company = verified_data.get("company", {})
    financial = verified_data.get("financial", {})
    risk_score = verified_data.get("risk_score", {})

    def _fv(f):
        return f.get("value") if isinstance(f, dict) else None

    name = _fv(company.get("denumire", {})) or meta.get("company_name", "N/A")
    cui = _fv(company.get("cui", {})) or ""
    caen = _fv(company.get("caen_code", {})) or ""
    caen_desc = _fv(company.get("caen_description", {})) or ""

    ca = _fv(financial.get("cifra_afaceri", {}))
    profit = _fv(financial.get("profit_net", {}))
    angajati = _fv(financial.get("numar_angajati", {}))
    score = risk_score.get("numeric_score")
    color = risk_score.get("score", "N/A")

    # Format CA
    ca_str = "N/A"
    if isinstance(ca, (int, float)):
        if ca >= 1_000_000:
            ca_str = f"{ca/1_000_000:.2f}M RON"
        elif ca >= 1_000:
            ca_str = f"{ca/1_000:.0f}K RON"
        else:
            ca_str = f"{ca:,.0f} RON"

    profit_str = ""
    if isinstance(profit, (int, float)):
        sign = "+" if profit >= 0 else ""
        if abs(profit) >= 1_000_000:
            profit_str = f" | Profit: {sign}{profit/1_000_000:.2f}M RON"
        else:
            profit_str = f" | Profit: {sign}{profit:,.0f} RON"

    ang_str = f" | {int(angajati)} angajati" if isinstance(angajati, (int, float)) and angajati > 0 else ""
    caen_str = f" | CAEN {caen}" if caen else ""
    if caen_desc:
        caen_str += f" ({_escape(caen_desc[:50])})"

    score_color = {"Verde": "#22c55e", "Galben": "#eab308", "Rosu": "#ef4444"}.get(color, "#888")
    score_str = f'<span style="color:{score_color};font-weight:700">{score}/100 ({color})</span>' if score else "N/A"

    # Key risk factor — CRITICAL must outrank HIGH (scoring.py emits both; a factor's
    # severity, not its position in the list, decides which one leads the summary).
    factors = risk_score.get("factors", [])
    _KEY_RISK_RANK = {"CRITICAL": 0, "HIGH": 1}
    key_risks = sorted(
        (f for f in factors if isinstance(f, (list, tuple)) and len(f) >= 2 and f[1] in _KEY_RISK_RANK),
        key=lambda f: _KEY_RISK_RANK[f[1]],
    )
    risk_line = ""
    if key_risks:
        risk_line = f'<div style="color:#ef4444;font-size:0.85em;margin-top:4px">Risc principal: {_escape(key_risks[0][0])}</div>'

    return f'''
    <div class="exec-summary">
        <div style="font-size:0.75em;color:#6366f1;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px">Executive Summary</div>
        <div style="font-size:1.05em;color:#e2e8f0"><strong>{_escape(str(name))}</strong> (CUI: {_escape(str(cui))}){caen_str}</div>
        <div style="font-size:0.95em;color:#cbd5e1;margin-top:4px">CA: <strong>{ca_str}</strong>{profit_str}{ang_str}</div>
        <div style="font-size:0.95em;margin-top:4px">Scor Risc: {score_str}</div>
        {risk_line}
    </div>'''


def _build_key_takeaways_html(verified_data: dict) -> str:
    """2026-07-16 ("RIS colecteaza > afiseaza"): verified["key_takeaways"] --
    3 bullet-uri de calitate generate real de agent_synthesis -- randate NICAIERI
    in cele 8 formate (grep in backend/reports/ = 0 potriviri inainte de acest fix).
    Placed right after the Executive Summary, the most natural pairing (both are
    "read this first" summaries)."""
    model = build_rich_fields_model(verified_data)
    if not model["key_takeaways"]["shown"]:
        return ""
    items = "".join(f'<li style="color:#cbd5e1;margin-bottom:6px">{_escape(t)}</li>' for t in model["key_takeaways"]["items"])
    return f'''
    <section id="key-takeaways" class="report-section" style="padding-top:24px">
        <h2>Puncte Cheie</h2>
        <ul class="list-disc ml-6" style="margin-top:8px">{items}</ul>
    </section>'''


def _build_financial_ratios_html(risk_score: dict) -> str:
    """N1: Financial ratios table from calculated data."""
    ratios = risk_score.get("financial_ratios", [])
    if not ratios:
        return ""

    rows = ""
    for r in ratios:
        val = r.get("value", 0)
        unit = r.get("unit", "")
        interp = r.get("interpretation", "")
        interp_color = "#22c55e" if interp in ("Excelent", "Solid", "Conservator") else "#eab308" if interp in ("Bun", "Moderat") else "#ef4444" if interp in ("Pierdere", "Negativ", "Periculos", "Subcapitalizat") else "#94a3b8"

        if unit == "RON":
            val_str = f"{val:,.0f} {unit}"
        else:
            val_str = f"{val}{unit}"

        rows += f'''<tr>
            <td style="padding:8px 12px;color:#e2e8f0;font-weight:500">{_escape(r.get("name", ""))}</td>
            <td style="padding:8px 12px;color:#a5b4fc;font-weight:700;text-align:right">{val_str}</td>
            <td style="padding:8px 12px;color:{interp_color};text-align:center">{_escape(interp)}</td>
        </tr>'''

    return f'''
    <section id="ratios" class="report-section">
        <h2>Indicatori Financiari</h2>
        <table style="width:100%;border-collapse:collapse;margin-top:12px">
            <thead><tr style="border-bottom:2px solid #2a3a5c">
                <th style="padding:8px 12px;text-align:left;color:#94a3b8;font-size:0.85em">Indicator</th>
                <th style="padding:8px 12px;text-align:right;color:#94a3b8;font-size:0.85em">Valoare</th>
                <th style="padding:8px 12px;text-align:center;color:#94a3b8;font-size:0.85em">Interpretare</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </section>'''


def _build_alarm_warnings_html(verified_data: dict) -> str:
    """D11 follow-up (2026-07-16): verified_data["early_warnings"] (real business
    signals from agent_verification._detect_early_warnings -- e.g. "Scadere CA > 30%",
    "Pierdere consecutiva 2+ ani") was NEVER read anywhere in html_generator.py (grep
    = 0 hits). PDF/DOCX already render this exact key under the title "Semnale de
    Alarma". HTML only had risk_score["early_warning_confidence"] (a DIFFERENT list --
    anomaly flags + a 0-100 confidence score) under the near-identical title "Semnale
    de Avertizare" -- a reader could not tell the two apart, and the real business
    signals were simply absent. Real data verified (job 85ec7fff, TAROM CUI 477647):
    "Scadere CA" and "Pierdere consecutiva" appear in raport.pdf/.docx, 0 hits in
    raport.html before this fix."""
    ew = verified_data.get("early_warnings", [])
    if not isinstance(ew, list) or not ew:
        return ""
    items_html = ""
    for w in ew[:10]:
        if isinstance(w, dict):
            signal = _escape(str(w.get("signal", w.get("message", "N/A"))))
            severity = str(w.get("severity", "MEDIUM"))
            detail = w.get("detail", "")
            sev_color = "#ef4444" if severity == "HIGH" else "#eab308" if severity == "MEDIUM" else "#94a3b8"
            detail_html = f'<div style="color:#94a3b8;font-size:0.85em;margin-top:4px">{_escape(str(detail))}</div>' if detail else ""
            items_html += (
                f'<div style="padding:10px 14px;margin-bottom:8px;background:#16213e;border-radius:8px;'
                f'border-left:4px solid {sev_color}">'
                f'<span style="color:{sev_color};font-weight:700">[{_escape(severity)}] {signal}</span>'
                f'{detail_html}'
                f'</div>\n'
            )
        elif isinstance(w, str):
            items_html += f'<div style="color:#eab308;padding:6px 0">- {_escape(w)}</div>\n'
    return f'''
    <section id="alarm-warnings" class="report-section">
        <h2>Semnale de Alarma</h2>
        <p style="color:#64748b;font-size:.82em;font-style:italic;margin-top:-8px">Semnale de business directe (scadere CA, pierderi consecutive) — a nu se confunda cu "Semnale de Avertizare" de mai jos (anomalii + scor de incredere).</p>
        <div style="margin-top:12px">{items_html}</div>
    </section>'''


def _build_company_network_html(verified_data: dict) -> str:
    """F1-6: Sectiunea 'Reteaua de Firme' — persoane comune, firme conexe, risk flags."""
    network = verified_data.get("company_network", {})
    if not network:
        return ""

    # network_client.get_company_network() (backend/agents/tools/network_client.py)
    # returneaza total_persons/total_firms sub forma len(persons) / "total_connected"
    # TOP-LEVEL, niciodata sub "stats" (care contine doar inactive/unknown_status/
    # active/depth_1/depth_2_plus) -- gate-ul citea chei care nu au existat
    # NICIODATA, deci sectiunea afisa mereu "Date retea indisponibile", chiar
    # cu has_data=True si date reale.
    stats = network.get("stats", {})
    persons = network.get("persons", [])
    total_persons = len(persons)
    total_firms = network.get("total_connected", 0)
    inactive_firms = stats.get("inactive", 0)

    if total_persons == 0 and total_firms == 0:
        return '''
    <section id="network" class="report-section">
        <h2>Reteaua de Firme</h2>
        <div style="color:#64748b;font-style:italic;padding:16px 0">Date retea indisponibile</div>
    </section>'''

    # ── Risk flags badges ─────────────────────────────────────────────────────
    # network_client emite risk_flags ca LISTA DE DICT-uri {type, severity, detail}
    # -- niciodata liste de string-uri. FLAG_COLORS.get(flag, ...) cu flag=dict
    # arunca TypeError (unhashable) inainte de acest fix.
    risk_flags = network.get("risk_flags", [])
    flags_html = ""
    FLAG_COLORS = {
        "ASOCIAT_FIRMA_INACTIVA": ("#ef4444", "#ef444420"),   # ROSU
        "RETEA_EXTINSA": ("#eab308", "#eab30820"),             # GALBEN
        "TOXIC_NETWORK": ("#ef4444", "#ef444420"),             # ROSU
        "CONFLICT_INTERESE": ("#f97316", "#f9731620"),         # PORTOCALIU
    }
    for flag in risk_flags:
        flag_type = flag.get("type", "") if isinstance(flag, dict) else str(flag)
        flag_detail = flag.get("detail") if isinstance(flag, dict) else None
        fg, bg = FLAG_COLORS.get(flag_type, ("#94a3b8", "#94a3b820"))
        label = _escape(flag_detail or flag_type)
        flags_html += (
            f'<span style="display:inline-block;padding:3px 10px;border-radius:12px;'
            f'font-size:0.78em;font-weight:700;background:{bg};color:{fg};'
            f'border:1px solid {fg}40;margin:2px 4px 2px 0" title="{_escape(flag_type)}">{label}</span>'
        )

    # ── Stats summary ─────────────────────────────────────────────────────────
    stats_html = (
        f'<div style="display:flex;gap:24px;flex-wrap:wrap;margin:16px 0">'
        f'<div style="background:#16213e;border-radius:8px;padding:12px 20px;text-align:center">'
        f'<div style="font-size:1.5em;font-weight:700;color:#a5b4fc">{total_firms}</div>'
        f'<div style="font-size:0.78em;color:#64748b;margin-top:2px">Firme conexe</div></div>'
        f'<div style="background:#16213e;border-radius:8px;padding:12px 20px;text-align:center">'
        f'<div style="font-size:1.5em;font-weight:700;color:{"#ef4444" if inactive_firms > 0 else "#22c55e"}">{inactive_firms}</div>'
        f'<div style="font-size:0.78em;color:#64748b;margin-top:2px">Firme inactive</div></div>'
        f'<div style="background:#16213e;border-radius:8px;padding:12px 20px;text-align:center">'
        f'<div style="font-size:1.5em;font-weight:700;color:#a5b4fc">{total_persons}</div>'
        f'<div style="font-size:0.78em;color:#64748b;margin-top:2px">Persoane comune</div></div>'
        f'</div>'
    )

    # ── Tabel persoane comune ─────────────────────────────────────────────────
    persons_html = ""
    if persons:
        rows = ""
        for p in persons:
            name = _escape(str(p.get("name") or p.get("nume") or "N/A"))
            role = _escape(str(p.get("role") or p.get("rol") or "—"))
            ownership = p.get("ownership_pct") if p.get("ownership_pct") is not None else (
                p.get("ownership") or p.get("ownership_percent") or p.get("cota_participare"))
            own_str = f"{ownership}%" if ownership is not None else "—"
            rows += (
                f'<tr>'
                f'<td style="padding:8px 12px;color:#e2e8f0;font-weight:500">{name}</td>'
                f'<td style="padding:8px 12px;color:#94a3b8">{role}</td>'
                f'<td style="padding:8px 12px;color:#a5b4fc;text-align:right">{own_str}</td>'
                f'</tr>'
            )
        persons_html = f'''
        <h3 style="color:#818cf8;margin:20px 0 10px;font-size:1em">Persoane cu functii in mai multe firme</h3>
        <table style="width:100%;border-collapse:collapse;font-size:0.9em">
            <thead><tr style="border-bottom:2px solid #2a3a5c">
                <th style="padding:8px 12px;text-align:left;color:#94a3b8;font-size:0.85em">Nume</th>
                <th style="padding:8px 12px;text-align:left;color:#94a3b8;font-size:0.85em">Rol</th>
                <th style="padding:8px 12px;text-align:right;color:#94a3b8;font-size:0.85em">Participare</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>'''

    # ── Tabel firme conexe ────────────────────────────────────────────────────
    # network_client pune lista sub cheia "related_companies" (nu "related_firms"),
    # cu campurile "company_name" (nu "denumire"/"name") si "is_active" int 0/1/None
    # (nu "activ"/"status_activ") -- niciun camp nu se potrivea, tabelul era mereu gol.
    related_firms = network.get("related_companies", [])
    firms_html = ""
    if related_firms:
        rows = ""
        for f in related_firms:
            den = _escape(str(f.get("company_name") or "N/A"))
            cui_val = _escape(str(f.get("cui") or "—"))
            is_active = f.get("is_active")
            if is_active == 0:
                status_badge = '<span style="color:#ef4444;font-weight:700">INACTIV</span>'
            elif is_active is None:
                status_badge = '<span style="color:#64748b">N/A</span>'
            else:
                status_badge = '<span style="color:#22c55e;font-weight:700">ACTIV</span>'
            depth = f.get("depth", 1)
            depth_str = "Directa" if depth == 1 else f"Extinsa (nivel {depth})"
            rows += (
                f'<tr>'
                f'<td style="padding:8px 12px;color:#e2e8f0;font-weight:500">{den}</td>'
                f'<td style="padding:8px 12px;color:#94a3b8;font-size:0.85em">{cui_val}</td>'
                f'<td style="padding:8px 12px;text-align:center">{status_badge}</td>'
                f'<td style="padding:8px 12px;color:#a5b4fc;text-align:right">{_escape(depth_str)}</td>'
                f'</tr>'
            )
        firms_html = f'''
        <h3 style="color:#818cf8;margin:20px 0 10px;font-size:1em">Firme conexe prin persoane comune</h3>
        <table style="width:100%;border-collapse:collapse;font-size:0.9em">
            <thead><tr style="border-bottom:2px solid #2a3a5c">
                <th style="padding:8px 12px;text-align:left;color:#94a3b8;font-size:0.85em">Denumire</th>
                <th style="padding:8px 12px;text-align:left;color:#94a3b8;font-size:0.85em">CUI</th>
                <th style="padding:8px 12px;text-align:center;color:#94a3b8;font-size:0.85em">Status</th>
                <th style="padding:8px 12px;text-align:right;color:#94a3b8;font-size:0.85em">Legatura</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>'''

    return f'''
    <section id="network" class="report-section">
        <h2>Reteaua de Firme</h2>
        {f'<div style="margin-bottom:12px">{flags_html}</div>' if flags_html else ''}
        {stats_html}
        {persons_html}
        {firms_html}
    </section>'''


def _fmt_num(v) -> str:
    """Format a numeric value with thousands separators; passthrough otherwise."""
    if isinstance(v, int | float):
        return f"{v:,.0f}"
    return str(v) if v is not None else "—"


def _fmt_ratio(v) -> str:
    """Format pastrand 1 zecimala pt valori ne-intregi (indicatori tip rata: angajati/firma etc.)."""
    if isinstance(v, int | float):
        return f"{v:,.0f}" if float(v).is_integer() else f"{v:,.1f}"
    return str(v) if v is not None else "—"


def _build_rich_fields_html(verified_data: dict) -> tuple[str, str]:
    """Surface rich verification fields previously dropped from reports:
    predictive_scores, benchmark, actionariat + relations, aegrm_guarantees,
    historical_flags, funding_programs. Returns (sections_html, nav_links_html)."""
    out: list[str] = []
    nav = ""
    model = build_rich_fields_model(verified_data)

    # ---- A6: verificare Tavily NEFACUTA (cota epuizata) — mesaj onest, nu tacere ----
    if model["tavily_quota_exhausted"]["shown"]:
        out.append(f'''
    <section id="tavily-quota" class="report-section" style="border-left:3px solid #eab308">
        <h2 style="color:#eab308">Verificare Incompleta — Cota Tavily Epuizata</h2>
        <p style="color:#fde68a">{_escape(model["tavily_quota_exhausted"]["message"])}</p>
    </section>''')
        nav += '<a href="#tavily-quota" class="nav-link">Verificare Incompleta</a>\n'

    # ---- Scoruri predictive faliment ----
    pred = model["predictive_scores"]["data"]
    if model["predictive_scores"]["shown"]:
        def _badge(label, value, tone):
            colors = {"ok": "#22c55e", "warn": "#eab308", "bad": "#ef4444", "na": "#64748b"}
            c = colors.get(tone, "#64748b")
            return (f'<div style="background:#16213e;border-radius:8px;padding:12px 16px;border-left:3px solid {c}">'
                    f'<div style="font-size:0.72em;color:#64748b;text-transform:uppercase;letter-spacing:1px">{_escape(label)}</div>'
                    f'<div style="font-size:1.02em;color:{c};font-weight:700;margin-top:3px">{_escape(value)}</div></div>')
        altman = pred.get("altman_z", {}) or {}
        piotroski = pred.get("piotroski_f", {}) or {}
        beneish = pred.get("beneish_m", {}) or {}
        zmijewski = pred.get("zmijewski_x", {}) or {}
        cards = []
        z_zone = altman.get("zone", "INDISPONIBIL")
        z_val = f"{altman.get('z_score')} ({z_zone})" if altman.get("z_score") is not None else "Indisponibil"
        cards.append(_badge("Altman Z''", z_val, {"SAFE": "ok", "GREY": "warn", "DISTRESS": "bad"}.get(z_zone, "na")))
        f_grade = piotroski.get("grade", "INSUFICIENT")
        f_val = f"{piotroski.get('f_score')}/{piotroski.get('max_possible', 9)} ({f_grade})" if piotroski.get("f_score") is not None else "Insuficient"
        cards.append(_badge("Piotroski F", f_val, {"STRONG": "ok", "AVERAGE": "warn", "WEAK": "bad"}.get(f_grade, "na")))
        m_risk = beneish.get("risk", "INDISPONIBIL")
        m_val = f"{beneish.get('m_score')} ({m_risk})" if beneish.get("m_score") is not None else "Indisponibil"
        cards.append(_badge("Beneish M", m_val, {"OK": "ok", "INVESTIGAT": "warn", "MANIPULATOR_PROBABIL": "bad"}.get(m_risk, "na")))
        z_av = zmijewski.get("available")
        x_val = f"{zmijewski.get('x_score')} ({'Distres' if zmijewski.get('distress') else 'OK'})" if z_av else "Indisponibil"
        cards.append(_badge("Zmijewski X", x_val, "bad" if zmijewski.get("distress") else ("ok" if z_av else "na")))
        signals = pred.get("distress_signals", 0)
        sig_color = "#ef4444" if signals >= 3 else "#eab308" if signals >= 1 else "#22c55e"
        # A4: divergenta FAPTICA fata de scorul 6D — un fapt raportat, nu un verdict nou.
        divergences = model["predictive_scores"]["divergences"]
        div_html = ""
        if divergences:
            items = "".join(f'<li style="color:#fca5a5;margin-top:4px">{_escape(d["text"])}</li>' for d in divergences)
            div_html = (
                '<div style="margin-top:14px;padding:10px 14px;background:#1f1520;border-left:3px solid #ef4444;border-radius:6px">'
                '<p style="color:#ef4444;font-weight:600;margin:0">Dezacord intre scorul 6D si modelele predictive</p>'
                f'<ul style="margin:6px 0 0 18px;padding:0">{items}</ul></div>'
            )
        out.append(f'''
    <section id="predictive" class="report-section">
        <h2>Scoruri Predictive Faliment</h2>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-top:8px">{"".join(cards)}</div>
        <p style="margin-top:14px;color:{sig_color};font-weight:600">{_escape(str(pred.get("summary", "")))} ({signals} semnale de distres)</p>
        {div_html}
        <p style="color:#64748b;font-size:0.78em;margin-top:6px;font-style:italic">Modele statistice orientative — praguri calibrate international, interpretare cu prudenta pentru piata RO.</p>
    </section>''')
        nav += '<a href="#predictive" class="nav-link">Scoruri Predictive</a>\n'

    # ---- Benchmark sector CAEN ----
    bench = model["benchmark"]["data"]
    if model["benchmark"]["shown"]:
        rows = ""
        for c in bench["comparisons"]:
            rows += (f'<tr><td style="padding:8px 12px;color:#e2e8f0">{_escape(str(c.get("metric", "")))}</td>'
                     f'<td style="padding:8px 12px;text-align:right;color:#a5b4fc">{_escape(_fmt_num(c.get("firma")))}</td>'
                     f'<td style="padding:8px 12px;text-align:right;color:#94a3b8">{_escape(_fmt_num(c.get("media_sector")))}</td>'
                     f'<td style="padding:8px 12px;text-align:center;color:#cbd5e1">{_escape(str(c.get("pozitie", "")))}</td></tr>')
        section_name = bench.get("caen_section_name", "") or ""
        meta_line = f'<p style="color:#94a3b8;font-size:0.9em">{_escape(section_name)} — {bench.get("nr_firme_sector") or "?"} firme in sector</p>' if section_name else ""
        out.append(f'''
    <section id="benchmark" class="report-section">
        <h2>Benchmark Sector CAEN {_escape(str(bench.get("caen_code", "")))}</h2>
        {meta_line}
        <table class="ris-table" style="margin-top:12px"><thead><tr><th>Indicator</th><th style="text-align:right">Firma</th><th style="text-align:right">Media sector</th><th style="text-align:center">Pozitie</th></tr></thead><tbody>{rows}</tbody></table>
    </section>''')
        nav += '<a href="#benchmark" class="nav-link">Benchmark</a>\n'

    # ---- Pozitie in Sector (bucket categorial, derivat din benchmark.comparisons) ----
    # 2026-07-16: risk_score["sector_position"] -- dict per-metrica {ratio_vs_avg,
    # estimated_percentile}. estimated_percentile e un BUCKET ("P90+".."sub P25"),
    # NU un procentil numeric exact -- randat ca eticheta, nu ca bara/procent fals
    # (greseala deja facuta si reparata in frontend pe 07-15 -- nu se repeta aici).
    sector_position = model["sector_position"]["data"]
    if model["sector_position"]["shown"]:
        SP_COLORS = {"P90+": "#22c55e", "P75-P90": "#22c55e", "P50-P75": "#94a3b8",
                     "P25-P50": "#eab308", "sub P25": "#ef4444"}
        sp_rows = ""
        for metric, info in sector_position.items():
            if not isinstance(info, dict):
                continue
            pct = str(info.get("estimated_percentile", ""))
            ratio = info.get("ratio_vs_avg")
            sp_color = SP_COLORS.get(pct, "#94a3b8")
            ratio_str = f"{_fmt_ratio(ratio)}x media" if ratio is not None else "&mdash;"
            sp_rows += (f'<tr><td style="padding:6px 12px;color:#e2e8f0">{_escape(str(metric))}</td>'
                        f'<td style="padding:6px 12px;text-align:right;color:#94a3b8">{ratio_str}</td>'
                        f'<td style="padding:6px 12px;text-align:center;color:{sp_color};font-weight:700">{_escape(pct)}</td></tr>')
        out.append(f'''
    <section id="sector-position" class="report-section">
        <h2>Pozitie in Sector</h2>
        <table class="ris-table" style="margin-top:8px"><thead><tr><th>Indicator</th><th style="text-align:right">Raport vs medie</th><th style="text-align:center">Pozitie estimata</th></tr></thead><tbody>{sp_rows}</tbody></table>
        <p style="color:#64748b;font-size:.78em;margin-top:6px;font-style:italic">Pozitie estimata pe baza raportului fata de media sectorului — bucket orientativ, nu un percentil statistic exact.</p>
    </section>''')
        nav += '<a href="#sector-position" class="nav-link">Pozitie Sector</a>\n'

    # ---- Benchmark sector UE (Eurostat) ----
    eust = model["eurostat_sector"]["data"]
    if model["eurostat_sector"]["shown"]:
        rows = ""
        for ind in eust["indicators"].values():
            if not isinstance(ind, dict):
                continue
            ro = ind.get("ro")
            eu = ind.get("eu")
            rows += (f'<tr><td style="padding:4px 10px;color:#cbd5e1">{_escape(str(ind.get("label", "")))}</td>'
                     f'<td style="padding:4px 10px;color:#e2e8f0;text-align:right">{_escape(_fmt_ratio(ro)) if ro is not None else "&mdash;"}</td>'
                     f'<td style="padding:4px 10px;color:#e2e8f0;text-align:right">{_escape(_fmt_ratio(eu)) if eu is not None else "&mdash;"}</td></tr>')
        out.append(f'''
    <section id="eurostat" class="report-section">
        <h2>Benchmark Sector UE (Eurostat)</h2>
        <p style="color:#94a3b8;font-size:.9em">Sector NACE {_escape(str(eust.get("nace_used", "")))} &middot; {_escape(str(eust.get("nace_label", "")))} &middot; an {_escape(str(eust.get("year", "")))}</p>
        <table style="border-collapse:collapse;margin-top:8px"><thead><tr>
            <th style="padding:4px 10px;text-align:left;color:#818cf8">Indicator</th>
            <th style="padding:4px 10px;text-align:right;color:#818cf8">Romania</th>
            <th style="padding:4px 10px;text-align:right;color:#818cf8">UE27</th>
        </tr></thead><tbody>{rows}</tbody></table>
        <p style="color:#64748b;font-size:.8em;margin-top:6px">Sursa: Eurostat (Structural Business Statistics).</p>
    </section>''')
        nav += '<a href="#eurostat" class="nav-link">Benchmark UE</a>\n'

    # ---- Istoric Achizitii Publice (SICAP/SEAP) ----
    seap = model["seap"]["data"]
    if model["seap"]["shown"]:
        tot = seap.get("total_contracts", 0)
        cc = seap.get("contracts_count", 0) or len(seap.get("contracts", []) or [])
        dc = seap.get("direct_count", 0) or len(seap.get("direct_acquisitions", []) or [])
        tval = seap.get("total_value")
        body = (f'<p style="color:#22c55e;font-weight:600">{tot} contracte publice castigate '
                f'({cc} licitatii + {dc} achizitii directe)'
                f'{f" &middot; valoare totala ~{_escape(_fmt_num(tval))} RON" if tval else ""}</p>')

        def _seap_rows(items):
            rows_html = ""
            for it in [i for i in (items or []) if isinstance(i, dict)][:8]:
                title = _escape(str(it.get("title", ""))[:120]) or "(fara titlu)"
                auth = _escape(str(it.get("authority", "")))
                val = it.get("value")
                cur = _escape(str(it.get("currency", "RON")))
                date = _escape(str(it.get("date", ""))[:10])
                val_s = f"{_escape(_fmt_num(val))} {cur}" if isinstance(val, (int, float)) else ""
                rows_html += (f'<li style="color:#cbd5e1"><strong>{title}</strong>'
                              f'{f" &mdash; {auth}" if auth else ""}'
                              f'{f" &middot; {val_s}" if val_s else ""}'
                              f'{f" &middot; {date}" if date else ""}</li>')
            return rows_html

        cw = _seap_rows(seap.get("contracts"))
        dw = _seap_rows(seap.get("direct_acquisitions"))
        if cw:
            body += ('<h3 style="color:#818cf8;margin:14px 0 6px;font-size:1em">Licitatii castigate</h3>'
                     f'<ul class="list-disc ml-6">{cw}</ul>')
        if dw:
            body += ('<h3 style="color:#818cf8;margin:14px 0 6px;font-size:1em">Achizitii directe</h3>'
                     f'<ul class="list-disc ml-6">{dw}</ul>')
        out.append(f'''
    <section id="achizitii" class="report-section">
        <h2>Istoric Achizitii Publice (SICAP)</h2>
        {body}
    </section>''')
        nav += '<a href="#achizitii" class="nav-link">Achizitii Publice</a>\n'

    # ---- Oportunitati de contracte: licitatii deschise (SICAP, Angle A) ----
    opp = model["tender_opportunities"]["data"]
    if model["tender_opportunities"]["shown"]:
        items = [i for i in (opp.get("opportunities") or []) if isinstance(i, dict)][:15]
        real_basis = opp.get("basis") == "istoric_real"
        rows = ""
        for it in items:
            title = _escape(str(it.get("title", ""))[:120]) or "(fara titlu)"
            auth = _escape(str(it.get("authority", "")))
            cpv = _escape(str(it.get("cpv", "")))
            val = it.get("value")
            deadline = _escape(str(it.get("deadline", ""))[:10])
            val_s = f"{_escape(_fmt_num(val))} RON" if isinstance(val, (int, float)) else ""
            mark = '<span style="color:#22c55e" title="competenta dovedita">&#10004;</span> ' if it.get("precise") else ""
            rows += (f'<li style="color:#cbd5e1">{mark}<strong>{title}</strong>'
                     f'{f" &mdash; {auth}" if auth else ""}'
                     f'{f" <span style=\"color:#94a3b8\">[CPV {cpv}]</span>" if cpv else ""}'
                     f'{f" &middot; {val_s}" if val_s else ""}'
                     f'{f" &middot; termen {deadline}" if deadline else ""}</li>')
        subtitle = "pe baza contractelor castigate + sector" if real_basis else "pe sectorul firmei (orientativ)"
        footer = ("Pe baza CPV-urilor reale castigate de firma + sector. &#10004; = competenta dovedita. Sursa: SICAP."
                  if real_basis else
                  "Orientativ — mapare CAEN&rarr;CPV la nivel de diviziune. Sursa: SICAP (e-licitatie.ro).")
        out.append(f'''
    <section id="oportunitati" class="report-section">
        <h2>Oportunitati de Contracte (SICAP)</h2>
        <p style="color:#94a3b8;font-size:.9em">{opp.get("count", 0)} licitatii deschise {subtitle} (ultimele {opp.get("days_back", 30)} zile)</p>
        <ul class="list-disc ml-6">{rows}</ul>
        <p style="color:#64748b;font-size:.8em;margin-top:6px">{footer}</p>
    </section>''')
        nav += '<a href="#oportunitati" class="nav-link">Oportunitati</a>\n'

    # ---- Actionariat + relatii ----
    act = model["actionariat"]["act"]
    act_ok = model["actionariat"]["act_ok"]
    rel_flags = model["actionariat"]["rel_flags"]
    if model["actionariat"]["shown"]:
        body = ""

        def _names(items):
            res = []
            for it in items or []:
                if isinstance(it, dict):
                    res.append(str(it.get("nume") or it.get("name") or it.get("denumire") or it))
                else:
                    res.append(str(it))
            return res
        if act_ok:
            cap = act.get("capital_social")
            stare = act.get("stare", "")
            if cap or stare:
                body += f'<p style="color:#cbd5e1">Capital social: <strong>{_escape(_fmt_num(cap))}</strong>{f" | Stare: {_escape(str(stare))}" if stare else ""}</p>'
            for label, items in (("Asociati", act.get("asociati")), ("Administratori", act.get("administratori"))):
                names = _names(items)
                if names:
                    body += f'<h3 style="color:#818cf8;margin:14px 0 6px;font-size:1em">{label}</h3><ul class="list-disc ml-6">'
                    body += "".join(f'<li style="color:#cbd5e1">{_escape(n)}</li>' for n in names)
                    body += "</ul>"
        for fl in rel_flags:
            sev = str(fl.get("severity", "INFO")).upper()
            c = {"RED": "#ef4444", "YELLOW": "#eab308"}.get(sev, "#6366f1")
            body += (f'<div style="padding:8px 12px;margin-top:8px;background:#16213e;border-radius:6px;border-left:3px solid {c}">'
                     f'<span style="color:{c};font-weight:600">{_escape(str(fl.get("type", "")))}</span> '
                     f'<span style="color:#cbd5e1">— {_escape(str(fl.get("detail", "")))}</span></div>')
        if body:
            out.append(f'''
    <section id="actionariat" class="report-section">
        <h2>Actionariat &amp; Relatii</h2>
        {body}
    </section>''')
            nav += '<a href="#actionariat" class="nav-link">Actionariat</a>\n'

    # ---- Screening sanctiuni (OFAC + UE FSF + ONU) ----
    sanc = model["sanctions"]["data"]
    if model["sanctions"]["shown"]:
        status = sanc.get("status")
        lists = ", ".join(sanc.get("lists_checked", []) or []) or "—"
        n_checked = len(sanc.get("checked", []) or [])
        ddate = str(sanc.get("data_date", ""))[:10]
        body = ""
        if status == "hit":
            hits = sanc.get("hits") or []
            body += (f'<p style="color:#ef4444;font-weight:700">&#9888; {len(hits)} potentiale potriviri pe '
                     'listele de sanctiuni — verificare manuala necesara</p><ul class="list-disc ml-6">')
            for h in hits[:20]:
                body += (f'<li style="color:#cbd5e1"><strong>{_escape(str(h.get("query", "")))}</strong> &asymp; '
                         f'{_escape(str(h.get("matched_name", "")))} '
                         f'<span style="color:#94a3b8">[{_escape(str(h.get("source", "")))}, '
                         f'{_escape(str(h.get("type", "")))}]</span></li>')
            body += "</ul>"
        elif status == "clean":
            body += (f'<p style="color:#22c55e;font-weight:600">&#10004; Screening sanctiuni: CURAT — '
                     f'{n_checked} nume verificate, 0 potriviri</p>')
        else:
            body += ('<p style="color:#94a3b8">Screening sanctiuni: indisponibil '
                     '(liste temporar inaccesibile)</p>')
        if status in ("clean", "hit") and not sanc.get("complete", True):
            missing = ", ".join(sanc.get("lists_missing", []) or [])
            n_lists = len(sanc.get("lists_checked", []) or [])
            body += (f'<p style="color:#eab308;font-size:.85em">&#9888; Screening partial: {n_lists}/3 surse'
                     f'{f" ({_escape(missing)} indisponibile)" if missing else ""} — verdict neautoritar, verificati ulterior.</p>')
        body += (f'<p style="color:#64748b;font-size:.85em;margin-top:6px">Liste oficiale: {_escape(lists)}'
                 f'{f" &middot; actualizat {_escape(ddate)}" if ddate else ""}. '
                 'Nu include PEP (persoane expuse politic).</p>')
        out.append(f'''
    <section id="sanctions" class="report-section">
        <h2>Screening Sanctiuni</h2>
        {body}
    </section>''')
        nav += '<a href="#sanctions" class="nav-link">Sanctiuni</a>\n'

    # ---- AEGRM garantii + semnale istorice OSINT ----
    aegrm = model["garantii"]["aegrm"]
    aegrm_ok = model["garantii"]["aegrm_ok"]
    if model["garantii"]["shown"]:
        body = ""
        if aegrm_ok:
            cnt = aegrm.get("count", 0)
            gc = "#eab308" if aegrm.get("has_guarantees") else "#22c55e"
            body += f'<p style="color:{gc};font-weight:600">Garantii reale mobiliare (AEGRM): {cnt}</p>'
            guarantees = model["garantii"]["guarantees"]
            if guarantees:
                body += '<ul class="list-disc ml-6">'
                for g in guarantees[:8]:
                    txt = f"{g['creditor']} — {g['tip_bun']} (status: {g['status']}, data: {g['data']})"
                    body += f'<li style="color:#cbd5e1">{_escape(txt[:200])}</li>'
                body += "</ul>"
        if model["garantii"]["hist_ok"]:
            body += '<h3 style="color:#818cf8;margin:14px 0 6px;font-size:1em">Semnale istorice (Monitorul Oficial)</h3>'
            for flx in model["garantii"]["historical_flags"]:
                if flx["is_dict"]:
                    sev = flx["severity"]
                    c = {"RED": "#ef4444", "YELLOW": "#eab308", "HIGH": "#ef4444", "MEDIUM": "#eab308"}.get(sev, "#6366f1")
                    label = _escape(flx["label"])
                    detail = _escape(flx["detail"][:240])
                    date_raw = flx["date"]
                    date_html = f'<span style="color:#64748b;font-size:0.8em">{_escape(str(date_raw))}</span> ' if date_raw else ""
                    body += (f'<div style="padding:8px 12px;margin-bottom:6px;background:#16213e;border-radius:6px;border-left:3px solid {c}">'
                             f'<span style="color:{c};font-weight:600">{label}</span> {date_html}'
                             f'<span style="color:#cbd5e1">— {detail}</span></div>')
                else:
                    body += f'<div style="color:#cbd5e1">{_escape(flx["detail"])}</div>'
        if body:
            out.append(f'''
    <section id="garantii" class="report-section">
        <h2>Garantii &amp; Istoric (OSINT)</h2>
        {body}
    </section>''')
            nav += '<a href="#garantii" class="nav-link">Garantii &amp; Istoric</a>\n'

    # ---- Programe de finantare ----
    funding = model["funding_programs"]["data"]
    if model["funding_programs"]["shown"]:
        rows = ""
        for p in funding["eligible"]:
            suma = p.get("suma_max_eur", 0)
            suma_str = f"{suma:,.0f} EUR" if isinstance(suma, int | float) and suma else "—"
            link = str(p.get("link", "") or "")
            nume = _escape(str(p.get("nume", "")))
            nume_html = f'<a href="{_escape(link)}" style="color:#a5b4fc" target="_blank" rel="noopener">{nume}</a>' if link.startswith(("http://", "https://")) else nume
            rows += (f'<tr><td style="padding:8px 12px;color:#e2e8f0">{nume_html}</td>'
                     f'<td style="padding:8px 12px;text-align:right;color:#22c55e;font-weight:600">{suma_str}</td>'
                     f'<td style="padding:8px 12px;color:#94a3b8;font-size:0.85em">{_escape(str(p.get("termen", "") or "—"))}</td></tr>')
        out.append(f'''
    <section id="funding" class="report-section">
        <h2>Programe de Finantare Eligibile</h2>
        <p style="color:#cbd5e1">{_escape(str(funding.get("summary", "")))}</p>
        <table class="ris-table" style="margin-top:12px"><thead><tr><th>Program</th><th style="text-align:right">Suma max</th><th>Termen</th></tr></thead><tbody>{rows}</tbody></table>
        <p style="color:#64748b;font-size:0.78em;margin-top:6px;font-style:italic">Eligibilitate orientativa pe profil (CAEN/angajati/vechime) — verificati conditiile complete la sursa.</p>
    </section>''')
        nav += '<a href="#funding" class="nav-link">Finantare</a>\n'

    # ---- Bonitate & Expunere comerciala recomandata (P1-4) ----
    cred = model["credit_exposure"]["data"]
    if model["credit_exposure"]["shown"]:
        cred_color = "#ef4444" if cred.get("kill_switch") else "#22c55e"
        out.append(f'''
    <section id="bonitate" class="report-section">
        <h2>Bonitate &amp; Expunere Comerciala</h2>
        <p style="font-size:1.4em;font-weight:700;color:{cred_color}">{cred.get("expunere_ron", 0):,.0f} RON</p>
        <p style="color:#94a3b8;font-size:.85em">{_escape(str(cred.get("formula", "")))} &middot; {cred.get("metode_folosite", 0)} metode folosite</p>
        <p style="color:#64748b;font-size:.78em;margin-top:6px;font-style:italic">{_escape(cred.get("disclaimer", ""))}</p>
    </section>''')
        nav += '<a href="#bonitate" class="nav-link">Bonitate</a>\n'

    # ---- Prezenta pe Google Maps ----
    # 2026-07-16: verified["maps_rating"] -- found:False / error e absenta LEGITIMA
    # (firma mica, nu e pe Google Maps), nu se afiseaza "0 stele" -- sectiunea e omisa.
    maps_rating = model["maps_rating"]["data"]
    if model["maps_rating"]["shown"]:
        rating = maps_rating.get("rating") or 0
        full_stars = int(round(rating))
        stars = "★" * min(full_stars, 5) + "☆" * max(0, 5 - full_stars)
        addr = str(maps_rating.get("address", "") or "")
        out.append(f'''
    <section id="maps-rating" class="report-section">
        <h2>Prezenta pe Google Maps</h2>
        <p style="font-size:1.3em;color:#eab308">{stars} <span style="color:#e2e8f0;font-weight:700;font-size:0.8em">{rating}/5</span></p>
        <p style="color:#94a3b8">{maps_rating.get("reviews_count", 0)} recenzii{f" &middot; {_escape(addr)}" if addr else ""}</p>
    </section>''')
        nav += '<a href="#maps-rating" class="nav-link">Google Maps</a>\n'

    # ---- Prezenta Online (OSINT: Brave Search + Jina enrichment) ----
    wi_sent = {"positive": ("Pozitiv", "#22c55e"), "negative": ("Negativ", "#ef4444"), "neutral": ("Neutru", "#94a3b8")}
    if model["web_intelligence"]["shown"]:
        body = ""
        for cat in model["web_intelligence"]["categories"]:
            body += f'<h3 style="color:#818cf8;margin:14px 0 6px;font-size:1em">{_escape(cat["label"])}</h3><ul class="list-disc ml-6">'
            for it in cat["items"][:8]:
                label, color = wi_sent.get(it["sentiment"], (it["sentiment"].capitalize() or "Neutru", "#94a3b8"))
                title_html = _escape(it["title"])
                if it["url"].startswith(("http://", "https://")):
                    title_html = f'<a href="{_escape(it["url"])}" style="color:#a5b4fc" target="_blank" rel="noopener">{title_html}</a>'
                body += (f'<li style="color:#cbd5e1">{title_html} '
                         f'<span style="color:{color};font-size:0.8em">[{_escape(label)}]</span></li>')
            body += "</ul>"
        out.append(f'''
    <section id="web_intelligence" class="report-section">
        <h2>Prezenta Online (OSINT)</h2>
        {body}
        <p style="color:#64748b;font-size:.78em;margin-top:6px;font-style:italic">Rezultate cautare (Brave Search) + enrichment continut (Jina). Sentimentul e metadata estimata automat de la sursa — nu un verdict RIS.</p>
    </section>''')
        nav += '<a href="#web_intelligence" class="nav-link">Prezenta Online</a>\n'

    return "\n".join(out), nav


def generate_html(report_sections: dict, meta: dict, verified_data: dict, output_path: str, lang: str = "ro"):
    """Genereaza HTML single-file din report_sections + verified_data. G5: i18n lang."""
    from backend.reports.i18n import t as _t
    company = _escape(meta.get("company_name", "N/A"))
    title = _escape(meta.get("title", "Raport"))
    generated = _escape(meta.get("generated_at", ""))
    risk = meta.get("risk_score", "N/A")
    numeric = meta.get("numeric_score")
    risk_rec = _escape(meta.get("risk_recommendation", ""))
    level = meta.get("report_level", 2)
    sources = meta.get("sources", [])

    risk_color = {"Verde": "#22c55e", "Galben": "#eab308", "Rosu": "#ef4444"}.get(risk, "#888")

    risk_display = f"{_t('risk_score', lang)}: {risk}"
    if numeric is not None:
        risk_display += f" ({numeric}/100)"

    # N3: Executive Summary
    exec_summary_html = _build_executive_summary(verified_data, meta)

    # 2026-07-16: Puncte Cheie (key_takeaways) — right after Executive Summary
    key_takeaways_html = _build_key_takeaways_html(verified_data)

    # N1: Financial Ratios
    risk_score_obj = verified_data.get("risk_score", {})
    financial_ratios_html = _build_financial_ratios_html(risk_score_obj)

    # E2: Sparkline trend CA (mini line chart)
    sparkline_html = _build_sparkline_html(verified_data)

    # Build sections HTML
    nav_items = '<a href="#ratios" class="nav-link">Indicatori</a>\n<a href="#charts" class="nav-link">Grafice</a>\n'
    if key_takeaways_html:
        nav_items += '<a href="#key-takeaways" class="nav-link">Puncte Cheie</a>\n'
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

    # A3 fix: Due Diligence Checklist section in HTML (was missing — PDF/DOCX/Excel had it, HTML didn't)
    due_diligence_html = ""
    dd_raw = verified_data.get("due_diligence", [])
    if isinstance(dd_raw, list):
        dd_checklist = dd_raw
    elif isinstance(dd_raw, dict):
        dd_checklist = dd_raw.get("checklist", [])
    else:
        dd_checklist = []
    dd_checklist = [item for item in dd_checklist if isinstance(item, dict)]
    if dd_checklist:
        dd_items = ""
        dd_passed = 0
        for item in dd_checklist:
            status = item.get("status", "INDISPONIBIL")
            if status == "DA":
                dd_passed += 1
                dd_color = "#22c55e"
                dd_icon = "DA"
            elif status == "NU":
                dd_color = "#ef4444"
                dd_icon = "NU"
            else:
                dd_color = "#6b7280"
                dd_icon = "N/A"
            dd_name = _escape(str(item.get("name", "")))
            dd_source = _escape(str(item.get("source", "")))
            dd_items += (
                f'<div style="padding:10px 14px;margin-bottom:8px;background:#16213e;border-radius:8px;'
                f'display:flex;align-items:center;gap:12px">'
                f'<span style="background:{dd_color}20;color:{dd_color};font-weight:700;font-size:0.85em;'
                f'padding:2px 10px;border-radius:4px;min-width:34px;text-align:center">{dd_icon}</span>'
                f'<span style="color:#e2e8f0;flex:1">{dd_name}</span>'
                f'<span style="color:#64748b;font-size:0.8em">{dd_source}</span>'
                f'</div>\n'
            )
        due_diligence_html = f'''
        <section id="due-diligence" class="report-section">
            <h2>Due Diligence Checklist</h2>
            <div style="color:#94a3b8;font-size:0.85em;margin-bottom:12px">{dd_passed}/{len(dd_checklist)} verificari OK</div>
            <div>{dd_items}</div>
        </section>'''
        nav_items += '<a href="#due-diligence" class="nav-link">Due Diligence</a>\n'

    # D11 fix: Early Warnings section in HTML (was missing — PDF/DOCX had it, HTML didn't)
    early_warnings_html = ""
    ew_list = risk_score_obj.get("early_warning_confidence", [])
    if ew_list:
        ew_items = ""
        for ew in ew_list:
            sev = ew.get("severity", "MEDIUM")
            conf = ew.get("confidence", 0)
            # Confidence-based gradient color for border-left
            if conf >= 80:
                border_color = "#ef4444"   # red — high confidence warning
            elif conf >= 60:
                border_color = "#f97316"   # orange
            elif conf >= 40:
                border_color = "#eab308"   # yellow
            else:
                border_color = "#6b7280"   # gray — low confidence
            sev_color = "#ef4444" if sev == "HIGH" else "#eab308" if sev == "MEDIUM" else "#22c55e"
            sev_icon = "!!" if sev == "HIGH" else "!" if sev == "MEDIUM" else "i"
            ew_items += (
                f'<div style="padding:10px 14px;margin-bottom:8px;background:#16213e;border-radius:8px;'
                f'border-left:4px solid {border_color};display:flex;align-items:center;gap:12px">'
                f'<span style="background:{sev_color}20;color:{sev_color};font-weight:700;font-size:0.85em;'
                f'padding:2px 8px;border-radius:4px;min-width:28px;text-align:center">{sev_icon}</span>'
                f'<span style="color:#e2e8f0;flex:1">{_escape(ew.get("warning", ""))}</span>'
                f'<span style="color:#64748b;font-size:0.8em">Conf: {conf}%</span>'
                f'</div>\n'
            )
        early_warnings_html = f'''
        <section id="warnings" class="report-section">
            <h2>Semnale de Avertizare</h2>
            <p style="color:#64748b;font-size:.82em;font-style:italic;margin-top:-8px">Anomalii detectate + scor de incredere (0-100%) per semnal — a nu se confunda cu "Semnale de Alarma" (semnale directe de business).</p>
            <div style="margin-top:12px">{ew_items}</div>
        </section>'''
        nav_items += '<a href="#warnings" class="nav-link">Avertizari</a>\n'

    # D11 follow-up: verified_data["early_warnings"] (real business signals) --
    # distinct from risk_score["early_warning_confidence"] above.
    alarm_warnings_html = _build_alarm_warnings_html(verified_data)
    if alarm_warnings_html:
        nav_items += '<a href="#alarm-warnings" class="nav-link">Semnale de Alarma</a>\n'

    # F1-6: Company Network section
    company_network_html = _build_company_network_html(verified_data)
    if company_network_html:
        nav_items += '<a href="#network" class="nav-link">Retea Firme</a>\n'

    # Rich fields previously dropped (predictive/benchmark/actionariat/aegrm/historical/funding)
    rich_fields_html, rich_fields_nav = _build_rich_fields_html(verified_data)
    nav_items += rich_fields_nav

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
.ris-table{{width:100%;border-collapse:collapse;margin:16px 0;font-size:0.9em;table-layout:fixed}}
.ris-table th{{background:#1e293b;color:#a5b4fc;padding:10px 12px;text-align:left;border-bottom:2px solid #6366f140;font-weight:600}}
.ris-table td{{padding:8px 12px;border-bottom:1px solid #2a3a5c;color:#cbd5e1}}
.ris-table tbody tr:hover{{background:#16213e80}}
.list-decimal{{list-style-type:decimal}}
.sources{{padding:40px 0}}
.sources h2{{color:#6366f1;margin-bottom:16px}}
.source-item{{padding:6px 12px;margin-bottom:4px;background:#16213e;border-radius:6px;font-size:0.85em}}
.source-level{{display:inline-block;width:28px;font-weight:700;color:#6366f1}}
.source-status{{float:right;color:#22c55e;font-size:0.85em}}
.disclaimer{{padding:40px 0;border-top:1px solid #2a3a5c;color:#64748b;font-size:0.75em;font-style:italic}}
.exec-summary{{background:#16213e;border:1px solid #6366f140;border-radius:12px;padding:20px 24px;margin:24px 0}}
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
        <div class="meta">Nivel {level} | Generat: {generated} | {len(sources)} surse{f" | Nr: {meta.get('report_number')}" if meta.get('report_number') else ""}</div>
        <div class="risk-badge">{risk_display}</div>
        {f'<p style="margin-top:8px;color:#94a3b8;font-size:0.85em">{risk_rec}</p>' if risk_rec else ''}
    </div>
    <nav class="nav">{nav_items}</nav>
    {exec_summary_html}
    {key_takeaways_html}
    {financial_ratios_html}
    {sparkline_html}
    {charts_html}
    {sections_html}
    {due_diligence_html}
    {alarm_warnings_html}
    {early_warnings_html}
    {company_network_html}
    {rich_fields_html}
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
