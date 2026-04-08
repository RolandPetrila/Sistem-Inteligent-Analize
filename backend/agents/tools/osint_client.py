"""
OSINT Client — Monitorul Oficial + Date Istorice Firme
Cauta publicatii din Monitorul Oficial (Partea a IV-a) pentru a detecta:
- Cesiuni suspecte de parti sociale
- Schimbari frecvente de asociati / administratori
- Majorari de capital suspicioase
- Schimbari de sediu repetate
- Fuziuni / divizari / lichidari

Implementare: Tavily search cu domenii tinta + NLP simplu pentru semnale.
"""

import re

from loguru import logger

from backend.agents.tools import tavily_client
from backend.services import cache_service

# Semnale de risc extrase din textele Monitorului Oficial
_RISK_PATTERNS = {
    "cesiune_parti_sociale": re.compile(
        r"cesion(are|eaza|at)|transf(er|era)\s+p[aă]r[tț]i\s+sociale|v[aâ]nzare\s+p[aă]r[tț]i",
        re.IGNORECASE,
    ),
    "schimbare_asociati": re.compile(
        r"retrag(ere|e)\s+(asociat|acționar|actionar)|exclud(ere|e)\s+asociat|nou\s+(asociat|acționar)",
        re.IGNORECASE,
    ),
    "schimbare_administrator": re.compile(
        r"revocar(e|ea)\s+(administratorului|administratorilor)|num(ire|irea)\s+administrator",
        re.IGNORECASE,
    ),
    "majorare_capital": re.compile(
        r"major(are|area)\s+(capitalului|capitalul\s+social)|aport\s+la\s+capital",
        re.IGNORECASE,
    ),
    "reducere_capital": re.compile(
        r"reduc(ere|erea)\s+(capitalului|capitalul\s+social)",
        re.IGNORECASE,
    ),
    "schimbare_sediu": re.compile(
        r"schimb(are|arii)\s+sediu|mutare\s+sediu|nou\s+sediu",
        re.IGNORECASE,
    ),
    "dizolvare_lichidare": re.compile(
        r"dizolv(are|arii|at)|lichid(are|arii|at)|radier(e|ea)",
        re.IGNORECASE,
    ),
    "fuziune_divizare": re.compile(
        r"fuzion(are|eaza)|diviz(are|eaza|at)|scindare",
        re.IGNORECASE,
    ),
}

# Severitate per tip semnal
_SIGNAL_SEVERITY = {
    "cesiune_parti_sociale": "HIGH",
    "schimbare_asociati": "HIGH",
    "schimbare_administrator": "MEDIUM",
    "majorare_capital": "LOW",
    "reducere_capital": "HIGH",
    "schimbare_sediu": "MEDIUM",
    "dizolvare_lichidare": "CRITICAL",
    "fuziune_divizare": "MEDIUM",
}

_SIGNAL_LABELS = {
    "cesiune_parti_sociale": "Cesiune parti sociale detectata",
    "schimbare_asociati": "Schimbare asociati/actionari",
    "schimbare_administrator": "Schimbare administrator",
    "majorare_capital": "Majorare capital social",
    "reducere_capital": "Reducere capital social",
    "schimbare_sediu": "Schimbare sediu",
    "dizolvare_lichidare": "Dizolvare / Lichidare / Radiere",
    "fuziune_divizare": "Fuziune / Divizare",
}


def _extract_signals_from_text(text: str) -> list[dict]:
    """Extrage semnale de risc dintr-un fragment de text din Monitorul Oficial."""
    signals = []
    for signal_type, pattern in _RISK_PATTERNS.items():
        if pattern.search(text):
            signals.append({
                "type": signal_type,
                "label": _SIGNAL_LABELS[signal_type],
                "severity": _SIGNAL_SEVERITY[signal_type],
            })
    return signals


async def search_monitorul_oficial(
    company_name: str,
    cui: str | None = None,
    max_results: int = 5,
) -> dict:
    """
    Cauta publicatii din Monitorul Oficial (Partea a IV-a) pentru o firma.

    Strategia:
    1. Query Tavily cu domenii tinta (rejournal.ro, monitoruloficial.ro, lege5.ro)
    2. Query suplimentar pe Google/Bing cu site:rejournal.ro
    3. Analiza NLP simpla pe fragmentele gasite

    Returns:
        dict cu:
        - has_data: bool
        - historical_flags: lista semnale detectate
        - sources: URL-uri gasite
        - raw_results: primele 3 titluri/fragmente
        - risk_summary: rezumat risc OSINT
    """
    if not company_name or len(company_name.strip()) < 3:
        return {
            "has_data": False,
            "historical_flags": [],
            "sources": [],
            "raw_results": [],
            "risk_summary": "Denumire firma insuficienta pentru cautare OSINT",
        }

    # Cache check
    cache_key = f"osint_monitorul_{cui or company_name[:20].replace(' ', '_')}"
    cached = await cache_service.get(cache_key, "osint")
    if cached:
        logger.debug(f"[osint] Cache hit for {company_name[:30]}")
        return cached

    logger.info(f"[osint] Cautare Monitorul Oficial: {company_name[:40]}")

    all_signals: list[dict] = []
    all_sources: list[str] = []
    raw_results: list[dict] = []
    queries_run = 0

    # Query 1: Monitorul Oficial specific
    query_mo = f'"{company_name}" "Monitorul Oficial" "partea a IV-a"'
    if cui:
        query_mo += f" {cui}"

    try:
        result_mo = await tavily_client.search(
            query=query_mo,
            max_results=max_results,
            search_depth="basic",
            include_domains=[
                "rejournal.ro",
                "monitoruloficial.ro",
                "lege5.ro",
                "legalis.ro",
                "doingbusiness.ro",
            ],
        )
        queries_run += 1

        for r in result_mo.get("results", []):
            url = r.get("url", "")
            content = r.get("content", "") + " " + r.get("title", "")
            if url:
                all_sources.append(url)
            signals = _extract_signals_from_text(content)
            for sig in signals:
                sig["source_url"] = url
                sig["snippet"] = content[:200]
                all_signals.append(sig)
            if r.get("title"):
                raw_results.append({
                    "title": r.get("title", ""),
                    "url": url,
                    "date": _extract_date_from_text(r.get("content", "")),
                })

    except Exception as e:
        logger.warning(f"[osint] Query MO error: {e}")

    # Query 2: Cautare generala cesiuni/schimbari firma
    if len(all_signals) == 0:
        query_changes = f'"{company_name}" cesiune parti sociale OR schimbare asociati OR administrator'
        if cui:
            query_changes = f'CUI {cui} cesiune OR schimbare asociati OR administrator'
        try:
            result_changes = await tavily_client.search(
                query=query_changes,
                max_results=3,
                search_depth="basic",
            )
            queries_run += 1

            for r in result_changes.get("results", []):
                url = r.get("url", "")
                content = r.get("content", "") + " " + r.get("title", "")
                signals = _extract_signals_from_text(content)
                for sig in signals:
                    sig["source_url"] = url
                    sig["snippet"] = content[:200]
                    all_signals.append(sig)
                if url and url not in all_sources:
                    all_sources.append(url)

        except Exception as e:
            logger.warning(f"[osint] Query changes error: {e}")

    # Deduplica semnalele (acelasi tip din surse diferite)
    seen_types: set[str] = set()
    deduped_signals = []
    for sig in all_signals:
        if sig["type"] not in seen_types:
            seen_types.add(sig["type"])
            deduped_signals.append(sig)

    # Risk summary
    critical_count = sum(1 for s in deduped_signals if s["severity"] == "CRITICAL")
    high_count = sum(1 for s in deduped_signals if s["severity"] == "HIGH")

    if critical_count > 0:
        risk_summary = "RISC CRITIC: Dizolvare/Lichidare detectata in Monitorul Oficial"
    elif high_count >= 2:
        risk_summary = f"RISC RIDICAT: {high_count} semnale critice (cesiuni/schimbari asociati)"
    elif high_count == 1:
        risk_summary = f"ATENTIE: {deduped_signals[0]['label']} identificata in Monitorul Oficial"
    elif deduped_signals:
        risk_summary = f"Semnale minore detectate: {', '.join(s['label'] for s in deduped_signals[:2])}"
    else:
        risk_summary = "Nu au fost detectate semnale de risc in Monitorul Oficial"

    output = {
        "has_data": len(all_sources) > 0,
        "historical_flags": deduped_signals,
        "sources": list(dict.fromkeys(all_sources))[:5],
        "raw_results": raw_results[:3],
        "risk_summary": risk_summary,
        "queries_run": queries_run,
        "signals_count": {
            "critical": critical_count,
            "high": high_count,
            "total": len(deduped_signals),
        },
    }

    # Cache 48h (date istorice se schimba rar)
    await cache_service.set(cache_key, output, "osint", ttl_hours=48)

    logger.info(
        f"[osint] {company_name[:30]}: {len(deduped_signals)} semnale detectate | "
        f"surse: {len(all_sources)}"
    )
    return output


def _extract_date_from_text(text: str) -> str | None:
    """Extrage o data calendaristica din text (format dd.mm.yyyy sau yyyy-mm-dd)."""
    m = re.search(r"(\d{2})[.\-/](\d{2})[.\-/](\d{4})", text)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    m = re.search(r"(\d{4})[.\-/](\d{2})[.\-/](\d{2})", text)
    if m:
        return m.group(0)
    return None


async def get_osint_summary_for_report(
    company_name: str,
    cui: str | None = None,
) -> dict:
    """
    Versiune simplificata pentru integrarea in rapoarte:
    Returneaza doar campurile relevante pentru afisare.
    """
    result = await search_monitorul_oficial(company_name, cui)
    return {
        "osint_historical": {
            "has_data": result["has_data"],
            "risk_summary": result["risk_summary"],
            "flags": result["historical_flags"],
            "source_count": len(result["sources"]),
        }
    }
