"""
Portal Just Client — Dosare judecatoresti de pe portal.just.ro.
Phase R6 F1-1: SOAP client pentru interogare dosare pe CUI/denumire.
Fallback: daca zeep nu e instalat, returneaza placeholder.
"""

import asyncio

from loguru import logger

WSDL = "http://portalquery.just.ro/query.asmx?WSDL"
_TIMEOUT_S = 30


def _parse_dosare(result, cui: str = "") -> dict:
    """Parseaza rezultatul SOAP in format standard."""
    if not result:
        return {"total_dosare": 0, "reclamant": 0, "parat": 0, "dosare": []}

    dosare = []
    total = 0
    reclamant_count = 0
    parat_count = 0

    try:
        items = result if isinstance(result, (list, tuple)) else [result]
        for item in items:
            dosar = {}
            if hasattr(item, "numarDosar"):
                dosar["numar"] = str(item.numarDosar or "")
            if hasattr(item, "dataDosar"):
                dosar["data"] = str(item.dataDosar or "")
            if hasattr(item, "institutie"):
                dosar["institutie"] = str(item.institutie or "")
            if hasattr(item, "categorie"):
                dosar["categorie"] = str(item.categorie or "")
            if hasattr(item, "calitate"):
                calitate = str(item.calitate or "")
                dosar["calitate"] = calitate
                if "reclamant" in calitate.lower():
                    reclamant_count += 1
                elif "parat" in calitate.lower():
                    parat_count += 1
            if hasattr(item, "stadiu"):
                dosar["stadiu"] = str(item.stadiu or "")
            if dosar:
                dosare.append(dosar)
                total += 1
    except Exception as e:
        logger.debug(f"[just] parse error: {e}")

    return {
        "total_dosare": total,
        "reclamant": reclamant_count,
        "parat": parat_count,
        "dosare": dosare[:20],  # limita 20 dosare in output
    }


async def search_dosare(company_name: str, cui: str = "") -> dict:
    """
    Cauta dosarele judecatoresti ale unei firme pe portal.just.ro.

    Args:
        company_name: Denumirea firmei
        cui: CUI (optional, folosit pt deduplicare)

    Returns:
        dict: total_dosare, reclamant, parat, dosare[], source
    """
    try:
        import requests as _requests
        import zeep
        from zeep.transports import Transport

        session = _requests.Session()
        session.timeout = _TIMEOUT_S
        transport = Transport(session=session, timeout=_TIMEOUT_S)

        loop = asyncio.get_event_loop()

        def _sync_search():
            client = zeep.Client(WSDL, transport=transport)
            result = client.service.CautareDosare(
                numeParte=company_name[:100],  # limita lungime
                obiect="",
                numardosar="",
                instanta=0,
            )
            return result

        result = await asyncio.wait_for(
            loop.run_in_executor(None, _sync_search),
            timeout=_TIMEOUT_S,
        )

        parsed = _parse_dosare(result, cui)
        parsed["source"] = "portal.just.ro (SOAP)"
        parsed["found"] = True
        logger.info(f"[just] {company_name}: {parsed['total_dosare']} dosare gasite")
        return parsed

    except ImportError:
        logger.debug("[just] zeep not installed — portal.just.ro indisponibil")
        return {
            "total_dosare": 0,
            "found": False,
            "source": "portal.just.ro (indisponibil — pip install zeep)",
            "error": "dependency_missing",
        }
    except TimeoutError:
        logger.warning(f"[just] timeout {_TIMEOUT_S}s pentru {company_name}")
        return {"total_dosare": 0, "found": False, "source": "portal.just.ro", "error": "timeout"}
    except Exception as e:
        logger.warning(f"[just] error pentru {company_name}: {e}")
        return {"total_dosare": 0, "found": False, "source": "portal.just.ro", "error": str(e)[:100]}
