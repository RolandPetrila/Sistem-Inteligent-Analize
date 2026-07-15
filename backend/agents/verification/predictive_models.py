"""
Modele predictive financiare — Altman Z''-EMS, Piotroski F, Beneish M, Zmijewski X.
Extrase din scoring.py pentru separarea responsabilitatilor (F9-2).

LIMITA DE DATE (verificata la sursa 2026-07-15 pe ANAF Bilant, CUI 26313362 firma
mica + CUI 6719278 firma mare, ani 2023+2024): endpoint-ul public ANAF Bilant
expune un format simplificat I1-I20 cu o SINGURA linie "DATORII" (I7), FARA split
curent/necurent. Identitatea bilantiera se inchide EXACT (diff=0 pe toate cele 4
firma-ani verificate): I1+I2+I6 == I10+I7+I9+I8, ceea ce confirma ca I7 e
TOTALUL datoriilor (nu doar cele pe termen scurt) — deci X4 (capitaluri/datorii
totale) din Altman si TD/TA din Zmijewski sunt CORECTE.

Consecinta: `datorii_curente` NU e obtenabil din aceasta sursa, deci capitalul
circulant net (WC = active curente - datorii curente) NU e calculabil. Vezi
`calculate_altman_z_ems` pentru cum e tratat (INDISPONIBIL, NU X1=0 tacut).
"""


def _num(bilant: dict, key: str) -> float | None:
    """Citeste o valoare numerica, distingand ABSENT (None) de ZERO (0.0).
    Codul de dinainte folosea `bilant.get(k, 0) or 0`, care colapseaza cele
    doua cazuri — sursa modului de esec reparat 2026-07-15 (X1=0 tacut)."""
    v = bilant.get(key)
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    return None


def calculate_altman_z_ems(bilant: dict) -> dict:
    """
    Altman Z''-Score pentru firme emergente (non-cotate la bursa).
    Formula EMS: Z'' = 3.25 + 6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X4
    Zone: Z > 2.60 = SAFE | 1.10-2.60 = GREY | < 1.10 = DISTRESS
    Disclaimer: praguri calibrate pe piata americana — zona gri recomandata 1.00-2.90 pentru Romania

    Necesita OBLIGATORIU `active_curente` SI `datorii_curente` pentru X1 (capital
    circulant net / active totale). X1 are coeficientul 6.56 — cel mai greu din
    formula, pe o scala unde banda gri intreaga are latimea 1.50 (1.10-2.60).
    Un X1 zeroit tacit deplaseaza Z cu pana la ~2.3 pentru o firma tipica, adica
    MAI MULT decat latimea benzii gri: poate transforma un DISTRESS real in SAFE.
    Nu e o estimare degradata, e o moneda aruncata cu aparenta de autoritate —
    si alimenteaza kill-switch-ul de expunere comerciala (credit_exposure.py).
    De aceea, daca lipsesc componentele WC -> INDISPONIBIL, cu motivul REAL.
    """
    TA = bilant.get("total_active", bilant.get("active_totale", 0))
    if not TA or TA <= 0:
        return {
            "z_score": None,
            "zone": "INDISPONIBIL",
            "confidence": 0,
            "reason": "Active totale indisponibile",
            "disclaimer": "Active totale indisponibile — scor nu poate fi calculat",
        }

    # X1 = Capital circulant net / Active totale
    active_curente = _num(bilant, "active_curente")
    datorii_curente = _num(bilant, "datorii_curente")
    if active_curente is None or datorii_curente is None:
        return {
            "z_score": None,
            "zone": "INDISPONIBIL",
            "confidence": 0,
            "reason": "Lipsa split datorii curente/necurente (ANAF Bilant expune o singura linie DATORII)",
            "disclaimer": (
                "Capitalul circulant net (X1) nu e calculabil din datele disponibile. "
                "X1 are coeficientul 6.56 din formula Z'' — mai mare decat intreaga "
                "banda gri (1.10-2.60), deci un scor calculat cu X1=0 ar putea indica "
                "SAFE pentru o firma in DISTRESS real. Scorul e raportat INDISPONIBIL "
                "in loc sa fie raportat gresit."
            ),
        }
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

    # F2: Cash flow operational pozitiv. F3: CFO > Profit net (calitate accruals).
    # `cash_flow_operational` NU e scris NICAIERI in backend (verificat prin grep
    # 2026-07-15, confirmat separat in `calculate_beneish_m` mai jos). Proxy-ul
    # anterior `profit * 1.1` facea ca semnul lui cfo sa fie IDENTIC cu semnul
    # lui profit -> F2 == F1 mereu (acelasi test, profit>0). Si cfo > profit se
    # reduce la 1.1*profit > profit, adevarat DOAR cand profit>0 -> F3 == F1
    # mereu. Deci 3 din 9 criterii (33%) erau, de fapt, un singur semnal (semnul
    # profitului) repetat de 3 ori — nu 3 masuratori independente ale calitatii
    # cash-flow-ului. Acelasi mod de esec ca F5/F7: date lipsa -> criteriu
    # nemasurabil -> None, nu un punct (sau un ecou al lui F1) deghizat in calcul.
    cfo = _num(bilant_t, "cash_flow_operational")
    if cfo is None:
        f2 = None
        f3 = None
    else:
        f2 = 1 if cfo > 0 else 0
        f3 = 1 if profit and cfo > profit else 0

    if bilant_t1:
        TA1 = bilant_t1.get("active_totale", bilant_t1.get("total_active", 0)) or 1
        profit1 = bilant_t1.get("profit_net", 0) or 0
        ca1 = bilant_t1.get("cifra_afaceri", 0) or 0
        datorii_t = bilant_t.get("total_datorii", 0) or 0
        datorii_t1 = bilant_t1.get("total_datorii", 0) or 0

        # F4: Leverage scazut (datorii/active mai mic)
        lev_t = datorii_t / TA
        lev_t1 = datorii_t1 / TA1
        f4 = 1 if lev_t <= lev_t1 else 0

        # F5: Lichiditate curenta imbunatatita.
        # Necesita split datorii curente/necurente, pe care ANAF Bilant nu-l
        # expune. Versiunea anterioara facea `.get(..., 0) or 1` -> compara
        # 0/1 >= 0/1 -> acorda punctul MEREU, fara sa masoare nimic. Intr-un
        # detector de faliment, un punct gratuit inclina scorul spre STRONG =
        # fals confort. Criteriu nemasurabil -> None, nu 1.
        active_cur_t = _num(bilant_t, "active_curente")
        active_cur_t1 = _num(bilant_t1, "active_curente")
        datorii_cur_t = _num(bilant_t, "datorii_curente")
        datorii_cur_t1 = _num(bilant_t1, "datorii_curente")
        if (
            None in (active_cur_t, active_cur_t1, datorii_cur_t, datorii_cur_t1)
            or not datorii_cur_t
            or not datorii_cur_t1
        ):
            f5 = None
        else:
            liq_t = active_cur_t / datorii_cur_t
            liq_t1 = active_cur_t1 / datorii_cur_t1
            f5 = 1 if liq_t >= liq_t1 else 0

        # F6: Fara emisiune de actiuni noi (capital propriu relativ stabil)
        cap_t = bilant_t.get("capitaluri_proprii", 0) or 0
        cap_t1 = bilant_t1.get("capitaluri_proprii", 0) or 0
        f6 = 1 if cap_t <= cap_t1 * 1.2 else 0

        # F7: Marja bruta imbunatatita. Acelasi mod de esec ca F5: fara
        # `cheltuieli_materiale` (absent din ANAF Bilant), marja devenea
        # (ca-0)/ca = 1.0 in ambii ani -> 1 >= 1 -> punct gratuit mereu.
        chm_t = _num(bilant_t, "cheltuieli_materiale")
        chm_t1 = _num(bilant_t1, "cheltuieli_materiale")
        if chm_t is None or chm_t1 is None or ca <= 0 or ca1 <= 0:
            f7 = None
        else:
            marja_t = (ca - chm_t) / ca
            marja_t1 = (ca1 - chm_t1) / ca1
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

    # Pragurile originale (7 si 4) sunt calibrate pe 9 criterii. Cand unele
    # criterii sunt nemasurabile (F2/F3 fara cash-flow operational real, F5
    # fara split datorii curente/necurente, F7 fara cheltuieli materiale — toate
    # patru absente din ANAF Bilant), un prag absolut de 7 devine aproape
    # imposibil de atins din cele 5 criterii ramase disponibile (F1/F4/F6/F8/F9)
    # -> orice firma ar aparea WEAK/AVERAGE artificial. Scalam proportional:
    # raportul 7/9 si 4/9 se pastreaza. Pe cazul complet (9 criterii, cand o
    # sursa viitoare aduce toate componentele) rezultatul e IDENTIC cu pragurile
    # absolute anterioare. `max_possible` de mai jos raporteaza numitorul REAL
    # (5, nu 7 sau 9) — onest despre cate criterii au fost chiar evaluate.
    if len(available) < 5:
        grade = "INSUFICIENT"
    else:
        ratio = f_score / len(available)
        if ratio >= 7 / 9:
            grade = "STRONG"
        elif ratio >= 4 / 9:
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


def _screening_signals(dsri: float, aqi: float, sgi: float) -> list[dict]:
    """Semnale de screening din indicii Beneish REALI (calculati din date ANAF
    autentice: creante, cifra de afaceri, active totale, active imobilizate).

    Separate deliberat de verdictul M-score: acesta din urma e o ACUZATIE si nu
    se poate publica cand 2 din 5 intrari sunt fabricate (vezi gate-ul din
    `calculate_beneish_m`). Semnalele de mai jos sunt insa FAPTE masurate — se
    raporteaza ca "merita verificat manual", niciodata ca frauda.

    Pragurile sunt orientative si deliberat conservatoare (crestere >= 1.5x fata
    de anul anterior). NU pretind calibrare pe praguri din literatura, tocmai ca
    sa nu inlocuim un numar nefondat cu altul.
    """
    signals: list[dict] = []
    if dsri >= 1.5:
        signals.append({
            "cod": "DSRI",
            "valoare": round(dsri, 3),
            "eticheta": "Creante in crestere accelerata fata de vanzari",
            "detaliu": (
                f"Raportul creante/cifra de afaceri a crescut de {dsri:.2f}x fata de anul "
                "anterior. Poate indica incasari intarziate, relaxarea termenelor de plata "
                "sau venituri recunoscute mai devreme decat incasarea. Merita verificat manual "
                "(vechimea creantelor, concentrarea pe clienti) — NU e un indiciu de frauda."
            ),
            "severitate": "ATENTIE" if dsri >= 2.0 else "INFO",
        })
    if aqi >= 1.5:
        signals.append({
            "cod": "AQI",
            "valoare": round(aqi, 3),
            "eticheta": "Ponderea activelor non-imobilizate a crescut",
            "detaliu": (
                f"Indicele calitatii activelor e {aqi:.2f}x fata de anul anterior. "
                "Merita verificat ce anume a crescut in activele circulante."
            ),
            "severitate": "INFO",
        })
    if sgi >= 1.5:
        signals.append({
            "cod": "SGI",
            "valoare": round(sgi, 3),
            "eticheta": "Crestere rapida a cifrei de afaceri",
            "detaliu": (
                f"Cifra de afaceri a crescut de {sgi:.2f}x fata de anul anterior. "
                "Cresterea rapida nu e negativa in sine, dar creste presiunea pe "
                "capitalul de lucru."
            ),
            "severitate": "INFO",
        })
    return signals


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

    # Activele totale sunt OBLIGATORII (numitor in AQI si TATA). Codul anterior
    # facea `.get("active_totale", 0) or 1` -> cu activele lipsa, TA devenea 1 si
    # TATA = (profit - cfo)/1 = zeci de milioane, cu coeficientul 7.770 -> M-score
    # de ordinul 1e8 si verdict "MANIPULATOR_PROBABIL" pe o firma perfect sanatoasa.
    # Verificat LIVE 2026-07-15 (CUI 6719278): M = 97.001.528 — o acuzatie falsa de
    # manipulare contabila, cu aparenta de autoritate. Mod de esec inaccesibil
    # inainte (Beneish era mereu INDISPONIBIL din lipsa anului anterior), deschis
    # exact de cablarea lui bilant_t1. Fara active totale -> INDISPONIBIL.
    TA_t_raw = _num(bilant_t, "active_totale") or _num(bilant_t, "total_active")
    TA_t1_raw = _num(bilant_t1, "active_totale") or _num(bilant_t1, "total_active")
    if not TA_t_raw or not TA_t1_raw or TA_t_raw <= 0 or TA_t1_raw <= 0:
        return {
            "m_score": None,
            "risk": "INDISPONIBIL",
            "available": False,
            "reason": "Active totale indisponibile pentru unul din cei 2 ani (necesare in AQI si TATA)",
        }

    receivables_t = bilant_t.get("creante", bilant_t.get("active_curente", 0) * 0.4) or 0
    receivables_t1 = bilant_t1.get("creante", bilant_t1.get("active_curente", 0) * 0.4) or 0

    # DSRI: Days Sales Receivables Index
    dsri = (receivables_t / ca_t) / (receivables_t1 / ca_t1) if ca_t1 > 0 and receivables_t1 >= 0 else 1.0

    # GMI: Gross Margin Index. `cheltuieli_materiale` NU exista in ANAF Bilant
    # (0 hituri in name_map), iar default-ul proportional (ca*0.7) produce aceeasi
    # marja in ambii ani -> GMI = exact 1.0 pentru ORICE firma. Slot umplut cu
    # non-informatie, dar cu pondere fixa 0.906 in formula.
    gmi_masurabil = (
        _num(bilant_t, "cheltuieli_materiale") is not None
        and _num(bilant_t1, "cheltuieli_materiale") is not None
    )
    gm_t = (ca_t - bilant_t.get("cheltuieli_materiale", ca_t * 0.7)) / ca_t
    gm_t1 = (ca_t1 - bilant_t1.get("cheltuieli_materiale", ca_t1 * 0.7)) / ca_t1
    gmi = (gm_t1 / gm_t) if gm_t > 0 else 1.0

    # AQI: Asset Quality Index — REAL (TA + active_imobilizate vin din ANAF)
    TA_t = TA_t_raw
    TA_t1 = TA_t1_raw
    imob_t = bilant_t.get("active_imobilizate", TA_t * 0.4) or 0
    imob_t1 = bilant_t1.get("active_imobilizate", TA_t1 * 0.4) or 0
    aqi = ((TA_t - imob_t) / TA_t) / ((TA_t1 - imob_t1) / TA_t1) if TA_t1 > 0 else 1.0

    # SGI: Sales Growth Index — REAL
    sgi = ca_t / ca_t1

    # TATA: `cash_flow_operational` NU e scris NICAIERI in tot backend-ul (verificat
    # prin grep: doar citit, cu default). Deci cfo_t = profit_t * 0.9 MEREU, iar
    # tata = (profit - 0.9*profit)/TA = 0.1 * ROA, DETERMINIST. Nu e un indice de
    # angajamente contabile (diferenta profit contabil vs cash real) — e ROA
    # rescalat si deghizat, purtand coeficientul 7.770, cel mai greu din formula.
    tata_masurabil = _num(bilant_t, "cash_flow_operational") is not None

    # TATA: Total Accruals to Total Assets (proxy)
    profit_t = bilant_t.get("profit_net", 0) or 0
    cfo_t = bilant_t.get("cash_flow_operational", profit_t * 0.9) or profit_t
    tata = (profit_t - cfo_t) / TA_t if TA_t > 0 else 0

    indici_cu_semnal = 3 + int(gmi_masurabil) + int(tata_masurabil)

    # GATE (2026-07-15): daca GMI sau TATA nu sunt masurabile, M-score-ul NU se
    # publica, si mai ales NU se publica eticheta acuzatoare.
    # Aritmetica, aceeasi disciplina ca la Altman X1: banda de decizie are latimea
    # 0.44 (-2.22 -> -1.78). GMI intra cu 0.906 FIX; o variatie reala plauzibila de
    # +-0.2 a GMI ar misca M cu +-0.18 = 41% din banda. TATA e mai rau: coeficient
    # 7.770 x o variatie reala plauzibila de +-0.05 a angajamentelor = +-0.39,
    # aproape INTREAGA banda, de unul singur. Deci oricare din cele 2 intrari
    # fabricate poate rasturna singura verdictul OK <-> MANIPULATOR: nu e o
    # estimare degradata, e o aruncare de moneda — exact ce am refuzat la Altman.
    # Agravant fata de Altman: Beneish emite o ACUZATIE ("manipulator probabil")
    # despre o firma reala, cu nume si CUI, iar rapoartele pot fi partajate public
    # (/api/reports/public/* e exceptat de la autentificare). Rata reala de
    # fals-pozitiv a variantei reduse e NECUNOSCUTA.
    # Semnalul REAL nu se pierde: DSRI/AQI/SGI sunt calculati din date ANAF
    # autentice si se expun ca semnale de screening (mai jos), fara verdict.
    if not (gmi_masurabil and tata_masurabil):
        nemasurabili = []
        if not gmi_masurabil:
            nemasurabili.append("GMI (marja bruta — lipsesc cheltuielile materiale)")
        if not tata_masurabil:
            nemasurabili.append(
                "TATA (angajamente contabile — lipseste cash-flow-ul operational, "
                "proxy-ul il reduce determinist la 0.1 x ROA)"
            )
        return {
            "m_score": None,
            "risk": "INDISPONIBIL",
            "available": False,
            "indici_cu_semnal": indici_cu_semnal,
            "reason": (
                f"{5 - indici_cu_semnal} din 5 indici nu sunt masurabili din ANAF Bilant: "
                f"{'; '.join(nemasurabili)}. Pragurile (-2.22 / -1.78, banda de doar 0.44) "
                "sunt calibrate pentru toti 5 indici purtatori de semnal — cu intrari "
                "fabricate, verdictul de manipulare ar fi arbitrar."
            ),
            "screening_signals": _screening_signals(dsri, aqi, sgi),
            "indici_reali": {"DSRI": round(dsri, 3), "AQI": round(aqi, 3), "SGI": round(sgi, 3)},
            "disclaimer": (
                "M-score-ul NU se calculeaza din date ANAF gratuite. Indicii reali "
                "(DSRI/AQI/SGI) sunt expusi ca semnale de screening, fara verdict de "
                "manipulare contabila."
            ),
        }

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
        "confidence": 1,
        "indici_cu_semnal": indici_cu_semnal,
        "screening_signals": _screening_signals(dsri, aqi, sgi),
        "components": {
            "DSRI": round(dsri, 3),
            "GMI": round(gmi, 3),
            "AQI": round(aqi, 3),
            "SGI": round(sgi, 3),
            "TATA": round(tata, 3),
        },
        "disclaimer": (
            "Prag adaptat pentru IMM-uri Romania: M5 > -2.22 = investigat, > -1.78 = risc ridicat. "
            "Semnal de SCREENING (indica ce merita verificat manual), NU o concluzie de manipulare contabila."
        ),
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
    AC = _num(bilant, "active_curente")
    DC = _num(bilant, "datorii_curente")

    # Termenul de lichiditate (AC/DC) are coeficientul 0.004 — cu TREI ordine de
    # marime sub ceilalti doi termeni (4.513 si 5.679). Spre deosebire de X1 din
    # Altman (coef 6.56), omiterea lui NU poate rasturna verdictul: pentru un
    # raport curent tipic (1-3) contributia reala e 0.004-0.012, sub 1% dintr-un
    # x-score aflat uzual in [-4, +2]. De aceea Zmijewski RAMANE disponibil cand
    # ANAF nu expune split-ul de datorii — dar o declaram explicit, nu tacit.
    # ATENTIE: `or 1` din versiunea anterioara era o mina — daca cineva ar mapa
    # `active_curente` fara `datorii_curente`, AC/DC devenea AC/1 (miliarde x
    # 0.004 = milioane) si distrugea scorul. Acum tratam explicit ambele absente.
    liq_omis = AC is None or DC is None or DC <= 0
    liq_term = 0.0 if liq_omis else 0.004 * (AC / DC)

    x = -4.336 - 4.513 * (PN / TA) + 5.679 * (TD / TA) + liq_term
    x = round(x, 3)

    distress = x > 0

    result = {
        "x_score": x,
        "distress": distress,
        "available": True,
        "interpretation": (
            "Probabilitate ridicata de distres financiar"
            if distress
            else "Fara semnal de distres"
        ),
    }
    if liq_omis:
        result["confidence"] = 0.95
        result["disclaimer"] = (
            "Termenul de lichiditate (active curente / datorii curente) a fost omis — "
            "ANAF Bilant nu expune split-ul datorii curente/necurente. Coeficientul sau "
            "e 0.004, deci impactul asupra scorului e sub 1%; ceilalti doi termeni "
            "(rentabilitate si indatorare) sunt calculati din date complete."
        )
    else:
        result["confidence"] = 1
    return result


def _to_predictive_shape(raw: dict) -> dict:
    """Remapeaza cheile brute dintr-un an de ANAF Bilant (cifra_afaceri_neta,
    datorii_totale) la cheile pe care functiile de mai sus le citesc
    (cifra_afaceri, total_datorii). `active_totale`, `capitaluri_proprii`,
    `creante`, `active_imobilizate`, `profit_net`, `profit_brut` au deja acelasi
    nume in ambele parti si trec neschimbate.

    DE CE `active_circulante` NU e mapat la `active_curente`, desi in
    contabilitatea romaneasca sunt SINONIME (active circulante == current assets):
    perechea lui, `datorii_curente`, nu exista in ANAF Bilant (o singura linie
    "DATORII" — vezi nota din capul modulului). Fiecare consumator al lui
    `active_curente` are nevoie de AMBELE:
      - Altman X1 = (AC - DC)/TA -> cu DC absent, X1 = AC/TA supraevalueaza
        capitalul circulant cu INTREGUL pasiv curent, adica exact in directia
        "firma pare mai sanatoasa". Intr-un detector de faliment, o eroare
        sistematic optimista e mai rea decat lipsa scorului.
      - Zmijewski: termenul 0.004*(AC/DC) cu DC lipsa (default 1) devenea
        AC/1 -> miliarde * 0.004 = milioane -> x-score complet distrus.
      - Piotroski F5: AC/DC in ambii ani, aceeasi problema.
    Deci a mapa doar jumatate din pereche e net DAUNATOR. Ramane nemapat
    deliberat; consumatorii trateaza acum absenta explicit (nu tacit)."""
    shaped = dict(raw)
    if raw.get("cifra_afaceri_neta") is not None:
        shaped["cifra_afaceri"] = raw["cifra_afaceri_neta"]
    if raw.get("datorii_totale") is not None:
        shaped["total_datorii"] = raw["datorii_totale"]
    return shaped


def calculate_all_predictive_scores(verified_data: dict, official_data: dict | None = None) -> dict:
    """
    Calculeaza toate scorurile predictive dintr-o singura apelare.
    Input: verified_data (structura standard din agent_verification), optional
    official_data (state["official_data"] brut) — sursa PREFERATA pentru ca are
    setul complet de componente bilant (active_imobilizate/active_circulante/
    creante/active_totale) pentru MAI MULTI ani, necesar pentru Piotroski F4-F9
    si Beneish M (comparatie an-curent vs an-anterior). Daca official_data lipseste
    sau nu are bilant multi-an (ex: apeluri legacy/teste izolate), se cade pe
    reconstructia partiala din verified["financial"] (doar CA + profit net,
    fara comparatie an-pe-an).
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
    bilant_t1: dict | None = None

    bilant_official = (official_data or {}).get("financial_official", {})
    bilant_years = bilant_official.get("data", {}) if isinstance(bilant_official, dict) else {}

    if isinstance(bilant_years, dict) and bilant_years:
        valid_years = sorted(
            (
                y for y, d in bilant_years.items()
                if isinstance(d, dict) and d.get("cifra_afaceri_neta") is not None
            ),
            key=lambda y: int(y),
            reverse=True,
        )
        if valid_years:
            bilant_curent = _to_predictive_shape(bilant_years[valid_years[0]])
            if len(valid_years) >= 2:
                bilant_t1 = _to_predictive_shape(bilant_years[valid_years[1]])

    if not bilant_curent:
        # Fallback (comportament pre-existent): reconstruieste partial din
        # verified["financial"] cand nu avem acces la official_data brut.
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
    piotroski = calculate_piotroski_f(bilant_curent, bilant_t1)
    beneish = calculate_beneish_m(bilant_curent, bilant_t1)
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

    # Cate din cele 4 modele s-au putut calcula efectiv (nu doar "au rulat" —
    # un model INDISPONIBIL/INSUFICIENT nu a produs niciun semnal real).
    models_computed = []
    if altman.get("z_score") is not None:
        models_computed.append("Altman Z''")
    if piotroski.get("grade") != "INSUFICIENT":
        models_computed.append("Piotroski F")
    if beneish.get("available"):
        models_computed.append("Beneish M")
    if zmijewski.get("available"):
        models_computed.append("Zmijewski X")
    n_avail = len(models_computed)
    n_total = 4

    # FIX CRITIC: summary-ul NU mai poate linisti fals cand n_avail == 0 — asta
    # era cazul de esec cel mai periculos posibil (firma poate fi in dificultate
    # reala, dar raportul spunea "zona normala" pentru ca niciun model nu rulase).
    if n_avail == 0:
        summary = (
            "Niciun model predictiv nu a putut fi calculat — lipsesc datele de "
            "bilant necesare (active/datorii totale sau bilant pe 2 ani consecutivi "
            "pentru Piotroski/Beneish). Riscul de faliment NU a fost evaluat din "
            "aceasta sursa — nu se poate deduce ca firma e in zona normala."
        )
    elif distress_signals >= 3:
        summary = (
            f"Semnale multiple de distres financiar ({n_avail}/{n_total} modele "
            "calculate) — monitorizare urgenta recomandata"
        )
    elif distress_signals >= 2:
        summary = (
            f"Semnale de fragilitate financiara ({n_avail}/{n_total} modele "
            "calculate) — analiza aprofundata recomandata"
        )
    elif distress_signals == 1:
        summary = f"Firma in zona gri ({n_avail}/{n_total} modele calculate) — monitorizare periodica recomandata"
    elif n_avail < n_total:
        summary = (
            f"Indicatori financiari in zona normala din modelele disponibile "
            f"({n_avail}/{n_total} modele calculate — restul indisponibile din lipsa de date)"
        )
    else:
        summary = "Indicatori financiari in zona normala (toate cele 4 modele calculate)"

    # Semnalele de screening (indici Beneish REALI) se adauga la summary pentru ca
    # summary e deja randat identic in HTML/PDF/DOCX — asa semnalul real ajunge in
    # raport FARA a atinge cei 3 rendereri (si fara a pierde informatia cand
    # M-score-ul e suprimat de gate-ul anti-acuzatie).
    screening = beneish.get("screening_signals") or []
    if screening:
        etichete = "; ".join(f"{s['eticheta']} ({s['cod']} {s['valoare']:.2f}x)" for s in screening)
        summary += f". Semnale de verificat manual: {etichete}"

    return {
        "altman_z": altman,
        "piotroski_f": piotroski,
        "beneish_m": beneish,
        "zmijewski_x": zmijewski,
        "distress_signals": distress_signals,
        "models_available": n_avail,
        "models_total": n_total,
        "screening_signals": screening,
        "summary": summary,
    }
