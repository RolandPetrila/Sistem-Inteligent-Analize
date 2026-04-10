import re

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel

from backend.errors import ErrorCode, RISError
from backend.models import ANALYSIS_TYPES_META, AnalysisType, AnalysisTypeResponse

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


@router.post("/quick-score")
async def quick_score_batch(body: dict):
    """F3-2: Scoring rapid pentru max 20 CUI-uri — doar ANAF TVA + Bilant, fara AI synthesis."""
    import asyncio

    from backend.agents.tools.anaf_bilant_client import ANAFBilantClient
    from backend.agents.tools.anaf_client import ANAFClient
    from backend.agents.tools.cui_validator import validate_cui

    cuis = body.get("cuis", [])[:20]
    if not cuis:
        raise RISError(ErrorCode.VALIDATION_ERROR, "Lista CUI goala")

    anaf = ANAFClient()
    bilant = ANAFBilantClient()

    async def score_one(cui: str) -> dict:
        val = validate_cui(cui)
        if not val.get("valid"):
            return {"cui": cui, "error": "CUI invalid"}
        try:
            tva_data, bil_data = await asyncio.gather(
                anaf.get_company_info(cui),
                bilant.get_latest_year(cui),
                return_exceptions=True
            )
            ca = bil_data.get("cifra_afaceri") if isinstance(bil_data, dict) else None
            angajati = bil_data.get("numar_angajati") if isinstance(bil_data, dict) else None
            inactiv = tva_data.get("stare_inactiv", False) if isinstance(tva_data, dict) else False
            tva_activ = tva_data.get("tva_activ", False) if isinstance(tva_data, dict) else False

            score = 50
            if ca and ca > 1_000_000: score += 15
            if ca and ca > 10_000_000: score += 10
            if inactiv: score -= 30
            if not tva_activ and ca and ca > 500_000: score -= 10
            score = max(0, min(100, score))

            return {
                "cui": cui,
                "name": tva_data.get("denumire", "?") if isinstance(tva_data, dict) else "?",
                "ca_last_year": ca,
                "angajati": angajati,
                "tva_activ": tva_activ,
                "inactiv_anaf": inactiv,
                "quick_score": score,
                "risk": "Verde" if score >= 70 else "Galben" if score >= 40 else "Rosu"
            }
        except Exception as e:
            logger.warning(f"[quick_score] CUI {cui} eroare: {e}")
            return {"cui": cui, "error": "Eroare la scoring rapid — sursa indisponibila"}

    results = await asyncio.gather(*[score_one(c) for c in cuis])
    return {"results": list(results), "note": "Scoring rapid — doar ANAF, fara AI synthesis"}
