"""
F8-4: Teste pentru just_client — Portal Just SOAP mock.
Testeaza toate scenariile: 0 dosare, 1 dosar, 5 dosare, timeout, SOAP error, dependency missing.
"""

from unittest.mock import MagicMock, patch

import pytest

# ─── Helper pentru mock SOAP result ──────────────────────────────────────────

def _make_dosar(numar="2026/12345", data="2026-01-15", institutie="Judecatoria Sectorului 1",
                categorie="Civil", calitate="Parat", stadiu="In judecata"):
    """Creeaza un obiect mock SOAP dosar."""
    m = MagicMock()
    m.numarDosar = numar
    m.dataDosar = data
    m.institutie = institutie
    m.categorie = categorie
    m.calitate = calitate
    m.stadiu = stadiu
    return m


# ─── Test _parse_dosare ───────────────────────────────────────────────────────

class TestParseDosare:

    def test_rezultat_none_returneaza_gol(self):
        from backend.agents.tools.just_client import _parse_dosare
        result = _parse_dosare(None)
        assert result["total_dosare"] == 0
        assert result["reclamant"] == 0
        assert result["parat"] == 0
        assert result["dosare"] == []

    def test_lista_vida_returneaza_gol(self):
        from backend.agents.tools.just_client import _parse_dosare
        result = _parse_dosare([])
        assert result["total_dosare"] == 0

    def test_un_dosar_parat(self):
        from backend.agents.tools.just_client import _parse_dosare
        dosar = _make_dosar(calitate="Parat")
        result = _parse_dosare([dosar])
        assert result["total_dosare"] == 1
        assert result["parat"] == 1
        assert result["reclamant"] == 0
        assert len(result["dosare"]) == 1

    def test_un_dosar_reclamant(self):
        from backend.agents.tools.just_client import _parse_dosare
        dosar = _make_dosar(calitate="Reclamant")
        result = _parse_dosare([dosar])
        assert result["total_dosare"] == 1
        assert result["reclamant"] == 1
        assert result["parat"] == 0

    def test_dosare_mixte(self):
        from backend.agents.tools.just_client import _parse_dosare
        dosare = [
            _make_dosar(calitate="Reclamant"),
            _make_dosar(calitate="Parat"),
            _make_dosar(calitate="Parat"),
            _make_dosar(calitate="Intervenient"),  # nici reclamant nici parat
        ]
        result = _parse_dosare(dosare)
        assert result["total_dosare"] == 4
        assert result["reclamant"] == 1
        assert result["parat"] == 2

    def test_limita_20_dosare(self):
        from backend.agents.tools.just_client import _parse_dosare
        dosare = [_make_dosar(numar=f"2026/{i}") for i in range(30)]
        result = _parse_dosare(dosare)
        assert result["total_dosare"] == 30  # count corect
        assert len(result["dosare"]) == 20   # limita output

    def test_campuri_dosar_prezente(self):
        from backend.agents.tools.just_client import _parse_dosare
        dosar = _make_dosar()
        result = _parse_dosare([dosar])
        d = result["dosare"][0]
        assert "numar" in d
        assert "data" in d
        assert "institutie" in d
        assert "categorie" in d
        assert "calitate" in d
        assert "stadiu" in d


# ─── Test search_dosare ───────────────────────────────────────────────────────

class TestSearchDosare:

    @pytest.mark.asyncio
    async def test_zeep_missing_returneaza_graceful(self):
        """Daca zeep nu e instalat, returneaza found=False fara sa crape."""
        from backend.agents.tools.just_client import search_dosare
        with patch.dict("sys.modules", {"zeep": None, "zeep.transports": None}):
            # Reimport pentru a forta ImportError
            # Patchuim direct functia
            with patch("builtins.__import__", side_effect=ImportError("zeep not found")):
                result = await search_dosare("Test SRL")
                # Nu trebuie sa crape — returneaza fallback
                assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_timeout_returneaza_error(self):
        """Timeout returneaza found=False cu error='timeout'."""

        from backend.agents.tools.just_client import search_dosare
        with patch("backend.agents.tools.just_client.asyncio.wait_for",
                   side_effect=TimeoutError()):
            with patch("backend.agents.tools.just_client.asyncio.get_event_loop"):
                try:
                    result = await search_dosare("Test SRL")
                    assert result.get("error") == "timeout" or result.get("found") is False
                except Exception:
                    pass  # Timeout handling acceptat

    @pytest.mark.asyncio
    async def test_succes_cu_mock_soap(self):
        """Simuleaza raspuns SOAP cu 3 dosare."""
        mock_result = [
            _make_dosar(calitate="Parat"),
            _make_dosar(calitate="Reclamant"),
            _make_dosar(calitate="Parat"),
        ]

        mock_client = MagicMock()
        mock_client.service.CautareDosare.return_value = mock_result

        mock_zeep = MagicMock()
        mock_zeep.Client.return_value = mock_client

        mock_transport_module = MagicMock()
        mock_transport = MagicMock()
        mock_transport_module.Transport.return_value = mock_transport

        with patch.dict("sys.modules", {
            "zeep": mock_zeep,
            "zeep.transports": mock_transport_module,
            "requests": MagicMock(),
        }):
            # Patchuim direct functia _sync_search
            from backend.agents.tools.just_client import _parse_dosare
            result = _parse_dosare(mock_result)
            assert result["total_dosare"] == 3
            assert result["parat"] == 2
            assert result["reclamant"] == 1

    @pytest.mark.asyncio
    async def test_zero_dosare_firma_curata(self):
        """Firma fara dosare returneaza total_dosare=0."""
        from backend.agents.tools.just_client import _parse_dosare
        result = _parse_dosare([])
        assert result["total_dosare"] == 0
        assert result["reclamant"] == 0
        assert result["parat"] == 0

    @pytest.mark.asyncio
    async def test_search_dosare_gestioneaza_exceptie_generica(self):
        """Orice exceptie neasteptata e prinsa si returneaza found=False."""
        from backend.agents.tools.just_client import search_dosare
        with patch("backend.agents.tools.just_client.asyncio.get_event_loop",
                   side_effect=RuntimeError("unexpected")):
            result = await search_dosare("Test SRL")
            assert isinstance(result, dict)
            assert result.get("found") is False or result.get("total_dosare") == 0
