"""
NLQ Ask RIS — Natural Language Query endpoint.
B1: Intent classifier rule-based → SQL → formatare raspuns.
POST /api/ask { "question": "..." }
"""

import re

from fastapi import APIRouter, Depends
from loguru import logger
from pydantic import BaseModel

from backend.security import require_api_key
from backend.database import db

router = APIRouter(prefix="/api/ask", tags=["Ask"])


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    intent: str
    data: list | None = None


def _classify_intent(q: str) -> str:
    q_lower = q.lower()
    if any(k in q_lower for k in ["risc ridicat", "risc mare", "rosu", "periculoas", "risc crescut", "risc"]):
        return "top_risc"
    if any(k in q_lower for k in ["cate", "câte", "statistici", "total", "cati", "câți", "nr", "numar", "număr"]):
        return "statistici"
    if any(k in q_lower for k in ["ultima", "ultimele", "recent", "ieri", "astazi", "astăzi", "noua", "nouă"]):
        return "ultimele"
    if any(k in q_lower for k in ["compara", "compară", " vs ", "versus", "diferenta", "diferență"]):
        return "comparatie"
    if any(k in q_lower for k in ["despre", "info", "detalii", "spune", "arata", "arată"]):
        return "firma_info"
    return "necunoscut"


@router.post("", response_model=AskResponse)
async def ask_ris(req: AskRequest, _=Depends(require_api_key)):
    question = req.question.strip()[:500]  # max 500 chars
    if not question:
        return AskResponse(answer="Introduceti o intrebare.", intent="gol")

    intent = _classify_intent(question)
    logger.info(f"[ask] intent={intent} | question={question[:80]}")

    if intent == "top_risc":
        rows = await db.fetch_all(
            "SELECT name, cui, risk_score, risk_color FROM companies "
            "WHERE risk_score IS NOT NULL ORDER BY risk_score ASC LIMIT 5"
        )
        if not rows:
            return AskResponse(answer="Nu exista date de scoring in sistem.", intent=intent)
        lines = [
            f"• {r['name']} (CUI {r['cui']}): {r['risk_score']}/100 — {r.get('risk_color', 'N/A')}"
            for r in rows
        ]
        return AskResponse(
            answer="Top 5 firme cu risc ridicat:\n" + "\n".join(lines),
            intent=intent,
            data=[dict(r) for r in rows],
        )

    if intent == "statistici":
        total = await db.fetch_one("SELECT COUNT(*) as c FROM jobs WHERE status='COMPLETED'")
        companies = await db.fetch_one("SELECT COUNT(*) as c FROM companies")
        alerts = await db.fetch_one("SELECT COUNT(*) as c FROM monitoring_alerts WHERE is_active=1")
        return AskResponse(
            answer=(
                "Statistici sistem:\n"
                f"• Analize completate: {total['c'] if total else 0}\n"
                f"• Companii in baza de date: {companies['c'] if companies else 0}\n"
                f"• Alerte active monitorizare: {alerts['c'] if alerts else 0}"
            ),
            intent=intent,
        )

    if intent == "ultimele":
        rows = await db.fetch_all(
            "SELECT j.id, c.name, c.cui, j.created_at, j.status "
            "FROM jobs j LEFT JOIN companies c ON c.cui = j.input_data "
            "ORDER BY j.created_at DESC LIMIT 5"
        )
        if not rows:
            return AskResponse(answer="Nu exista analize recente.", intent=intent)
        lines = [
            f"• {r['name'] or r['cui'] or 'N/A'} — {r['created_at'][:10] if r['created_at'] else 'N/A'} ({r['status']})"
            for r in rows
        ]
        return AskResponse(
            answer="Ultimele 5 analize:\n" + "\n".join(lines),
            intent=intent,
        )

    if intent == "firma_info":
        name_match = re.search(r'(?:despre|info|detalii|spune|arata)\s+(.+?)(?:\?|$)', question, re.IGNORECASE)
        search_term = name_match.group(1).strip() if name_match else question
        rows = await db.fetch_all(
            "SELECT name, cui, risk_score, risk_color, caen_code FROM companies "
            "WHERE name LIKE ? LIMIT 3",
            (f"%{search_term}%",),
        )
        if not rows:
            return AskResponse(
                answer=f"Nu am gasit companii cu numele '{search_term}'.", intent=intent
            )
        lines = [
            f"• {r['name']} — CUI: {r['cui']}, Scor: {r['risk_score']}/100 ({r.get('risk_color', 'N/A')}), CAEN: {r.get('caen_code', 'N/A')}"
            for r in rows
        ]
        return AskResponse(answer="\n".join(lines), intent=intent, data=[dict(r) for r in rows])

    return AskResponse(
        answer=(
            "Nu am inteles intrebarea. Incearca:\n"
            "• 'Care firme au risc ridicat?'\n"
            "• 'Cate analize am facut?'\n"
            "• 'Ce am analizat ultima oara?'\n"
            "• 'Spune-mi despre [nume firma]'"
        ),
        intent="necunoscut",
    )
