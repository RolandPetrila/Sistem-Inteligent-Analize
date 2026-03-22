"""
Risk scoring logic — 6 dimensiuni ponderate, scor 0-100.
Phase 8B: Trend scoring, solvency ratio, volatility index, age-adjusted.
Phase 9B: Cash flow proxy, anomaly feedback, confidence scoring.
"""
import math
from datetime import date


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
    ca_val = _fval(financial.get("cifra_afaceri", {}))
    if ca_val is not None:
        if ca_val > 10_000_000:
            fin_score += 15
        elif ca_val > 1_000_000:
            fin_score += 10
        elif ca_val > 100_000:
            fin_score += 5
        elif ca_val <= 0:
            fin_score -= 20
            risk_factors.append(("CA zero sau negativa", "MEDIUM"))

    profit_val = _fval(financial.get("profit_net", {}))
    if profit_val is not None:
        if profit_val > 0:
            fin_score += 10
        elif profit_val < 0:
            fin_score -= 15
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
                risk_factors.append((f"Crestere CA exceptionala +{growth:.0f}%", "POSITIVE"))
            elif growth > 20:
                fin_score += 10
            elif growth > 0:
                fin_score += 5
            elif growth < -30:
                fin_score -= 20
                risk_factors.append((f"Scadere CA critica {growth:.0f}%", "HIGH"))
            elif growth < -10:
                fin_score -= 10
                risk_factors.append((f"Scadere CA {growth:.0f}%", "MEDIUM"))
            elif growth < 0:
                fin_score -= 5

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
                    risk_factors.append((f"Trend structural pozitiv: +{base_growth_pct}%/an", "POSITIVE"))
                elif base_growth_pct < -10:
                    risk_factors.append((f"Trend structural negativ: {base_growth_pct}%/an", "HIGH"))
                    fin_score -= 5

                if anomaly_years:
                    risk_factors.append((f"Anomalii CA in {anomaly_years} (deviatie >2 std)", "MEDIUM"))

                # Volatility scoring (existing logic enhanced)
                if cv > 0.5:
                    fin_score -= 10
                    risk_factors.append((f"Volatilitate CA ridicata (CV={cv:.1%})", "MEDIUM"))
                elif cv > 0.3:
                    fin_score -= 5
                    risk_factors.append((f"Volatilitate CA moderata (CV={cv:.1%})", "LOW"))

        # Profit trend
        pn_trend = trend_val.get("profit_net", {})
        pn_growth = pn_trend.get("growth_percent")
        if pn_growth is not None and pn_growth < -30:
            fin_score -= 5
            risk_factors.append((f"Scadere profit neta {pn_growth:.0f}%", "MEDIUM"))

    # Solvency Ratio (8B)
    cap_val = _fval(financial.get("capitaluri_proprii", {}))
    if cap_val is not None and ca_val is not None and ca_val > 0:
        solvency_ratio = cap_val / ca_val
        if cap_val < 0:
            fin_score -= 15
            risk_factors.append(("Capitaluri proprii NEGATIVE — subcapitalizare", "HIGH"))
        elif solvency_ratio < 0.05:
            fin_score -= 10
            risk_factors.append((f"Subcapitalizare (capital < 5% din CA)", "MEDIUM"))
        elif solvency_ratio > 0.3:
            fin_score += 5

    # C5 fix: Flag missing profit/equity as INDETERMINAT
    if ca_val is not None and ca_val > 0:
        if profit_val is None:
            risk_factors.append(("Profit net indisponibil — solvabilitate inestimabila", "MEDIUM"))
            fin_score -= 5
        if cap_val is None:
            risk_factors.append(("Capitaluri proprii indisponibile — subcapitalizare neverificabila", "MEDIUM"))
            fin_score -= 5

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
            risk_factors.append(("Cash flow stress: marja negativa + capital negativ", "HIGH"))
        elif profit_margin < 0.01 and ca_val > 1_000_000:
            risk_factors.append(("Marja profit sub 1% la CA > 1M — posibil cash flow strain", "MEDIUM"))
            fin_score -= 5

    dimensions["financiar"] = {"score": max(0, min(100, fin_score)), "weight": 30}

    # --- JURIDIC (20%) ---
    jur_score = 85
    insolvency = risk_data.get("insolvency", {})
    if isinstance(insolvency, dict):
        val = insolvency.get("value", {})
        if isinstance(val, dict) and val.get("found"):
            jur_score -= 60
            risk_factors.append(("Mentiune insolventa gasita", "HIGH"))

    litigation = risk_data.get("litigation", {})
    if isinstance(litigation, dict):
        val = litigation.get("value", {})
        if isinstance(val, dict):
            lit_count = val.get("count", 0)
            if lit_count > 5:
                jur_score -= 30
                risk_factors.append(("Numar ridicat de litigii (5+)", "MEDIUM"))
            elif lit_count > 3:
                jur_score -= 15
                risk_factors.append(("Litigii multiple gasite", "LOW"))
            elif val.get("found"):
                jur_score -= 5
                risk_factors.append(("Litigii gasite", "LOW"))

    dimensions["juridic"] = {"score": max(0, min(100, jur_score)), "weight": 20}

    # --- FISCAL (15%) ---
    fisc_score = 90
    anaf_inactive = risk_data.get("anaf_inactive", {})
    if isinstance(anaf_inactive, dict) and anaf_inactive.get("value"):
        fisc_score -= 50
        risk_factors.append(("Firma inactiva la ANAF", "HIGH"))

    platitor = financial.get("platitor_tva", {})
    if isinstance(platitor, dict) and platitor.get("value") is False:
        fisc_score -= 10
        risk_factors.append(("Neplatitor TVA", "LOW"))

    split_tva = financial.get("split_tva", {})
    if isinstance(split_tva, dict) and split_tva.get("value"):
        fisc_score -= 15
        risk_factors.append(("Split TVA activ", "LOW"))

    dimensions["fiscal"] = {"score": max(0, min(100, fisc_score)), "weight": 15}

    # --- OPERATIONAL (15%) --- with age adjustment (8B)
    op_score = 70
    angajati_val = _fval(financial.get("numar_angajati", {}))
    if angajati_val is not None:
        if angajati_val >= 50:
            op_score += 15
        elif angajati_val >= 10:
            op_score += 10
        elif angajati_val >= 1:
            op_score += 5
        elif angajati_val == 0:
            op_score -= 10
            if ca_val and ca_val > 1_000_000:
                risk_factors.append(("0 angajati + CA > 1M RON = SUSPECT", "HIGH"))
                op_score -= 20

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
        except (ValueError, IndexError):
            pass

    if company_age_years is not None:
        if company_age_years >= 10:
            op_score += 10
            if profit_val is not None and profit_val < 0:
                risk_factors.append(("Firma >10 ani cu pierderi = regres", "MEDIUM"))
                op_score -= 10
        elif company_age_years >= 5:
            op_score += 5
        elif company_age_years < 2:
            # Startup tolerance — reduce penalties
            if profit_val is not None and profit_val < 0:
                op_score += 5  # compensare: startup cu pierderi e normal
                risk_factors.append(("Firma <2 ani cu pierderi (toleranta startup)", "LOW"))

    # Angajati trend (8B)
    if isinstance(trend_val, dict):
        ang_trend = trend_val.get("numar_mediu_salariati", {})
        ang_growth = ang_trend.get("growth_percent")
        if ang_growth is not None and ang_growth < -50:
            op_score -= 15
            risk_factors.append((f"Reducere angajati {ang_growth:.0f}%", "HIGH"))

    dimensions["operational"] = {"score": max(0, min(100, op_score)), "weight": 15}

    # --- REPUTATIONAL (10%) --- nuantat (8B)
    rep_score = 50
    web = verified.get("web_presence", {})
    if isinstance(web, dict):
        categories = len(web)
        if categories >= 3:
            rep_score = 80
        elif categories >= 2:
            rep_score = 70
        elif categories >= 1:
            rep_score = 60
    elif web:
        rep_score = 65

    dimensions["reputational"] = {"score": max(0, min(100, rep_score)), "weight": 10}

    # --- PIATA (10%) ---
    mkt_score = 50
    market = verified.get("market", {})
    if isinstance(market, dict) and market:
        mkt_score = 70
        # C4 fix: Unwrap _make_field wrapper to access actual SEAP data
        seap = market.get("seap", {})
        seap_val = seap.get("value", seap) if isinstance(seap, dict) else {}
        if isinstance(seap_val, dict) and (seap_val.get("total_contracts", 0) or 0) > 0:
            mkt_score += 10

    # Benchmark comparison bonus (8B)
    benchmark = verified.get("benchmark", {})
    sector_position = {}
    if isinstance(benchmark, dict) and benchmark.get("available"):
        comparisons = benchmark.get("comparisons", [])
        above_avg = sum(1 for c in comparisons if isinstance(c, dict) and c.get("ratio", 0) > 1)
        if above_avg >= 2:
            mkt_score += 10
        elif above_avg >= 1:
            mkt_score += 5

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
            risk_factors.append((f"Pozitie sector: {', '.join(f'{k}={v['estimated_percentile']}' for k, v in sector_position.items())}", "INFO"))

    dimensions["piata"] = {"score": max(0, min(100, mkt_score)), "weight": 10}

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

    # B7 fix: Apply confidence weighting — low confidence pulls score toward neutral 50
    NEUTRAL_SCORE = 50
    for dim_name, dim_data in dimensions.items():
        dim_conf = confidence.get(dim_name, 0.5)
        raw = dim_data["score"]
        dim_data["score"] = round(raw * dim_conf + NEUTRAL_SCORE * (1 - dim_conf), 1)
        dim_data["confidence"] = dim_conf

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

    # 9B: Anomaly flags for synthesis feedback loop
    anomalies = []
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
    }
