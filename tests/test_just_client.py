"""
F8-4: Teste pentru just_client — Portal Just SOAP mock.

Shape-ul mock e aliniat la raspunsul REAL al WSDL (verificat live 2026-07-12, dupa
instalarea pachetului `zeep` — pana atunci `search_dosare` nu rulase NICIODATA cu
succes contra portal.just.ro, deci parsarea + parametrii SOAP originali testau o
structura fictiva care nu exista in realitate). Fiecare Dosar real are `numar`,
`data`, `institutie`, `obiect`, `categorieCazNume`, `stadiuProcesualNume` si
`parti.DosarParte[]` cu `{nume, calitateParte}` — nu campuri plate `numarDosar`/
`calitate` cum presupunea codul vechi.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest


def _make_parte(nume, calitate):
    return SimpleNamespace(nume=nume, calitateParte=calitate)


def _make_dosar(numar="2026/12345", data="2026-01-15", institutie="TribunalulCLUJ",
                obiect="pretentii", categorie="Civil", stadiu="Fond", parti=None):
    """Creeaza un obiect mock aliniat la shape-ul real WSDL."""
    return SimpleNamespace(
        numar=numar, data=data, institutie=institutie, obiect=obiect,
        categorieCazNume=categorie, stadiuProcesualNume=stadiu,
        parti=SimpleNamespace(DosarParte=parti or []),
    )


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

    def test_firma_ca_parat(self):
        from backend.agents.tools.just_client import _parse_dosare
        dosar = _make_dosar(parti=[
            _make_parte("Ion Popescu", "Reclamant"),
            _make_parte("Firma Test SRL", "Pârât"),
        ])
        result = _parse_dosare([dosar], company_name="Firma Test SRL")
        assert result["total_dosare"] == 1
        assert result["parat"] == 1
        assert result["reclamant"] == 0
        assert len(result["dosare"]) == 1

    def test_firma_ca_reclamant(self):
        from backend.agents.tools.just_client import _parse_dosare
        dosar = _make_dosar(parti=[
            _make_parte("Firma Test SRL", "Reclamant"),
            _make_parte("Ion Popescu", "Pârât"),
        ])
        result = _parse_dosare([dosar], company_name="Firma Test SRL")
        assert result["reclamant"] == 1
        assert result["parat"] == 0

    def test_dosare_mixte(self):
        from backend.agents.tools.just_client import _parse_dosare
        dosare = [
            _make_dosar(parti=[_make_parte("Firma Test SRL", "Reclamant")]),
            _make_dosar(parti=[_make_parte("Firma Test SRL", "Pârât")]),
            _make_dosar(parti=[_make_parte("Firma Test SRL", "Pârât")]),
            _make_dosar(parti=[_make_parte("Altcineva SRL", "Reclamant")]),  # firma nu apare
        ]
        result = _parse_dosare(dosare, company_name="Firma Test SRL")
        assert result["total_dosare"] == 4
        assert result["reclamant"] == 1
        assert result["parat"] == 2

    def test_firma_neimplicata_nu_e_numarata(self):
        """Firma cautata nu apare in parti -> nici reclamant nici parat, dosarul ramane listat."""
        from backend.agents.tools.just_client import _parse_dosare
        dosar = _make_dosar(parti=[_make_parte("Cu Totul Altcineva SRL", "Reclamant")])
        result = _parse_dosare([dosar], company_name="Firma Test SRL")
        assert result["total_dosare"] == 1
        assert result["reclamant"] == 0
        assert result["parat"] == 0

    def test_limita_20_in_preview_dar_total_corect(self):
        """Numarul total reflecta toate potrivirile; doar lista de preview e limitata la 20."""
        from backend.agents.tools.just_client import _parse_dosare
        dosare = [
            _make_dosar(numar=f"2026/{i}", parti=[_make_parte("Firma Test SRL", "Reclamant")])
            for i in range(30)
        ]
        result = _parse_dosare(dosare, company_name="Firma Test SRL")
        assert result["total_dosare"] == 30
        assert len(result["dosare"]) == 20

    def test_campuri_dosar_prezente(self):
        from backend.agents.tools.just_client import _parse_dosare
        dosar = _make_dosar(parti=[_make_parte("Firma Test SRL", "Reclamant")])
        result = _parse_dosare([dosar], company_name="Firma Test SRL")
        d = result["dosare"][0]
        assert "numar" in d
        assert "data" in d
        assert "institutie" in d
        assert "categorie" in d
        assert "calitate" in d
        assert "stadiu" in d


# ─── Test _institutions_for_judet (fix critic 2026-07-12) ────────────────────

class TestInstitutionsForJudet:
    """`institutie` e camp SOAP obligatoriu (246 valori posibile), fara varianta
    'toate instantele' — cautam Tribunalul judetului + Curtea de Apel regionala."""

    def test_judet_simplu(self):
        from backend.agents.tools.just_client import _institutions_for_judet
        assert _institutions_for_judet("Arad") == ["TribunalulARAD", "CurteadeApelTIMISOARA"]

    def test_judet_cu_diacritice_si_cratima(self):
        from backend.agents.tools.just_client import _institutions_for_judet
        assert _institutions_for_judet("Bistrița-Năsăud") == [
            "TribunalulBISTRITANASAUD", "CurteadeApelCLUJ",
        ]

    def test_judet_cu_spatiu(self):
        from backend.agents.tools.just_client import _institutions_for_judet
        assert _institutions_for_judet("Satu Mare") == ["TribunalulSATUMARE", "CurteadeApelORADEA"]

    def test_judet_gol_returneaza_lista_goala(self):
        from backend.agents.tools.just_client import _institutions_for_judet
        assert _institutions_for_judet("") == []


# ─── Test search_dosare ───────────────────────────────────────────────────────

class TestSearchDosare:

    @pytest.mark.asyncio
    async def test_fara_judet_returneaza_graceful(self):
        """Fara judet cunoscut nu putem alege institutie (camp obligatoriu) -> found=False."""
        from backend.agents.tools.just_client import search_dosare
        result = await search_dosare("Test SRL", judet="")
        assert result["found"] is False
        assert "judet" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_zeep_missing_returneaza_graceful(self):
        """Daca zeep nu e instalat, returneaza found=False fara sa crape."""
        from backend.agents.tools.just_client import search_dosare
        with patch("builtins.__import__", side_effect=ImportError("zeep not found")):
            result = await search_dosare("Test SRL", judet="Cluj")
            assert isinstance(result, dict)
            assert result.get("found") is False

    @pytest.mark.asyncio
    async def test_search_dosare_gestioneaza_exceptie_generica(self):
        """Orice exceptie neasteptata la setup-ul clientului WSDL e prinsa, fara crash."""
        from backend.agents.tools.just_client import search_dosare
        with patch("backend.agents.tools.just_client.asyncio.get_event_loop",
                   side_effect=RuntimeError("unexpected")):
            result = await search_dosare("Test SRL", judet="Cluj")
            assert isinstance(result, dict)
            assert result.get("found") is False
