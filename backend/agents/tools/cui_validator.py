"""
Validare CUI Romania cu cifra de control (MOD 11).
Previne request-uri inutile catre ANAF pentru CUI-uri invalide.
"""


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
    Extrage si valideaza un CUI din text liber.
    Accepta formate: 12345678, RO12345678, RO 12345678
    """
    import re

    # Pattern CUI: optional RO prefix, 2-10 cifre
    match = re.search(r'\b(?:RO\s*)?(\d{2,10})\b', text.strip(), re.IGNORECASE)
    if not match:
        return {"valid": False, "cui_clean": "", "error": "Nu s-a gasit un CUI valid in text"}

    return validate_cui(match.group(1))
