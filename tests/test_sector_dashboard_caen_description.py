"""
Test de regresie: `sector_dashboard` (backend/routers/compare.py) apela
`get_caen_info(caen_code)` — o functie care NU EXISTA nicaieri in repo (doar
importul si apelul, niciun `def`). Fiecare apel arunca ImportError, prins de
un `except Exception` larg urmat de `logger.debug` (invizibil) -> `caen_info = {}`
-> `caen_description` era mereu "" -> frontend-ul (SectorDashboard.tsx) afisa
"Descriere indisponibila" pentru ORICE cod CAEN, de cand exista feature-ul.

Fix: functia reala existenta e `get_caen_description(caen_code) -> str`
(deja importata in compare.py, deja folosita la linia `caen_desc =
get_caen_description(section)` din `sector_report`) — cablata direct, fara
except larg (nu poate arunca pentru input valid: doar lookup-uri de dict).

Rulat pe codul dinaintea fix-ului, acest test PICA: caen_description == "".
"""
import asyncio

from backend.routers import compare as compare_router


class _FakeDB:
    """Stub minimal pt db.fetch_one/fetch_all folosite de sector_dashboard."""

    def __init__(self, stats: dict | None, top_companies: list):
        self._stats = stats
        self._top_companies = top_companies

    async def fetch_one(self, query, params=None):
        return self._stats

    async def fetch_all(self, query, params=None):
        return self._top_companies


class TestSectorDashboardCaenDescription:
    def test_caen_valid_returneaza_descriere_reala(self, monkeypatch):
        """CAEN 6201 (IT, prezent in CAEN_DESCRIPTIONS) trebuie sa produca o
        descriere reala, nu string gol."""
        fake_db = _FakeDB(
            stats={"total_companies": 2, "avg_score": 75.0, "count_verde": 1, "count_galben": 1, "count_rosu": 0},
            top_companies=[],
        )
        monkeypatch.setattr(compare_router, "db", fake_db)

        result = asyncio.run(compare_router.sector_dashboard("6201"))

        assert result["caen_description"] != "", "caen_description e goala — bug-ul get_caen_info reintrodus"
        assert "software" in result["caen_description"].lower()

    def test_caen_necunoscut_dar_cu_sectiune_valida_foloseste_fallback_sectiune(self, monkeypatch):
        """Cod CAEN cu 4 cifre valide dar absent din dictionarul detaliat trebuie
        sa cada pe numele sectiunii (2 cifre), nu pe string gol — comportamentul
        real al get_caen_description(), nu al lookup-ului mort get_caen_info()."""
        fake_db = _FakeDB(stats=None, top_companies=[])
        monkeypatch.setattr(compare_router, "db", fake_db)

        # "6299" nu e in CAEN_DESCRIPTIONS, dar sectiunea "62" (IT) e in CAEN_SECTIONS.
        result = asyncio.run(compare_router.sector_dashboard("6299"))

        assert result["caen_description"] != ""

    def test_get_caen_info_nu_mai_e_referentiat(self):
        """Regresie directa: sursa endpoint-ului nu mai importa/apeleaza o
        functie inexistenta `get_caen_info`."""
        import inspect

        src = inspect.getsource(compare_router.sector_dashboard)
        assert "get_caen_info" not in src
