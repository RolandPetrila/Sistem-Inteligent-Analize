"""
Client Sanctiuni — liste oficiale consolidate: OFAC SDN (US) + UE FSF + ONU.

Toate FREE, fara cheie, uz comercial permis (domeniu public / reuse policy).
Endpoint-uri confirmate live 2026-07-11 (urmeaza redirect-uri -> get_client are follow_redirects).

Scop RIS (due-diligence): verifica firma + administratori/asociati + contraparti straine
contra listelor oficiale de sanctiuni. NU acopera PEP (persoane expuse politic) — pentru PEP
nu exista sursa free-comerciala (OpenSanctions e CC BY-NC = platit).

Matching CONSERVATOR: egalitate de set de token-uri normalizate (diacritice stripate, sufixe
juridice + stopwords eliminate). Evita false pozitive de tip substring. Rezultatele sunt
"potentiale potriviri de verificat manual", nu verdicte automate.
"""

import csv
import io
import json
import os
import re
import time
import unicodedata
import xml.etree.ElementTree as ET

from loguru import logger

from backend.agents.tools.retry import with_retry
from backend.http_client import get_client

OFAC_SDN_URL = "https://sanctionslistservice.ofac.treas.gov/api/download/SDN.CSV"
EU_FSF_URL = (
    "https://webgate.ec.europa.eu/fsd/fsf/public/files/"
    "xmlFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw"
)
UN_CONSOLIDATED_URL = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"

CACHE_PATH = os.path.join("data", "sanctions_cache.json")
CACHE_TTL_SECONDS = 24 * 3600
_DOWNLOAD_TIMEOUT = 90.0  # listele sunt 2-15 MB

# Sufixe juridice + stopwords eliminate din chei (reduc coliziunile triviale)
_LEGAL_SUFFIXES = {
    "SRL", "SA", "SCA", "SNC", "SCS", "PFA", "II", "IF", "SRO", "GMBH", "AG",
    "LTD", "LIMITED", "LLC", "INC", "CORP", "CORPORATION", "CO", "COMPANY",
    "BV", "NV", "SPA", "OOO", "LLP", "PLC", "SL", "SAS", "SARL", "KFT", "ZRT",
    "AD", "EOOD", "OOD", "DOO", "AS", "OY", "AB", "GROUP", "HOLDING", "HOLDINGS",
}
_STOP_TOKENS = {"THE", "AND", "OF", "DE", "LA", "EL", "AL", "FOR", "FZE", "FZ"}


# ---------------------------------------------------------------------------
# Normalizare + chei de matching
# ---------------------------------------------------------------------------
def _strip_diacritics(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _norm_tokens(name: str) -> frozenset:
    s = _strip_diacritics(str(name or "")).upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    toks = [
        t for t in s.split()
        if len(t) > 1 and t not in _LEGAL_SUFFIXES and t not in _STOP_TOKENS
    ]
    return frozenset(toks)


def _key(name: str) -> str | None:
    """Cheie de matching sau None daca numele e prea generic (anti-fals-pozitiv)."""
    toks = _norm_tokens(name)
    if not toks:
        return None
    if len(toks) >= 2:
        return "|".join(sorted(toks))
    # Un singur token -> doar daca e lung/distinctiv (>= 8 caractere).
    # Prag inalt intentionat: blocheaza cuvinte comune (GLOBAL/COMPANY) = anti-fals-pozitiv.
    (only,) = tuple(toks)
    return only if len(only) >= 8 else None


# ---------------------------------------------------------------------------
# Parsere per sursa -> lista de {name, type, source}
# ---------------------------------------------------------------------------
def _parse_ofac(text: str) -> list[dict]:
    records = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 3:
            continue
        name = (row[1] or "").strip()
        if not name or name == "-0-":
            continue
        stype = (row[2] or "").strip()
        records.append({"name": name, "type": ("" if stype == "-0-" else stype) or "entity", "source": "OFAC"})
    return records


def _parse_eu(text: str) -> list[dict]:
    records = []
    root = ET.fromstring(text)
    ns = "{http://eu.europa.ec/fpi/fsd/export}"
    for ent in root.findall(f"{ns}sanctionEntity"):
        subj = ent.find(f"{ns}subjectType")
        stype = subj.get("code") if subj is not None else ""
        for alias in ent.findall(f"{ns}nameAlias"):
            whole = (alias.get("wholeName") or "").strip()
            if whole:
                records.append({"name": whole, "type": stype or "entity", "source": "EU"})
    return records


def _un_full_name(el) -> str:
    parts = [
        (el.findtext(t) or "").strip()
        for t in ("FIRST_NAME", "SECOND_NAME", "THIRD_NAME", "FOURTH_NAME")
    ]
    return " ".join(p for p in parts if p)


def _parse_un(text: str) -> list[dict]:
    records = []
    root = ET.fromstring(text)
    for ind in root.findall(".//INDIVIDUAL"):
        name = _un_full_name(ind)
        if name:
            records.append({"name": name, "type": "individual", "source": "UN"})
        for al in ind.findall(".//INDIVIDUAL_ALIAS"):
            an = (al.findtext("ALIAS_NAME") or "").strip()
            if an:
                records.append({"name": an, "type": "individual", "source": "UN"})
    for ent in root.findall(".//ENTITY"):
        name = (ent.findtext("FIRST_NAME") or "").strip()
        if name:
            records.append({"name": name, "type": "entity", "source": "UN"})
        for al in ent.findall(".//ENTITY_ALIAS"):
            an = (al.findtext("ALIAS_NAME") or "").strip()
            if an:
                records.append({"name": an, "type": "entity", "source": "UN"})
    return records


# ---------------------------------------------------------------------------
# Fetch + cache
# ---------------------------------------------------------------------------
_index: dict[str, list[dict]] | None = None
_meta: dict = {"sources": [], "total": 0, "built_at": ""}


async def _fetch(url: str, source: str) -> str:
    async def _do():
        c = get_client()
        r = await c.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 RIS-Compliance-Screening"},
            timeout=_DOWNLOAD_TIMEOUT,
        )
        r.raise_for_status()
        return r

    resp = await with_retry(_do, retries=2, backoff=[3, 8], source_name=f"SANCTIONS/{source}")
    return resp.text


async def _build_from_sources() -> dict:
    """Descarca + parseaza cele 3 liste. Fiecare sursa esueaza independent."""
    parsers = [
        ("OFAC", OFAC_SDN_URL, _parse_ofac),
        ("EU", EU_FSF_URL, _parse_eu),
        ("UN", UN_CONSOLIDATED_URL, _parse_un),
    ]
    records: list[dict] = []
    sources_ok: list[str] = []
    for source, url, parser in parsers:
        try:
            text = await _fetch(url, source)
            recs = parser(text)
            if recs:
                records.extend(recs)
                sources_ok.append(source)
                logger.info(f"[sanctions] {source}: {len(recs)} intrari")
        except Exception as e:
            logger.warning(f"[sanctions] {source} esuat: {e}")

    return {
        "records": records,
        "sources": sources_ok,
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def _build_index(records: list[dict]) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
    for rec in records:
        k = _key(rec["name"])
        if not k:
            continue
        bucket = index.setdefault(k, [])
        # dedup pe (source, name)
        if not any(r["source"] == rec["source"] and r["name"] == rec["name"] for r in bucket):
            bucket.append(rec)
    return index


def _load_cache() -> dict | None:
    try:
        if not os.path.exists(CACHE_PATH):
            return None
        if time.time() - os.path.getmtime(CACHE_PATH) > CACHE_TTL_SECONDS:
            return None
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.debug(f"[sanctions] cache load fail: {e}")
        return None


def _save_cache(data: dict) -> None:
    try:
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        logger.debug(f"[sanctions] cache save fail: {e}")


async def ensure_loaded(force: bool = False) -> bool:
    """Asigura ca indexul e in memorie. Returneaza True daca sunt date disponibile."""
    global _index, _meta
    if _index is not None and not force:
        return bool(_index)

    data = None if force else _load_cache()
    if data is None:
        data = await _build_from_sources()
        if data["records"]:
            _save_cache(data)

    _index = _build_index(data.get("records", []))
    _meta = {
        "sources": data.get("sources", []),
        "total": len(data.get("records", [])),
        "built_at": data.get("built_at", ""),
    }
    return bool(_index)


async def refresh() -> dict:
    """Fortare refresh (pentru scheduler zilnic)."""
    await ensure_loaded(force=True)
    return dict(_meta)


# ---------------------------------------------------------------------------
# API public
# ---------------------------------------------------------------------------
async def screen(names: list[str]) -> dict:
    """
    Ecraneaza o lista de nume (firma + administratori/asociati) contra listelor de sanctiuni.

    Returneaza:
      status: "clean" | "hit" | "unavailable"
      hits: [{query, matched_name, source, type}]
      checked: [nume ecranate]
      lists_checked, total_entries, data_date
    """
    clean_names = [n.strip() for n in (names or []) if n and n.strip()]
    ok = await ensure_loaded()
    if not ok or _index is None:
        return {
            "status": "unavailable",
            "hits": [],
            "checked": clean_names,
            "lists_checked": _meta.get("sources", []),
            "total_entries": _meta.get("total", 0),
            "data_date": _meta.get("built_at", ""),
        }

    hits: list[dict] = []
    seen = set()
    for query in clean_names:
        k = _key(query)
        if not k or k not in _index:
            continue
        for rec in _index[k]:
            dedup = (query, rec["source"], rec["name"])
            if dedup in seen:
                continue
            seen.add(dedup)
            hits.append({
                "query": query,
                "matched_name": rec["name"],
                "source": rec["source"],
                "type": rec["type"],
            })

    return {
        "status": "hit" if hits else "clean",
        "hits": hits,
        "checked": clean_names,
        "lists_checked": _meta.get("sources", []),
        "total_entries": _meta.get("total", 0),
        "data_date": _meta.get("built_at", ""),
    }
