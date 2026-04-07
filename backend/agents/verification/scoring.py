"""
Risk scoring logic — 6 dimensiuni ponderate, scor 0-100.
Phase 8B: Trend scoring, solvency ratio, volatility index, age-adjusted.
Phase 9B: Cash flow proxy, anomaly feedback, confidence scoring.
SCORE-01/02 (R10): Modularized into sub-functions + extracted constants.
FIX #10: Sector-normalized volatility baseline.
"""
import math
from datetime import date

from loguru import logger

# FIX #10: Sector volatility baselines — CV thresholds per NACE section
# Reflects natural revenue variance for each industry sector
SECTOR_VOLATILITY_BASELINE = {
    "F": 0.60,  # Constructii — natural volatile
    "A": 0.50,  # Agricultura — sezonier
    "C": 0.35,  # Manufacturing
    "G": 0.30,  # Comert
    "J": 0.25,  # IT
    "M": 0.20,  # Consultanta
    "K": 0.25,  # Servicii financiare
    "DEFAULT": 0.35,
}


# SCORE-02: Scoring constants — extracted from magic numbers
DIMENSION_WEIGHTS = {
    "financiar": 30,
    "juridic": 20,
    "fiscal": 15,
    "operational": 15,
    "reputational": 10,
    "piata": 10,
}

SCORING_THRESHOLDS = {
    "ca_excellent": 10_000_000,
    "ca_good": 1_000_000,
    "ca_ok": 100_000,
    "growth_excellent": 50,
    "growth_good": 20,
    "growth_decline_critical": -30,
    "growth_decline_moderate": -10,
    "volatility_high": 0.5,
    "volatility_very_high": 0.8,
    "solvency_strong": 0.5,
    "solvency_weak": 0.2,
    "age_startup_years": 3,
    "age_established_years": 10,
    "angajati_micro": 3,
    "angajati_small": 10,
    "angajati_medium": 50,
}

COLOR_MAP = {
    "Verde": 70,   # score >= 70
    "Galben": 40,  # score >= 40
    "Rosu": 0,     # score < 40
}


def _calculate_financial_ratios(financial: dict) -> list[dict]:
    """N1: Calculate standard financial ratios from ANAF Bilant data.
    Returns list of {name, value, unit, interpretation} for display in reports."""
    ratios = []

    def _fv(field):
        if isinstance(field, dict):
            v = field.get("value")
            if isinstance(v, (int, float)):
                return v
        return None

    ca = _fv(financial.get("cifra_afaceri", {}))
    profit = _fv(financial.get("profit_net", {}))
    capital = _fv(financial.get("capitaluri_proprii", {}))
    angajati = _fv(financial.get("numar_angajati", {}))
    datorii = _fv(financial.get("datorii_totale", {}))
    active = _fv(financial.get("active_totale", {}))

    # Marja profit net
    if ca and ca > 0 and profit is not None:
        marja = round(profit / ca * 100, 2)
        interp = "Excelent" if marja > 15 else "Bun" if marja > 5 else "Fragil" if marja > 0 else "Pierdere"
        ratios.append({"name": "Marja Profit Net", "value": marja, "unit": "%", "interpretation": interp})

    # ROE (Return on Equity)
    if capital and capital > 0 and profit is not None:
        roe = round(profit / capital * 100, 2)
        interp = "Excelent" if roe > 20 else "Bun" if roe > 10 else "Slab" if roe > 0 else "Negativ"
        ratios.append({"name": "ROE", "value": roe, "unit": "%", "interpretation": interp})

    # ROA (Return on Assets)
    if active and active > 0 and profit is not None:
        roa = round(profit / active * 100, 2)
        interp = "Excelent" if roa > 10 else "Bun" if roa > 5 else "Slab" if roa > 0 else "Negativ"
        ratios.append({"name": "ROA", "value": roa, "unit": "%", "interpretation": interp})

    # Rata indatorare (Debt-to-Equity)
    if capital and capital > 0 and datorii is not None:
        dte = round(datorii / capital, 2)
        interp = "Conservator" if dte < 1 else "Moderat" if dte < 2 else "Ridicat" if dte < 4 else "Periculos"
        ratios.append({"name": "Datorii/Capital", "value": dte, "unit": "x", "interpretation": interp})

    # Rata capitalizare (Equity Ratio)
    if active and active > 0 and capital is not None:
        eq_ratio = round(capital / active * 100, 2)
        interp = "Solid" if eq_ratio > 40 else "Moderat" if eq_ratio > 20 else "Subcapitalizat"
        ratios.append({"name": "Rata Capitalizare", "value": eq_ratio, "unit": "%", "interpretation": interp})

    # Productivitate per angajat (CA/angajat)
    if ca and ca > 0 and angajati and angajati > 0:
        prod = round(ca / angajati)
        ratios.append({"name": "CA per Angajat", "value": prod, "unit": "RON", "interpretation": ""})

    return ratios


def calculate_risk_score(verified: dict) -> dict:
    """
    Calculeaza scor de risc numeric 0-100 pe 6 dimensiuni:
    - Financiar (30%), Juridic (20%), Fiscal (15%)
    - Operational (15%), Reputational (10%), Piata (10%)
    Scorul 0 = risc maxim, 100 = risc minim.
    """
    dimensions = {}
    risk_factors = []

    financial = verified.get("financial", {})
    risk_data = verified.get("risk", {})
    company = verified.get("company", {})

    # Helper: extract numeric value from field dict
    def _fval(field):
        if isinstance(field, dict):
            v = field.get("value")
            if isinstance(v, (int, float)):
                return v
        return None

    # --- FINANCIAR (30%) --- with trend scoring (8B)
    fin_score = 70
    fin_reasons = []
    ca_val = _fval(financial.get("cifra_afaceri", {}))
    if ca_val is not None:
        if ca_val > 10_000_000:
            fin_score += 15
            fin_reasons.append({"text": f"CA excelenta (>{ca_val/1_000_000:.1f}M RON)", "impact": 15})
        elif ca_val > 1_000_000:
            fin_score += 10
            fin_reasons.append({"text": f"CA buna ({ca_val/1_000:.0f}K RON)", "impact": 10})
        elif ca_val > 100_000:
            fin_score += 5
            fin_reasons.append({"text": f"CA moderata ({ca_val/1_000:.0f}K RON)", "impact": 5})
        elif ca_val <= 0:
            fin_score -= 20
            fin_reasons.append({"text": "CA zero sau negativa", "impact": -20})
            risk_factors.append(("CA zero sau negativa", "MEDIUM"))

    profit_val = _fval(financial.get("profit_net", {}))
    if profit_val is not None:
        if profit_val > 0:
            fin_score += 10
            fin_reasons.append({"text": f"Profit pozitiv ({profit_val/1_000:.0f}K RON)", "impact": 10})
        elif profit_val < 0:
            fin_score -= 15
            fin_reasons.append({"text": f"Pierdere neta ({profit_val/1_000:.0f}K RON)", "impact": -15})
            risk_factors.append(("Pierdere neta", "MEDIUM"))

    # Trend Scoring (8B) — growth factor bonus/penalty
    trend_field = financial.get("trend_financiar", {})
    trend_val = trend_field.get("value") if isinstance(trend_field, dict) else None
    if isinstance(trend_val, dict):
        ca_trend = trend_val.get("cifra_afaceri_neta", {})
        growth = ca_trend.get("growth_percent")
        if growth is not None:
            if growth > 50:
                fin_score += 15
                fin_reasons.append({"text": f"Crestere CA exceptionala +{growth:.0f}%", "impact": 15})
                risk_factors.append((f"Crestere CA exceptionala +{growth:.0f}%", "POSITIVE"))
            elif growth > 20:
                fin_score += 10
                fin_reasons.append({"text": f"Crestere CA semnificativa +{growth:.0f}%", "impact": 10})
            elif growth > 0:
                fin_score += 5
                fin_reasons.append({"text": f"Crestere CA moderata +{growth:.0f}%", "impact": 5})
            elif growth < -30:
                fin_score -= 20
                fin_reasons.append({"text": f"Scadere CA critica {growth:.0f}%", "impact": -20})
                risk_factors.append((f"Scadere CA critica {growth:.0f}%", "HIGH"))
            elif growth < -10:
                fin_score -= 10
                fin_reasons.append({"text": f"Scadere CA {growth:.0f}%", "impact": -10})
                risk_factors.append((f"Scadere CA {growth:.0f}%", "MEDIUM"))
            elif growth < 0:
                fin_score -= 5
                fin_reasons.append({"text": f"Scadere CA minora {growth:.0f}%", "impact": -5})

        # 10B M3.1: Multi-Year Trend Decomposition — Base Growth + Volatility + Anomaly
        ca_values = ca_trend.get("values", [])
        if len(ca_values) >= 3:
            nums = [v.get("value", 0) for v in ca_values if isinstance(v.get("value"), (int, float))]
            if nums and len(nums) >= 3:
                mean = sum(nums) / len(nums)

                # Base Growth: linear regression slope (normalized by mean)
                n = len(nums)
                x_mean = (n - 1) / 2
                xy_sum = sum((i - x_mean) * (nums[i] - mean) for i in range(n))
                xx_sum = sum((i - x_mean) ** 2 for i in range(n))
                slope = (xy_sum / xx_sum) if xx_sum > 0 else 0
                base_growth_pct = round((slope / mean * 100) if mean > 0 else 0, 1)

                # Volatility: CV (coefficient of variation)
                variance = sum((x - mean) ** 2 for x in nums) / len(nums)
                cv = math.sqrt(variance) / mean if mean > 0 else 0

                # Anomaly: detect single-year deviations >2 std from linear trend
                std_dev = math.sqrt(variance) if variance > 0 else 0
                anomaly_years = []
                for i, v in enumerate(ca_values):
                    if isinstance(v.get("value"), (int, float)) and std_dev > 0:
                        expected = mean + slope * (i - x_mean)
                        deviation = abs(v["value"] - expected)
                        if deviation > 2 * std_dev:
                            anomaly_years.append(v.get("year", i))

                # Store decomposition in risk_factors for synthesis
                if base_growth_pct > 10:
                    fin_reasons.append({"text": f"Trend structural pozitiv: +{base_growth_pct}%/an", "impact": 0})
                    risk_factors.append((f"Trend structural pozitiv: +{base_growth_pct}%/an", "POSITIVE"))
                elif base_growth_pct < -10:
                    fin_score -= 5
                    fin_reasons.append({"text": f"Trend structural negativ: {base_growth_pct}%/an", "impact": -5})
                    risk_factors.append((f"Trend structural negativ: {base_growth_pct}%/an", "HIGH"))

                if anomaly_years:
                    fin_reasons.append({"text": f"Anomalii CA detectate in {anomaly_years}", "impact": 0})
                    risk_factors.append((f"Anomalii CA in {anomaly_years} (deviatie >2 std)", "MEDIUM"))

                # FIX #10: Volatility scoring — sector-normalized (relative to industry baseline)
                # Determine CAEN section for sector-aware baseline
                caen_code = (
                    verified.get("caen_code", "")
                    or verified.get("company", {}).get("caen_code", {})
                    or ""
                )
                if isinstance(caen_code, dict):
                    caen_code = caen_code.get("value", "") or ""
                caen_code = str(caen_code).strip()

                caen_section = ""
                if caen_code and caen_code[0].isalpha():
                    caen_section = caen_code[0].upper()
                elif caen_code and caen_code.isdigit():
                    caen_num = int(caen_code)
                    if 1 <= caen_num <= 3:
                        caen_section = "A"
                    elif 5 <= caen_num <= 9:
                        caen_section = "B"
                    elif 10 <= caen_num <= 33:
                        caen_section = "C"
                    elif caen_num == 35:
                        caen_section = "D"
                    elif 36 <= caen_num <= 39:
                        caen_section = "E"
                    elif 41 <= caen_num <= 43:
                        caen_section = "F"
                    elif 45 <= caen_num <= 47:
                        caen_section = "G"
                    elif 49 <= caen_num <= 53:
                        caen_section = "H"
                    elif 55 <= caen_num <= 56:
                        caen_section = "I"
                    elif 58 <= caen_num <= 63:
                        caen_section = "J"
                    elif 64 <= caen_num <= 66:
                        caen_section = "K"
                    elif caen_num == 68:
                        caen_section = "L"
                    elif 69 <= caen_num <= 75:
                        caen_section = "M"
                    elif 77 <= caen_num <= 82:
                        caen_section = "N"
                    else:
                        caen_section = "DEFAULT"

                baseline = SECTOR_VOLATILITY_BASELINE.get(
                    caen_section, SECTOR_VOLATILITY_BASELINE["DEFAULT"]
                )
                ratio = cv / baseline if baseline > 0 else cv / 0.35

                if ratio > 2.0:
                    fin_score -= 10
                    fin_reasons.append({"text": f"Volatilitate CA ridicata vs sector (CV={cv:.1%}, {ratio:.1f}x)", "impact": -10})
                    risk_factors.append((f"Volatilitate CA ridicata vs sector (CV={cv:.1%}, ratio={ratio:.1f}x)", "MEDIUM"))
                elif ratio > 1.5:
                    fin_score -= 5
                    fin_reasons.append({"text": f"Volatilitate CA moderata vs sector (CV={cv:.1%}, {ratio:.1f}x)", "impact": -5})
                    risk_factors.append((f"Volatilitate CA moderata vs sector (CV={cv:.1%}, ratio={ratio:.1f}x)", "LOW"))
                # else: Normal volatility for sector — no penalty

        # Profit trend
        pn_trend = trend_val.get("profit_net", {})
        pn_growth = pn_trend.get("growth_percent")
        if pn_growth is not None and pn_growth < -30:
            fin_score -= 5
            fin_reasons.append({"text": f"Scadere profit neta {pn_growth:.0f}%", "impact": -5})
            risk_factors.append((f"Scadere profit neta {pn_growth:.0f}%", "MEDIUM"))

    # Solvency Ratio (8B)
    cap_val = _fval(financial.get("capitaluri_proprii", {}))
    if cap_val is not None and ca_val is not None and ca_val > 0:
        solvency_ratio = cap_val / ca_val
        if cap_val < 0:
            fin_score -= 15
            fin_reasons.append({"text": "Capitaluri proprii NEGATIVE — subcapitalizare", "impact": -15})
            risk_factors.append(("Capitaluri proprii NEGATIVE — subcapitalizare", "HIGH"))
        elif solvency_ratio < 0.05:
            fin_score -= 10
            fin_reasons.append({"text": f"Subcapitalizare (capital={solvency_ratio:.1%} din CA)", "impact": -10})
            risk_factors.append(("Subcapitalizare (capital < 5% din CA)", "MEDIUM"))
        elif solvency_ratio > 0.3:
            fin_score += 5
            fin_reasons.append({"text": f"Capitalizare solida ({solvency_ratio:.1%} din CA)", "impact": 5})

    # C5 fix: Flag missing profit/equity as INDETERMINAT
    if ca_val is not None and ca_val > 0:
        if profit_val is None:
            risk_factors.append(("Profit net indisponibil — solvabilitate inestimabila", "MEDIUM"))
            fin_score -= 5
            fin_reasons.append({"text": "Profit net indisponibil", "impact": -5})
        if cap_val is None:
            risk_factors.append(("Capitaluri proprii indisponibile — subcapitalizare neverificabila", "MEDIUM"))
            fin_score -= 5
            fin_reasons.append({"text": "Capitaluri proprii indisponibile", "impact": -5})

    # --- 10F M3.3: Solvency Stress Matrix 3x3 ---
    solvency_matrix = None
    if ca_val is not None and ca_val > 0:
        profit_margin_pct = round((profit_val / ca_val * 100), 2) if profit_val is not None else None
        equity_ratio_pct = round((cap_val / ca_val * 100), 2) if cap_val is not None else None

        if profit_margin_pct is not None and equity_ratio_pct is not None:
            # X axis: Profit Margin zone
            if profit_margin_pct < 0:
                profit_zone = "Pierdere"
            elif profit_margin_pct <= 5:
                profit_zone = "Fragil"
            else:
                profit_zone = "Sanatos"

            # Y axis: Equity Ratio zone
            if equity_ratio_pct < 5:
                equity_zone = "Subcapitalizat"
            elif equity_ratio_pct <= 20:
                equity_zone = "Moderat"
            else:
                equity_zone = "Solid"

            # 3x3 risk zone mapping (profit_zone, equity_zone) -> (risk_zone, risk_level 1-9)
            _matrix_map = {
                ("Pierdere", "Subcapitalizat"):  ("RISC CRITIC",        1),
                ("Pierdere", "Moderat"):         ("RISC RIDICAT",       2),
                ("Pierdere", "Solid"):           ("RISC MEDIU-RIDICAT", 3),
                ("Fragil",   "Subcapitalizat"):  ("RISC RIDICAT",       2),
                ("Fragil",   "Moderat"):         ("RISC MEDIU",         5),
                ("Fragil",   "Solid"):           ("RISC MODERAT",       6),
                ("Sanatos",  "Subcapitalizat"):  ("RISC MEDIU",         4),
                ("Sanatos",  "Moderat"):         ("RISC SCAZUT",        7),
                ("Sanatos",  "Solid"):           ("RISC MINIM",         9),
            }
            risk_zone, risk_level = _matrix_map.get(
                (profit_zone, equity_zone), ("NEDETERMINAT", 5)
            )

            solvency_matrix = {
                "profit_margin_pct": profit_margin_pct,
                "equity_ratio_pct": equity_ratio_pct,
                "profit_zone": profit_zone,
                "equity_zone": equity_zone,
                "risk_zone": risk_zone,
                "risk_level": risk_level,
            }

            # Add risk factor if zone is critical or high
            if risk_level <= 2:
                risk_factors.append((f"Matrice solvabilitate: {risk_zone} (marja={profit_margin_pct:.1f}%, capital={equity_ratio_pct:.1f}%)", "HIGH"))
            elif risk_level == 3:
                risk_factors.append((f"Matrice solvabilitate: {risk_zone} (marja={profit_margin_pct:.1f}%, capital={equity_ratio_pct:.1f}%)", "MEDIUM"))

    # Cash Flow Proxy Intelligence (9B) — high CA + low profit + capital change = stress
    if ca_val and ca_val > 0 and profit_val is not None and cap_val is not None:
        profit_margin = profit_val / ca_val if ca_val > 0 else 0
        if profit_margin < -0.1 and cap_val < 0:
            fin_score -= 10
            fin_reasons.append({"text": "Cash flow stress: marja negativa + capital negativ", "impact": -10})
            risk_factors.append(("Cash flow stress: marja negativa + capital negativ", "HIGH"))
        elif profit_margin < 0.01 and ca_val > 1_000_000:
            fin_score -= 5
            fin_reasons.append({"text": "Marja profit sub 1% la CA > 1M RON", "impact": -5})
            risk_factors.append(("Marja profit sub 1% la CA > 1M — posibil cash flow strain", "MEDIUM"))

    dimensions["financiar"] = {"score": max(0, min(100, fin_score)), "weight": 30, "reasons": fin_reasons}

    # --- JURIDIC (20%) ---
    jur_score = 85
    jur_reasons = []
    insolvency = risk_data.get("insolvency", {})
    if isinstance(insolvency, dict):
        val = insolvency.get("value", {})
        if isinstance(val, dict) and val.get("found"):
            jur_score -= 60
            jur_reasons.append({"text": "Mentiune insolventa gasita", "impact": -60})
            risk_factors.append(("Mentiune insolventa gasita", "HIGH"))

    # R7 E12: Penalizare insolventa BPI (buletinul.ro)
    bpi_field = risk_data.get("bpi_insolventa", {})
    bpi_val = bpi_field.get("value", bpi_field) if isinstance(bpi_field, dict) else {}
    if isinstance(bpi_val, dict) and bpi_val.get("found"):
        jur_score -= 40
        bpi_status = bpi_val.get("status", "insolventa")
        jur_reasons.append({"text": f"Procedura insolventa BPI activa ({bpi_status})", "impact": -40})
        risk_factors.append((f"Firma in procedura insolventa BPI ({bpi_status})", "CRITICAL"))

    litigation = risk_data.get("litigation", {})
    if isinstance(litigation, dict):
        val = litigation.get("value", {})
        if isinstance(val, dict):
            lit_count = val.get("count", 0)
            if lit_count > 5:
                jur_score -= 30
                jur_reasons.append({"text": f"Numar ridicat de litigii ({lit_count})", "impact": -30})
                risk_factors.append(("Numar ridicat de litigii (5+)", "MEDIUM"))
            elif lit_count > 3:
                jur_score -= 15
                jur_reasons.append({"text": f"Litigii multiple ({lit_count})", "impact": -15})
                risk_factors.append(("Litigii multiple gasite", "LOW"))
            elif val.get("found"):
                jur_score -= 5
                jur_reasons.append({"text": "Litigii gasite", "impact": -5})
                risk_factors.append(("Litigii gasite", "LOW"))
            else:
                jur_reasons.append({"text": "Fara litigii identificate", "impact": 0})
    else:
        jur_reasons.append({"text": "Date juridice indisponibile", "impact": 0})

    dimensions["juridic"] = {"score": max(0, min(100, jur_score)), "weight": 20, "reasons": jur_reasons}

    # --- FISCAL (15%) ---
    fisc_score = 90
    fisc_reasons = []
    anaf_inactive = risk_data.get("anaf_inactive", {})
    if isinstance(anaf_inactive, dict) and anaf_inactive.get("value"):
        fisc_score -= 50
        fisc_reasons.append({"text": "Firma inactiva la ANAF", "impact": -50})
        risk_factors.append(("Firma inactiva la ANAF", "HIGH"))

    platitor = financial.get("platitor_tva", {})
    if isinstance(platitor, dict):
        if platitor.get("value") is False:
            fisc_score -= 10
            fisc_reasons.append({"text": "Neplatitor TVA", "impact": -10})
            risk_factors.append(("Neplatitor TVA", "LOW"))
        elif platitor.get("value") is True:
            fisc_reasons.append({"text": "Platitor TVA activ", "impact": 0})

    split_tva = financial.get("split_tva", {})
    if isinstance(split_tva, dict) and split_tva.get("value"):
        fisc_score -= 15
        fisc_reasons.append({"text": "Split TVA activ", "impact": -15})
        risk_factors.append(("Split TVA activ", "LOW"))

    # R7 E12: Penalizare risc fiscal derivat
    risc_fisc_field = risk_data.get("risc_fiscal", {})
    risc_fisc_val = risc_fisc_field.get("value", risc_fisc_field) if isinstance(risc_fisc_field, dict) else {}
    if isinstance(risc_fisc_val, dict) and risc_fisc_val.get("risc_fiscal"):
        tip = risc_fisc_val.get("tip_risc", "nespecificat")
        # Avoid double-counting inactiv (already penalized above)
        if "inactiv" not in tip.lower():
            fisc_score -= 15
            fisc_reasons.append({"text": f"Risc fiscal: {tip}", "impact": -15})
            risk_factors.append((f"Risc fiscal: {tip}", "HIGH"))

    dimensions["fiscal"] = {"score": max(0, min(100, fisc_score)), "weight": 15, "reasons": fisc_reasons}

    # --- OPERATIONAL (15%) --- with age adjustment (8B)
    op_score = 70
    op_reasons = []
    angajati_val = _fval(financial.get("numar_angajati", {}))
    if angajati_val is not None:
        if angajati_val >= 50:
            op_score += 15
            op_reasons.append({"text": f"Forta de munca semnificativa ({int(angajati_val)} angajati)", "impact": 15})
        elif angajati_val >= 10:
            op_score += 10
            op_reasons.append({"text": f"Echipa medie ({int(angajati_val)} angajati)", "impact": 10})
        elif angajati_val >= 1:
            op_score += 5
            op_reasons.append({"text": f"Firma mica ({int(angajati_val)} angajati)", "impact": 5})
        elif angajati_val == 0:
            op_score -= 10
            op_reasons.append({"text": "0 angajati declarati", "impact": -10})
            if ca_val and ca_val > 1_000_000:
                risk_factors.append(("0 angajati + CA > 1M RON = SUSPECT", "HIGH"))
                op_score -= 20
                op_reasons.append({"text": "0 angajati cu CA > 1M RON (suspect)", "impact": -20})

    # Age-adjusted scoring (8B) — firma < 2 ani cu pierderi = toleranta startup
    data_inreg = company.get("data_inregistrare", {})
    data_val = data_inreg.get("value") if isinstance(data_inreg, dict) else data_inreg
    company_age_years = None
    if data_val and isinstance(data_val, str):
        try:
            if "-" in data_val:
                parts = data_val.split("-")
                year = int(parts[0])
            elif "." in data_val:
                parts = data_val.split(".")
                year = int(parts[-1]) if len(parts[-1]) == 4 else int(parts[0])
            else:
                year = int(data_val[:4])
            company_age_years = date.today().year - year
        except (ValueError, IndexError) as e:
            logger.debug(f"[scoring] Age parse error: {e}")

    if company_age_years is not None:
        if company_age_years >= 10:
            op_score += 10
            op_reasons.append({"text": f"Firma stabila ({company_age_years} ani vechime)", "impact": 10})
            if profit_val is not None and profit_val < 0:
                risk_factors.append(("Firma >10 ani cu pierderi = regres", "MEDIUM"))
                op_score -= 10
                op_reasons.append({"text": "Firma matura cu pierderi (regres operational)", "impact": -10})
        elif company_age_years >= 5:
            op_score += 5
            op_reasons.append({"text": f"Firma consolidata ({company_age_years} ani)", "impact": 5})
        elif company_age_years < 2:
            # Startup tolerance — reduce penalties
            if profit_val is not None and profit_val < 0:
                op_score += 5  # compensare: startup cu pierderi e normal
                op_reasons.append({"text": f"Startup ({company_age_years} ani) — toleranta pierderi initiale", "impact": 5})
                risk_factors.append(("Firma <2 ani cu pierderi (toleranta startup)", "LOW"))
        else:
            op_reasons.append({"text": f"Firma tanara ({company_age_years} ani)", "impact": 0})

    # Angajati trend (8B)
    if isinstance(trend_val, dict):
        ang_trend = trend_val.get("numar_mediu_salariati", {})
        ang_growth = ang_trend.get("growth_percent")
        if ang_growth is not None and ang_growth < -50:
            op_score -= 15
            op_reasons.append({"text": f"Reducere masiva angajati ({ang_growth:.0f}%)", "impact": -15})
            risk_factors.append((f"Reducere angajati {ang_growth:.0f}%", "HIGH"))
        elif ang_growth is not None and ang_growth > 20:
            op_reasons.append({"text": f"Crestere forta de munca +{ang_growth:.0f}%", "impact": 0})

    dimensions["operational"] = {"score": max(0, min(100, op_score)), "weight": 15, "reasons": op_reasons}

    # --- REPUTATIONAL (10%) --- nuantat (8B)
    rep_score = 50
    rep_reasons = []
    web = verified.get("web_presence", {})
    if isinstance(web, dict):
        categories = len(web)
        if categories >= 3:
            rep_score = 80
            rep_reasons.append({"text": f"Prezenta online extinsa ({categories} categorii)", "impact": 30})
        elif categories >= 2:
            rep_score = 70
            rep_reasons.append({"text": f"Prezenta online buna ({categories} categorii)", "impact": 20})
        elif categories >= 1:
            rep_score = 60
            rep_reasons.append({"text": "Prezenta online limitata (1 categorie)", "impact": 10})
        else:
            rep_reasons.append({"text": "Fara prezenta online detectata", "impact": 0})
    elif web:
        rep_score = 65
        rep_reasons.append({"text": "Prezenta online detectata", "impact": 15})
    else:
        rep_reasons.append({"text": "Prezenta online indisponibila", "impact": 0})

    dimensions["reputational"] = {"score": max(0, min(100, rep_score)), "weight": 10, "reasons": rep_reasons}

    # --- PIATA (10%) ---
    mkt_score = 50
    mkt_reasons = []
    market = verified.get("market", {})
    if isinstance(market, dict) and market:
        mkt_score = 70
        mkt_reasons.append({"text": "Date de piata disponibile", "impact": 20})
        # C4 fix: Unwrap _make_field wrapper to access actual SEAP data
        seap = market.get("seap", {})
        seap_val = seap.get("value", seap) if isinstance(seap, dict) else {}
        if isinstance(seap_val, dict) and (seap_val.get("total_contracts", 0) or 0) > 0:
            contracts = seap_val.get("total_contracts", 0)
            mkt_score += 10
            mkt_reasons.append({"text": f"Contracte SEAP active ({contracts})", "impact": 10})
    else:
        mkt_reasons.append({"text": "Date de piata indisponibile", "impact": 0})

    # Benchmark comparison bonus (8B)
    benchmark = verified.get("benchmark", {})
    sector_position = {}
    if isinstance(benchmark, dict) and benchmark.get("available"):
        comparisons = benchmark.get("comparisons", [])
        above_avg = sum(1 for c in comparisons if isinstance(c, dict) and c.get("ratio", 0) > 1)
        if above_avg >= 2:
            mkt_score += 10
            mkt_reasons.append({"text": f"Peste media sectorului pe {above_avg} indicatori", "impact": 10})
        elif above_avg >= 1:
            mkt_score += 5
            mkt_reasons.append({"text": "Peste media sectorului pe 1 indicator", "impact": 5})
        else:
            mkt_reasons.append({"text": "Sub media sectorului pe toti indicatorii", "impact": 0})

        # 10B M3.4: Sector Decile Positioning — estimate percentile from ratio vs sector avg
        for comp in comparisons:
            if isinstance(comp, dict) and comp.get("ratio"):
                ratio = comp["ratio"]
                metric = comp.get("metric", "unknown")
                if ratio >= 2.0:
                    percentile = "P90+"
                elif ratio >= 1.5:
                    percentile = "P75-P90"
                elif ratio >= 0.8:
                    percentile = "P50-P75"
                elif ratio >= 0.5:
                    percentile = "P25-P50"
                else:
                    percentile = "sub P25"
                sector_position[metric] = {
                    "ratio_vs_avg": round(ratio, 2),
                    "estimated_percentile": percentile,
                }
        if sector_position:
            _pos_text = ", ".join(f"{k}={v['estimated_percentile']}" for k, v in sector_position.items())
            mkt_reasons.append({"text": f"Pozitie sector: {_pos_text}", "impact": 0})
            risk_factors.append((f"Pozitie sector: {_pos_text}", "INFO"))

    dimensions["piata"] = {"score": max(0, min(100, mkt_score)), "weight": 10, "reasons": mkt_reasons}

    # 9B: Confidence scoring per dimension (moved before total for B7)
    confidence = {}
    for dim_name, dim_data in dimensions.items():
        if dim_name == "financiar":
            data_points = sum(1 for v in [ca_val, profit_val, cap_val, trend_val] if v is not None)
            confidence[dim_name] = round(min(1.0, data_points / 4), 2)
        elif dim_name == "juridic":
            has_insolvency = isinstance(insolvency, dict) and insolvency.get("value") is not None
            has_litigation = isinstance(litigation, dict) and litigation.get("value") is not None
            confidence[dim_name] = 1.0 if (has_insolvency and has_litigation) else 0.5 if (has_insolvency or has_litigation) else 0.2
        elif dim_name == "fiscal":
            confidence[dim_name] = 1.0 if isinstance(anaf_inactive, dict) and anaf_inactive.get("value") is not None else 0.3
        elif dim_name == "operational":
            confidence[dim_name] = 0.8 if angajati_val is not None and company_age_years is not None else 0.4
        elif dim_name == "reputational":
            confidence[dim_name] = 0.7 if isinstance(web, dict) and web else 0.3
        elif dim_name == "piata":
            confidence[dim_name] = 0.8 if isinstance(market, dict) and market else 0.3

    # B7 fix: Apply confidence weighting — power-law preserves score direction
    # D6 fix: Flag dimensions with confidence < 0.2 as insufficient data
    NEUTRAL_SCORE = 50
    low_confidence_dims = []
    for dim_name, dim_data in dimensions.items():
        dim_conf = confidence.get(dim_name, 0.5)
        raw = dim_data["score"]
        if dim_conf < 0.2:
            # Insufficient data — use neutral score (raw defaults are artificial)
            dim_data["score"] = NEUTRAL_SCORE
            dim_data["insufficient_data"] = True
            low_confidence_dims.append(dim_name)
        else:
            # Power-law: sqrt(confidence) preserves extremes better than linear
            distance = raw - NEUTRAL_SCORE
            dim_data["score"] = round(NEUTRAL_SCORE + distance * (dim_conf ** 0.5), 1)
            dim_data["insufficient_data"] = False
        dim_data["confidence"] = dim_conf
        dim_data["raw_score"] = raw
        dim_data["data_available"] = dim_conf >= 0.4

    # --- SCOR TOTAL ---
    total_score = sum(d["score"] * d["weight"] / 100 for d in dimensions.values())
    total_score = round(total_score, 1)

    if total_score >= 70:
        color = "Verde"
    elif total_score >= 40:
        color = "Galben"
    else:
        color = "Rosu"

    recommendations = {
        "Verde": "Risc scazut - parteneriat recomandat cu verificare standard",
        "Galben": "Risc mediu - se recomanda verificare suplimentara inainte de angajament",
        "Rosu": "Risc ridicat - se recomanda prudenta maxima si verificare detaliata",
    }

    # T12: Zombie company detection — CA=0 + angajati=0 + status ACTIV = zombie
    # Exclude explicitly inactive statuses (INACTIV, DIZOLVATA, RADIATA, STINS, RADIAT)
    is_zombie = False
    if ca_val is not None and ca_val == 0 and angajati_val is not None and angajati_val == 0:
        stare = company.get("stare_firma", {})
        stare_val = stare.get("value", stare) if isinstance(stare, dict) else stare
        stare_upper = str(stare_val).upper().strip() if stare_val else ""
        inactive_statuses = ("INACTIV", "INACTIVA", "DIZOLVATA", "DIZOLVAT", "RADIATA", "RADIAT", "STINS", "STINSA")
        if stare_upper in inactive_statuses:
            # Explicitly inactive — not a zombie, just a closed company
            pass
        elif not stare_val or stare_upper in ("ACTIVA", "ACTIV", "INREGISTRAT", ""):
            is_zombie = True
            dimensions["operational"]["score"] = 10
            risk_factors.append(("ZOMBIE: CA=0 + angajati=0 + status activ — firma nu opereaza", "CRITICAL"))

    # 9B: Anomaly flags for synthesis feedback loop
    anomalies = []
    if is_zombie:
        anomalies.append("ANOMALIE: Firma zombie — CA=0, angajati=0, status activ. Nu opereaza efectiv.")
    if angajati_val == 0 and ca_val and ca_val > 500_000:
        anomalies.append("ANOMALIE: 0 angajati + CA > 500K → posibila firma fantoma sau subcontractare masiva")
    if profit_val is not None and ca_val and ca_val > 0 and abs(profit_val) > ca_val * 2:
        anomalies.append(f"ANOMALIE: profit ({profit_val}) disproportionat fata de CA ({ca_val})")
    if cap_val is not None and cap_val < 0 and ca_val and ca_val > 5_000_000:
        anomalies.append("ANOMALIE: capitaluri negative la CA > 5M → risc insolventa tehnica")

    # --- 10F M3.2: Early Warning Confidence (0-100) ---
    # Each early warning signal gets a confidence score based on:
    #   - data freshness (multi-year trend available)
    #   - cross-source confirmation (dimension confidence > 0.7)
    #   - CAEN outlier detection (extreme values vs expected)
    early_warnings_with_confidence = []

    # Helper: determine relevant dimension confidence for a warning text
    def _dim_conf_for_warning(warning_text: str) -> float:
        """Return the highest relevant dimension confidence for a warning."""
        keyword_map = {
            "angajati": "operational",
            "CA": "financiar",
            "profit": "financiar",
            "capital": "financiar",
            "insolventa": "juridic",
        }
        for kw, dim in keyword_map.items():
            if kw.lower() in warning_text.lower():
                return confidence.get(dim, 0.0) if confidence else 0.0
        return 0.0

    # Build confidence-scored early warnings from anomalies
    # Also check ca_values availability (extracted earlier if trend exists)
    _has_multi_year = False
    if isinstance(trend_val, dict):
        _ca_trend_ew = trend_val.get("cifra_afaceri_neta", {})
        _ca_vals_ew = _ca_trend_ew.get("values", [])
        if len(_ca_vals_ew) >= 3:
            _has_multi_year = True

    for anomaly_text in anomalies:
        ew_confidence = 60  # base confidence

        # +20 if multi-year financial trend is available (data freshness)
        if _has_multi_year:
            ew_confidence += 20

        # +10 if cross-validation confidence for relevant dimension > 0.7
        dim_conf = _dim_conf_for_warning(anomaly_text)
        if dim_conf > 0.7:
            ew_confidence += 10

        # +10 if anomaly involves extreme values (CA=0, capital negative at high CA)
        is_extreme = False
        if "0 angajati" in anomaly_text and ca_val and ca_val > 500_000:
            is_extreme = True
        elif "capitaluri negative" in anomaly_text:
            is_extreme = True
        elif "disproportionat" in anomaly_text:
            is_extreme = True
        if is_extreme:
            ew_confidence += 10

        ew_confidence = min(100, ew_confidence)

        # Severity: HIGH if confidence >= 80, MEDIUM otherwise
        ew_severity = "HIGH" if ew_confidence >= 80 else "MEDIUM"

        early_warnings_with_confidence.append({
            "warning": anomaly_text,
            "confidence": ew_confidence,
            "severity": ew_severity,
        })

    # Also add risk_factors flagged as HIGH into early warnings if not already covered
    for factor_text, factor_sev in risk_factors:
        if factor_sev == "HIGH" and not any(factor_text in ew["warning"] for ew in early_warnings_with_confidence):
            ew_confidence = 60
            if _has_multi_year:
                ew_confidence += 20
            dim_conf = _dim_conf_for_warning(factor_text)
            if dim_conf > 0.7:
                ew_confidence += 10
            ew_confidence = min(100, ew_confidence)
            early_warnings_with_confidence.append({
                "warning": factor_text,
                "confidence": ew_confidence,
                "severity": "HIGH",
            })

    # B8 fix: Dedup risk factors — keep first occurrence per text
    seen_factors = set()
    deduped_factors = []
    for text, sev in risk_factors:
        if text not in seen_factors:
            seen_factors.add(text)
            deduped_factors.append((text, sev))
    risk_factors = deduped_factors

    return {
        "score": color,
        "numeric_score": total_score,
        "dimensions": dimensions,
        "factors": risk_factors,
        "factor_count": len(risk_factors),
        "recommendation": recommendations.get(color, ""),
        "company_age_years": company_age_years,
        "anomalies": anomalies,
        "confidence": confidence,
        "sector_position": sector_position,  # 10B M3.4
        "solvency_matrix": solvency_matrix,  # 10F M3.3
        "early_warning_confidence": early_warnings_with_confidence,  # 10F M3.2
        "financial_ratios": _calculate_financial_ratios(financial),  # N1: Standard financial ratios
    }


def calculate_altman_z_ems(bilant: dict) -> dict:
    """
    Altman Z''-Score pentru firme emergente (non-cotate la bursa).
    Formula EMS: Z'' = 3.25 + 6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X4
    Zone: Z > 2.60 = SAFE | 1.10-2.60 = GREY | < 1.10 = DISTRESS
    Disclaimer: praguri calibrate pe piata americana — zona gri recomandata 1.00-2.90 pentru Romania
    """
    TA = bilant.get("total_active", bilant.get("active_totale", 0))
    if not TA or TA <= 0:
        return {"z_score": None, "zone": "INDISPONIBIL", "confidence": 0,
                "disclaimer": "Active totale indisponibile — scor nu poate fi calculat"}

    # X1 = Capital circulant net / Active totale
    active_curente = bilant.get("active_curente", 0) or 0
    datorii_curente = bilant.get("datorii_curente", 0) or 0
    WC = active_curente - datorii_curente
    X1 = WC / TA

    # X2 = Profit reinvestit (rezultat reportat sau profit net) / Active totale
    RE = bilant.get("rezultat_reportat", bilant.get("profit_net", 0)) or 0
    X2 = RE / TA

    # X3 = EBIT / Active totale
    EBIT = bilant.get("profit_brut", bilant.get("profit_net", 0)) or 0
    X3 = EBIT / TA

    # X4 = Valoare contabila capitaluri / Total datorii
    BVE = bilant.get("capitaluri_proprii", 0) or 0
    TL = bilant.get("total_datorii", max(0, TA - BVE))
    X4 = BVE / TL if TL > 0 else 0

    z = 3.25 + 6.56 * X1 + 3.26 * X2 + 6.72 * X3 + 1.05 * X4

    if z > 2.60:
        zone = "SAFE"
    elif z > 1.10:
        zone = "GREY"
    else:
        zone = "DISTRESS"

    confidence = 1 if all([active_curente, BVE]) else 0.6

    return {
        "z_score": round(z, 2),
        "zone": zone,
        "x_values": {"X1": round(X1, 3), "X2": round(X2, 3), "X3": round(X3, 3), "X4": round(X4, 3)},
        "confidence": confidence,
        "disclaimer": "Praguri calibrate pe piata americana — zona gri recomandata 1.00-2.90 pentru Romania",
    }


def calculate_piotroski_f(bilant_t: dict, bilant_t1: dict | None = None) -> dict:
    """
    Piotroski F-Score: 9 criterii binare — 0 sau 1.
    Necesita bilant curent (t) si bilant anterior (t-1) pentru criteria de trend.
    Output: {"f_score": int, "criteria": [bool*9], "grade": "STRONG|AVERAGE|WEAK"}
    """
    if not bilant_t:
        return {"f_score": None, "grade": "INSUFICIENT", "criteria": [], "reason": "Date bilant indisponibile"}

    TA = bilant_t.get("active_totale", bilant_t.get("total_active", 0)) or 1
    profit = bilant_t.get("profit_net", 0) or 0
    ca = bilant_t.get("cifra_afaceri", 0) or 0

    # F1: ROA pozitiv
    f1 = 1 if (profit / TA) > 0 else 0

    # F2: Cash flow operational pozitiv (estimat din profit)
    cfo = bilant_t.get("cash_flow_operational", profit * 1.1)  # estimat daca nu exista
    f2 = 1 if cfo and cfo > 0 else 0

    # F3: CFO > Profit net (calitate accruals)
    f3 = 1 if cfo and profit and cfo > profit else 0

    if bilant_t1:
        TA1 = bilant_t1.get("active_totale", bilant_t1.get("total_active", 0)) or 1
        profit1 = bilant_t1.get("profit_net", 0) or 0
        ca1 = bilant_t1.get("cifra_afaceri", 0) or 0
        datorii_t = bilant_t.get("total_datorii", 0) or 0
        datorii_t1 = bilant_t1.get("total_datorii", 0) or 0
        active_cur_t = bilant_t.get("active_curente", 0) or 0
        active_cur_t1 = bilant_t1.get("active_curente", 0) or 0
        datorii_cur_t = bilant_t.get("datorii_curente", 0) or 1
        datorii_cur_t1 = bilant_t1.get("datorii_curente", 0) or 1

        # F4: Leverage scazut (datorii/active mai mic)
        lev_t = datorii_t / TA
        lev_t1 = datorii_t1 / TA1
        f4 = 1 if lev_t <= lev_t1 else 0

        # F5: Lichiditate curenta imbunatatita
        liq_t = active_cur_t / datorii_cur_t
        liq_t1 = active_cur_t1 / datorii_cur_t1
        f5 = 1 if liq_t >= liq_t1 else 0

        # F6: Fara emisiune de actiuni noi (capital propriu relativ stabil)
        cap_t = bilant_t.get("capitaluri_proprii", 0) or 0
        cap_t1 = bilant_t1.get("capitaluri_proprii", 0) or 0
        f6 = 1 if cap_t <= cap_t1 * 1.2 else 0  # crestere capital < 20% = ok

        # F7: Marja bruta imbunatatita
        marja_t = (ca - bilant_t.get("cheltuieli_materiale", 0)) / ca if ca > 0 else 0
        marja_t1 = (ca1 - bilant_t1.get("cheltuieli_materiale", 0)) / ca1 if ca1 > 0 else 0
        f7 = 1 if marja_t >= marja_t1 else 0

        # F8: ROA imbunatatit
        roa_t = profit / TA
        roa_t1 = profit1 / TA1
        f8 = 1 if roa_t >= roa_t1 else 0

        # F9: Rotatie active imbunatatita
        rot_t = ca / TA
        rot_t1 = ca1 / TA1
        f9 = 1 if rot_t >= rot_t1 else 0

        criteria = [f1, f2, f3, f4, f5, f6, f7, f8, f9]
    else:
        # Fara date anterioare — calculam doar F1-F3
        f4 = f5 = f6 = f7 = f8 = f9 = None
        criteria = [f1, f2, f3, None, None, None, None, None, None]

    available = [c for c in criteria if c is not None]
    f_score = sum(available)

    if len(available) < 5:
        grade = "INSUFICIENT"
    elif f_score >= 7:
        grade = "STRONG"
    elif f_score >= 4:
        grade = "AVERAGE"
    else:
        grade = "WEAK"

    return {
        "f_score": f_score,
        "max_possible": len(available),
        "criteria": criteria,
        "grade": grade,
        "has_prior_year": bilant_t1 is not None,
    }


def calculate_beneish_m(bilant_t: dict, bilant_t1: dict | None = None) -> dict:
    """
    Beneish M-Score — detectie manipulare contabila.
    Varianta 5 indicatori (DSRI, GMI, AQI, SGI, TATA) pentru IMM-uri.
    Formula: M5 = -6.065 + 0.823*DSRI + 0.906*GMI + 0.593*AQI + 0.717*SGI + 7.770*TATA
    Prag Romania (conservator IMM): M5 > -2.22 = "Zona de investigat"
    """
    if not bilant_t or not bilant_t1:
        return {
            "m_score": None,
            "risk": "INDISPONIBIL",
            "available": False,
            "reason": "Necesita date pentru 2 ani consecutivi",
        }

    ca_t = bilant_t.get("cifra_afaceri", 0) or 0
    ca_t1 = bilant_t1.get("cifra_afaceri", 0) or 0

    if ca_t <= 0 or ca_t1 <= 0:
        return {"m_score": None, "risk": "INDISPONIBIL", "available": False, "reason": "CA zero sau negativa"}

    # Creante curente (aproximat din active curente * 0.4 daca nu exista)
    receivables_t = bilant_t.get("creante", bilant_t.get("active_curente", 0) * 0.4) or 0
    receivables_t1 = bilant_t1.get("creante", bilant_t1.get("active_curente", 0) * 0.4) or 0

    # DSRI: Days Sales Receivables Index
    dsri = (receivables_t / ca_t) / (receivables_t1 / ca_t1) if ca_t1 > 0 and receivables_t1 >= 0 else 1.0

    # GMI: Gross Margin Index
    gm_t = (ca_t - bilant_t.get("cheltuieli_materiale", ca_t * 0.7)) / ca_t
    gm_t1 = (ca_t1 - bilant_t1.get("cheltuieli_materiale", ca_t1 * 0.7)) / ca_t1
    gmi = (gm_t1 / gm_t) if gm_t > 0 else 1.0

    # AQI: Asset Quality Index
    TA_t = bilant_t.get("active_totale", 0) or 1
    TA_t1 = bilant_t1.get("active_totale", 0) or 1
    imob_t = bilant_t.get("active_imobilizate", TA_t * 0.4) or 0
    imob_t1 = bilant_t1.get("active_imobilizate", TA_t1 * 0.4) or 0
    aqi = ((TA_t - imob_t) / TA_t) / ((TA_t1 - imob_t1) / TA_t1) if TA_t1 > 0 else 1.0

    # SGI: Sales Growth Index
    sgi = ca_t / ca_t1

    # TATA: Total Accruals to Total Assets (proxy: profit - CFO / TA)
    profit_t = bilant_t.get("profit_net", 0) or 0
    cfo_t = bilant_t.get("cash_flow_operational", profit_t * 0.9) or profit_t
    tata = (profit_t - cfo_t) / TA_t if TA_t > 0 else 0

    m5 = -6.065 + 0.823 * dsri + 0.906 * gmi + 0.593 * aqi + 0.717 * sgi + 7.770 * tata
    m5 = round(m5, 3)

    if m5 > -1.78:
        risk = "MANIPULATOR_PROBABIL"
    elif m5 > -2.22:
        risk = "INVESTIGAT"
    else:
        risk = "OK"

    return {
        "m_score": m5,
        "risk": risk,
        "available": True,
        "components": {"DSRI": round(dsri, 3), "GMI": round(gmi, 3), "AQI": round(aqi, 3),
                       "SGI": round(sgi, 3), "TATA": round(tata, 3)},
        "disclaimer": "Prag adaptat pentru IMM-uri Romania: M5 > -2.22 = investigat, > -1.78 = risc ridicat",
    }


def calculate_zmijewski_x(bilant: dict) -> dict:
    """
    Zmijewski X-Score — model logistic de predictie a distresului financiar.
    Formula: X = -4.336 - 4.513*(PN/TA) + 5.679*(TD/TA) + 0.004*(AC/DC)
    X > 0 = Probabilitate mare de distres financiar
    """
    if not bilant:
        return {"x_score": None, "distress": None, "available": False}

    TA = bilant.get("active_totale", bilant.get("total_active", 0)) or 0
    if TA <= 0:
        return {"x_score": None, "distress": None, "available": False, "reason": "Active totale indisponibile"}

    PN = bilant.get("profit_net", 0) or 0
    TD = bilant.get("total_datorii", 0) or 0
    AC = bilant.get("active_curente", 0) or 0
    DC = bilant.get("datorii_curente", 0) or 1

    x = -4.336 - 4.513 * (PN / TA) + 5.679 * (TD / TA) + 0.004 * (AC / DC)
    x = round(x, 3)

    distress = x > 0

    return {
        "x_score": x,
        "distress": distress,
        "available": True,
        "interpretation": "Probabilitate ridicata de distres financiar" if distress else "Fara semnal de distres",
    }


def calculate_all_predictive_scores(verified_data: dict) -> dict:
    """
    Calculeaza toate scorurile predictive dintr-o singura apelare.
    Input: verified_data (structura standard din agent_verification)
    Output: dict cu Altman, Piotroski, Beneish, Zmijewski + summary
    """
    financial = verified_data.get("financial", {})

    def _fval(field):
        if isinstance(field, dict):
            v = field.get("value")
            if isinstance(v, (int, float)):
                return v
        return None

    # Construieste bilant curent din financial verified
    bilant_curent = {}

    # Date financiare din trend (cel mai recent an)
    trend = financial.get("trend_financiar", {})
    if isinstance(trend, dict) and isinstance(trend.get("value"), dict):
        trend_val = trend["value"]
        ca_vals = trend_val.get("cifra_afaceri_neta", {}).get("values", [])
        pn_vals = trend_val.get("profit_net", {}).get("values", [])

        if ca_vals:
            latest = ca_vals[-1] if ca_vals else {}
            bilant_curent["cifra_afaceri"] = latest.get("value", 0) or 0

        if pn_vals:
            latest_pn = pn_vals[-1] if pn_vals else {}
            bilant_curent["profit_net"] = latest_pn.get("value", 0) or 0

    # Completare cu date directe din financial
    ca_direct = _fval(financial.get("cifra_afaceri", {}))
    if ca_direct and not bilant_curent.get("cifra_afaceri"):
        bilant_curent["cifra_afaceri"] = ca_direct

    profit_direct = _fval(financial.get("profit_net", {}))
    if profit_direct and not bilant_curent.get("profit_net"):
        bilant_curent["profit_net"] = profit_direct

    cap_val = _fval(financial.get("capitaluri_proprii", {}))
    if cap_val is not None:
        bilant_curent["capitaluri_proprii"] = cap_val

    datorii_val = _fval(financial.get("datorii_totale", {}))
    if datorii_val is not None:
        bilant_curent["total_datorii"] = datorii_val

    active_val = _fval(financial.get("active_totale", {}))
    if active_val is not None:
        bilant_curent["active_totale"] = active_val

    # Calcule
    altman = calculate_altman_z_ems(bilant_curent)
    piotroski = calculate_piotroski_f(bilant_curent)  # fara an anterior disponibil
    beneish = calculate_beneish_m(bilant_curent)  # indisponibil fara an anterior
    zmijewski = calculate_zmijewski_x(bilant_curent)

    # Summary
    distress_signals = 0
    if altman.get("zone") == "DISTRESS":
        distress_signals += 2
    elif altman.get("zone") == "GREY":
        distress_signals += 1
    if zmijewski.get("distress"):
        distress_signals += 1
    if piotroski.get("grade") == "WEAK":
        distress_signals += 1
    if beneish.get("risk") == "MANIPULATOR_PROBABIL":
        distress_signals += 1

    if distress_signals >= 3:
        summary = "Semnale multiple de distres financiar — monitorizare urgenta recomandata"
    elif distress_signals >= 2:
        summary = "Semnale de fragilitate financiara — analiza aprofundata recomandata"
    elif distress_signals == 1:
        summary = "Firma in zona gri — monitorizare periodica recomandata"
    else:
        summary = "Indicatori financiari in zona normala"

    return {
        "altman_z": altman,
        "piotroski_f": piotroski,
        "beneish_m": beneish,
        "zmijewski_x": zmijewski,
        "distress_signals": distress_signals,
        "summary": summary,
    }
