"""
Validare CUI Romania cu cifra de control (MOD 11).
Previne request-uri inutile catre ANAF pentru CUI-uri invalide.
"""
import re

# Numarul de cifre al unui CUI extras din text liber. Sub 6 cifre = prea mult zgomot
# (orice "42"/"1234" ar fi prins); campul dedicat accepta in continuare 2-10 cifre via
# validate_cui. Definit o singura data — reutilizat si de detectia anti-halucinatie din
# agent_synthesis (acelasi bound, semantica diferita: findall peste matches invalide).
CUI_DIGITS = r"\d{6,10}"

# Extractor din text liber: optional prefix RO, apoi 6-10 cifre. \b la ambele capete
# impiedica prinderea unui subsir dintr-un numar mai lung — un telefon/CNP de 11+ cifre
# nu se potriveste deloc, nu se ciopartesc primele 10 cifre. IGNORECASE: analysis.py
# paseaza query deja lowercased, deci "ro9901265" se potriveste doar cu flag-ul pornit.
_CUI_EXTRACT_RX = re.compile(rf"\b(?:RO\s*)?({CUI_DIGITS})\b", re.IGNORECASE)


def validate_cui(cui: str) -> dict:
    """
    Valideaza un CUI romanesc folosind algoritmul cifrei de control.
    Returneaza dict cu valid, cui_clean, error.
    """
    # Curata input
    cleaned = str(cui).strip().upper().replace("RO", "").replace(" ", "")

    if not cleaned:
        return {"valid": False, "cui_clean": "", "error": "CUI gol"}

    if not cleaned.isdigit():
        return {"valid": False, "cui_clean": cleaned, "error": "CUI contine caractere non-numerice"}

    if len(cleaned) < 2 or len(cleaned) > 10:
        return {"valid": False, "cui_clean": cleaned, "error": f"CUI trebuie sa aiba 2-10 cifre (are {len(cleaned)})"}

    # Algoritmul cifrei de control MOD 11
    weights = [7, 5, 3, 2, 1, 7, 5, 3, 2]

    # Ultimul digit e cifra de control
    check_digit = int(cleaned[-1])
    digits = [int(d) for d in cleaned[:-1]]

    # Pad la stanga cu zerouri daca e nevoie (weights are 9 positions)
    while len(digits) < 9:
        digits.insert(0, 0)

    # Calculeaza suma ponderata
    # strict=True: digits e pad-uit la exact 9 iar weights are 9 — egalitatea e o
    # invarianta, nu o coincidenta. Daca pad-area se strica vreodata, vrem exceptie
    # zgomotoasa, nu o cifra de control calculata pe o lista trunchiata tacut.
    weighted_sum = sum(d * w for d, w in zip(digits, weights, strict=True))

    # MOD 11, apoi MOD 10 daca rezultatul e 10
    remainder = (weighted_sum * 10) % 11
    if remainder == 10:
        remainder = 0

    if remainder != check_digit:
        return {
            "valid": False,
            "cui_clean": cleaned,
            "error": f"Cifra de control invalida (expected {remainder}, got {check_digit})",
        }

    return {"valid": True, "cui_clean": cleaned, "error": None}


def extract_and_validate_cui(text: str) -> dict:
    """
    Extrage si valideaza un CUI dintr-un text liber.

    Scaneaza TOTI candidatii 6-10 cifre si valideaza fiecare MOD11 — un numar de
    zgomot (valoare, telefon) care pica MOD11 nu mai poate fura slotul unui CUI real
    de mai tarziu (bug-ul vechi: re.search prindea doar primul numar). Ambiguitatea
    (>=2 CUI-uri DISTINCTE valide) OPRESTE: nu ghicim care e tinta. Acelasi pattern
    0-sau->=2->STOP ca filtrarea de furnizor SEAP din 93fa5de.
    Accepta formate: 12345678, RO12345678, RO 12345678.
    """
    # Dedup pe sirul curatat EXACT: teoretic "09901265" si "9901265" ar putea numara
    # ca 2 distincte (limita cunoscuta, nu bug — leading-zero pe CUI e practic inexistent).
    valid_distinct: list[str] = []
    for cand in _CUI_EXTRACT_RX.findall(text or ""):
        v = validate_cui(cand)
        if v["valid"] and v["cui_clean"] not in valid_distinct:
            valid_distinct.append(v["cui_clean"])

    if len(valid_distinct) == 1:
        return {"valid": True, "cui_clean": valid_distinct[0], "error": None}
    if len(valid_distinct) >= 2:
        return {
            "valid": False,
            "cui_clean": "",
            "error": f"Candidati multipli valizi ({', '.join(valid_distinct)}) — ambiguu",
        }
    return {"valid": False, "cui_clean": "", "error": "CUI neidentificat"}
