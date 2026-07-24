"""Teste Angle A — mapare CAEN->CPV + descoperire licitatii deschise SEAP (mock)."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from backend.agents.tools.caen_cpv_map import caen_to_cpv_prefixes
from backend.agents.tools.seap_client import _cpv_code8, get_contracts_won, search_open_tenders


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


class TestCpvCode8:
    def test_extract(self):
        assert _cpv_code8("09123000-7 - Gaze naturale (Rev.2)") == "09123000"
        assert _cpv_code8("45210000-2") == "45210000"
        assert _cpv_code8("") == ""
        assert _cpv_code8("abc") == ""


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
        assert r["basis"] == "caen_orientativ"

    async def test_unknown_caen_no_history_no_call(self):
        with patch("backend.agents.tools.seap_client.get_client") as mc:
            r = await search_open_tenders("9999", use_cache=False)
        assert r["available"] is False
        mc.return_value.post.assert_not_called()

    async def test_raw_cache_skips_fetch(self):
        raw = {"notices": [{"cpv": "45210000-2", "title": "Scoala", "authority": "X", "notice_no": "CN1"}]}
        with patch("backend.services.cache_service.get", new_callable=AsyncMock, return_value=raw), \
                patch("backend.agents.tools.seap_client.get_client") as mc:
            r = await search_open_tenders("4120")  # CAEN 4120 -> [45,71]
        assert r["available"] is True and r["count"] == 1
        mc.return_value.post.assert_not_called()  # fetch sarit (raw cache hit)

    async def test_won_cpv_marks_precise_and_sorts_first(self):
        raw = {"notices": [
            {"cpv": "45450000-6", "title": "Finisaje", "authority": "Y", "notice_no": "CN2"},
            {"cpv": "45210000-2", "title": "Cladire", "authority": "X", "notice_no": "CN1"},
        ]}
        with patch("backend.services.cache_service.get", new_callable=AsyncMock, return_value=raw):
            r = await search_open_tenders("4120", won_cpv_codes=["45210000-7"])
        assert r["basis"] == "istoric_real"
        # clasa 4521 = competenta dovedita -> precise, afisat primul
        assert r["opportunities"][0]["cpv"] == "45210000-2"
        assert r["opportunities"][0]["precise"] is True
        assert any(o["cpv"] == "45450000-6" and o["precise"] is False for o in r["opportunities"])

    async def test_won_cpv_expands_beyond_caen(self):
        # CAEN 6201 -> [72,48]; firma a castigat si CPV 79 (business) -> divizia 79 devine eligibila
        raw = {"notices": [{"cpv": "79820000-8", "title": "Servicii", "authority": "X", "notice_no": "CN9"}]}
        with patch("backend.services.cache_service.get", new_callable=AsyncMock, return_value=raw):
            r_no = await search_open_tenders("6201")
            r_yes = await search_open_tenders("6201", won_cpv_codes=["79000000-4"])
        assert r_no["count"] == 0
        assert r_yes["count"] == 1 and r_yes["basis"] == "istoric_real"

    async def test_get_contracts_won_extracts_cpv(self):
        # Forma REALA masurata 2026-07-24: autoritatea e `contractingAuthorityNameAndFN`
        # pe CA si `contractingAuthority` pe DA — `contractingAuthorityName` (folosit
        # de fixture-ul anterior) nu exista pe NICIUNUL. Itemul DA poarta `supplier`
        # si `sysDirectAcquisitionState`, ambele validate per-item de client.
        ca_items = [{"contractTitle": "Gaze", "cpvCodeAndName": "09123000-7 - Gaze naturale",
                     "ronContractValue": 1000, "contractingAuthorityNameAndFN": "X",
                     "noticeStateDate": "2026-01-01T00:00:00+02:00"}]
        da_items = [{"directAcquisitionName": "Birotica", "cpvCode": "30190000-7",
                     "closingValue": 500, "contractingAuthority": "Y",
                     "publicationDate": "2026-01-01T00:00:00+02:00",
                     "supplier": "RO 12345678 FIRMA TEST",
                     "sysDirectAcquisitionState": {"id": 7, "text": "Oferta acceptata"}}]
        with patch("backend.agents.tools.seap_client.resolve_supplier_id",
                   new_callable=AsyncMock,
                   return_value={"resolved": True, "supplier_id": 4242, "reason": ""}), \
                patch("backend.agents.tools.seap_client.get_client") as mc, \
                patch("backend.services.cache_service.get", new_callable=AsyncMock, return_value=None), \
                patch("backend.services.cache_service.set", new_callable=AsyncMock), \
                patch("backend.agents.tools.seap_client.asyncio.sleep", new_callable=AsyncMock):
            mc.return_value.post = AsyncMock(side_effect=[_mock_resp(ca_items), _mock_resp(da_items)])
            r = await get_contracts_won("12345678")
        assert r["contracts_verified"] is True
        assert "09123000" in r["won_cpv_codes"]
        assert "30190000" in r["won_cpv_codes"]
        assert r["contracts"][0]["cpv"] == "09123000"
        assert r["direct_acquisitions"][0]["authority"] == "Y"
        assert r["contracts"][0]["authority"] == "X"
