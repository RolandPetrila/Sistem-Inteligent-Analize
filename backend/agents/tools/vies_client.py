"""
Client VIES (VAT Information Exchange System) — validare TVA intracomunitar UE.

Endpoint oficial al Comisiei Europene, FARA cheie, uz comercial permis (EU reuse policy).
Rate-limited, per-tranzactie (NU bulk — nu interoga tot registrul).
REST primar (confirmat live 2026-07-11) + fallback SOAP pentru rezilienta la schimbari de endpoint.

Scop in RIS: verificarea unui partener/contraparte din UE (numar TVA valid + denumire/adresa
inregistrata) — completeaza ANAF/ONRC care acopera doar firme RO.
"""

import re

from loguru import logger

from backend.agents.tools.retry import with_retry
from backend.http_client import get_client

VIES_REST_URL = "https://ec.europa.eu/taxation_customs/vies/rest-api/check-vat-number"
VIES_SOAP_URL = "https://ec.europa.eu/taxation_customs/vies/services/checkVatService"

# Coduri de tara folosite ca prefix TVA in VIES (nu ISO pur: Grecia = EL, Irlanda de Nord = XI)
EU_VAT_COUNTRY_CODES = {
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR",
    "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO",
    "SE", "SI", "SK", "XI",
}

# Alias uzual ISO -> cod VIES. NU mapam GB/UK -> XI: Marea Britanie a iesit din UE si nu e
# validabila in VIES; doar Irlanda de Nord (XI) ramane. GB -> respins corect ca ne-UE.
_COUNTRY_ALIAS = {"GR": "EL"}

SOAP_ENVELOPE = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
    'xmlns:urn="urn:ec.europa.eu:taxud:vies:services:checkVat:types">'
    "<soapenv:Header/><soapenv:Body>"
    "<urn:checkVat><urn:countryCode>{cc}</urn:countryCode>"
    "<urn:vatNumber>{vat}</urn:vatNumber></urn:checkVat>"
    "</soapenv:Body></soapenv:Envelope>"
)


def _normalize(country_code: str, vat_number: str) -> tuple[str, str]:
    """Normalizeaza codul de tara + numarul TVA (elimina prefix tara dublat, spatii, punctuatie)."""
    cc = (country_code or "").strip().upper()
    cc = _COUNTRY_ALIAS.get(cc, cc)
    vat = re.sub(r"[^0-9A-Za-z]", "", str(vat_number or "")).upper()
    # Daca userul a inclus prefixul tarii in numar (ex. "RO14837428") -> il taiem
    if cc and vat.startswith(cc):
        stripped = vat[len(cc):]
        if stripped:
            vat = stripped
    return cc, vat


def _shape(cc, vat, valid, name, address, request_date, request_identifier) -> dict:
    """Forma canonica a unui rezultat VIES reusit."""
    def _clean(s):
        s = (s or "").strip()
        return "" if s in ("---", "") else s

    return {
        "available": True,
        "source": "VIES",
        "source_url": "https://ec.europa.eu/taxation_customs/vies",
        "country_code": cc,
        "vat_number": vat,
        "valid": bool(valid),
        "name": _clean(name),
        "address": _clean(address),
        "request_date": request_date or "",
        "consultation_number": request_identifier or "",
    }


def _unavailable(cc, vat, error) -> dict:
    return {
        "available": False,
        "valid": None,
        "source": "VIES",
        "country_code": cc,
        "vat_number": vat,
        "error": str(error),
    }


async def validate_vat(
    country_code: str,
    vat_number: str,
    requester_country: str | None = None,
    requester_vat: str | None = None,
) -> dict:
    """
    Valideaza un numar TVA intracomunitar in VIES.

    country_code: cod tara UE (RO, DE, FR, EL...). vat_number: fara prefix tara (se taie automat daca e inclus).
    requester_*: optional — TVA-ul propriu al solicitantului; daca sunt date, VIES intoarce un
                 `consultation_number` (dovada legala a verificarii, de pastrat pentru audit).

    Returneaza dict: {available, valid, name, address, request_date, consultation_number, ...}
    La indisponibilitate/eroare: {available: False, valid: None, error: ...} (nu arunca).
    """
    cc, vat = _normalize(country_code, vat_number)

    if cc not in EU_VAT_COUNTRY_CODES:
        return _unavailable(cc, vat, f"Cod tara ne-UE sau invalid pentru VIES: '{country_code}'")
    if not vat:
        return _unavailable(cc, vat, "Numar TVA gol")

    payload = {"countryCode": cc, "vatNumber": vat}
    if requester_country and requester_vat:
        rcc, rvat = _normalize(requester_country, requester_vat)
        payload["requesterMemberStateCode"] = rcc
        payload["requesterNumber"] = rvat

    try:
        return await _validate_rest(payload)
    except Exception as e:
        logger.warning(f"[VIES] REST esuat pentru {cc}{vat}: {e} — incerc fallback SOAP")
        try:
            return await _validate_soap(cc, vat)
        except Exception as e2:
            logger.error(f"[VIES] SOAP fallback esuat pentru {cc}{vat}: {e2}")
            return _unavailable(cc, vat, f"VIES indisponibil: {e2}")


async def _validate_rest(payload: dict) -> dict:
    """VIES REST — 200 cu body atat pentru valid/invalid cat si pentru erori de serviciu."""
    async def _do():
        c = get_client()
        return await c.post(
            VIES_REST_URL, json=payload, headers={"Accept": "application/json"}
        )

    resp = await with_retry(_do, retries=2, backoff=[2, 5], source_name="VIES")
    try:
        data = resp.json()
    except Exception:
        resp.raise_for_status()  # forteaza exceptie -> retry/fallback
        raise

    cc, vat = payload["countryCode"], payload["vatNumber"]
    if isinstance(data.get("valid"), bool):
        return _shape(
            cc, vat, data.get("valid"), data.get("name"),
            data.get("address"), data.get("requestDate"), data.get("requestIdentifier"),
        )

    # Eroare la nivel de serviciu (ex. stat membru indisponibil, rate limit)
    err = None
    wrappers = data.get("errorWrappers")
    if isinstance(wrappers, list) and wrappers:
        err = wrappers[0].get("error")
    err = err or data.get("userError") or f"raspuns VIES neasteptat (HTTP {resp.status_code})"
    return _unavailable(cc, vat, err)


async def _validate_soap(cc: str, vat: str) -> dict:
    """Fallback SOAP — daca REST-ul isi schimba forma silentios, degradam gratios."""
    body = SOAP_ENVELOPE.format(cc=cc, vat=vat).encode("utf-8")

    async def _do():
        c = get_client()
        return await c.post(
            VIES_SOAP_URL,
            content=body,
            headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": ""},
        )

    resp = await with_retry(_do, retries=1, backoff=[3], source_name="VIES-SOAP")
    resp.raise_for_status()
    xml = resp.text

    def _tag(tag: str) -> str:
        m = re.search(rf"<(?:\w+:)?{tag}>(.*?)</(?:\w+:)?{tag}>", xml, re.S)
        return m.group(1).strip() if m else ""

    valid_raw = _tag("valid").lower()
    if valid_raw not in ("true", "false"):
        # Lipsa <valid> = SOAP fault / shape drift -> indisponibil, NU "invalid" (fals-negativ)
        return _unavailable(cc, vat, "raspuns SOAP fara camp valid (fault sau format schimbat)")
    return _shape(
        cc, vat, valid_raw == "true",
        _tag("name"), _tag("address"), _tag("requestDate"), "",
    )
