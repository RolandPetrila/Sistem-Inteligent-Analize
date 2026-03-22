"""
Client ANAF Bilant API — Date financiare oficiale per CUI.
Endpoint: GET https://webservicesp.anaf.ro/bilant?an={year}&cui={cui}
Gratuit, fara API key. Date disponibile 2014-2024.
"""

import asyncio
from datetime import date

from loguru import logger
from backend.http_client import get_client


ANAF_BILANT_URL = "https://webservicesp.anaf.ro/bilant"
REQUEST_DELAY = 2  # secunde intre request-uri


async def get_bilant(cui: str, year: int) -> dict:
    """
    Interogheaza ANAF Bilant API pentru un CUI si an specific.
    Returneaza dict cu date financiare sau error.
    """
    cui_clean = str(cui).strip().replace("RO", "").replace("ro", "")
    if not cui_clean.isdigit():
        return {"cui": cui, "year": year, "found": False, "error": "CUI invalid"}

    params = {"an": year, "cui": int(cui_clean)}

    client = get_client()
    logger.debug(f"ANAF Bilant: CUI={cui_clean} an={year}")

    # C2 fix: Retry once on transient errors (timeout, 5xx)
    response = None
    for attempt in range(2):
        try:
            response = await client.get(ANAF_BILANT_URL, params=params)
            if response.status_code < 500:
                break
            if attempt == 0:
                logger.debug(f"ANAF Bilant: retrying {cui_clean}/{year} after HTTP {response.status_code}")
                await asyncio.sleep(2)
        except Exception as e:
            if attempt == 0:
                logger.debug(f"ANAF Bilant: retrying {cui_clean}/{year} after {e}")
                await asyncio.sleep(2)
            else:
                return {"cui": cui_clean, "year": year, "found": False, "error": str(e)[:100]}

    if response is None or response.status_code != 200:
        return {
            "cui": cui_clean,
            "year": year,
            "found": False,
            "error": f"HTTP {response.status_code if response else 'no response'}",
        }

    data = response.json()

    # ANAF returneaza dict cu: an, cui, deni, caen, den_caen, i (lista indicatori)
    if not data:
        return {
            "cui": cui_clean,
            "year": year,
            "found": False,
            "error": "Nicio data disponibila pentru acest an",
        }

    # Structura reala: {"an": 2023, "cui": 18189442, "deni": "...", "caen": "5829",
    #                   "den_caen": "...", "i": [{"indicator": "I1", "val_indicator": 123, ...}]}

    result = {
        "cui": cui_clean,
        "year": year,
        "found": True,
        "source": "ANAF Bilant",
        "source_url": f"{ANAF_BILANT_URL}?an={year}&cui={cui_clean}",
    }

    if isinstance(data, dict):
        result["denumire"] = data.get("deni", "")
        result["caen_code"] = str(data.get("caen", ""))
        result["caen_description"] = data.get("den_caen", "")

        # ANAF are formate diferite pt firme mari vs mici
        # Parsam dupa val_den_indicator (text) nu dupa cod (variabil)
        name_map = {
            "active imobilizate": "active_imobilizate",
            "active circulante": "active_circulante",
            "stocuri": "stocuri",
            "creante": "creante",
            "casa": "casa_conturi_banci",
            "cheltuieli in avans": "cheltuieli_avans",
            "datorii": "datorii_totale",
            "venituri in avans": "venituri_avans",
            "provizioane": "provizioane",
            "capitaluri": "capitaluri_proprii",
            "capital subscris": "capital_social",
            "patrimoniul regiei": "patrimoniul_regiei",
            "cifra de afaceri": "cifra_afaceri_neta",
            "venituri totale": "venituri_totale",
            "cheltuieli totale": "cheltuieli_totale",
            "profit brut": "profit_brut",
            "pierdere brut": "pierdere_bruta",
            "profit net": "profit_net",
            "pierdere net": "pierdere_neta",
            "numar mediu": "numar_mediu_salariati",
        }

        indicators = data.get("i", [])
        for item in indicators:
            if isinstance(item, dict):
                val = item.get("val_indicator")
                den = (item.get("val_den_indicator") or "").lower().strip()
                if val is not None and den:
                    for pattern, field_name in name_map.items():
                        if pattern in den:
                            result[field_name] = val
                            break

    return result


async def get_bilant_multi_year(cui: str, start_year: int = 2019, end_year: int = None) -> dict:
    """
    Interogheaza ANAF Bilant pentru mai multi ani consecutivi.
    10A M2.3: Fetch newest-first, stop after 2 consecutive not-found (saves requests for newer firms).
    """
    if end_year is None:
        end_year = date.today().year - 1  # Ultimul an complet disponibil

    # 10B M2.3: Fetch from newest to oldest, stop early when data ends
    years_desc = list(range(end_year, start_year - 1, -1))
    results = {}
    errors = []
    consecutive_not_found = 0

    for year in years_desc:
        try:
            data = await get_bilant(cui, year)
            if data.get("found"):
                results[year] = data
                consecutive_not_found = 0
            else:
                errors.append({"year": year, "error": data.get("error", "Not found")})
                consecutive_not_found += 1
                # Stop after 2 consecutive not-found (firm didn't exist yet)
                if consecutive_not_found >= 2 and len(results) > 0:
                    logger.debug(f"ANAF Bilant: stopping at {year}, 2 consecutive not-found after data")
                    break
        except Exception as e:
            errors.append({"year": year, "error": str(e)})
            consecutive_not_found += 1
            if consecutive_not_found >= 2 and len(results) > 0:
                break
        await asyncio.sleep(REQUEST_DELAY)

    # Calculeaza trend-uri
    trend = _calculate_trends(results)

    return {
        "cui": str(cui).strip(),
        "years_requested": years_desc,
        "years_found": list(results.keys()),
        "data": results,
        "trend": trend,
        "errors": errors,
        "source": "ANAF Bilant",
    }


def _calculate_trends(data: dict) -> dict:
    """Calculeaza trend-uri din date multi-an."""
    if len(data) < 2:
        return {}

    trend = {}
    sorted_years = sorted(data.keys())

    metrics = [
        ("cifra_afaceri_neta", "CA"),
        ("profit_net", "Profit Net"),
        ("numar_mediu_salariati", "Angajati"),
        ("capitaluri_proprii", "Capitaluri"),
    ]

    for metric_key, metric_name in metrics:
        values = []
        for year in sorted_years:
            val = data[year].get(metric_key)
            # C1 fix: Use pierdere_neta as negative profit when profit_net is missing
            if val is None and metric_key == "profit_net":
                pierdere = data[year].get("pierdere_neta")
                if pierdere is not None and pierdere > 0:
                    val = -pierdere
            if val is not None:
                values.append({"year": year, "value": val})

        if len(values) >= 2:
            first = values[0]["value"]
            last = values[-1]["value"]
            if first and first != 0:
                growth = round(((last - first) / abs(first)) * 100, 1)
                direction = "crestere" if growth > 0 else "scadere" if growth < 0 else "stabil"
            else:
                growth = None
                direction = "N/A"

            trend[metric_key] = {
                "name": metric_name,
                "values": values,
                "growth_percent": growth,
                "direction": direction,
                "first_year": values[0]["year"],
                "last_year": values[-1]["year"],
            }

    return trend
