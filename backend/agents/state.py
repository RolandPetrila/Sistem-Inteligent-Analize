from typing import TypedDict, Optional, Annotated
from operator import add


def _last_value(a, b):
    """Reducer: pastreaza ultima valoare (pt campuri updatate concurent)."""
    return b


class SourceResult(TypedDict, total=False):
    source_name: str
    source_url: str
    status: str  # OK / TIMEOUT / BLOCKED / ERROR / CAPTCHA
    data_found: bool
    response_time_ms: int
    data: dict


class AgentError(TypedDict):
    agent: str
    error: str
    recoverable: bool


class AnalysisState(TypedDict, total=False):
    # Input (setat la creare)
    job_id: str
    analysis_type: str
    report_level: int
    input_params: dict

    # Date colectate per agent
    official_data: Optional[dict]
    web_data: Optional[dict]
    market_data: Optional[dict]

    # Post-verificare
    verified_data: Optional[dict]

    # Sinteza
    report_sections: Optional[dict]

    # Raport generat
    report_paths: Optional[dict]

    # Control flow
    errors: Annotated[list[AgentError], add]
    sources: Annotated[list[SourceResult], add]
    progress: Annotated[float, _last_value]
    current_step: Annotated[str, _last_value]

    # Config per tip analiza
    agents_needed: list[str]


# Mapping: ce agenti trebuie per analysis_type + report_level
def get_agents_needed(analysis_type: str, report_level: int) -> list[str]:
    # Nivel 1: doar date oficiale
    if report_level == 1:
        return ["official"]

    # TIP 3 (Risc Partener): nu are nevoie de web intelligence
    if analysis_type == "PARTNER_RISK_ASSESSMENT":
        return ["official"]

    # TIP 4 (Licitatii): doar market (SEAP)
    if analysis_type == "TENDER_OPPORTUNITIES":
        return ["official", "market"]

    # Nivel 2: oficial + web + market pentru profiluri complete
    if report_level == 2 and analysis_type in (
        "FULL_COMPANY_PROFILE",
        "COMPETITION_ANALYSIS",
        "MARKET_ENTRY_ANALYSIS",
        "LEAD_GENERATION",
    ):
        return ["official", "web", "market"]

    # Nivel 2 restul: oficial + web
    if report_level == 2:
        return ["official", "web"]

    # Default: toti
    return ["official", "web", "market"]


# Progress weights per agent
PROGRESS_WEIGHTS = {
    "official": 0.20,
    "web": 0.20,
    "market": 0.20,
    "verification": 0.10,
    "synthesis": 0.25,
    "report": 0.25,
}
