"""
Cautare firme candidate (leads) pentru AnalysisType LEAD_GENERATION.

Sursa de date: tabela proprie `companies` (firme deja analizate de RIS) — NU un
dataset national complet. Dataset-ul bulk ONRC (onrc_companies, D1) nu e populat
pe aceasta masina la data implementarii; codul de mai jos e scris sa functioneze
neschimbat cand tabela aceea va avea date (fallback silentios la un pool mai mic
acum, extindere automata ulterior — nu necesita alt refactor).

Flux: text liber (ideal_client) -> parsare AI in filtre (judet + cuvinte cheie
activitate) -> cautare in `companies` dupa caen_description/county -> filtrare/
sortare dupa prioritate (crestere / licitatii active / probleme cunoscute).
"""

import json
import re

from loguru import logger

from backend.agents import ai_models
from backend.config import settings
from backend.database import db
from backend.http_client import get_client

PRIORITY_LABELS = {
    "Firme in crestere": "crestere",
    "Firme cu licitatii active": "licitatii",
    "Firme cu probleme cunoscute": "probleme",
}


async def parse_lead_criteria(ideal_client: str) -> dict:
    """Extrage judet + cuvinte cheie de activitate din descrierea libera a clientului ideal.
    Foloseste Groq (rapid, gratuit) — fallback la extractie goala daca esueaza (nu blocheaza)."""
    fallback = {"judet": None, "keywords": [], "raw": ideal_client}
    api_key = settings.groq_api_key
    if not api_key or not ideal_client:
        return fallback

    prompt = (
        "Extrage din urmatoarea descriere a unui profil de client ideal doua lucruri, "
        "in format JSON strict (fara alt text):\n"
        '{"judet": "NUME_JUDET sau null", "keywords": ["cuvant1", "cuvant2"]}\n\n'
        "- judet: numele judetului romanesc mentionat (ex: ARAD, TIMIS, BUCURESTI), "
        "MAJUSCULE fara diacritice, sau null daca nu e mentionat un judet anume.\n"
        "- keywords: maxim 4 cuvinte cheie ROMANESTI scurte despre domeniul de activitate "
        "(ex: 'constructii', 'instalatii', 'transport'), fara nume proprii, fara CUI.\n\n"
        f"Descriere: \"{ideal_client}\"\n\nJSON:"
    )
    try:
        client = get_client()
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                # Model din sursa unica (ai_models) — scout-ul vechi era RETRAS -> 404 tacut
                # -> parsarea criteriilor cadea mereu pe fallback gol.
                "model": ai_models.get_model("groq"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 200,
            },
            timeout=15,
        )
        if r.status_code != 200:
            logger.warning(f"[lead_search] Groq parse HTTP {r.status_code}")
            return fallback
        text = r.json()["choices"][0]["message"]["content"].strip()
        text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
        parsed = json.loads(text)
        judet = parsed.get("judet")
        judet = str(judet).strip().upper() if judet else None
        keywords = [str(k).strip().lower() for k in parsed.get("keywords", []) if str(k).strip()][:4]
        return {"judet": judet or None, "keywords": keywords, "raw": ideal_client}
    except Exception as e:
        logger.warning(f"[lead_search] parse_lead_criteria esuat: {e}")
        return fallback


async def search_candidate_companies(filters: dict, priority: str, limit: int) -> list[dict]:
    """Cauta in `companies` firme ce se potrivesc filtrelor, filtrate/sortate dupa prioritate."""
    conditions = []
    params: list = []

    judet = filters.get("judet")
    if judet:
        # county e stocat inconsecvent (ARAD vs Arad, dupa cum a raportat sursa upstream la
        # momentul analizei) -- comparatie case-insensitive ca sa nu rateze potriviri reale.
        conditions.append("UPPER(county) = UPPER(?)")
        params.append(judet)

    keywords = filters.get("keywords") or []
    if keywords:
        kw_clauses = []
        for kw in keywords:
            kw_clauses.append("caen_description LIKE ?")
            params.append(f"%{kw}%")
        conditions.append(f"({' OR '.join(kw_clauses)})")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    # Pool candidat generos — filtrarea de prioritate (mai jos) poate elimina o parte.
    rows = await db.fetch_all(
        f"SELECT id, cui, name, caen_code, caen_description, county, risk_score, "
        f"last_risk_score_numeric, analysis_count, last_analyzed_at, latest_ca "
        f"FROM companies {where} ORDER BY last_analyzed_at DESC LIMIT 100",
        tuple(params),
    )
    candidates = [dict(r) for r in rows]
    if not candidates:
        return []

    prio_key = PRIORITY_LABELS.get(priority)
    if prio_key == "probleme":
        candidates = [c for c in candidates if c.get("risk_score") in ("Rosu", "Galben")]
    elif prio_key == "crestere":
        candidates = await _filter_growing(candidates)
    elif prio_key == "licitatii":
        candidates = await _filter_active_tenders(candidates)

    return candidates[:limit]


async def _filter_growing(candidates: list[dict]) -> list[dict]:
    """Pastreaza doar firmele cu scor numeric in crestere intre primele si ultimele
    inregistrari din score_history (proxy pentru "in crestere" — nu avem CA istoric
    bulk pt firme din afara RIS)."""
    growing = []
    for c in candidates:
        rows = await db.fetch_all(
            "SELECT numeric_score FROM score_history WHERE company_id = ? "
            "ORDER BY recorded_at ASC",
            (c["id"],),
        )
        scores = [r["numeric_score"] for r in rows if r["numeric_score"] is not None]
        if len(scores) >= 2 and scores[-1] > scores[0]:
            c["match_reason"] = f"Scor risc in crestere: {scores[0]:.0f} -> {scores[-1]:.0f}"
            growing.append(c)
    return growing


async def _filter_active_tenders(candidates: list[dict]) -> list[dict]:
    """Pastreaza doar firmele al caror ultim raport are contracte SEAP castigate sau
    licitatii deschise identificate (Angle A/B)."""
    active = []
    for c in candidates:
        row = await db.fetch_one(
            "SELECT full_data FROM reports WHERE company_id = ? "
            "ORDER BY created_at DESC LIMIT 1",
            (c["id"],),
        )
        if not row or not row["full_data"]:
            continue
        try:
            data = json.loads(row["full_data"])
        except (json.JSONDecodeError, TypeError):
            continue
        seap_won = (data.get("market", {}) or {}).get("seap", {}) or {}
        # market.seap e infasurat de _verify_market() -> _make_field():
        # {"value": {...total_contracts...}, "trust":..., "source":..., "timestamp":...}.
        # Fara unwrap, total_contracts nu exista niciodata pe wrapper (doar pe .value) ->
        # citit mereu 0 (fix aliniat cu 738cf22, acelasi pattern deja folosit in
        # scoring.py/agent_verification.py/agent_synthesis.py/section_prompts.py).
        seap_val = seap_won.get("value", seap_won) if isinstance(seap_won, dict) else {}
        # tender_opportunities NU e infasurat (assignat direct in
        # agent_verification.py::_fetch_tender_opportunities, fara _make_field) -> "count"
        # e la nivelul de top, deja corect, verificat pe date reale din data/ris.db.
        tenders = (data.get("tender_opportunities", {}) or {})
        won_count = seap_val.get("total_contracts", 0) or 0
        open_count = tenders.get("count", 0) or 0
        if won_count > 0 or open_count > 0:
            c["match_reason"] = f"{won_count} contracte castigate, {open_count} licitatii deschise identificate"
            active.append(c)
    return active
