"""
Client ANAF REST API — webservicesp.anaf.ro
Extrage: date firma (TVA, datorii, sediu fiscal, stare)
Rate limit: 1 request / 2 secunde
"""

import asyncio
from datetime import date

from loguru import logger
from backend.http_client import get_client


ANAF_API_URL = "https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva"
REQUEST_DELAY = 2  # secunde intre request-uri


async def get_anaf_data(cui: str | int) -> dict:
    """Interogheaza ANAF API pentru un CUI. Returneaza dict cu datele disponibile."""
    cui_clean = str(cui).strip().replace("RO", "").replace("ro", "")

    if not cui_clean.isdigit():
        raise ValueError(f"CUI invalid: {cui}")

    payload = [
        {
            "cui": int(cui_clean),
            "data": date.today().strftime("%Y-%m-%d"),
        }
    ]

    from backend.agents.tools.retry import with_retry

    async def _do_request():
        c = get_client()
        return await c.post(ANAF_API_URL, json=payload)

    logger.debug(f"ANAF request for CUI {cui_clean}")
    response = await with_retry(_do_request, retries=2, backoff=[2, 5], source_name="ANAF")
    # v9 API returneaza 404 HTTP dar cu JSON valid (found/notFound)
    data = response.json()

    if not data.get("found") or not data.get("found")[0]:
        return {
            "cui": cui_clean,
            "found": False,
            "error": "CUI negasit in baza de date ANAF",
        }

    found = data["found"][0]
    date_generale = found.get("date_generale", {})
    inregistrare_scop_tva = found.get("inregistrare_scop_Tva", {})
    inregistrare_ropi = found.get("inregistrare_ROPI", {})
    stare_inactiv = found.get("stare_inactiv", {})
    inregistrare_split_tva = found.get("inregistrare_SplitTVA", {})

    result = {
        "cui": cui_clean,
        "found": True,
        "source": "ANAF",
        "source_url": "https://webservicesp.anaf.ro",

        # Date generale
        "denumire": date_generale.get("denumire", ""),
        "adresa": date_generale.get("adresa", ""),
        "numar_reg_com": date_generale.get("nrRegCom", ""),
        "telefon": date_generale.get("telefon", ""),
        "cod_postal": date_generale.get("codPostal", ""),
        "stare_inregistrare": date_generale.get("stare_inregistrare", ""),
        "data_inregistrare": date_generale.get("data_inregistrare", ""),
        "status_rpc": date_generale.get("statusRO_e_Factura", False),

        # TVA
        "platitor_tva": inregistrare_scop_tva.get("scpTVA", False),
        "data_inceput_tva": inregistrare_scop_tva.get("dataInceputScpTVA", ""),
        "data_sfarsit_tva": inregistrare_scop_tva.get("dataSfarsitScpTVA", ""),

        # ROPI (Registrul Operatorilor Intracomunitari)
        "inregistrat_ropi": inregistrare_ropi.get("statusROPI", False),

        # Stare inactiv
        "inactiv": stare_inactiv.get("statusInactivi", False),
        "data_inactivare": stare_inactiv.get("dataInactivare", ""),
        "data_reactivare": stare_inactiv.get("dataReactivare", ""),

        # Split TVA
        "split_tva": inregistrare_split_tva.get("statusSplitTVA", False),
    }

    return result


async def get_anaf_multiple(cui_list: list[str]) -> list[dict]:
    """Interogheaza ANAF pentru mai multe CUI-uri, cu delay intre request-uri."""
    results = []
    for cui in cui_list:
        try:
            result = await get_anaf_data(cui)
            results.append(result)
        except Exception as e:
            results.append({
                "cui": str(cui),
                "found": False,
                "error": str(e),
            })
        await asyncio.sleep(REQUEST_DELAY)
    return results
