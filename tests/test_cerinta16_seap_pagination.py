"""CERINTA #16 (C) — paginare SEAP: aduce TOATE achizitiile directe, nu doar 200.

Pana la #16, fetch-ul aducea DOAR pagina 0 (`pageSize=200`) -> o firma cu >200 achizitii
directe (MOSSLEIN: 485) avea setul trunchiat la 200, deci `items_truncated=True` desi 485 <
plafonul serverului (2000). Acum se pagineaza pe `pageIndex` pana la `total` (sau pana la
plafon), deci `counts_reliable` devine True cand numarul real incape sub plafon.

Non-vacuitate: pe HEAD (fara paginare) un `direct_count`=300 aduce 200 itemi + `items_truncated`
=True; dupa fix aduce 300 + `items_truncated`=False. Al doilea test (2500 > plafon 2000) e garda
anti-regresie P4: paginarea aduce pana la plafon DAR `total_capped` ramane True si calificativul
#15 (`seap_count_caveat`) TREBUIE sa apara in continuare. Al treilea test e o PLASA: daca SICAP
ar ignora tacit `pageIndex` (scarul `spiCuiSupplier`), dedup-ul opreste dublarea numarului/valorii.

Verificat LIVE 2026-07-30 (scratchpad probe): pageIndex functioneaza real pe ambele endpointuri
(DA total=485, page0/page1 = 200 itemi distincti, overlap=0).
"""
from unittest.mock import AsyncMock, patch

import pytest

from backend.agents.tools import seap_client
from backend.agents.tools.seap_client import get_contracts_won
from backend.reports.rich_fields import seap_count_caveat

CUI = "26313362"
SUPPLIER_ID = 93384


class _Resp:
    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload

    def json(self):
        return self._payload


class _PagedClient:
    """Server SICAP simulat cu paginare `pageIndex` REALA (sau ignorata, pt plasa)."""

    def __init__(self, ca_total: int, da_total: int, ignore_pageindex: bool = False):
        self.ca_total = ca_total
        self.da_total = da_total
        self.ignore_pageindex = ignore_pageindex

    async def post(self, url, json=None, headers=None):
        page = int(json.get("pageIndex", 0))
        size = int(json.get("pageSize", 200))
        if url == seap_client.SEAP_NOTICES_URL:
            return _Resp({"items": self._slice(page, size, self.ca_total, self._ca_item),
                          "total": self.ca_total})
        if url == seap_client.SEAP_DIRECT_URL:
            return _Resp({"items": self._slice(page, size, self.da_total, self._da_item),
                          "total": self.da_total})
        raise AssertionError(f"URL neasteptat: {url}")

    def _slice(self, page, size, total, make):
        eff = 0 if self.ignore_pageindex else page  # ignore_pageindex -> mereu pagina 0
        start = eff * size
        end = min(start + size, total)
        if start >= total:
            return []
        return [make(i) for i in range(start, end)]

    def _da_item(self, i):
        return {
            "directAcquisitionId": 100000 + i,
            "directAcquisitionName": f"Achizitie {i}",
            "closingValue": 1000.0,
            "contractingAuthority": "Primaria X",
            "publicationDate": "2025-01-01",
            "uniqueIdentificationCode": f"DA{i}",
            "supplier": f"RO {CUI} FIRMA",
            "sysDirectAcquisitionState": {"id": 7, "text": "Oferta acceptata"},
            "cpvCode": "45000000-7 - Lucrari",
        }

    def _ca_item(self, i):  # neutilizat in testele de aici (ca_total=0), dar coerent
        return {"caNoticeId": 200000 + i, "contractTitle": f"Contract {i}",
                "ronContractValue": 5000.0, "currencyCode": "RON",
                "contractingAuthorityNameAndFN": "Autoritate", "noticeNo": f"CAN{i}",
                "cpvCodeAndName": "45000000-7 - Lucrari"}


async def _run(da_total, ignore_pageindex=False):
    client = _PagedClient(ca_total=0, da_total=da_total, ignore_pageindex=ignore_pageindex)
    with patch.object(seap_client, "resolve_supplier_id",
                      AsyncMock(return_value={"resolved": True, "outcome": "resolved",
                                              "supplier_id": SUPPLIER_ID, "reason": ""})), \
         patch.object(seap_client, "get_client", return_value=client), \
         patch("backend.services.cache_service.get", AsyncMock(return_value=None)), \
         patch("backend.services.cache_service.set", AsyncMock()):
        return await get_contracts_won(CUI, use_cache=False)


@pytest.fixture(autouse=True)
def _no_delay(monkeypatch):
    # delay 3s/req -> 0 in teste (fara a atinge asyncio.sleep global)
    monkeypatch.setattr(seap_client, "REQUEST_DELAY", 0)


class TestPaginareAchizitiiDirecte:
    @pytest.mark.asyncio
    async def test_aduce_toate_paginile_sub_plafon(self):
        """300 directe (peste vechiul cap 200) -> paginate integral, numaratoare fiabila."""
        r = await _run(da_total=300)
        assert len(r["direct_acquisitions"]) == 300, "paginarea nu a adus toate paginile"
        assert r["direct_count"] == 300
        assert r["items_truncated"] is False
        assert r["counts_reliable"] is True

    @pytest.mark.asyncio
    async def test_plafon_server_pastreaza_calificativul_P4(self):
        """2500 directe (peste plafon 2000) -> aduce pana la plafon, DAR total_capped=True
        si calificativul #15 ramane (garda anti-regresie P4)."""
        r = await _run(da_total=2500)
        assert len(r["direct_acquisitions"]) == 2000, "trebuie sa aduca pana la plafonul serverului"
        assert r["direct_count"] == 2500  # `total` autoritar (filtrele au tinut)
        assert r["total_capped"] is True
        assert r["items_truncated"] is True  # 2000 adusi < 2500 raportati
        assert seap_count_caveat(r) is not None, "calificativul SEAP #15 a disparut la plafon"

    @pytest.mark.asyncio
    async def test_pageindex_ignorat_nu_umfla_numarul(self):
        """PLASA: daca SICAP ar ignora tacit `pageIndex` (reintoarce pagina 0), dedup-ul
        opreste dublarea — numarul si valoarea raman ale unei singure pagini, marcate partial."""
        r = await _run(da_total=485, ignore_pageindex=True)
        assert len(r["direct_acquisitions"]) == 200, "paginare ignorata a dublat setul"
        assert r["items_truncated"] is True  # 200 < 485 -> onest partial
        # valoarea NU e umflata: 200 itemi x 1000, nu 400 x 1000
        assert r["total_value"] == 200 * 1000
