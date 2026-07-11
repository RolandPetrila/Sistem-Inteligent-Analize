"""
Client Eurostat — benchmark sector UE (Structural Business Statistics, NACE Rev.2).

API oficial al Comisiei Europene, FARA cheie, uz comercial permis (EU reuse policy).
Confirmat live 2026-07-11: dataset `sbs_ovw_act`, format JSON-stat 2.0, `lastTimePeriod=1`.

Scop RIS: context sectorial la nivel UE (nr. firme, angajati/firma, valoare adaugata) —
complementar benchmark-ului RO din INS TEMPO. Pozitioneaza RO vs media UE27 pe sectorul firmei.

Mapare CAEN -> NACE: CAEN e aliniat NACE Rev.2 pe primele 4 cifre; Eurostat prefixeaza cu
litera sectiunii (ex. CAEN 6201 -> NACE J6201). Fallback pe nivel divizie (J62) apoi sectiune (J),
fiindca datele 4-cifre lipsesc adesea la nivel de tara.
"""

import urllib.parse

from loguru import logger

from backend.agents.tools.retry import with_retry
from backend.http_client import get_client

EUROSTAT_BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/sbs_ovw_act"
GEO_EU = "EU27_2020"

# indic_sbs -> eticheta scurta RO
_INDICATORS = {
    "ENT_NR": "Numar firme",
    "EMP_ENT_NR": "Angajati / firma",
    "AV_SAL_TEUR": "Valoare adaugata / angajat (mii EUR)",
}

# Sectiuni NACE Rev.2: litera + interval de diviziuni
_NACE_SECTIONS = [
    ("A", 1, 3), ("B", 5, 9), ("C", 10, 33), ("D", 35, 35), ("E", 36, 39),
    ("F", 41, 43), ("G", 45, 47), ("H", 49, 53), ("I", 55, 56), ("J", 58, 63),
    ("K", 64, 66), ("L", 68, 68), ("M", 69, 75), ("N", 77, 82), ("O", 84, 84),
    ("P", 85, 85), ("Q", 86, 88), ("R", 90, 93), ("S", 94, 96), ("T", 97, 98),
    ("U", 99, 99),
]


def _nace_section(division: int) -> str:
    for letter, lo, hi in _NACE_SECTIONS:
        if lo <= division <= hi:
            return letter
    return ""


def _nace_candidates(caen_code: str) -> list[str]:
    """CAEN -> [NACE detaliat, NACE divizie, NACE sectiune] (cel mai specific intai)."""
    digits = "".join(c for c in str(caen_code or "") if c.isdigit())
    if len(digits) < 2:
        return []
    div = int(digits[:2])
    letter = _nace_section(div)
    if not letter:
        return []
    cands = []
    if len(digits) >= 4:
        cands.append(f"{letter}{digits[:4]}")
    cands.append(f"{letter}{div:02d}")
    cands.append(letter)
    seen: set[str] = set()
    return [c for c in cands if not (c in seen or seen.add(c))]


def _jsonstat_value(data: dict, coords: dict) -> float | None:
    """Extrage o valoare dintr-un cub JSON-stat 2.0 dupa coordonate {dim: cod}."""
    ids = data.get("id", [])
    size = data.get("size", [])
    dims = data.get("dimension", {})
    if not ids or not size or len(ids) != len(size):
        return None
    stride = [1] * len(size)
    for i in range(len(size) - 2, -1, -1):
        stride[i] = stride[i + 1] * size[i + 1]
    idx = 0
    for i, dim in enumerate(ids):
        pos = dims.get(dim, {}).get("category", {}).get("index", {}).get(coords.get(dim))
        if pos is None:
            return None
        idx += pos * stride[i]
    return data.get("value", {}).get(str(idx))


async def get_sector_context(caen_code: str) -> dict:
    """
    Context sector UE pentru un cod CAEN (nr. firme, angajati/firma, valoare adaugata).
    Compara RO vs media UE27. Returneaza {available: False, ...} la lipsa date / eroare.
    """
    cands = _nace_candidates(caen_code)
    if not cands:
        return {"available": False, "source": "Eurostat", "reason": "CAEN invalid"}

    params = [("format", "JSON"), ("lang", "EN"), ("lastTimePeriod", "1"),
              ("geo", "RO"), ("geo", GEO_EU)]
    params += [("indic_sbs", ind) for ind in _INDICATORS]
    params += [("nace_r2", c) for c in cands]
    url = EUROSTAT_BASE + "?" + urllib.parse.urlencode(params)

    try:
        async def _do():
            c = get_client()
            r = await c.get(url, timeout=40)
            r.raise_for_status()
            return r

        resp = await with_retry(_do, retries=2, backoff=[3, 8], source_name="Eurostat")
        data = resp.json()
    except Exception as e:
        logger.warning(f"[eurostat] fetch esuat pentru CAEN {caen_code}: {e}")
        return {"available": False, "source": "Eurostat", "error": str(e)}

    time_idx = data.get("dimension", {}).get("time", {}).get("category", {}).get("index", {})
    if not time_idx:
        return {"available": False, "source": "Eurostat", "reason": "fara date"}
    year = list(time_idx)[0]
    nace_labels = data.get("dimension", {}).get("nace_r2", {}).get("category", {}).get("label", {})

    indicators: dict[str, dict] = {}
    nace_used = None
    for ind, label in _INDICATORS.items():
        for nace in cands:
            ro = _jsonstat_value(data, {"freq": "A", "nace_r2": nace, "indic_sbs": ind, "geo": "RO", "time": year})
            eu = _jsonstat_value(data, {"freq": "A", "nace_r2": nace, "indic_sbs": ind, "geo": GEO_EU, "time": year})
            if ro is not None or eu is not None:
                indicators[ind] = {"label": label, "ro": ro, "eu": eu, "nace": nace}
                if nace_used is None:
                    nace_used = nace
                break

    if not indicators:
        return {"available": False, "source": "Eurostat", "reason": "fara date sector", "year": year}

    return {
        "available": True,
        "source": "Eurostat",
        "source_url": "https://ec.europa.eu/eurostat",
        "caen_code": str(caen_code),
        "nace_used": nace_used,
        "nace_label": nace_labels.get(nace_used, ""),
        "year": year,
        "indicators": indicators,
    }
