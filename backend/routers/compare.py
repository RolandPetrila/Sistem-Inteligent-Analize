"""
Compare API — Compara 2-5 firme side-by-side pe baza datelor ANAF + ANAF Bilant.
8D: Cache ANAF, consistent risk scoring, compare persistence.
"""

import asyncio
import json
import os
import uuid
from datetime import date

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from loguru import logger
from pydantic import BaseModel

from backend.agents.tools.anaf_bilant_client import get_bilant
from backend.agents.tools.anaf_client import get_anaf_data
from backend.agents.tools.caen_context import CAEN_BENCHMARK, get_caen_description
from backend.agents.tools.cui_validator import validate_cui
from backend.agents.verification.scoring import calculate_risk_score
from backend.config import settings
from backend.database import db
from backend.services import cache_service

router = APIRouter()


class CompareRequest(BaseModel):
    cui_list: list[str]


@router.post("")
async def compare_companies(data: CompareRequest):
    """Compara 2-5 firme pe baza CUI-urilor. 8D: cached + consistent scoring."""
    if len(data.cui_list) < 2 or len(data.cui_list) > 5:
        raise HTTPException(status_code=400, detail="Introdu intre 2 si 5 CUI-uri")

    clean_cuis = []
    for cui in data.cui_list:
        v = validate_cui(cui.strip())
        if not v["valid"]:
            raise HTTPException(status_code=400, detail=f"CUI invalid: {cui} - {v['error']}")
        clean_cuis.append(v["cui_clean"])

    results = []
    # B18 fix: Use year-1 (last complete year), not year-2
    last_year = date.today().year - 1

    for cui in clean_cuis:
        company = {"cui": cui}

        # 8D: Cache ANAF data for Compare (use cache_service)
        cache_key_anaf = cache_service.make_cache_key("anaf", cui)
        anaf = await cache_service.get(cache_key_anaf)
        if anaf is None:
            try:
                anaf = await get_anaf_data(cui)
                if anaf:
                    await cache_service.set(cache_key_anaf, anaf, "anaf")
            except Exception as e:
                anaf = {}
                company["error_anaf"] = str(e)
            # C17 fix: Only sleep on cache miss (rate limit), not on hit
            await asyncio.sleep(settings.compare_rate_delay_s)  # rate limit: doar la fetch real, nu la cache hit

        if anaf and anaf.get("found"):
            company["denumire"] = anaf.get("denumire", "N/A")
            company["adresa"] = anaf.get("adresa", "")
            company["stare"] = anaf.get("stare_inregistrare", "")
            company["platitor_tva"] = anaf.get("platitor_tva", False)
            company["inactiv"] = anaf.get("inactiv", False)
            company["data_inregistrare"] = anaf.get("data_inregistrare", "")
        else:
            company["denumire"] = f"CUI {cui} - negasit ANAF"

        # 8D: Cache Bilant data
        cache_key_bilant = cache_service.make_cache_key("anaf", f"bilant_{cui}_{last_year}")
        bilant = await cache_service.get(cache_key_bilant)
        if bilant is None:
            try:
                bilant = await get_bilant(cui, last_year)
                if bilant:
                    await cache_service.set(cache_key_bilant, bilant, "anaf")
            except Exception as e:
                logger.warning(f"[compare] bilant fetch: {e}")
                bilant = {}
            # C17 fix: Only sleep on cache miss (rate limit), not on hit
            await asyncio.sleep(settings.compare_rate_delay_s)  # rate limit: doar la fetch real, nu la cache hit

        if bilant and bilant.get("found"):
            company["cifra_afaceri"] = bilant.get("cifra_afaceri_neta")
            company["profit_brut"] = bilant.get("profit_brut")
            company["profit_net"] = bilant.get("profit_net")
            company["pierdere_neta"] = bilant.get("pierdere_neta")
            company["angajati"] = bilant.get("numar_mediu_salariati")
            company["capitaluri"] = bilant.get("capitaluri_proprii")
            company["caen_code"] = bilant.get("caen_code", "")
            company["caen_description"] = bilant.get("caen_description", "")
            company["an_financiar"] = last_year
        else:
            company["an_financiar"] = None

        # 8D: Consistent risk scoring (aligned with Agent 4 formula)
        company["scor_risc"] = _calculate_compare_score(company)
        results.append(company)

    # Determina cel mai bun per indicator
    best = {}
    for key in ["cifra_afaceri", "profit_net", "angajati", "capitaluri", "scor_risc"]:
        vals = [(i, r.get(key)) for i, r in enumerate(results) if r.get(key) is not None]
        if vals:
            best[key] = max(vals, key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0)[0]

    # 8D: Persist compare in DB
    compare_id = str(uuid.uuid4())
    try:
        await db.execute(
            "INSERT INTO compare_history (id, cui_list, result_data) VALUES (?, ?, ?)",
            (compare_id, json.dumps(clean_cuis), json.dumps(results, ensure_ascii=False, default=str)),
        )
    except Exception as e:
        logger.warning(f"[compare] history: {e}")

    # 10D M7.4: Chart.js-ready data format for frontend instant charts
    chart_data = _build_chart_data(results)

    # 10D M7.2: Financial ratios auto-calculated
    for company in results:
        company["ratios"] = _calculate_financial_ratios(company)

    # 10F M7.5: Sector Percentile Scoring
    for company in results:
        company["sector_percentile"] = _calculate_sector_percentile(company, results)

    return {
        "compare_id": compare_id,
        "companies": results,
        "best_per_indicator": best,
        "an_financiar": last_year,
        "count": len(results),
        "chart_data": chart_data,
    }


def _calculate_compare_score(company: dict) -> int:
    """DRY scoring: delegates to canonical calculate_risk_score (Agent 4).
    Builds the verified-data structure expected by the canonical function
    from the flat compare company dict."""
    # Build verified-data structure compatible with canonical scoring
    def _field(val):
        return {"value": val} if val is not None else {}

    verified = {
        "financial": {
            "cifra_afaceri": _field(company.get("cifra_afaceri")),
            "profit_net": _field(company.get("profit_net")),
            "profit_brut": _field(company.get("profit_brut")),
            "capitaluri_proprii": _field(company.get("capitaluri")),
            "numar_mediu_salariati": _field(company.get("angajati")),
        },
        "risk": {
            "inactiv": {"value": company.get("inactiv", False)},
            "platitor_tva": {"value": company.get("platitor_tva", False)},
        },
        "company": {
            "data_inregistrare": {"value": company.get("data_inregistrare", "")},
            "stare_inregistrare": {"value": company.get("stare", "")},
        },
    }

    try:
        result = calculate_risk_score(verified)
        return result.get("total_score", 70)
    except Exception as e:
        logger.warning(f"[compare] fallback scoring: {e}")
        return 70


def _calculate_financial_ratios(company: dict) -> dict:
    """10D M7.2: Auto-calculate financial ratios from compare data."""
    ratios = {}
    ca = company.get("cifra_afaceri") or 0
    pn = company.get("profit_net") or 0
    cap = company.get("capitaluri")
    angajati = company.get("angajati")

    if ca > 0:
        ratios["profit_margin_pct"] = round(pn / ca * 100, 2)
    if cap and cap != 0:
        ratios["roe_pct"] = round(pn / cap * 100, 2)
    if ca > 0 and cap is not None:
        ratios["solvency_ratio"] = round(cap / ca, 3) if ca > 0 else None
    if angajati and angajati > 0 and ca > 0:
        ratios["ca_per_angajat"] = round(ca / angajati)
        ratios["angajati_per_1m_ca"] = round(angajati / (ca / 1_000_000), 1) if ca >= 1_000_000 else None

    return ratios


def _calculate_sector_percentile(company: dict, all_companies: list[dict]) -> dict:
    """10F M7.5: Position company within the compare group (percentile for CA, profit, angajati)."""
    percentiles = {}
    for key in ["cifra_afaceri", "profit_net", "angajati", "scor_risc"]:
        val = company.get(key)
        if val is None:
            continue
        all_vals = sorted([c.get(key) for c in all_companies if c.get(key) is not None])
        if not all_vals:
            continue
        rank = sum(1 for v in all_vals if v <= val)
        pct = round(rank / len(all_vals) * 100)
        if pct >= 90:
            label = "P90+ (Top)"
        elif pct >= 75:
            label = "P75-P90"
        elif pct >= 50:
            label = "P50-P75"
        elif pct >= 25:
            label = "P25-P50"
        else:
            label = "sub P25"
        percentiles[key] = {"percentile": pct, "label": label, "rank": rank, "total": len(all_vals)}
    return percentiles


def _build_chart_data(results: list[dict]) -> dict:
    """10D M7.4: Chart.js-ready data for frontend instant rendering."""
    labels = [r.get("denumire", r.get("cui", "?"))[:25] for r in results]
    colors = ["#6366F1", "#22C55E", "#3B82F6", "#EAB308", "#EF4444"]

    datasets = {}
    for key, label in [("cifra_afaceri", "Cifra Afaceri"), ("profit_net", "Profit Net"),
                        ("angajati", "Angajati"), ("scor_risc", "Scor Risc")]:
        values = [r.get(key) or 0 for r in results]
        if any(v != 0 for v in values):
            datasets[key] = {
                "label": label,
                "labels": labels,
                "data": values,
                "backgroundColor": colors[:len(results)],
            }

    return datasets


class CompareReportRequest(BaseModel):
    cui_1: str
    cui_2: str


@router.post("/report")
async def compare_report_pdf(data: CompareReportRequest):
    """E9: Generate comparative PDF for 2 companies."""
    from backend.reports.compare_generator import generate_compare_pdf

    # Reuse compare logic to get both companies' data
    compare_data = await compare_companies(CompareRequest(cui_list=[data.cui_1, data.cui_2]))
    companies = compare_data["companies"]
    if len(companies) < 2:
        raise HTTPException(status_code=400, detail="Nu s-au putut obtine date pentru ambele firme")

    output_dir = os.path.join("outputs", "compare")
    os.makedirs(output_dir, exist_ok=True)
    import uuid
    filename = f"comparativ_{uuid.uuid4().hex[:16]}.pdf"
    output_path = os.path.join(output_dir, filename)

    generate_compare_pdf(companies[0], companies[1], output_path)

    return FileResponse(
        output_path,
        media_type="application/pdf",
        filename=filename,
    )


# --- Compare Templates (F3-8) ---
@router.get("/templates")
async def list_compare_templates():
    rows = await db.fetch_all("SELECT id, name, cuis, created_at FROM compare_templates ORDER BY created_at DESC")
    return {
        "templates": [
            {
                "id": r["id"],
                "name": r["name"],
                "cuis": json.loads(r["cuis"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    }


@router.post("/templates")
async def save_compare_template(body: dict):
    name = str(body.get("name", "")).strip()[:50]
    cuis = body.get("cuis", [])
    if not name or not cuis:
        from backend.errors import ErrorCode, RISError
        raise RISError(ErrorCode.VALIDATION_ERROR, "Nume si CUI-uri obligatorii")
    template_id = uuid.uuid4().hex
    await db.execute(
        "INSERT INTO compare_templates(id, name, cuis) VALUES (?,?,?)",
        (template_id, name, json.dumps(cuis)),
    )
    return {"ok": True, "id": template_id}


@router.delete("/templates/{template_id}")
async def delete_compare_template(template_id: str):
    await db.execute("DELETE FROM compare_templates WHERE id = ?", (template_id,))
    return {"ok": True}


# --- Sector CAEN Dashboard (F3-6) ---
@router.get("/sector/{caen_code}/dashboard")
async def sector_dashboard(caen_code: str):
    """Agregat sector din DB: scoruri, distributie, top firme."""
    import re as _re
    if not _re.match(r"^\d{4}$", caen_code):
        from backend.errors import ErrorCode, RISError
        raise RISError(ErrorCode.VALIDATION_ERROR, "Cod CAEN invalid (4 cifre)")

    stats = await db.fetch_one(
        """
        SELECT
            COUNT(DISTINCT c.id) as total_companies,
            ROUND(AVG(sh.numeric_score), 1) as avg_score,
            SUM(CASE WHEN sh.numeric_score >= 70 THEN 1 ELSE 0 END) as count_verde,
            SUM(CASE WHEN sh.numeric_score >= 40 AND sh.numeric_score < 70 THEN 1 ELSE 0 END) as count_galben,
            SUM(CASE WHEN sh.numeric_score < 40 THEN 1 ELSE 0 END) as count_rosu
        FROM companies c
        LEFT JOIN score_history sh ON sh.company_id = c.id
        WHERE c.caen_code = ?
        """,
        (caen_code,),
    )

    top_companies = await db.fetch_all(
        """
        SELECT c.id, c.name, c.cui, MAX(sh.numeric_score) as score, c.county
        FROM companies c
        JOIN score_history sh ON sh.company_id = c.id
        WHERE c.caen_code = ?
        GROUP BY c.id ORDER BY score DESC LIMIT 10
        """,
        (caen_code,),
    )

    try:
        from backend.agents.tools.caen_context import get_caen_info
        caen_info = get_caen_info(caen_code)
    except Exception:
        caen_info = {}

    return {
        "caen_code": caen_code,
        "caen_description": caen_info.get("description", "") if isinstance(caen_info, dict) else "",
        "stats": dict(stats) if stats else {},
        "top_companies": [dict(r) for r in top_companies],
    }


class SectorRequest(BaseModel):
    caen_section: str
    min_ca: int = 0
    limit: int = 50


@router.post("/sector")
async def sector_report(data: SectorRequest):
    """ADV4: Raport sector — agregate firme din baza de date per CAEN."""
    section = data.caen_section.strip()[:2]
    caen_desc = get_caen_description(section)
    benchmark = CAEN_BENCHMARK.get(section, {})

    rows = await db.fetch_all(
        "SELECT c.cui, c.name, c.caen_code, c.caen_description, c.county, c.analysis_count, "
        "r.risk_score, r.created_at as last_report_at "
        "FROM companies c "
        "LEFT JOIN reports r ON c.id = r.company_id "
        "WHERE c.caen_code LIKE ? "
        "GROUP BY c.id "
        "ORDER BY c.last_analyzed_at DESC "
        "LIMIT ?",
        (f"{section}%", data.limit),
    )

    companies = [dict(r) for r in rows]
    total = len(companies)
    with_score = [c for c in companies if c.get("risk_score")]

    return {
        "caen_section": section,
        "caen_description": caen_desc,
        "benchmark": benchmark,
        "companies": companies,
        "total_in_db": total,
        "stats": {
            "total_analyzed": total,
            "with_risk_score": len(with_score),
            "risk_distribution": {
                "verde": sum(1 for c in with_score if c["risk_score"] == "Verde"),
                "galben": sum(1 for c in with_score if c["risk_score"] == "Galben"),
                "rosu": sum(1 for c in with_score if c["risk_score"] == "Rosu"),
            },
        },
    }
