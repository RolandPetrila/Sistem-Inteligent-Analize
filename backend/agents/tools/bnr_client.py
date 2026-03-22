"""
Client BNR — Cursuri valutare din XML feed
URL: https://www.bnr.ro/nbrfxrates.xml
Stabil, actualizat zilnic.
"""

from datetime import date
from xml.etree import ElementTree

from loguru import logger
from backend.http_client import get_client


BNR_URL = "https://www.bnr.ro/nbrfxrates.xml"
BNR_NS = {"bnr": "http://www.bnr.ro/xsd"}


async def get_exchange_rates() -> dict:
    """Extrage cursurile BNR din XML. Returneaza dict {currency: rate}."""
    from backend.agents.tools.retry import with_retry

    async def _do_request():
        c = get_client()
        r = await c.get(BNR_URL)
        r.raise_for_status()
        return r

    logger.debug("BNR: fetching exchange rates")
    response = await with_retry(_do_request, retries=2, backoff=[2, 5], source_name="BNR")

    root = ElementTree.fromstring(response.text)

    # Gaseste data cursului
    body = root.find("bnr:Body", BNR_NS)
    if body is None:
        return {"error": "BNR XML format unexpected", "rates": {}}

    cube = body.find("bnr:Cube", BNR_NS)
    if cube is None:
        return {"error": "BNR Cube not found", "rates": {}}

    rate_date = cube.get("date", str(date.today()))

    rates = {"RON": 1.0}
    for rate_elem in cube.findall("bnr:Rate", BNR_NS):
        currency = rate_elem.get("currency", "")
        multiplier = int(rate_elem.get("multiplier", "1"))
        try:
            value = float(rate_elem.text)
            rates[currency] = value / multiplier
        except (TypeError, ValueError):
            continue

    logger.debug(f"BNR: {len(rates)} rates for {rate_date}")

    return {
        "source": "BNR",
        "source_url": BNR_URL,
        "date": rate_date,
        "rates": rates,
    }


async def convert_currency(
    amount: float, from_currency: str, to_currency: str = "RON"
) -> dict:
    """Conversie valutara folosind cursul BNR."""
    data = await get_exchange_rates()
    rates = data.get("rates", {})

    if from_currency not in rates or to_currency not in rates:
        return {
            "error": f"Currency not found: {from_currency} or {to_currency}",
            "available": list(rates.keys()),
        }

    # Conversie prin RON
    amount_in_ron = amount * rates[from_currency]
    if to_currency == "RON":
        result = amount_in_ron
    else:
        result = amount_in_ron / rates[to_currency]

    return {
        "from": from_currency,
        "to": to_currency,
        "amount": amount,
        "result": round(result, 4),
        "rate": rates[from_currency],
        "date": data.get("date"),
    }
