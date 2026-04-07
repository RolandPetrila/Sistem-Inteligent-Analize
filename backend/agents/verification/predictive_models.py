"""
Modele predictive financiare — Altman Z''-EMS, Piotroski F, Beneish M, Zmijewski X.
Extrase din scoring.py pentru separarea responsabilitatilor (F9-2).
"""


def calculate_altman_z_ems(bilant: dict) -> dict:
    """
    Altman Z''-Score pentru firme emergente (non-cotate la bursa).
    Formula EMS: Z'' = 3.25 + 6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X4
    Zone: Z > 2.60 = SAFE | 1.10-2.60 = GREY | < 1.10 = DISTRESS
    Disclaimer: praguri calibrate pe piata americana — zona gri recomandata 1.00-2.90 pentru Romania
    """
    TA = bilant.get("total_active", bilant.get("active_totale", 0))
    if not TA or TA <= 0:
        return {
            "z_score": None,
            "zone": "INDISPONIBIL",
            "confidence": 0,
            "disclaimer": "Active totale indisponibile — scor nu poate fi calculat",
        }

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
        "x_values": {
            "X1": round(X1, 3),
            "X2": round(X2, 3),
            "X3": round(X3, 3),
            "X4": round(X4, 3),
        },
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
        return {
            "f_score": None,
            "grade": "INSUFICIENT",
            "criteria": [],
            "reason": "Date bilant indisponibile",
        }

    TA = bilant_t.get("active_totale", bilant_t.get("total_active", 0)) or 1
    profit = bilant_t.get("profit_net", 0) or 0
    ca = bilant_t.get("cifra_afaceri", 0) or 0

    # F1: ROA pozitiv
    f1 = 1 if (profit / TA) > 0 else 0

    # F2: Cash flow operational pozitiv (estimat din profit)
    cfo = bilant_t.get("cash_flow_operational", profit * 1.1)
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
        f6 = 1 if cap_t <= cap_t1 * 1.2 else 0

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
        return {
            "m_score": None,
            "risk": "INDISPONIBIL",
            "available": False,
            "reason": "CA zero sau negativa",
        }

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

    # TATA: Total Accruals to Total Assets (proxy)
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
        "components": {
            "DSRI": round(dsri, 3),
            "GMI": round(gmi, 3),
            "AQI": round(aqi, 3),
            "SGI": round(sgi, 3),
            "TATA": round(tata, 3),
        },
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
        return {
            "x_score": None,
            "distress": None,
            "available": False,
            "reason": "Active totale indisponibile",
        }

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
        "interpretation": (
            "Probabilitate ridicata de distres financiar"
            if distress
            else "Fara semnal de distres"
        ),
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

    bilant_curent: dict = {}

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
    piotroski = calculate_piotroski_f(bilant_curent)
    beneish = calculate_beneish_m(bilant_curent)
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
