"""Teste Angle A — mapare CAEN->CPV + descoperire licitatii deschise SEAP (mock)."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from backend.agents.tools.caen_cpv_map import caen_to_cpv_prefixes
from backend.agents.tools.seap_client import search_open_tenders


class TestCaenCpvMap:
    def test_construction(self):
        assert "45" in caen_to_cpv_prefixes("4120")

    def test_it(self):
        assert set(caen_to_cpv_prefixes("6201")) == {"72", "48"}

    def test_unknown_division(self):
        assert caen_to_cpv_prefixes("9999") == []

    def test_invalid(self):
        assert caen_to_cpv_prefixes("x") == []
        assert caen_to_cpv_prefixes("") == []
        assert caen_to_cpv_prefixes("6") == []  # < 2 cifre


def _mock_resp(items):
    r = MagicMock(spec=httpx.Response)
    r.status_code = 200
    r.json.return_value = {"items": items, "total": len(items)}
    return r


class TestSearchOpenTenders:
    async def test_filters_by_cpv_prefix(self):
        items = [
            {"cpvCodeAndName": "45210000-2 - Constructii cladiri (Rev.2)", "contractTitle": "Scoala noua",
             "contractingAuthorityNameAndFN": "Primaria X", "estimatedValueRon": 500000,
             "maxTenderReceiptDeadline": "2026-08-01", "noticeNo": "CN1", "procedureId": 111},
            {"cpvCodeAndName": "72000000-0 - Servicii IT (Rev.2)", "contractTitle": "Soft",
             "contractingAuthorityNameAndFN": "Primaria Y", "estimatedValueRon": 30000,
             "maxTenderReceiptDeadline": "2026-08-01", "noticeNo": "CN2", "procedureId": 222},
        ]
        with patch("backend.agents.tools.seap_client.get_client") as mc, \
                patch("backend.services.cache_service.get", new_callable=AsyncMock, return_value=None), \
                patch("backend.services.cache_service.set", new_callable=AsyncMock), \
                patch("backend.agents.tools.seap_client.asyncio.sleep", new_callable=AsyncMock):
            mc.return_value.post = AsyncMock(return_value=_mock_resp(items))
            r = await search_open_tenders("4120", days_back=20, max_pages=1)  # CPV [45, 71]
        assert r["available"] is True
        assert r["count"] == 1  # doar CPV 45 se potriveste; 72 (IT) e exclus pt sectorul constructii
        assert r["opportunities"][0]["cpv"] == "45210000-2"
        assert r["opportunities"][0]["title"] == "Scoala noua"

    async def test_unknown_caen_no_call(self):
        with patch("backend.agents.tools.seap_client.get_client") as mc:
            r = await search_open_tenders("9999", use_cache=False)
        assert r["available"] is False
        mc.return_value.post.assert_not_called()

    async def test_cache_hit_skips_fetch(self):
        cached = {"available": True, "count": 5, "opportunities": []}
        with patch("backend.services.cache_service.get", new_callable=AsyncMock, return_value=cached), \
                patch("backend.agents.tools.seap_client.get_client") as mc:
            r = await search_open_tenders("4120")
        assert r == cached
        mc.return_value.post.assert_not_called()

    async def test_no_matches_returns_available_zero(self):
        items = [{"cpvCodeAndName": "72000000-0 - IT", "contractTitle": "Soft",
                  "contractingAuthorityNameAndFN": "X", "noticeNo": "CN9"}]
        with patch("backend.agents.tools.seap_client.get_client") as mc, \
                patch("backend.services.cache_service.get", new_callable=AsyncMock, return_value=None), \
                patch("backend.services.cache_service.set", new_callable=AsyncMock), \
                patch("backend.agents.tools.seap_client.asyncio.sleep", new_callable=AsyncMock):
            mc.return_value.post = AsyncMock(return_value=_mock_resp(items))
            r = await search_open_tenders("4120", max_pages=1)  # CPV [45,71]; 72 nu se potriveste
        assert r["available"] is True
        assert r["count"] == 0
