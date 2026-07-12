"""
Portal Just Client — Dosare judecatoresti de pe portal.just.ro.
Phase R6 F1-1: SOAP client pentru interogare dosare pe CUI/denumire.
Fallback: daca zeep nu e instalat, returneaza placeholder.

WSDL-ul real (verificat 2026-07-12, dupa instalarea `zeep` — pana atunci codul nu
rulase NICIODATA cu succes) cere un camp `institutie` OBLIGATORIU: enum cu 246 de
instante posibile, fara valoare "toate instantele". Nu exista cautare nationala
intr-un singur apel. Cautam Tribunalul judetului firmei + Curtea de Apel regionala
(cf. circumscriptiilor oficiale ale instantelor, portal.just.ro/SitePages/circumscriptii.aspx) —
acopera marea majoritate a litigiilor uzuale, dar rateaza dosare depuse in alt judet.
"""

import asyncio
import re
import unicodedata
from datetime import datetime

from loguru import logger

WSDL = "http://portalquery.just.ro/query.asmx?WSDL"
_TIMEOUT_S = 30

# Circumscriptii Curti de Apel -> judete arondate (cele 15 curti civile + Bucuresti).
# Sursa: portal.just.ro/SitePages/circumscriptii.aspx (structura oficiala instante RO).
_CURTE_APEL_JUDETE: dict[str, list[str]] = {
    "ALBAIULIA": ["ALBA", "HUNEDOARA", "SIBIU"],
    "BACAU": ["BACAU", "NEAMT"],
    "BRASOV": ["BRASOV", "COVASNA"],
    "BUCURESTI": ["BUCURESTI", "CALARASI", "GIURGIU", "IALOMITA", "TELEORMAN", "ILFOV"],
    "CLUJ": ["CLUJ", "BISTRITANASAUD", "MARAMURES", "SALAJ"],
    "CONSTANTA": ["CONSTANTA", "TULCEA"],
    "CRAIOVA": ["DOLJ", "GORJ", "MEHEDINTI", "OLT"],
    "GALATI": ["GALATI", "BRAILA", "VRANCEA"],
    "IASI": ["IASI", "VASLUI"],
    "ORADEA": ["BIHOR", "SATUMARE"],
    "PITESTI": ["ARGES", "VALCEA"],
    "PLOIESTI": ["PRAHOVA", "BUZAU", "DAMBOVITA"],
    "SUCEAVA": ["SUCEAVA", "BOTOSANI"],
    "TARGUMURES": ["MURES", "HARGHITA"],
    "TIMISOARA": ["TIMIS", "ARAD", "CARASSEVERIN"],
}
_JUDET_TO_CURTE = {j: curte for curte, judete in _CURTE_APEL_JUDETE.items() for j in judete}


def _normalize_judet(judet: str) -> str:
    """Normalizeaza un nume de judet (orice diacritice/casing) la formatul folosit de
    codurile Institutie din WSDL (ex. 'Bistrița-Năsăud' -> 'BISTRITANASAUD',
    'Satu Mare' -> 'SATUMARE') — coincide cu numele Tribunalul<COD> din enum."""
    s = unicodedata.normalize("NFKD", judet or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^A-Za-z]", "", s).upper()


def _institutions_for_judet(judet: str) -> list[str]:
    """Tribunalul judetului + Curtea de Apel regionala. Fara judet cunoscut -> lista
    goala (institutie e obligatoriu, nu putem ghici o instanta)."""
    code = _normalize_judet(judet)
    if not code:
        return []
    institutions = [f"Tribunalul{code}"]
    curte = _JUDET_TO_CURTE.get(code)
    if curte:
        institutions.append(f"CurteadeApel{curte}")
    return institutions


def _norm_name(s: str) -> str:
    """Normalizare fuzzy pt potrivirea numelui firmei in lista de parti ale unui dosar
    (diacritice + majuscule/minuscule variaza intre ANAF si portal.just.ro)."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^A-Za-z0-9]", "", s).upper()


def _party_role(parti_list, company_name: str) -> str | None:
    """Cauta firma in lista de parti ale unui dosar (obiect.parti.DosarParte[]) si
    returneaza rolul ei ("reclamant"/"parat") sau None daca nu se gaseste potrivire."""
    if not parti_list or not company_name:
        return None
    target = _norm_name(company_name)
    if not target:
        return None
    for p in parti_list:
        nume = _norm_name(str(getattr(p, "nume", "") or ""))
        if nume and (target in nume or nume in target):
            calitate = _norm_name(str(getattr(p, "calitateParte", "") or ""))
            if "RECLAMANT" in calitate:
                return "reclamant"
            if "PARAT" in calitate:  # _norm_name strips diacritice: "Pârât" -> "PARAT"
                return "parat"
    return None


def _parse_dosare(result, company_name: str = "", cui: str = "") -> dict:
    """Parseaza rezultatul SOAP (lista de obiecte Dosar) in format standard.

    Shape reala confirmata live 2026-07-12 (pana atunci codul nu rulase niciodata
    cu succes — campurile presupuse initial nu existau pe obiectul real): fiecare
    Dosar are `numar`, `data`, `institutie`, `obiect`, `categorieCazNume`,
    `stadiuProcesualNume`, si `parti.DosarParte[]` cu {nume, calitateParte}."""
    if not result:
        return {"total_dosare": 0, "reclamant": 0, "parat": 0, "dosare": []}

    dosare = []
    reclamant_count = 0
    parat_count = 0

    try:
        items = result if isinstance(result, (list, tuple)) else [result]
        for item in items:
            parti = getattr(item, "parti", None)
            parti_list = getattr(parti, "DosarParte", None) if parti is not None else None
            role = _party_role(parti_list, company_name)
            if role == "reclamant":
                reclamant_count += 1
            elif role == "parat":
                parat_count += 1

            dosare.append({
                "numar": str(getattr(item, "numar", "") or ""),
                "data": str(getattr(item, "data", "") or ""),
                "institutie": str(getattr(item, "institutie", "") or ""),
                "obiect": str(getattr(item, "obiect", "") or ""),
                "categorie": str(getattr(item, "categorieCazNume", "") or ""),
                "stadiu": str(getattr(item, "stadiuProcesualNume", "") or ""),
                "calitate": role or "",
            })
    except Exception as e:
        logger.debug(f"[just] parse error: {e}")

    return {
        "total_dosare": len(dosare),
        "reclamant": reclamant_count,
        "parat": parat_count,
        "dosare": dosare[:20],  # limita 20 dosare in output
    }


async def search_dosare(company_name: str, cui: str = "", judet: str = "") -> dict:
    """
    Cauta dosarele judecatoresti ale unei firme pe portal.just.ro.

    Args:
        company_name: Denumirea firmei
        cui: CUI (optional, folosit pt deduplicare)
        judet: judetul firmei (din ANAF/openapi.ro) — determina ce instante se cauta.
            Fara judet, `institutie` (camp SOAP obligatoriu) nu poate fi ales -> found=False.

    Returns:
        dict: total_dosare, reclamant, parat, dosare[], source, institutions_searched
    """
    institutions = _institutions_for_judet(judet)
    if not institutions:
        return {
            "total_dosare": 0,
            "found": False,
            "source": "portal.just.ro",
            "error": "judet necunoscut — institutie e camp SOAP obligatoriu, nu se poate alege instanta",
        }

    try:
        import requests as _requests
        import zeep
        from zeep.transports import Transport
    except ImportError:
        logger.debug("[just] zeep not installed — portal.just.ro indisponibil")
        return {
            "total_dosare": 0,
            "found": False,
            "source": "portal.just.ro (indisponibil — pip install zeep)",
            "error": "dependency_missing",
        }

    try:
        session = _requests.Session()
        session.timeout = _TIMEOUT_S
        transport = Transport(session=session, timeout=_TIMEOUT_S)
        loop = asyncio.get_event_loop()

        def _sync_client():
            return zeep.Client(WSDL, transport=transport)

        client = await asyncio.wait_for(loop.run_in_executor(None, _sync_client), timeout=_TIMEOUT_S)
    except Exception as e:
        logger.warning(f"[just] WSDL fetch esuat: {e}")
        return {"total_dosare": 0, "found": False, "source": "portal.just.ro", "error": str(e)[:150]}

    all_dosare: list[dict] = []
    total_dosare_sum = 0
    reclamant_total = 0
    parat_total = 0
    errors: list[str] = []

    for institutie in institutions:
        def _sync_search(inst=institutie):
            return client.service.CautareDosare(
                numarDosar="",
                obiectDosar="",
                numeParte=company_name[:100],  # limita lungime
                institutie=inst,
                dataStart=datetime(2000, 1, 1),
                dataStop=datetime.now(),
            )

        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, _sync_search), timeout=_TIMEOUT_S,
            )
            parsed = _parse_dosare(result, company_name, cui)
            total_dosare_sum += parsed["total_dosare"]
            all_dosare.extend(parsed["dosare"])
            reclamant_total += parsed["reclamant"]
            parat_total += parsed["parat"]
        except TimeoutError:
            errors.append(f"{institutie}: timeout")
        except Exception as e:
            errors.append(f"{institutie}: {str(e)[:100]}")

        await asyncio.sleep(1)  # politicos intre apeluri catre acelasi serviciu public

    parsed_final = {
        "total_dosare": total_dosare_sum,
        "reclamant": reclamant_total,
        "parat": parat_total,
        "dosare": all_dosare[:20],
        "source": "portal.just.ro (SOAP)",
        "institutions_searched": institutions,
        "found": True,
    }
    if errors:
        parsed_final["partial_errors"] = errors
    logger.info(f"[just] {company_name}: {parsed_final['total_dosare']} dosare gasite in {institutions}")
    return parsed_final
