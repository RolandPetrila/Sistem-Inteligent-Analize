"""
Completeness check logic — 0% toleranta la date nedocumentate.
Extras din agent_verification.py pentru modularitate.
"""


def check_completeness(verified: dict, official: dict, market: dict) -> dict:
    """
    Verifica completitudinea raportului si raporteaza FIECARE camp lipsa.
    0% toleranta la date nedocumentate.
    """
    gaps = []
    total_checks = 0
    passed_checks = 0

    # --- Profil firma ---
    company = verified.get("company", {})
    profile_fields = [
        ("cui", "CUI firma"),
        ("denumire", "Denumire firma"),
        ("adresa", "Adresa sediu"),
        ("stare_inregistrare", "Stare inregistrare"),
        ("data_inregistrare", "Data inregistrare"),
        ("platitor_tva", "Status TVA"),
        ("caen_code", "Cod CAEN"),
        ("caen_description", "Descriere CAEN"),
    ]
    for field_key, field_name in profile_fields:
        total_checks += 1
        f = company.get(field_key)
        if f and isinstance(f, dict) and f.get("value") not in (None, "", "N/A"):
            passed_checks += 1
        elif f and not isinstance(f, dict) and f not in (None, "", "N/A"):
            passed_checks += 1
        else:
            gaps.append({
                "field": field_name,
                "section": "Profil firma",
                "severity": "HIGH" if field_key in ("cui", "denumire", "caen_code") else "MEDIUM",
                "reason": "Sursa nu a returnat date sau camp absent",
            })

    # --- Actionariat ---
    total_checks += 1
    actionariat = verified.get("actionariat", {})
    if actionariat.get("available"):
        passed_checks += 1
    else:
        gaps.append({
            "field": "Actionariat (asociati + administratori)",
            "section": "Actionariat",
            "severity": "HIGH",
            "reason": "openapi.ro nu a returnat date ONRC structurate",
        })

    # --- Date financiare ---
    financial = verified.get("financial", {})
    # Mapping from verified field key to bilant trend metric key
    fin_fields = [
        ("cifra_afaceri", "Cifra de afaceri", "cifra_afaceri_neta"),
        ("profit_net", "Profit net", "profit_net"),
        ("numar_angajati", "Numar angajati", "numar_mediu_salariati"),
    ]
    trend_field = financial.get("trend_financiar", {})
    trend_val = trend_field.get("value", {}) if isinstance(trend_field, dict) else {}
    for field_key, field_name, trend_key in fin_fields:
        total_checks += 1
        f = financial.get(field_key)
        if f and isinstance(f, dict) and f.get("value") is not None:
            passed_checks += 1
        elif isinstance(trend_val, dict) and trend_val.get(trend_key, {}).get("values"):
            # Fallback: trend data has historical values for this metric
            passed_checks += 1
        else:
            gaps.append({
                "field": field_name,
                "section": "Financiar",
                "severity": "HIGH",
                "reason": "ANAF Bilant nu a returnat date",
            })

    # --- CAEN Context ---
    total_checks += 1
    if verified.get("caen_context", {}).get("available"):
        passed_checks += 1
    else:
        gaps.append({
            "field": "Context sector CAEN (nr firme, benchmark)",
            "section": "CAEN",
            "severity": "MEDIUM",
            "reason": "Cod CAEN nedisponibil sau INS TEMPO nereachabil",
        })

    # --- Benchmark ---
    total_checks += 1
    benchmark = verified.get("benchmark", {})
    if benchmark.get("available"):
        passed_checks += 1
    else:
        gaps.append({
            "field": "Benchmark financiar sector",
            "section": "Benchmark",
            "severity": "MEDIUM",
            "reason": "Necesita CAEN context + date financiare firma",
        })

    # --- SEAP/Market ---
    total_checks += 1
    market_verified = verified.get("market", {})
    seap_data = market.get("seap", {})
    # B6 fix: Check actual SEAP data, not bare dict truthiness
    seap_contracts = seap_data.get("total_contracts", 0) or 0
    if seap_contracts > 0:
        passed_checks += 1
    else:
        gaps.append({
            "field": "Contracte publice SEAP",
            "section": "Piata",
            "severity": "MEDIUM",
            "reason": "SEAP nu a returnat contracte sau Agent 3 nu a fost activat",
        })

    # --- Litigii ---
    total_checks += 1
    risk = verified.get("risk", {})
    if risk.get("litigation"):
        passed_checks += 1
    else:
        gaps.append({
            "field": "Verificare litigii",
            "section": "Risc",
            "severity": "MEDIUM",
            "reason": "portal.just.ro nu a returnat date via Tavily",
        })

    score = round((passed_checks / max(total_checks, 1)) * 100)

    return {
        "score": score,
        "total_checks": total_checks,
        "passed": passed_checks,
        "gaps": gaps,
        "gaps_count": len(gaps),
        "quality_level": (
            "COMPLET" if score >= 90 else
            "BUN" if score >= 70 else
            "PARTIAL" if score >= 50 else
            "INCOMPLET"
        ),
    }
