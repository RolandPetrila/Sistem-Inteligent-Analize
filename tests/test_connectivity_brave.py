"""
TEST — ping_brave (connectivity.py): regressie pt "gate verde care nu dovedeste nimic".

Pana la 2026-07-16, ping_brave facea un GET minimal cu params inventati (fara
"country"), care raspundea HTTP 200 chiar si atunci cand cererea REALA de productie
(search_company_reputation, cu "country": "RO") pica sistematic cu HTTP 422 pe Brave.
Dashboard-ul raporta "Brave OK" pt o functionalitate 100% moarta in 78/78 rapoarte.

Fix: ping_brave apeleaza acum direct search_company_reputation (aceeasi cale ca
productia -- pattern identic cu ping_google_maps -> get_maps_rating).
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


class TestPingBraveNoKey:
    @pytest.mark.asyncio
    async def test_no_api_key(self):
        from backend.agents.tools.connectivity import ping_brave
        from backend.config import settings

        with patch.object(settings, "brave_api_key", ""):
            result = await ping_brave()

        assert result["ok"] is False
        assert "BRAVE_API_KEY" in result["message"]


class TestPingBraveExercisesProductionPath:
    """Ping-ul trebuie sa cheme functia REALA de productie, nu un GET separat."""

    @pytest.mark.asyncio
    async def test_calls_search_company_reputation_with_test_cui(self):
        from backend.agents.tools.connectivity import TEST_CUI, ping_brave
        from backend.config import settings

        with patch.object(settings, "brave_api_key", "fake-key-for-test"):
            with patch(
                "backend.agents.tools.brave_client.search_company_reputation",
                new_callable=AsyncMock,
                return_value={"results": [{"url": "https://x.ro"}], "summary": "x", "source": "brave_search"},
            ) as mock_search:
                await ping_brave()

        mock_search.assert_awaited_once()
        args, _ = mock_search.await_args
        assert args[1] == TEST_CUI


class TestPingBraveNonVacuity:
    """Dovada obligatorie: ping-ul trebuie sa RAPORTEZE PICAT cand bug-ul
    country='RO' e prezent (simulat aici la nivel HTTP, fara sa patch-uim
    ping-ul insusi -- proba end-to-end prin ambele straturi)."""

    @pytest.mark.asyncio
    async def test_ping_fails_when_underlying_search_returns_none(self):
        """Echivalent cu bug-ul real: search_company_reputation intoarce None
        (ambele query-uri au picat cu HTTP 422 country invalid) -> ping trebuie
        sa raporteze ok=False, NU 'OK' cum se intampla cu vechiul ping minimal."""
        from backend.agents.tools.connectivity import ping_brave
        from backend.config import settings

        with patch.object(settings, "brave_api_key", "fake-key-for-test"):
            with patch(
                "backend.agents.tools.brave_client.search_company_reputation",
                new_callable=AsyncMock,
                return_value=None,
            ):
                result = await ping_brave()

        assert result["ok"] is False, "Ping-ul e vacuu daca raporteaza OK cand productia n-ar gasi nimic"

    @pytest.mark.asyncio
    async def test_ping_fails_end_to_end_with_http_422(self):
        """Nu patch-uim search_company_reputation -- lasam ping_brave sa cheme
        functia REALA, care la randul ei face cereri HTTP mock-uite sa raspunda
        422 (exact eroarea reala de la Brave pt country='RO'). Daca ping-ul ar fi
        vacuu (ca vechiul cod), ar raporta OK indiferent de asta."""
        from backend.agents.tools.connectivity import ping_brave
        from backend.config import settings

        with patch.object(settings, "brave_api_key", "fake-key-for-test"):
            with patch("backend.agents.tools.brave_client.get_client") as mock_client:
                mock_client.return_value.get = AsyncMock(return_value=_mock_response({}, status_code=422))
                result = await ping_brave()

        assert result["ok"] is False


class TestPingBraveSuccess:
    @pytest.mark.asyncio
    async def test_ping_ok_with_real_results(self):
        from backend.agents.tools.connectivity import ping_brave
        from backend.config import settings

        fake_result = {
            "results": [{"url": "https://a.ro"}, {"url": "https://b.ro"}],
            "summary": "- a\n- b",
            "source": "brave_search",
            "queries": ["q1", "q2"],
        }
        with patch.object(settings, "brave_api_key", "fake-key-for-test"):
            with patch(
                "backend.agents.tools.brave_client.search_company_reputation",
                new_callable=AsyncMock,
                return_value=fake_result,
            ):
                result = await ping_brave()

        assert result["ok"] is True
        assert "2" in result["message"]
