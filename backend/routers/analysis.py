import re

from fastapi import APIRouter
from pydantic import BaseModel

from backend.models import AnalysisType, ANALYSIS_TYPES_META, AnalysisTypeResponse

router = APIRouter()


class ParseQueryRequest(BaseModel):
    query: str


class ParseQueryResponse(BaseModel):
    analysis_type: str
    input_params: dict
    confidence: float
    suggestion: str


@router.get("/types", response_model=list[AnalysisTypeResponse])
async def get_analysis_types():
    result = []
    for atype in AnalysisType:
        meta = ANALYSIS_TYPES_META[atype]
        result.append(AnalysisTypeResponse(
            type=atype.value,
            name=meta["name"],
            description=meta["description"],
            icon=meta["icon"],
            time_estimate=meta["time_estimate"],
            feasibility=meta["feasibility"],
            questions=meta["questions"],
            deferred=meta.get("deferred", False),
        ))
    return result


@router.get("/types/{analysis_type}", response_model=AnalysisTypeResponse)
async def get_analysis_type(analysis_type: str):
    try:
        atype = AnalysisType(analysis_type)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Analysis type not found")

    meta = ANALYSIS_TYPES_META[atype]
    return AnalysisTypeResponse(
        type=atype.value,
        name=meta["name"],
        description=meta["description"],
        icon=meta["icon"],
        time_estimate=meta["time_estimate"],
        feasibility=meta["feasibility"],
        questions=meta["questions"],
        deferred=meta.get("deferred", False),
    )


@router.post("/parse-query", response_model=ParseQueryResponse)
async def parse_natural_query(data: ParseQueryRequest):
    """Parseaza o cerere in limba naturala si sugereaza tip analiza + parametri."""
    query = data.query.lower().strip()
    params: dict = {}
    confidence = 0.6

    # Extrage CUI daca exista
    cui_match = re.search(r"\b(?:cui\s*)?(\d{6,10})\b", query)
    if cui_match:
        params["cui"] = cui_match.group(1)
        confidence += 0.15

    # Extrage nume firma (text intre ghilimele sau dupa "firma/compania")
    name_match = re.search(r'"([^"]+)"', data.query)
    if not name_match:
        name_match = re.search(r"(?:firma|compania|analizeaza|verifica)\s+(.+?)(?:\s+din|\s+cui|\s*$)", query)
    if name_match:
        params["cui"] = params.get("cui", name_match.group(1).strip())

    # Detecteaza tipul analizei
    analysis_type = "FULL_COMPANY_PROFILE"
    suggestion = "Profil complet firma"

    keywords = {
        "PARTNER_RISK_ASSESSMENT": ["risc", "partener", "verificare", "due diligence", "contract", "furnizor"],
        "COMPETITION_ANALYSIS": ["competit", "concurent", "piata", "rivali"],
        "TENDER_OPPORTUNITIES": ["licitati", "seap", "achiziti", "contract public"],
        "FUNDING_OPPORTUNITIES": ["fonduri", "finantare", "grant", "european", "pnrr"],
        "MARKET_ENTRY_ANALYSIS": ["intrare pe piata", "piata noua", "expandare"],
        "LEAD_GENERATION": ["clienti", "prospectare", "lead", "potentiali"],
        "FULL_COMPANY_PROFILE": ["profil", "analiza complet", "tot despre"],
    }

    best_score = 0
    for atype, kws in keywords.items():
        score = sum(1 for kw in kws if kw in query)
        if score > best_score:
            best_score = score
            analysis_type = atype
            meta = ANALYSIS_TYPES_META.get(AnalysisType(atype), {})
            suggestion = meta.get("name", atype) if meta else atype

    if best_score > 0:
        confidence += 0.1 * min(best_score, 3)

    confidence = min(confidence, 0.95)

    return ParseQueryResponse(
        analysis_type=analysis_type,
        input_params=params,
        confidence=round(confidence, 2),
        suggestion=f"Sugerez: {suggestion}",
    )
