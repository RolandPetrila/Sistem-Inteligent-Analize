"""
AEGRM Client — Arhiva Electronica de Garantii Reale Mobiliare.
A5: Verificare garantii mobiliare per CUI — date extrem de relevante in due diligence.
API public gratuit: aegrm.justportal.ro/aegrm/rest/
"""

from loguru import logger

from backend.http_client import get_http_client

AEGRM_BASE = "https://aegrm.justportal.ro/aegrm/rest"


async def check_aegrm_guarantees(cui: str) -> dict:
    """
    Verifica garantiile reale mobiliare ale unei firme dupa CUI.
    Returneaza: has_guarantees, count, details, source.
    """
    if not cui:
        return {"has_data": False, "has_guarantees": False, "count": 0, "details": []}

    cui_clean = str(cui).strip().lstrip("RO").lstrip("0")

    try:
        client = await get_http_client()
        resp = await client.get(
            f"{AEGRM_BASE}/debitoriPJ",
            params={"cui": cui_clean},
            timeout=15.0,
        )
        if resp.status_code != 200:
            logger.debug(f"[aegrm] HTTP {resp.status_code} pentru CUI {cui_clean}")
            return {"has_data": False, "error": f"HTTP {resp.status_code}"}

        data = resp.json()
        entries = data.get("debitoriPJ", []) or []

        details = []
        for entry in entries[:10]:  # max 10 garantii afisate
            details.append({
                "nr_inregistrare": entry.get("numarInregistrare", "N/A"),
                "data": entry.get("dataInregistrare", "N/A"),
                "creditor": entry.get("creditor", {}).get("denumire", "N/A") if isinstance(entry.get("creditor"), dict) else "N/A",
                "tip_bun": entry.get("descriereBun", "N/A"),
                "status": entry.get("status", "N/A"),
            })

        logger.info(f"[aegrm] CUI {cui_clean}: {len(entries)} garantii gasite")
        return {
            "has_data": True,
            "has_guarantees": len(entries) > 0,
            "count": len(entries),
            "details": details,
            "source": "AEGRM",
            "source_url": "https://aegrm.justportal.ro",
        }

    except Exception as e:
        logger.warning(f"[aegrm] Eroare pentru CUI {cui}: {e}")
        return {"has_data": False, "error": str(e)}
