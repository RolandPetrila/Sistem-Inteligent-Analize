"""Teste eurostat_client — mapare CAEN->NACE, extractor JSON-stat, get_sector_context (mock)."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from backend.agents.tools.eurostat_client import (
    _jsonstat_value,
    _nace_candidates,
    _nace_section,
    get_sector_context,
)


class TestNaceMapping:
    def test_section_from_division(self):
        assert _nace_section(62) == "J"   # IT
        assert _nace_section(10) == "C"   # productie alimentara
        assert _nace_section(49) == "H"   # transport
        assert _nace_section(0) == ""     # invalid

    def test_candidates_it(self):
        assert _nace_candidates("6201") == ["J6201", "J62", "J"]

    def test_candidates_two_digit_only(self):
        assert _nace_candidates("62") == ["J62", "J"]

    def test_candidates_invalid(self):
        assert _nace_candidates("x") == []
        assert _nace_candidates("") == []


class TestJsonStat:
    def _cube(self):
        return {
            "id": ["freq", "nace_r2", "indic_sbs", "geo", "time"],
            "size": [1, 1, 1, 2, 1],
            "dimension": {
                "freq": {"category": {"index": {"A": 0}}},
                "nace_r2": {"category": {"index": {"J62": 0}, "label": {"J62": "Computer programming"}}},
                "indic_sbs": {"category": {"index": {"ENT_NR": 0}}},
                "geo": {"category": {"index": {"RO": 0, "EU27_2020": 1}}},
                "time": {"category": {"index": {"2024": 0}}},
            },
            "value": {"0": 45240, "1": 1008501},
        }

    def test_extracts_ro_and_eu(self):
        cube = self._cube()
        ro = _jsonstat_value(cube, {"freq": "A", "nace_r2": "J62", "indic_sbs": "ENT_NR", "geo": "RO", "time": "2024"})
        eu = _jsonstat_value(cube, {"freq": "A", "nace_r2": "J62", "indic_sbs": "ENT_NR", "geo": "EU27_2020", "time": "2024"})
        assert ro == 45240
        assert eu == 1008501

    def test_missing_code_returns_none(self):
        cube = self._cube()
        assert _jsonstat_value(cube, {"freq": "A", "nace_r2": "J6201", "indic_sbs": "ENT_NR", "geo": "RO", "time": "2024"}) is None


def _mock_resp(payload):
    r = MagicMock(spec=httpx.Response)
    r.json.return_value = payload
    r.raise_for_status.return_value = None
    return r


class TestGetSectorContext:
    def _cube(self):
        return {
            "id": ["freq", "nace_r2", "indic_sbs", "geo", "time"],
            "size": [1, 1, 1, 2, 1],
            "dimension": {
                "freq": {"category": {"index": {"A": 0}}},
                "nace_r2": {"category": {"index": {"J62": 0}, "label": {"J62": "Computer programming"}}},
                "indic_sbs": {"category": {"index": {"ENT_NR": 0}}},
                "geo": {"category": {"index": {"RO": 0, "EU27_2020": 1}}},
                "time": {"category": {"index": {"2024": 0}}},
            },
            "value": {"0": 45240, "1": 1008501},
        }

    async def test_returns_sector_context(self):
        with patch("backend.agents.tools.eurostat_client.get_client") as mc:
            mc.return_value.get = AsyncMock(return_value=_mock_resp(self._cube()))
            r = await get_sector_context("6201")
        assert r["available"] is True
        assert r["nace_used"] == "J62"
        assert r["year"] == "2024"
        assert r["indicators"]["ENT_NR"]["ro"] == 45240
        assert r["indicators"]["ENT_NR"]["eu"] == 1008501

    async def test_invalid_caen_no_call(self):
        with patch("backend.agents.tools.eurostat_client.get_client") as mc:
            r = await get_sector_context("xx")
        assert r["available"] is False
        mc.return_value.get.assert_not_called()

    async def test_empty_data_unavailable(self):
        empty = {"id": [], "size": [], "dimension": {"time": {"category": {"index": {}}}}, "value": {}}
        with patch("backend.agents.tools.eurostat_client.get_client") as mc:
            mc.return_value.get = AsyncMock(return_value=_mock_resp(empty))
            r = await get_sector_context("6201")
        assert r["available"] is False
