"""
TEST-01: Teste BPI Client — insolventa detection.
Acopera: false positives (firma name), CUI normalization, keyword boundary,
Tavily fallback case sensitivity, timeout, empty response, malformed HTML.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx


# --- Helpers: mock httpx response ---

def _mock_response(text: str, status_code: int = 200):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = text
    return resp


# --- Tests: _check_buletinul_ro ---

class TestCheckBuletinulRo:
    """Tests for direct buletinul.ro scraping."""

    @pytest.mark.asyncio
    async def test_false_positive_company_name(self):
        """BPI-01: Firma cu 'lichidare' in NUME nu trebuie detectata ca insolventa."""
        from backend.agents.tools.bpi_client import _check_buletinul_ro

        # Page mentions CUI near the company name which contains "lichidare"
        html = (
            '<div class="result">'
            '<span>CUI: 12345678</span>'
            '<span>LICHIDARE DESEURI SRL</span>'
            '<span>Firma activa, fara proceduri</span>'
            '</div>'
        )
        with patch("backend.agents.tools.bpi_client.get_client") as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=_mock_response(html))
            result = await _check_buletinul_ro("12345678")

        assert result is not None
        assert result["found"] is False, "Firma cu 'lichidare' in NUME nu e insolventa"

    @pytest.mark.asyncio
    async def test_real_insolvency_detected(self):
        """Firma cu procedura reala de insolventa trebuie detectata."""
        from backend.agents.tools.bpi_client import _check_buletinul_ro

        html = (
            '<div class="result">'
            '<span>CUI: 99887766</span>'
            '<span>EXEMPLU CONSTRUCT SRL</span>'
            '<span>Procedura de insolventa deschisa 2025-01-15</span>'
            '</div>'
        )
        with patch("backend.agents.tools.bpi_client.get_client") as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=_mock_response(html))
            result = await _check_buletinul_ro("99887766")

        assert result is not None
        assert result["found"] is True

    @pytest.mark.asyncio
    async def test_cui_not_found_on_page(self):
        """CUI absent from page → found=False."""
        from backend.agents.tools.bpi_client import _check_buletinul_ro

        html = '<div>Niciun rezultat gasit.</div>'
        with patch("backend.agents.tools.bpi_client.get_client") as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=_mock_response(html))
            result = await _check_buletinul_ro("11111111")

        assert result is not None
        assert result["found"] is False

    @pytest.mark.asyncio
    async def test_403_returns_none(self):
        """Site blocks (403/429/503) → return None for Tavily fallback."""
        from backend.agents.tools.bpi_client import _check_buletinul_ro

        with patch("backend.agents.tools.bpi_client.get_client") as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=_mock_response("", 403))
            result = await _check_buletinul_ro("12345678")

        assert result is None

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self):
        """Network timeout → return None (fallback to Tavily)."""
        from backend.agents.tools.bpi_client import _check_buletinul_ro

        with patch("backend.agents.tools.bpi_client.get_client") as mock_client:
            mock_client.return_value.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            result = await _check_buletinul_ro("12345678")

        assert result is None

    @pytest.mark.asyncio
    async def test_keyword_boundary_not_in_name(self):
        """BPI-01: Keywords in procedura context (not in company name) → detected."""
        from backend.agents.tools.bpi_client import _check_buletinul_ro

        html = (
            '<div>'
            '<span>CUI: 55667788</span>'
            '<span>ACME BUILDING SRL</span>'
            '<span>Procedura faliment deschisa conform Legii 85/2014</span>'
            '</div>'
        )
        with patch("backend.agents.tools.bpi_client.get_client") as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=_mock_response(html))
            result = await _check_buletinul_ro("55667788")

        assert result is not None
        assert result["found"] is True


# --- Tests: _check_via_tavily ---

class TestCheckViaTavily:
    """Tests for Tavily fallback search."""

    @pytest.mark.asyncio
    async def test_cui_case_insensitive_match(self):
        """BPI-02: CUI match should work regardless of RO prefix."""
        from backend.agents.tools.bpi_client import _check_via_tavily

        tavily_results = {
            "results": [{
                "title": "Proceduri insolventa",
                "content": "Debitor: Firma cu CUI RO12345678, procedura insolventa deschisa 2025",
            }]
        }
        with patch("backend.agents.tools.tavily_client.search", new_callable=AsyncMock, return_value=tavily_results):
            with patch("backend.services.cache_service.get", new_callable=AsyncMock, return_value=None):
                with patch("backend.services.cache_service.set", new_callable=AsyncMock):
                    result = await _check_via_tavily("12345678")

        assert result["found"] is True

    @pytest.mark.asyncio
    async def test_empty_results(self):
        """Empty Tavily results → found=False."""
        from backend.agents.tools.bpi_client import _check_via_tavily

        with patch("backend.agents.tools.tavily_client.search", new_callable=AsyncMock, return_value={"results": []}):
            with patch("backend.services.cache_service.get", new_callable=AsyncMock, return_value=None):
                with patch("backend.services.cache_service.set", new_callable=AsyncMock):
                    result = await _check_via_tavily("12345678")

        assert result["found"] is False

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Cached result returned without calling Tavily."""
        from backend.agents.tools.bpi_client import _check_via_tavily

        cached = {"found": False, "status": None, "details": None, "source": "cache"}
        with patch("backend.services.cache_service.get", new_callable=AsyncMock, return_value=cached):
            result = await _check_via_tavily("12345678")

        assert result == cached


# --- Tests: check_insolvency (top-level) ---

class TestCheckInsolvency:
    """Tests for the main check_insolvency function."""

    @pytest.mark.asyncio
    async def test_returns_dict_with_checked_at(self):
        """Result always has checked_at timestamp."""
        from backend.agents.tools.bpi_client import check_insolvency

        with patch("backend.agents.tools.bpi_client._check_buletinul_ro", new_callable=AsyncMock, return_value={
            "found": False, "status": None, "details": None, "source": "buletinul.ro"
        }):
            result = await check_insolvency("12345678")

        assert "checked_at" in result
        assert isinstance(result["checked_at"], str)

    @pytest.mark.asyncio
    async def test_strips_ro_prefix(self):
        """CUI with RO prefix is normalized."""
        from backend.agents.tools.bpi_client import check_insolvency

        with patch("backend.agents.tools.bpi_client._check_buletinul_ro", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = {"found": False, "status": None, "details": None, "source": "buletinul.ro"}
            await check_insolvency("RO12345678")
            # Verify the clean CUI was passed
            mock_check.assert_called_once_with("12345678")
