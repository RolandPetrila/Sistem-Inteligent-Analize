"""
Client ANAF Bilant API — Date financiare oficiale per CUI.
Endpoint: GET https://webservicesp.anaf.ro/bilant?an={year}&cui={cui}
Gratuit, fara API key. Date disponibile 2014-2024.
"""

import asyncio
from datetime import date

from loguru import logger

from backend.agents.tools.retry import with_retry
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

    # F19: route transient-error retry through the shared with_retry helper.
    # _fetch raises on HTTP 5xx so with_retry retries it; 4xx is returned as-is.
    async def _fetch():
        resp = await client.get(ANAF_BILANT_URL, params=params)
        if resp.status_code >= 500:
            resp.raise_for_status()
        return resp

    try:
        response = await with_retry(
            _fetch, retries=2, backoff=[2, 5], source_name="ANAF Bilant"
        )
    except Exception as e:
        return {"cui": cui_clean, "year": year, "found": False, "error": str(e)[:100]}

    if response.status_code != 200:
        return {
            "cui": cui_clean,
            "year": year,
            "found": False,
            "error": f"HTTP {response.status_code}",
        }

    # D2 fix: Safe JSON parsing
    try:
        data = response.json()
    except (ValueError, Exception):
        return {"cui": cui_clean, "year": year, "found": False, "error": "Invalid JSON response"}

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

        # Verificat live 2026-07-15 (OMV Petrom CUI 1590082, TAROM CUI 477647,
        # MOSSLEIN CUI 26313362, ani 2021-2023): indicatorii I1-I20 sunt STABILI
        # — aceleasi 20 coduri, aceeasi semnificatie, indiferent de marimea firmei
        # sau de an. Comentariul vechi ("formate diferite pt firme mari vs mici",
        # "parsam dupa text pt ca dupa cod e variabil") era FALS pe ambele afirmatii
        # — codul e stabil, TEXTUL (val_den_indicator) e cel inconsecvent.
        #
        # Dovada concreta: I19 (Pierdere neta) vine cu eticheta text diferita per
        # firma — la OMV/TAROM apare DUPLICAT ca "Pierdere bruta" (identic cu I17),
        # la MOSSLEIN apare corect ca "Pierdere  neta" (dar cu SPATIU DUBLU). Text
        # matching pe "pierdere brut"/"pierdere net" (spatiu simplu) fie suprascria
        # tacut pierdere_bruta cu valoarea NETA (last-write-wins pe I17 apoi I19),
        # fie rata complet "Pierdere  neta" (spatiul dublu rupe substring-ul) — in
        # ambele cazuri pierdere_neta nu era scrisa NICIODATA si profit_net ramanea
        # 0 pt firme cu pierdere neta (ANAF pune 0 la "Profit net"/I18 cand firma
        # e pe pierdere, valoarea reala fiind la I19).
        #
        # Fix: cei 4 indicatori de profit/pierdere se parseaza DUPA COD (stabil),
        # nu dupa text (inconsecvent). Restul campurilor raman pe text matching.
        CODE_FIELD_MAP = {
            "I16": "profit_brut",
            "I17": "pierdere_bruta",
            "I18": "profit_net",
            "I19": "pierdere_neta",
        }

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
            "numar mediu": "numar_mediu_salariati",
        }

        indicators = data.get("i", [])
        for item in indicators:
            if not isinstance(item, dict):
                continue
            val = item.get("val_indicator")
            if val is None:
                continue
            code = item.get("indicator")
            if code in CODE_FIELD_MAP:
                result[CODE_FIELD_MAP[code]] = val
                continue
            # Normalizeaza whitespace-ul (colapseaza spatii multiple) — ieftin si
            # prinde variante ca "Pierdere  neta" (spatiu dublu) pe orice camp viitor.
            den = " ".join((item.get("val_den_indicator") or "").lower().split())
            if den:
                for pattern, field_name in name_map.items():
                    if pattern in den:
                        result[field_name] = val
                        break

        # ANAF pune 0 la "Profit net" (I18) cand firma e pe pierdere si muta
        # valoarea reala la "Pierdere neta" (I19) — facem semnul explicit aici,
        # o singura data la parsare, ca toti consumatorii (scoring, predictive
        # models) sa vada profit_net negativ direct din dictul principal.
        if result.get("profit_net") == 0 and (result.get("pierdere_neta") or 0) > 0:
            result["profit_net"] = -result["pierdere_neta"]

        # Total Active = Active imobilizate + Active circulante + Cheltuieli in avans
        # (identitate bilant prescurtat ANAF — verificat pe date live 2026-07-15 ca se
        # echilibreaza exact cu Capitaluri + Datorii + Provizioane + Venituri in avans,
        # atat pt o firma mica (MOSSLEIN, CUI 26313362) cat si una mare (MEGA IMAGE,
        # CUI 6719278) — formatul "i" e uniform indiferent de marimea firmei pe acest
        # endpoint simplificat, deci formula nu difera pe marime de firma).
        if "active_imobilizate" in result and "active_circulante" in result:
            result["active_totale"] = (
                result["active_imobilizate"]
                + result["active_circulante"]
                + result.get("cheltuieli_avans", 0)
            )

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
