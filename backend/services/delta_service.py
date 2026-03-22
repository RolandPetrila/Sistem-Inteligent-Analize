"""
Delta Service — Compara raport nou vs anterior pentru aceeasi firma.
Detecteaza schimbari in: CA, profit, angajati, scor risc, stare ANAF.
"""

import json
from datetime import datetime

from loguru import logger

from backend.database import db


async def compute_delta(company_id: str, new_verified_data: dict) -> dict | None:
    """
    Cauta ultimul raport pt aceeasi companie si calculeaza delta.
    Returneaza dict cu schimbarile sau None daca nu exista raport anterior.
    """
    if not company_id:
        return None

    # Cauta raportul anterior (al doilea cel mai recent pt aceasta companie)
    rows = await db.fetch_all(
        "SELECT id, full_data, created_at FROM reports "
        "WHERE company_id = ? ORDER BY created_at DESC LIMIT 2",
        (company_id,),
    )

    if len(rows) < 2:
        return None

    # C12 fix: rows[0] is the report just inserted, rows[1] is the actual previous
    old_row = rows[1]
    old_data = {}
    if old_row["full_data"]:
        try:
            old_data = json.loads(old_row["full_data"])
        except (json.JSONDecodeError, TypeError):
            return None

    if not old_data:
        return None

    old_date = old_row["created_at"]
    delta = {
        "previous_report_id": old_row["id"],
        "previous_date": old_date,
        "changes": [],
    }

    # Extrage valori din old si new
    comparisons = [
        ("Cifra de Afaceri", _extract_ca(old_data), _extract_ca(new_verified_data), "RON"),
        ("Profit Net", _extract_profit(old_data), _extract_profit(new_verified_data), "RON"),
        ("Nr. Angajati", _extract_employees(old_data), _extract_employees(new_verified_data), ""),
        ("Scor Risc", _extract_risk_score(old_data), _extract_risk_score(new_verified_data), "/100"),
    ]

    for name, old_val, new_val, unit in comparisons:
        if old_val is not None and new_val is not None:
            change = _compute_change(name, old_val, new_val, unit)
            if change:
                delta["changes"].append(change)

    # Stare ANAF (text comparison)
    old_company = old_data.get("company", {})
    new_company = new_verified_data.get("company", {})
    old_stare = _get_field_value(old_company.get("stare_inregistrare", {}))
    new_stare = _get_field_value(new_company.get("stare_inregistrare", {}))
    if old_stare and new_stare and old_stare != new_stare:
        delta["changes"].append({
            "indicator": "Stare ANAF",
            "old_value": str(old_stare),
            "new_value": str(new_stare),
            "direction": "schimbare",
            "display": f"Stare ANAF: {old_stare} → {new_stare}",
        })

    # 10F M7.3: Anomaly Flags pe Delta — auto-detect critical changes
    anomaly_flags = []
    for change in delta["changes"]:
        pct = change.get("percent_change")
        indicator = change.get("indicator", "")
        if pct is not None:
            if indicator == "Cifra de Afaceri" and pct < -30:
                anomaly_flags.append({"indicator": indicator, "type": "CA_DROP_CRITICAL", "severity": "RED", "message": f"Scadere CA critica: {pct}%"})
            elif indicator == "Profit Net" and change.get("new_value", 0) < 0 and change.get("old_value", 0) >= 0:
                anomaly_flags.append({"indicator": indicator, "type": "PROFIT_TO_LOSS", "severity": "RED", "message": "Trecere de la profit la pierdere"})
            elif indicator == "Nr. Angajati" and pct < -50:
                anomaly_flags.append({"indicator": indicator, "type": "EMPLOYEES_HALVED", "severity": "YELLOW", "message": f"Reducere angajati {pct}%"})
            elif indicator == "Scor Risc" and change.get("diff", 0) < -15:
                anomaly_flags.append({"indicator": indicator, "type": "SCORE_DROP", "severity": "YELLOW", "message": f"Scadere scor risc cu {abs(change['diff'])} puncte"})

    if anomaly_flags:
        delta["anomaly_flags"] = anomaly_flags

    if not delta["changes"]:
        return None

    logger.info(f"[delta] {len(delta['changes'])} changes detected vs report {old_row['id'][:8]}")
    return delta


def _get_field_value(field):
    if isinstance(field, dict):
        return field.get("value")
    return field


def _extract_ca(data: dict):
    fin = data.get("financial", {})
    ca_field = fin.get("cifra_afaceri", {})
    return _get_field_value(ca_field) if isinstance(ca_field, dict) else None


def _extract_profit(data: dict):
    fin = data.get("financial", {})
    p = fin.get("profit_net", {})
    return _get_field_value(p) if isinstance(p, dict) else None


def _extract_employees(data: dict):
    fin = data.get("financial", {})
    e = fin.get("numar_angajati", {})
    return _get_field_value(e) if isinstance(e, dict) else None


def _extract_risk_score(data: dict):
    rs = data.get("risk_score", {})
    return rs.get("numeric_score") if isinstance(rs, dict) else None


def _compute_change(name: str, old_val, new_val, unit: str) -> dict | None:
    try:
        old_num = float(old_val)
        new_num = float(new_val)
    except (TypeError, ValueError):
        return None

    diff = new_num - old_num
    if abs(diff) < 0.01:
        return None

    if old_num != 0:
        pct = round(((new_num - old_num) / abs(old_num)) * 100, 1)
    else:
        pct = None

    if diff > 0:
        direction = "crestere"
        arrow = "↑"
    else:
        direction = "scadere"
        arrow = "↓"

    pct_str = f" ({'+' if pct and pct > 0 else ''}{pct}%)" if pct is not None else ""

    if unit == "RON" and abs(new_num) > 1000:
        display = f"{arrow} {name}: {old_num:,.0f} → {new_num:,.0f} {unit}{pct_str}"
    else:
        display = f"{arrow} {name}: {old_val} → {new_val} {unit}{pct_str}"

    return {
        "indicator": name,
        "old_value": old_val,
        "new_value": new_val,
        "diff": diff,
        "percent_change": pct,
        "direction": direction,
        "display": display,
    }


async def compute_time_series(company_id: str, max_reports: int = 5) -> dict | None:
    """10D M7.1: Time-Series Delta — trend CA/Profit/Angajati/Scor across 2-5 reports."""
    if not company_id:
        return None

    rows = await db.fetch_all(
        "SELECT full_data, created_at FROM reports "
        "WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
        (company_id, max_reports),
    )

    if len(rows) < 2:
        return None

    series = {"dates": [], "cifra_afaceri": [], "profit_net": [], "angajati": [], "scor_risc": []}

    for row in reversed(rows):  # oldest first
        data = {}
        try:
            data = json.loads(row["full_data"]) if row["full_data"] else {}
        except (json.JSONDecodeError, TypeError):
            continue

        series["dates"].append(row["created_at"][:10] if row["created_at"] else "?")
        series["cifra_afaceri"].append(_extract_ca(data))
        series["profit_net"].append(_extract_profit(data))
        series["angajati"].append(_extract_employees(data))
        series["scor_risc"].append(_extract_risk_score(data))

    # Chart.js ready format
    chart_data = {}
    for key in ["cifra_afaceri", "profit_net", "angajati", "scor_risc"]:
        values = series[key]
        if any(v is not None for v in values):
            chart_data[key] = {
                "labels": series["dates"],
                "data": [v if v is not None else 0 for v in values],
            }

    return {"reports_count": len(rows), "series": series, "chart_data": chart_data}


async def save_delta(report_id_new: str, report_id_old: str, delta_summary: str):
    """Salveaza delta in tabelul report_deltas."""
    import uuid
    delta_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO report_deltas (id, report_id_new, report_id_old, delta_summary) "
        "VALUES (?, ?, ?, ?)",
        (delta_id, report_id_new, report_id_old, delta_summary),
    )
