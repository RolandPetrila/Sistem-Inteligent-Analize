"""
Funding Programs — Matching programe de finantare pentru firme.
Phase R6 F5-1: Baza de date locala programe active + matching logic.
"""

import json
from datetime import date
from pathlib import Path

from loguru import logger

_DATA_FILE = Path(__file__).parent.parent.parent.parent / "data" / "funding_programs.json"
_programs_cache: list[dict] | None = None


def _load_programs() -> list[dict]:
    """Incarca programele din JSON local (cu cache in-memory)."""
    global _programs_cache
    if _programs_cache is None:
        try:
            with open(_DATA_FILE, encoding="utf-8") as f:
                _programs_cache = json.load(f)
            logger.debug(f"[funding] Loaded {len(_programs_cache)} programs from {_DATA_FILE}")
        except Exception as e:
            logger.warning(f"[funding] Cannot load {_DATA_FILE}: {e}")
            _programs_cache = []
    return _programs_cache


def match_programs(
    caen_code: str = "",
    angajati: int = 0,
    vechime_ani: int = 0,
    are_datorii_anaf: bool = False,
    regiune: str = "toate",
) -> list[dict]:
    """
    Returneaza programele de finantare eligibile pentru un profil de firma.

    Args:
        caen_code: Codul CAEN principal (ex: "6201")
        angajati: Numarul de angajati
        vechime_ani: Vechimea firmei in ani
        are_datorii_anaf: True daca firma are datorii la ANAF
        regiune: Codul regiunii (NE, NV, V, SV, S, SE, C, B, rural, toate)

    Returns:
        Lista de programe eligibile, sortata dupa suma_max_eur desc
    """
    programs = _load_programs()
    today = date.today().isoformat()
    eligible = []

    for prog in programs:
        # Filtru: program activ
        if not prog.get("activ", False):
            continue

        # Filtru: termen expirat
        termen = prog.get("termen", "")
        if termen and termen < today:
            continue

        elig = prog.get("eligibilitate", {})

        # Filtru: datorii ANAF
        if elig.get("datorii_anaf") is False and are_datorii_anaf:
            continue

        # Filtru: nr angajati
        ang_min = elig.get("angajati_min", 0)
        ang_max = elig.get("angajati_max", 9999)
        if angajati < ang_min or angajati > ang_max:
            continue

        # Filtru: vechime
        vech_min = elig.get("vechime_ani_min", 0)
        vech_max = elig.get("vechime_ani_max", 999)
        if vechime_ani < vech_min or vechime_ani > vech_max:
            continue

        # Filtru: CAEN exclus
        caen_exclude = elig.get("caen_exclude", [])
        if caen_code and caen_code in caen_exclude:
            continue

        # Filtru: CAEN inclus (daca lista e specificata, firma trebuie sa fie in ea)
        caen_include = elig.get("caen_includ", [])
        if caen_include and caen_code and caen_code not in caen_include:
            continue

        # Filtru: regiune
        regiuni_prog = elig.get("regiuni", ["toate"])
        if "toate" not in regiuni_prog and regiune not in regiuni_prog:
            continue

        eligible.append({
            "id": prog["id"],
            "nume": prog["nume"],
            "suma_max_eur": prog.get("suma_max_eur", 0),
            "termen": prog.get("termen", ""),
            "link": prog.get("link", ""),
            "descriere": prog.get("descriere", ""),
            "sursa": prog.get("sursa", ""),
        })

    # Sorteaza dupa suma maxima (desc)
    eligible.sort(key=lambda p: p.get("suma_max_eur", 0), reverse=True)
    logger.debug(f"[funding] {len(eligible)} programe eligibile din {len(programs)} pentru CAEN={caen_code}, angajati={angajati}")
    return eligible


def get_funding_summary(eligible: list[dict]) -> str:
    """Genereaza un text sumar despre programele eligibile."""
    if not eligible:
        return "Nu s-au identificat programe de finantare eligibile pentru profilul firmei."

    total = len(eligible)
    max_suma = max(p.get("suma_max_eur", 0) for p in eligible)
    names = [p["nume"] for p in eligible[:3]]

    summary = (
        f"Au fost identificate {total} programe de finantare eligibile, "
        f"cu un maxim de {max_suma:,.0f} EUR per proiect. "
        f"Principale: {'; '.join(names)}."
    )
    if total > 3:
        summary += f" (+{total-3} alte programe disponibile)"

    return summary
