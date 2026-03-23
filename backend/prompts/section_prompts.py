"""
Prompt templates per sectiune de raport.
Fiecare primeste verified_data JSON si genereaza text narativ.
"""

SECTION_PROMPTS = {
    "executive_summary": {
        "title": "Rezumat Executiv",
        "prompt": (
            "Scrie un rezumat executiv de {word_count} cuvinte.\n"
            "Include: cine e firma, ce face, starea financiara pe scurt, riscuri cheie, "
            "oportunitate principala. Tonul: decisiv, concis, actionabil.\n"
            "Daca datele sunt limitate, mentioneaza explicit ce lipseste.\n\n"
            "EXEMPLU FRAGMENT (adapteaza la datele reale):\n"
            "\"SC EXEMPLU S.R.L. (CUI 12345678), infiintata in 2010, opereaza in domeniul "
            "constructiilor (CAEN 4120). Cu o cifra de afaceri de 2.3M RON in 2024 (+12% fata "
            "de 2023) si un profit net de 180K RON, firma prezinta o traiectorie ascendenta. "
            "Riscul principal identificat este dependenta de un singur client major (45% din CA).\""
        ),
        "word_count": {"1": 300, "2": 600, "3": 1000},
    },
    "company_profile": {
        "title": "Profil Companie",
        "prompt": (
            "Descrie firma pe baza datelor oficiale ANAF/ONRC.\n"
            "Include: denumire, CUI, CAEN, data infiintare, asociati, administrator, "
            "capital social, sediu, puncte de lucru.\n"
            "Marcheaza fiecare camp cu eticheta trust corespunzatoare.\n\n"
            "EXEMPLU FRAGMENT (adapteaza la datele reale):\n"
            "\"SC EXEMPLU S.R.L. (CUI 12345678), infiintata la 15.03.2010, cu sediul in Bucuresti, Sector 3. "
            "CAEN principal: 4120 — Lucrari de constructii a cladirilor rezidentiale si nerezidentiale. "
            "Capital social: 10,000 RON. Administrator: Ion Popescu (din 2010). "
            "Asociati: Ion Popescu (60%), Maria Popescu (40%). Puncte de lucru: 2 (Ilfov, Constanta). "
            "[Sursa: openapi.ro | Trust: OFICIAL]\""
        ),
        "word_count": {"1": 200, "2": 400, "3": 600},
    },
    "financial_analysis": {
        "title": "Analiza Financiara",
        "prompt": (
            "Analizeaza situatia financiara cu datele disponibile.\n"
            "Daca ai cifra de afaceri multi-an: trend si interpretare.\n"
            "Daca ai doar datorii ANAF: focuseaza pe solvabilitate.\n"
            "Daca datele sunt limitate: spune EXPLICIT ce lipseste si de ce.\n"
            "Include cursul BNR EUR/RON daca e relevant.\n"
            "Daca datele contin ratii financiare calculate (financial_ratios), prezinta-le intr-un tabel:\n"
            "| Ratio | Valoare | Interpretare |\n"
            "Ratiile standard: Marja Profit Net, ROE, ROA, Datorii/Capital, Rata Capitalizare, CA/Angajat.\n"
            "Interpreteaza fiecare valoare in contextul sectorului CAEN al firmei.\n\n"
            "EXEMPLU FRAGMENT:\n"
            "\"Evolutia cifrei de afaceri in ultimii 3 ani: 2022: 1.8M RON | 2023: 2.1M RON (+16%) "
            "| 2024: 2.3M RON (+9.5%). Profitul net a crescut de la 120K la 180K RON, cu o marja "
            "neta de 7.8%. Capitalurile proprii de 450K RON ofera un buffer de solvabilitate adecvat. "
            "[INDISPONIBIL] — Date despre datorii bancare nu au fost furnizate de surse.\""
        ),
        "word_count": {"1": 200, "2": 500, "3": 800},
    },
    "risk_assessment": {
        "title": "Evaluare Risc",
        "prompt": (
            "Evalueaza riscurile pe categorii: financiar, juridic, operational, reputational.\n"
            "Scor final: VERDE (risc scazut) / GALBEN (risc mediu) / ROSU (risc ridicat).\n"
            "Fiecare risc: descriere + sursa + severitate + recomandare.\n"
            "Baza analiza EXCLUSIV pe datele din JSON, nu pe presupuneri.\n\n"
            "EXEMPLU FRAGMENT:\n"
            "\"RISC FINANCIAR (severitate: MEDIE) — Marja de profit a scazut de la 9.2% la 7.8% "
            "in ultimul an. Sursa: ANAF Bilant 2024. Recomandare: monitorizare trimestriala a costurilor "
            "operationale.\n"
            "RISC JURIDIC (severitate: SCAZUTA) — Niciun litigiu activ identificat pe portal.just.ro.\""
        ),
        "word_count": {"1": 300, "2": 600, "3": 1000},
    },
    "competition": {
        "title": "Analiza Competitie",
        "prompt": (
            "Prezinta competitorii identificati in format tabel + analiza narativa.\n"
            "Per competitor: nume, CUI, CAEN, zona, dimensiune estimata.\n"
            "Pozitionarea firmei analizate vs competitie: puncte tari/slabe relative.\n"
            "IMPORTANT: Daca nu ai date suficiente despre competitori, scrie explicit:\n"
            "'Date insuficiente pentru analiza competitiei. Nu au fost identificati competitori '\n"
            "'in sursele consultate.' NU INVENTA nume de firme, CUI-uri sau cifre.\n\n"
            "EXEMPLU FRAGMENT (adapteaza la datele reale):\n"
            "\"| Nr | Competitor | CUI | CAEN | Judet | CA estimata |\n"
            "|---|---|---|---|---|---|\n"
            "| 1 | ALFA CONSTRUCT S.R.L. | 87654321 | 4120 | Bucuresti | ~3.5M RON |\n"
            "| 2 | BETA BUILDINGS S.R.L. | 11223344 | 4120 | Ilfov | ~1.8M RON |\n"
            "Pozitionare: Firma analizata se situeaza pe locul 2 din 3 competitori identificati ca dimensiune CA. "
            "Punct forte relativ: marja profit superioara (+2.3pp vs media). Punct slab: numar angajati inferior.\""
        ),
        "word_count": {"1": 150, "2": 500, "3": 1000},
    },
    "opportunities": {
        "title": "Oportunitati",
        "prompt": (
            "Prezinta oportunitatile identificate: licitatii active, fonduri, piete noi.\n"
            "Per oportunitate: descriere, valoare, deadline, eligibilitate, link sursa.\n"
            "Prioritizeaza dupa: urgenta (deadline) > valoare > grad potrivire.\n"
            "IMPORTANT: Prezinta DOAR oportunitati care apar in datele furnizate (SEAP, web).\n"
            "Daca nu exista oportunitati in date, scrie: 'Nu au fost identificate oportunitati '\n"
            "'concrete in sursele consultate.' NU INVENTA licitatii, fonduri sau proiecte.\n\n"
            "EXEMPLU FRAGMENT (adapteaza la datele reale):\n"
            "\"1. LICITATIE SEAP: 'Reabilitare scoala nr. 5 Sector 2' — Valoare estimata: 1.2M RON. "
            "Deadline depunere: 15.04.2025. Autoritate: Primaria Sector 2. Eligibilitate: CAEN 4120, experienta similara.\n"
            "2. FOND EUROPEAN: PNRR Componenta C5 — renovare energetica cladiri publice. "
            "Buget disponibil: 500M EUR national. Eligibilitate: firme constructii cu min 3 ani experienta.\""
        ),
        "word_count": {"1": 150, "2": 400, "3": 800},
    },
    "swot": {
        "title": "Analiza SWOT",
        "prompt": (
            "Genereaza analiza SWOT structurata pe 4 cadrane.\n"
            "Fiecare punct: max 2 randuri, bazat pe DATE din raport (nu generic).\n"
            "Strengths/Weaknesses: din date interne (financiar, profil, online).\n"
            "Opportunities/Threats: din date externe (piata, competitie, reglementari).\n"
            "IMPORTANT: Fiecare punct SWOT trebuie sa fie justificat de o sursa din date.\n"
            "Daca nu ai date pentru un cadran, scrie: '[Date insuficiente pentru acest cadran].'\n\n"
            "EXEMPLU FRAGMENT (adapteaza la datele reale):\n"
            "\"STRENGTHS: Marja profit 7.8% peste media sector 5.2% (Sursa: ANAF Bilant 2024) | Experienta 14 ani in piata\n"
            "WEAKNESSES: Dependenta client major 45% din CA (Sursa: analiza portofoliu) | Capital social minim 10K RON\n"
            "OPPORTUNITIES: 3 licitatii SEAP active in CAEN 4120, val. totala 4.5M RON (Sursa: e-licitatie.ro)\n"
            "THREATS: Concurenta intensa — 12 firme CAEN 4120 in aceeasi zona (Sursa: listafirme.ro)\""
        ),
        "word_count": {"1": 0, "2": 300, "3": 500},
    },
    "recommendations": {
        "title": "Recomandari",
        "prompt": (
            "3-5 recomandari strategice CONCRETE si ACTIONABILE.\n"
            "Fiecare: ce sa faca, de ce, cum, cu ce resurse estimate.\n"
            "Ordinea: urgenta (risc imediat) > oportunitate rapida > strategie termen lung.\n"
            "Baza EXCLUSIV pe datele din raport. Fara sfaturi generice.\n"
            "IMPORTANT (B14): Verifica campul 'early_warnings' din date. Daca exista semnale de alarma "
            "(scadere CA, pierdere consecutiva, reducere angajati), PRIMA recomandare trebuie sa adreseze "
            "direct aceste semnale cu actiuni concrete si urgente.\n\n"
            "EXEMPLU FRAGMENT:\n"
            "\"1. URGENTA: Diversificarea portofoliului de clienti — firma depinde 45% de un singur "
            "client. Actiune: identificare a minim 3 clienti noi in urmatoarele 6 luni. "
            "Resurse estimate: 1 angajat vanzari, buget marketing 5K RON/luna.\n"
            "2. OPORTUNITATE: Participare la licitatii publice SEAP — firma are experienta relevanta "
            "si nu apare in bazele SEAP. Actiune: inregistrare pe e-licitatie.ro si certificare.\""
        ),
        "word_count": {"1": 200, "2": 400, "3": 600},
    },
}

# Sectiuni per tip de analiza
SECTIONS_PER_TYPE = {
    "FULL_COMPANY_PROFILE": [
        "executive_summary", "company_profile", "financial_analysis",
        "risk_assessment", "competition", "opportunities", "swot", "recommendations",
    ],
    "COMPETITION_ANALYSIS": [
        "executive_summary", "competition", "swot", "recommendations",
    ],
    "PARTNER_RISK_ASSESSMENT": [
        "executive_summary", "company_profile", "financial_analysis",
        "risk_assessment", "recommendations",
    ],
    "TENDER_OPPORTUNITIES": [
        "executive_summary", "company_profile", "opportunities", "recommendations",
    ],
    "FUNDING_OPPORTUNITIES": [
        "executive_summary", "company_profile", "opportunities", "recommendations",
    ],
    "MARKET_ENTRY_ANALYSIS": [
        "executive_summary", "competition", "opportunities", "swot", "recommendations",
    ],
    "LEAD_GENERATION": [
        "executive_summary", "recommendations",
    ],
    "CUSTOM_REPORT": [
        "executive_summary", "company_profile", "financial_analysis",
        "risk_assessment", "recommendations",
    ],
}


# Provider routing hints per section (8C)
SECTION_PROVIDER_PREFERENCE = {
    "executive_summary": "quality",
    "company_profile": "fast",
    "financial_analysis": "quality",
    "risk_assessment": "quality",
    "competition": "fast",
    "opportunities": "fast",
    "swot": "fast",
    "recommendations": "quality",
}


def get_sections_for_analysis(
    analysis_type: str,
    report_level: int,
    verified_data: dict | None = None,
) -> list[dict]:
    """Returneaza lista sectiunilor cu prompt-urile configurate per nivel.
    8C: Dynamic word count bazat pe complexitatea datelor."""
    section_keys = SECTIONS_PER_TYPE.get(analysis_type, SECTIONS_PER_TYPE["CUSTOM_REPORT"])

    sections = []
    for key in section_keys:
        tmpl = SECTION_PROMPTS.get(key)
        if not tmpl:
            continue
        wc = tmpl["word_count"].get(str(report_level), 0)
        if wc == 0 and report_level < 3:
            continue

        # Dynamic word count adjustment (8C)
        if verified_data:
            wc = _adjust_word_count(key, wc, verified_data)

        sections.append({
            "key": key,
            "title": tmpl["title"],
            "prompt": tmpl["prompt"].format(word_count=wc),
            "word_count": wc,
            "route_preference": SECTION_PROVIDER_PREFERENCE.get(key, "quality"),
        })
    return sections


def _adjust_word_count(key: str, base_wc: int, data: dict) -> int:
    """Ajusteaza word count pe baza complexitatii datelor (8C)."""
    factor = 1.0

    if key == "financial_analysis":
        trend = data.get("financial", {}).get("trend_financiar", {})
        tv = trend.get("value") if isinstance(trend, dict) else None
        if isinstance(tv, dict):
            # Multi-year data = more to analyze
            ca_vals = tv.get("cifra_afaceri_neta", {}).get("values", [])
            if len(ca_vals) >= 4:
                factor = 1.3
            elif len(ca_vals) >= 2:
                factor = 1.15

    elif key == "competition":
        market = data.get("market", {})
        web = data.get("web_presence", {})
        competitors = 0
        if isinstance(web, dict):
            competitors += len(web.get("competitors", {}).get("results", []))
        if isinstance(market, dict) and market.get("seap", {}).get("total_contracts", 0) > 5:
            factor = 1.2
        if competitors >= 3:
            factor = max(factor, 1.3)
        elif competitors == 0:
            factor = 0.6  # Reduce if no competitor data

    elif key == "risk_assessment":
        risk = data.get("risk_score", {})
        factors = risk.get("factor_count", 0)
        if factors >= 5:
            factor = 1.3
        elif factors >= 3:
            factor = 1.15

    return int(base_wc * factor)
