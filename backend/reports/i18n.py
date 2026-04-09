"""
G5: i18n — Traduceri pentru rapoarte PDF/HTML.
Suporta: ro (romana, default) + en (english).
Continutul generat de AI ramane in romana; doar etichetele/antetele sunt traduse.
"""

TRANSLATIONS: dict[str, dict[str, str]] = {
    "ro": {
        # Sectiuni raport
        "executive_summary": "Rezumat Executiv",
        "financial_analysis": "Analiza Financiara",
        "risk_assessment": "Evaluare Risc",
        "legal_status": "Statut Juridic",
        "market_position": "Pozitie de Piata",
        "competition": "Concurenta",
        "opportunities": "Oportunitati",
        "recommendations": "Recomandari",
        "swot_analysis": "Analiza SWOT",
        "due_diligence": "Due Diligence",
        "early_warnings": "Semnale de Avertizare",
        "benchmark": "Benchmark Sector",
        "monitorul_oficial": "Monitorul Oficial",
        "sources": "Surse de Date",
        "disclaimer": "Disclaimer",
        "table_of_contents": "Cuprins",
        # Scoruri si risc
        "risk_score": "Scor Risc",
        "score": "Scor",
        "low_risk": "Risc Scazut",
        "medium_risk": "Risc Mediu",
        "high_risk": "Risc Ridicat",
        "financial": "Financiar",
        "legal": "Juridic",
        "fiscal": "Fiscal",
        "operational": "Operational",
        "reputational": "Reputational",
        "market": "Piata",
        # Metrici financiare
        "revenue": "Cifra de Afaceri",
        "profit": "Profit Net",
        "employees": "Angajati",
        "equity": "Capitaluri Proprii",
        "year": "An",
        "trend": "Tendinta",
        # Due Diligence
        "yes": "DA",
        "no": "NU",
        "unavailable": "INDISPONIBIL",
        # Etichete meta
        "company_name": "Denumire Firma",
        "cui": "CUI",
        "generated_at": "Generat la",
        "report_number": "Nr. Raport",
        "report_level": "Nivel Raport",
        "analysis_type": "Tip Analiza",
        "sources_count": "Surse Folosite",
        "page": "Pagina",
        "of": "din",
        # Watermark
        "confidential": "CONFIDENTIAL",
    },
    "en": {
        # Sectiuni raport
        "executive_summary": "Executive Summary",
        "financial_analysis": "Financial Analysis",
        "risk_assessment": "Risk Assessment",
        "legal_status": "Legal Status",
        "market_position": "Market Position",
        "competition": "Competition",
        "opportunities": "Opportunities",
        "recommendations": "Recommendations",
        "swot_analysis": "SWOT Analysis",
        "due_diligence": "Due Diligence",
        "early_warnings": "Early Warning Signals",
        "benchmark": "Sector Benchmark",
        "monitorul_oficial": "Official Gazette",
        "sources": "Data Sources",
        "disclaimer": "Disclaimer",
        "table_of_contents": "Table of Contents",
        # Scoruri si risc
        "risk_score": "Risk Score",
        "score": "Score",
        "low_risk": "Low Risk",
        "medium_risk": "Medium Risk",
        "high_risk": "High Risk",
        "financial": "Financial",
        "legal": "Legal",
        "fiscal": "Fiscal",
        "operational": "Operational",
        "reputational": "Reputational",
        "market": "Market",
        # Metrici financiare
        "revenue": "Revenue",
        "profit": "Net Profit",
        "employees": "Employees",
        "equity": "Equity",
        "year": "Year",
        "trend": "Trend",
        # Due Diligence
        "yes": "YES",
        "no": "NO",
        "unavailable": "UNAVAILABLE",
        # Etichete meta
        "company_name": "Company Name",
        "cui": "Tax ID (CUI)",
        "generated_at": "Generated at",
        "report_number": "Report No.",
        "report_level": "Report Level",
        "analysis_type": "Analysis Type",
        "sources_count": "Sources Used",
        "page": "Page",
        "of": "of",
        # Watermark
        "confidential": "CONFIDENTIAL",
    },
}

SUPPORTED_LANGS = frozenset(TRANSLATIONS.keys())


def t(key: str, lang: str = "ro") -> str:
    """
    Returneaza traducerea pentru key in lang.
    Fallback: romana, apoi key-ul netraducit.
    """
    lang = lang if lang in SUPPORTED_LANGS else "ro"
    return TRANSLATIONS[lang].get(key) or TRANSLATIONS["ro"].get(key, key)
