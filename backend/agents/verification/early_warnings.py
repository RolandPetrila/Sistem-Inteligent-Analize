"""F13: Early Warning Signals — extracted from agent_verification.py."""

from loguru import logger


def detect_early_warnings(official: dict) -> list[dict]:
    """
    DF5: Early Warning Signals — detecteaza semnale de alarma din trend multi-an.
    Reguli: scadere CA >30% YoY, pierdere 2 ani consecutivi, reducere angajati >50%.
    """
    warnings = []
    bilant = official.get("financial_official", {})
    if not isinstance(bilant, dict):
        return warnings

    bilant_data = bilant.get("data", {})
    if not bilant_data or len(bilant_data) < 2:
        return warnings

    years = sorted(bilant_data.keys())

    # Regula 1: Scadere CA > 30% YoY
    for i in range(1, len(years)):
        prev_year = years[i - 1]
        curr_year = years[i]
        prev = bilant_data.get(prev_year, {})
        curr = bilant_data.get(curr_year, {})

        ca_prev = prev.get("cifra_afaceri_neta")
        ca_curr = curr.get("cifra_afaceri_neta")
        if ca_prev and ca_curr and isinstance(ca_prev, (int, float)) and isinstance(ca_curr, (int, float)):
            if ca_prev > 0:
                change_pct = ((ca_curr - ca_prev) / ca_prev) * 100
                if change_pct < -30:
                    warnings.append({
                        "signal": "Scadere CA > 30%",
                        "severity": "HIGH",
                        "detail": f"CA a scazut cu {abs(change_pct):.0f}% din {prev_year} ({ca_prev:,.0f} RON) in {curr_year} ({ca_curr:,.0f} RON)",
                        "years": f"{prev_year}-{curr_year}",
                    })

    # Regula 2: Pierdere 2 ani consecutivi
    consecutive_loss = 0
    loss_years = []
    for year in years:
        data = bilant_data.get(year, {})
        profit = data.get("profit_net")
        pierdere = data.get("pierdere_neta")
        is_loss = (profit is not None and profit < 0) or (pierdere is not None and pierdere > 0)
        if is_loss:
            consecutive_loss += 1
            loss_years.append(year)
        else:
            if consecutive_loss >= 2:
                warnings.append({
                    "signal": "Pierdere consecutiva 2+ ani",
                    "severity": "HIGH",
                    "detail": f"Pierdere neta in anii: {', '.join(loss_years[-consecutive_loss:])}",
                    "years": f"{loss_years[-consecutive_loss]}-{loss_years[-1]}",
                })
            consecutive_loss = 0
            loss_years = []

    if consecutive_loss >= 2:
        warnings.append({
            "signal": "Pierdere consecutiva 2+ ani",
            "severity": "HIGH",
            "detail": f"Pierdere neta in anii: {', '.join(loss_years[-consecutive_loss:])}",
            "years": f"{loss_years[-consecutive_loss]}-{loss_years[-1]}",
        })

    # Regula 3: Reducere angajati > 50%
    for i in range(1, len(years)):
        prev_year = years[i - 1]
        curr_year = years[i]
        prev = bilant_data.get(prev_year, {})
        curr = bilant_data.get(curr_year, {})

        ang_prev = prev.get("numar_mediu_salariati")
        ang_curr = curr.get("numar_mediu_salariati")
        if (ang_prev and ang_curr
                and isinstance(ang_prev, (int, float))
                and isinstance(ang_curr, (int, float))
                and ang_prev > 0):
            change_pct = ((ang_curr - ang_prev) / ang_prev) * 100
            if change_pct < -50:
                warnings.append({
                    "signal": "Reducere angajati > 50%",
                    "severity": "MEDIUM",
                    "detail": f"Angajati: {int(ang_prev)} ({prev_year}) -> {int(ang_curr)} ({curr_year}), scadere {abs(change_pct):.0f}%",
                    "years": f"{prev_year}-{curr_year}",
                })

    # E11: BPI insolventa warning
    bpi = official.get("bpi_insolventa", {})
    if isinstance(bpi, dict) and bpi.get("found"):
        bpi_status = bpi.get("status", "insolventa")
        warnings.append({
            "signal": "Firma in procedura de insolventa",
            "severity": "CRITICAL",
            "detail": f"BPI: {bpi.get('details', bpi_status)}",
            "confidence": 95,
        })

    # E11: ANAF inactiv warning
    anaf_inactiv = official.get("anaf_inactiv", {})
    if isinstance(anaf_inactiv, dict) and anaf_inactiv.get("inactiv"):
        warnings.append({
            "signal": "Contribuabil inactiv ANAF",
            "severity": "CRITICAL",
            "detail": f"Data inactivare: {anaf_inactiv.get('data_inactivare', 'N/A')}",
            "confidence": 99,
        })

    if warnings:
        logger.warning(f"[verification] Early warnings: {len(warnings)} semnale detectate")
    return warnings
