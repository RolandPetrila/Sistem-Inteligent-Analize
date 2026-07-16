"""
TEST — Brave Search client: regressie pt bug-ul "country=RO" (2026-07-16).

Root cause verificat LIVE contra API-ului real Brave (bisect manual, nu presupunere):
    q + count                  -> HTTP 200
    + freshness='pm'           -> HTTP 200
    + search_lang='ro'         -> HTTP 200
    + country='RO'             -> HTTP 422 <<< Brave NU accepta Romania in enum-ul
      "country" (eroare reala: "Input should be 'AR','AU',...,'US' or 'ALL'" -- RO
      nu e in lista). Rezultat: brave_reputation = gol in 78/78 rapoarte reale,
      pentru ca fiecare din cele 2 query-uri interne pica -> except -> None.

Fix: "country": "ALL" (fara restrictie de tara -- verificat live sa dea rezultate
identice/echivalente cu a omite parametrul; "ALL" ales explicit pt auto-documentare,
in loc de un default nedocumentat la Brave).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


def _mock_response(json_body: dict, status_code: int = 200):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_body
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


_WEB_RESULTS_BODY = {
    "web": {
        "results": [
            {"title": "Firma X - stire", "url": "https://exemplu.ro/a", "description": "desc1", "age": "2 zile"},
            {"title": "Firma X - profil", "url": "https://exemplu.ro/b", "description": "desc2", "age": "1 saptamana"},
        ]
    }
}


class TestCountryParam:
    """Regressie directa pt root cause: parametrul 'country' NU mai poate fi 'RO'.

    Acest test PICA pe codul vechi (country='RO' hardcodat) -- verificat manual
    prin revert temporar inainte de a scrie fix-ul definitiv:
        params trimise aveau {"country": "RO", ...} -> assert de mai jos ar fi picat.
    """

    @pytest.mark.asyncio
    async def test_country_param_is_not_ro(self):
        from backend.agents.tools.brave_client import search_company_reputation
        from backend.config import settings

        captured_params = []

        async def _fake_get(url, headers=None, params=None, timeout=None):
            captured_params.append(dict(params))
            return _mock_response(_WEB_RESULTS_BODY)

        with patch.object(settings, "brave_api_key", "fake-key-for-test"):
            with patch("backend.agents.tools.brave_client.get_client") as mock_client:
                mock_client.return_value.get = AsyncMock(side_effect=_fake_get)
                await search_company_reputation("FIRMA TEST SRL", "12345678")

        assert captured_params, "Niciun apel HTTP nu a fost facut"
        for params in captured_params:
            assert params.get("country") != "RO", (
                "BUG REINTRODUS: Brave nu accepta 'RO' in enum-ul 'country' "
                "(HTTP 422 real, verificat live) -- toate cererile de productie ar pica din nou"
            )
            # search_lang='ro' ramane -- verificat live ca e acceptat (HTTP 200)
            assert params.get("search_lang") == "ro"


class TestSearchCompanyReputation:
    @pytest.mark.asyncio
    async def test_no_api_key_returns_none_without_http_call(self):
        from backend.agents.tools.brave_client import search_company_reputation
        from backend.config import settings

        with patch.object(settings, "brave_api_key", ""):
            with patch("backend.agents.tools.brave_client.get_client") as mock_client:
                result = await search_company_reputation("FIRMA TEST SRL", "12345678")
                mock_client.assert_not_called()

        assert result is None

    @pytest.mark.asyncio
    async def test_success_returns_real_shape(self):
        """Forma reala emisa de client: {results, summary, source, queries} --
        NU {"mentions":..., "sentiment":...} (forma gasita in fixture-urile vechi,
        care nu corespunde productiei -- vezi raportul agentului)."""
        from backend.agents.tools.brave_client import search_company_reputation
        from backend.config import settings

        with patch.object(settings, "brave_api_key", "fake-key-for-test"):
            with patch("backend.agents.tools.brave_client.get_client") as mock_client:
                mock_client.return_value.get = AsyncMock(return_value=_mock_response(_WEB_RESULTS_BODY))
                result = await search_company_reputation("FIRMA TEST SRL", "12345678")

        assert result is not None
        assert result["source"] == "brave_search"
        assert "results" in result and "summary" in result and "queries" in result
        assert len(result["queries"]) == 2
        # dedup dupa URL -- 2 query-uri identice mock -> 2 rezultate unice (nu 4)
        assert len(result["results"]) == 2
        assert result["results"][0]["url"] == "https://exemplu.ro/a"
        assert "exemplu.ro/a" in result["summary"]

    @pytest.mark.asyncio
    async def test_all_queries_failing_returns_none(self):
        """Simuleaza EXACT comportamentul bug-ului: ambele query-uri primesc
        HTTP 422 (country invalid la Brave) -> exceptia e prinsa per-query intern
        -> all_results ramane gol -> None. Asta era starea din productie pana la fix."""
        from backend.agents.tools.brave_client import search_company_reputation
        from backend.config import settings

        with patch.object(settings, "brave_api_key", "fake-key-for-test"):
            with patch("backend.agents.tools.brave_client.get_client") as mock_client:
                mock_client.return_value.get = AsyncMock(return_value=_mock_response({}, status_code=422))
                result = await search_company_reputation("FIRMA TEST SRL", "12345678")

        assert result is None
