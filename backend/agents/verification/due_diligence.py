"""F13: Due Diligence Checklist — extracted from agent_verification.py."""

from loguru import logger


def build_due_diligence(verified: dict, official: dict) -> list[dict]:
    """
    DF1: Due Diligence Checklist — lista DA/NU pentru verificare rapida.
    Fiecare item: name, status (DA/NU/INDISPONIBIL), severity (info/warning/critical), source.
    """
    checklist = []
    company = verified.get("company", {})
    financial = verified.get("financial", {})
    risk = verified.get("risk", {})
    anaf = official.get("anaf", {})

    # 1. Firma activa la ANAF
    inactiv = anaf.get("inactiv")
    checklist.append({
        "name": "Firma activa la ANAF",
        "status": "DA" if inactiv is False else "NU" if inactiv else "INDISPONIBIL",
        "severity": "critical" if inactiv else "info",
        "source": "ANAF",
    })

    # 2. Platitor TVA
    tva = anaf.get("platitor_tva")
    checklist.append({
        "name": "Platitor TVA",
        "status": "DA" if tva else "NU" if tva is False else "INDISPONIBIL",
        "severity": "info",
        "source": "ANAF",
    })

    # 3. Split TVA (negativ = bine)
    split = anaf.get("split_tva")
    checklist.append({
        "name": "Fara Split TVA",
        "status": "DA" if split is False else "NU" if split else "INDISPONIBIL",
        "severity": "warning" if split else "info",
        "source": "ANAF",
    })

    # 4. Fara insolventa
    insolvency = risk.get("insolvency", {})
    ins_val = insolvency.get("value", {}) if isinstance(insolvency, dict) else {}
    ins_found = ins_val.get("found", False) if isinstance(ins_val, dict) else False
    checklist.append({
        "name": "Fara insolventa",
        "status": "DA" if not ins_found else "NU",
        "severity": "critical" if ins_found else "info",
        "source": "BPI",
    })

    # Helper: extract latest value from trend if direct field is None
    trend_field = financial.get("trend_financiar", {})
    trend_val = trend_field.get("value", {}) if isinstance(trend_field, dict) else {}

    def _get_fin_val(field_key, trend_key):
        """Get financial value from direct field, fallback to trend last value."""
        f = financial.get(field_key, {})
        val = f.get("value") if isinstance(f, dict) else None
        if val is not None and isinstance(val, (int, float)):
            return val
        if isinstance(trend_val, dict):
            metric = trend_val.get(trend_key, {})
            if isinstance(metric, dict):
                values = metric.get("values", [])
                if values and isinstance(values[-1], dict):
                    tv = values[-1].get("value")
                    if tv is not None and isinstance(tv, (int, float)):
                        return tv
        return None

    # 5. Angajati > 0
    ang_val = _get_fin_val("numar_angajati", "numar_mediu_salariati")
    if ang_val is not None:
        checklist.append({
            "name": "Are angajati (>0)",
            "status": "DA" if ang_val > 0 else "NU",
            "severity": "warning" if ang_val == 0 else "info",
            "source": "ANAF Bilant",
        })
    else:
        checklist.append({
            "name": "Are angajati (>0)",
            "status": "INDISPONIBIL",
            "severity": "info",
            "source": "-",
        })

    # 6. Cifra de afaceri > 0
    ca_val = _get_fin_val("cifra_afaceri", "cifra_afaceri_neta")
    if ca_val is not None:
        checklist.append({
            "name": "Cifra de afaceri > 0",
            "status": "DA" if ca_val > 0 else "NU",
            "severity": "warning" if ca_val <= 0 else "info",
            "source": "ANAF Bilant",
        })
    else:
        checklist.append({
            "name": "Cifra de afaceri > 0",
            "status": "INDISPONIBIL",
            "severity": "info",
            "source": "-",
        })

    # 7. Profit pozitiv
    profit_val = _get_fin_val("profit_net", "profit_net")
    if profit_val is not None:
        checklist.append({
            "name": "Profit pozitiv",
            "status": "DA" if profit_val > 0 else "NU",
            "severity": "warning" if profit_val <= 0 else "info",
            "source": "ANAF Bilant",
        })
    else:
        checklist.append({
            "name": "Profit pozitiv",
            "status": "INDISPONIBIL",
            "severity": "info",
            "source": "-",
        })

    # 8. Capitaluri proprii pozitive
    cap_val = _get_fin_val("capitaluri_proprii", "capitaluri_proprii")
    if cap_val is not None:
        checklist.append({
            "name": "Capitaluri proprii pozitive",
            "status": "DA" if cap_val > 0 else "NU",
            "severity": "critical" if cap_val < 0 else "info",
            "source": "ANAF Bilant",
        })
    else:
        checklist.append({
            "name": "Capitaluri proprii pozitive",
            "status": "INDISPONIBIL",
            "severity": "info",
            "source": "-",
        })

    # 9. Date ONRC disponibile
    onrc = official.get("onrc_structured", {})
    has_onrc = isinstance(onrc, dict) and onrc.get("found", False)
    checklist.append({
        "name": "Date ONRC disponibile",
        "status": "DA" if has_onrc else "NU",
        "severity": "info",
        "source": "openapi.ro",
    })

    # 10. Fara anomalii SUSPECT
    anomalies = verified.get("anomalies", [])
    suspect_count = sum(1 for a in anomalies if a.get("level") == "SUSPECT")
    checklist.append({
        "name": "Fara anomalii suspecte",
        "status": "DA" if suspect_count == 0 else "NU",
        "severity": "critical" if suspect_count > 0 else "info",
        "source": "Analiza interna",
    })

    logger.info(f"[verification] Due diligence: {sum(1 for c in checklist if c['status'] == 'DA')}/{len(checklist)} OK")
    return checklist
