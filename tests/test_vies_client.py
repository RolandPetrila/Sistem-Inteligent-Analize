"""Teste VIES client — normalizare, parsare REST, degradare gratioasa + fallback SOAP."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from backend.agents.tools.vies_client import _normalize, validate_vat


def _mock_json_response(payload: dict, status_code: int = 200):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


class TestNormalize:
    def test_strips_country_prefix(self):
        assert _normalize("RO", "RO14837428") == ("RO", "14837428")

    def test_alias_gr_to_el(self):
        assert _normalize("GR", "123456") == ("EL", "123456")

    def test_strips_punctuation_and_spaces(self):
        assert _normalize("DE", "DE 123.456 789") == ("DE", "123456789")


class TestValidateVat:
    async def test_valid_vat(self):
        payload = {
            "countryCode": "RO", "vatNumber": "14837428", "valid": True,
            "name": "BORG DESIGN SRL", "address": "BUCURESTI",
            "requestDate": "2026-07-11T00:00:00Z", "requestIdentifier": "",
        }
        with patch("backend.agents.tools.vies_client.get_client") as mc:
            mc.return_value.post = AsyncMock(return_value=_mock_json_response(payload))
            r = await validate_vat("RO", "RO14837428")  # prefix inclus -> normalizat
        assert r["available"] is True
        assert r["valid"] is True
        assert r["name"] == "BORG DESIGN SRL"
        assert r["country_code"] == "RO"
        assert r["vat_number"] == "14837428"

    async def test_invalid_vat_cleans_dashes(self):
        payload = {"countryCode": "RO", "vatNumber": "99999999999", "valid": False,
                   "name": "---", "address": "---"}
        with patch("backend.agents.tools.vies_client.get_client") as mc:
            mc.return_value.post = AsyncMock(return_value=_mock_json_response(payload))
            r = await validate_vat("RO", "99999999999")
        assert r["available"] is True
        assert r["valid"] is False
        assert r["name"] == ""  # "---" curatat
        assert r["address"] == ""

    async def test_non_eu_country_short_circuits(self):
        with patch("backend.agents.tools.vies_client.get_client") as mc:
            r = await validate_vat("US", "123")
        assert r["available"] is False
        assert r["valid"] is None
        assert "ne-UE" in r["error"]
        mc.return_value.post.assert_not_called()

    async def test_empty_vat_short_circuits(self):
        with patch("backend.agents.tools.vies_client.get_client") as mc:
            r = await validate_vat("RO", "   ")
        assert r["available"] is False
        assert r["valid"] is None
        mc.return_value.post.assert_not_called()

    async def test_service_error_returns_unavailable(self):
        # REST 200 fara `valid` bool -> eroare de serviciu; SOAP fallback esueaza si el
        rest_err = _mock_json_response({"errorWrappers": [{"error": "MS_UNAVAILABLE"}]})
        with patch("backend.agents.tools.vies_client.get_client") as mc:
            mc.return_value.post = AsyncMock(return_value=rest_err)
            r = await validate_vat("RO", "14837428")
        assert r["available"] is False
        assert "MS_UNAVAILABLE" in r["error"]

    async def test_rest_exception_falls_back_to_soap(self):
        soap_xml = (
            "<env:Envelope><env:Body><ns2:checkVatResponse>"
            "<ns2:countryCode>DE</ns2:countryCode>"
            "<ns2:vatNumber>123456789</ns2:vatNumber>"
            "<ns2:valid>true</ns2:valid><ns2:name>ACME GMBH</ns2:name>"
            "<ns2:address>BERLIN</ns2:address>"
            "</ns2:checkVatResponse></env:Body></env:Envelope>"
        )
        soap_resp = MagicMock(spec=httpx.Response)
        soap_resp.raise_for_status.return_value = None
        soap_resp.text = soap_xml
        # 3 esecuri REST (retries=2 -> 3 incercari) + 1 succes SOAP
        posts = AsyncMock(side_effect=[
            httpx.ConnectError("boom"),
            httpx.ConnectError("boom"),
            httpx.ConnectError("boom"),
            soap_resp,
        ])
        with patch("backend.agents.tools.vies_client.get_client") as mc, \
                patch("backend.agents.tools.retry.asyncio.sleep", new_callable=AsyncMock):
            mc.return_value.post = posts
            r = await validate_vat("DE", "123456789")
        assert r["available"] is True
        assert r["valid"] is True
        assert r["name"] == "ACME GMBH"
        assert r["address"] == "BERLIN"
