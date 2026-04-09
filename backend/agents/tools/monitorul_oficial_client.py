"""
G2: Monitorul Oficial Partea IV-a — cesiuni, dizolvari, numiri.
Crawler pentru publicatii MO care detecteaza evenimente de risc precoce.

Strategia:
- PRIMAR: Tavily search cu query targetat MO Partea IV + CUI/denumire
- FALLBACK: httpx direct pe monitoruloficial.ro/cautare (HTML parse)

Valoare: cesiuni de parti sociale, dizolvari, radieri apar cu 1-6 luni inainte
de probleme financiare oficiale.
"""

import re
from datetime import UTC, datetime

from loguru import logger

from backend.agents.tools.tavily_client import search as tavily_search
from backend.http_client import get_client

MO_BASE = "https://www.monitoruloficial.ro"

# Tipuri de evenimente cautate in MO Partea IV
EVENT_TYPES = {
    "cesiune_parti_sociale": [
        "cesiune", "cesionar", "cedent", "parti sociale", "transfer parti",
    ],
    "dizolvare": [
        "dizolvare", "dizolvarea", "lichidare", "lichidator",
    ],
    "radiere": [
        "radiere", "radierea",
    ],
    "numire_administrator": [
        "numire administrator", "administrator nou", "revocare administrator",
    ],
    "majorare_capital": [
        "majorare capital", "aport", "marire capital social",
    ],
    "reducere_capital": [
        "reducere capital", "diminuare capital",
    ],
}


def _classify_event(text: str) -> str | None:
    """Clasifica textul intr-un tip de eveniment MO."""
    text_lower = text.lower()
    for event_type, keywords in EVENT_TYPES.items():
        if any(kw in text_lower for kw in keywords):
            return event_type
    return None


def _extract_date(text: str) -> str | None:
    """Extrage o data din text (format dd.mm.yyyy sau dd/mm/yyyy)."""
    patterns = [
        r"(\d{2})[./](\d{2})[./](\d{4})",
        r"(\d{4})-(\d{2})-(\d{2})",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            groups = m.groups()
            if len(groups[0]) == 4:
                return f"{groups[0]}-{groups[1]}-{groups[2]}"
            return f"{groups[2]}-{groups[1]}-{groups[0]}"
    return None


async def search_company_publications(
    cui: str, company_name: str, max_results: int = 5
) -> list[dict]:
    """
    Cauta publicatii din Monitorul Oficial Partea IV pentru o firma.

    Returneaza lista de evenimente gasite:
    [{"date": "2024-03-15", "type": "cesiune_parti_sociale", "snippet": "...", "source": "tavily/mo"}]
    """
    events: list[dict] = []

    if not company_name and not cui:
        return events

    # Strategia 1: Tavily search targetat
    try:
        query = f'"{company_name}" monitorul oficial partea IV'
        if cui:
            query += f" CUI {cui}"

        results = await tavily_search(
            query=query,
            max_results=max_results,
            search_depth="basic",
        )

        if results and isinstance(results, list):
            for r in results:
                snippet = r.get("content", "") or r.get("snippet", "")
                title = r.get("title", "")
                full_text = f"{title} {snippet}"

                event_type = _classify_event(full_text)
                if event_type:
                    event_date = _extract_date(full_text)
                    events.append({
                        "date": event_date or datetime.now(UTC).strftime("%Y-%m-%d"),
                        "type": event_type,
                        "snippet": snippet[:300] if snippet else title[:200],
                        "url": r.get("url", ""),
                        "source": "tavily",
                    })
    except Exception as e:
        logger.debug(f"[monitorul_oficial] Tavily search failed: {e}")

    # Strategia 2: Scrape direct monitoruloficial.ro (fallback)
    if not events and company_name:
        try:
            client = await get_client()
            search_name = company_name.split(" ")[0] if company_name else ""
            if len(search_name) >= 3:
                resp = await client.get(
                    f"{MO_BASE}/cautare",
                    params={"query": search_name, "sectiune": "4"},
                    timeout=10.0,
                    follow_redirects=True,
                )
                if resp.status_code == 200:
                    html = resp.text
                    # Parse simplificat: cauta titluri de publicatii
                    title_matches = re.findall(
                        r'class="titlu[^"]*"[^>]*>([^<]+)</\w+>', html
                    )
                    for title in title_matches[:max_results]:
                        event_type = _classify_event(title)
                        if event_type:
                            event_date = _extract_date(title)
                            events.append({
                                "date": event_date or "",
                                "type": event_type,
                                "snippet": title.strip()[:300],
                                "url": MO_BASE,
                                "source": "monitoruloficial.ro",
                            })
        except Exception as e:
            logger.debug(f"[monitorul_oficial] Direct scrape failed: {e}")

    # Deduplicate by type
    seen_types = set()
    unique_events = []
    for ev in events:
        key = (ev["type"], ev.get("date", ""))
        if key not in seen_types:
            seen_types.add(key)
            unique_events.append(ev)

    if unique_events:
        logger.info(f"[monitorul_oficial] {len(unique_events)} events found for {company_name}")

    return unique_events


def score_penalty(events: list[dict]) -> dict:
    """
    Calculeaza penalty scoring pe baza evenimentelor MO.
    Returneaza dict cu penalties si flags.
    """
    penalty = 0
    flags: list[str] = []

    for ev in events:
        ev_type = ev.get("type", "")
        if ev_type == "cesiune_parti_sociale":
            penalty += 10
            flags.append("Cesiune parti sociale detectata in MO")
        elif ev_type == "dizolvare":
            penalty += 20
            flags.append("Dizolvare in curs detectata in MO")
        elif ev_type == "radiere":
            penalty += 25
            flags.append("Radiere detectata in MO")
        elif ev_type == "reducere_capital":
            penalty += 5
            flags.append("Reducere capital social in MO")
        # numire_administrator si majorare_capital nu sunt negative

    return {
        "penalty": min(penalty, 30),  # Cap la -30 puncte
        "flags": flags,
        "event_count": len(events),
    }
