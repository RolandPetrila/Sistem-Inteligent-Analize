"""CERINTA #8 (M) — izolare cheie Google Maps PLATITA in teste.

Google Maps Places API factureaza $ real (billing activ pe proiectul GCloud). Un test care
atinge `maps_client.get_maps_rating` NEMOCKAT cu cheia reala ar factura Google. Fixture-ul
autouse `_no_paid_external_keys_in_tests` (conftest.py) goleste `google_cloud_api_key` pt toata
suita. Aici dovedim ca garda e PREZENTA si DISCRIMINANTA (pica pe conftest-ul vechi, fara fixture).

R-SEC: aserturile compara bool / string-uri FIXE de eroare, NICIODATA valoarea cheii — un
`assert settings.google_cloud_api_key == ""` ar tipari cheia reala pe picare (lectia #7).
"""

from unittest.mock import patch

import pytest

from backend.agents.tools import maps_client
from backend.config import settings


class TestGoogleCloudKeyEmptiedInTests:
    def test_google_cloud_key_is_empty(self):
        """M-E1: fixture-ul autouse a golit cheia pt toata sesiunea de teste.
        Non-vacuitate: pe conftest-ul vechi (fara fixture-ul nou) cheia reala (len 39) e prezenta
        -> non-goala -> PICA. R-SEC: capturam bool INAINTE de assert, ca pytest sa tipareasca doar
        `assert False`, nu valoarea cheii reale."""
        is_empty = settings.google_cloud_api_key == ""
        assert is_empty, (
            "google_cloud_api_key NU e goala in teste — fixture-ul _no_paid_external_keys_in_tests "
            "lipseste sau nu ruleaza (risc: apel PLATIT Google Maps Places)."
        )


class TestMapsGuardBlocksPaidCallWithoutKey:
    @pytest.mark.asyncio
    async def test_get_maps_rating_short_circuits_before_get_client(self):
        """M-E2 (behavioral, discriminant): cu cheia golita de fixture, `get_maps_rating` iese
        TIMPURIU (maps_client.py:34-35) INAINTE de `get_client()` -> zero apel HTTP platit.

        Spy pe `get_client` cu MagicMock simplu (NU AsyncMock: nu vrem sa devina awaitable si sa
        ratacim in .json()/status pe mock-children). Doua aserturi DISCRIMINANTE:
          - `error == "GOOGLE_CLOUD_API_KEY neconfigurat"` (string FIX al ramurii cheie-lipsa);
          - `get_client` NU e apelat.
        Non-vacuitate: pe conftest-ul vechi (cheie reala) ramura `if not key` e falsa -> `get_client`
        E apelat (assert_not_called PICA) SI eroarea ar fi `str(TypeError)` din wait_for pe mock-ul
        non-awaitable, nu string-ul fix (a doua aserta PICA). Fara HTTP real (get_client e mock).
        R-SEC: `get_client()` e apelat FARA argumente (maps_client.py:40) -> mesajul de picare nu
        poarta nimic sensibil (spre deosebire de `client.get`, care are 'key' in params)."""
        with patch.object(maps_client, "get_client") as mock_get_client:
            result = await maps_client.get_maps_rating("Firma Test SRL")

        assert result["found"] is False
        assert result["error"] == "GOOGLE_CLOUD_API_KEY neconfigurat"
        mock_get_client.assert_not_called()
