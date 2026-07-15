"""Tests for ANAF Bilant client — trend calculation and data parsing logic."""
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.agents.tools.anaf_bilant_client import _calculate_trends, get_bilant


def _mock_resp(payload, status=200):
    r = MagicMock(spec=httpx.Response)
    r.status_code = status
    r.json.return_value = payload
    return r


# Payload fictiv, cu forma IDENTICA celei reale intoarse de ANAF Bilant
# (verificat live 2026-07-15 pe 2 CUI-uri reale, o firma mica si una mare —
# ambele folosesc acelasi format simplificat I1-I20, o singura linie DATORII
# fara split curent/necurent). Cifre 100% fictive — repo public.
FICTIONAL_ANAF_PAYLOAD = {
    "an": 2024, "cui": 99999999, "deni": "FIRMA FICTIVA SRL", "caen": "4711",
    "den_caen": "Comert cu amanuntul in magazine nespecializate",
    "i": [
        {"indicator": "I1", "val_indicator": 500_000, "val_den_indicator": "ACTIVE IMOBILIZATE - TOTAL "},
        {"indicator": "I2", "val_indicator": 300_000, "val_den_indicator": "ACTIVE CIRCULANTE - TOTAL, din care:"},
        {"indicator": "I3", "val_indicator": 100_000, "val_den_indicator": "Stocuri"},
        {"indicator": "I4", "val_indicator": 150_000, "val_den_indicator": "Creante"},
        {"indicator": "I5", "val_indicator": 50_000, "val_den_indicator": "Casa şi conturi la bănci"},
        {"indicator": "I6", "val_indicator": 10_000, "val_den_indicator": "CHELTUIELI IN AVANS"},
        {"indicator": "I7", "val_indicator": 250_000, "val_den_indicator": "DATORII"},
        {"indicator": "I8", "val_indicator": 1_000, "val_den_indicator": "VENITURI IN AVANS"},
        {"indicator": "I9", "val_indicator": 5_000, "val_den_indicator": "PROVIZIOANE"},
        {"indicator": "I10", "val_indicator": 554_000, "val_den_indicator": "CAPITALURI - TOTAL, din care:"},
        {"indicator": "I11", "val_indicator": 10_000, "val_den_indicator": "Capital subscris varsat"},
        {"indicator": "I13", "val_indicator": 2_000_000, "val_den_indicator": "Cifra de afaceri neta"},
        {"indicator": "I16", "val_indicator": 150_000, "val_den_indicator": "Profit brut"},
        {"indicator": "I18", "val_indicator": 120_000, "val_den_indicator": "Profit net"},
        {"indicator": "I20", "val_indicator": 25, "val_den_indicator": "Numar mediu de salariati"},
    ],
}


class TestActiveTotaleComputed:
    """active_totale = active_imobilizate + active_circulante + cheltuieli_avans —
    identitate de bilant prescurtat ANAF, verificata pe date live 2026-07-15."""

    @pytest.mark.asyncio
    async def test_active_totale_calculat_corect(self):
        with patch("backend.agents.tools.anaf_bilant_client.get_client") as mc:
            mc.return_value.get = AsyncMock(return_value=_mock_resp(FICTIONAL_ANAF_PAYLOAD))
            result = await get_bilant("99999999", 2024)

        assert result["found"] is True
        assert result["active_totale"] == 810_000  # 500_000 + 300_000 + 10_000
        assert result["datorii_totale"] == 250_000
        # Identitatea de bilant: Active = Capitaluri + Datorii + Provizioane + Venituri avans
        assert result["active_totale"] == (
            result["capitaluri_proprii"] + result["datorii_totale"]
            + result["provizioane"] + result["venituri_avans"]
        )

    @pytest.mark.asyncio
    async def test_active_totale_absent_fara_componente(self):
        """Daca lipsesc active_imobilizate SAU active_circulante, active_totale
        ramane ABSENT (nu se calculeaza gresit dintr-un subset)."""
        payload = {
            "an": 2024, "cui": 99999999, "deni": "FIRMA FICTIVA SRL", "caen": "4711",
            "den_caen": "test",
            "i": [
                {"indicator": "I1", "val_indicator": 500_000, "val_den_indicator": "ACTIVE IMOBILIZATE - TOTAL "},
                {"indicator": "I18", "val_indicator": 120_000, "val_den_indicator": "Profit net"},
            ],
        }
        with patch("backend.agents.tools.anaf_bilant_client.get_client") as mc:
            mc.return_value.get = AsyncMock(return_value=_mock_resp(payload))
            result = await get_bilant("99999999", 2024)

        assert "active_totale" not in result


class TestCalculateTrends:
    """Test financial trend calculations from multi-year data."""

    def test_growth_positive(self):
        data = {
            2022: {"cifra_afaceri_neta": 1000000},
            2023: {"cifra_afaceri_neta": 1200000},
        }
        trend = _calculate_trends(data)
        assert "cifra_afaceri_neta" in trend
        assert trend["cifra_afaceri_neta"]["growth_percent"] == 20.0
        assert trend["cifra_afaceri_neta"]["direction"] == "crestere"

    def test_growth_negative(self):
        data = {
            2022: {"cifra_afaceri_neta": 1000000},
            2023: {"cifra_afaceri_neta": 700000},
        }
        trend = _calculate_trends(data)
        assert trend["cifra_afaceri_neta"]["growth_percent"] == -30.0
        assert trend["cifra_afaceri_neta"]["direction"] == "scadere"

    def test_growth_stable(self):
        data = {
            2022: {"cifra_afaceri_neta": 500000},
            2023: {"cifra_afaceri_neta": 500000},
        }
        trend = _calculate_trends(data)
        assert trend["cifra_afaceri_neta"]["growth_percent"] == 0.0
        assert trend["cifra_afaceri_neta"]["direction"] == "stabil"

    def test_zero_base_year(self):
        data = {
            2022: {"cifra_afaceri_neta": 0},
            2023: {"cifra_afaceri_neta": 500000},
        }
        trend = _calculate_trends(data)
        assert trend["cifra_afaceri_neta"]["growth_percent"] is None
        assert trend["cifra_afaceri_neta"]["direction"] == "N/A"

    def test_single_year_no_trend(self):
        data = {2023: {"cifra_afaceri_neta": 1000000}}
        trend = _calculate_trends(data)
        assert trend == {}

    def test_empty_data_no_trend(self):
        trend = _calculate_trends({})
        assert trend == {}

    def test_multiple_metrics(self):
        data = {
            2022: {"cifra_afaceri_neta": 1000000, "profit_net": 100000, "numar_mediu_salariati": 10},
            2023: {"cifra_afaceri_neta": 1500000, "profit_net": 200000, "numar_mediu_salariati": 15},
        }
        trend = _calculate_trends(data)
        assert "cifra_afaceri_neta" in trend
        assert "profit_net" in trend
        assert "numar_mediu_salariati" in trend
        assert trend["profit_net"]["growth_percent"] == 100.0

    def test_three_years_uses_first_and_last(self):
        data = {
            2021: {"cifra_afaceri_neta": 100000},
            2022: {"cifra_afaceri_neta": 500000},  # spike, but ignored for growth calc
            2023: {"cifra_afaceri_neta": 200000},
        }
        trend = _calculate_trends(data)
        assert trend["cifra_afaceri_neta"]["growth_percent"] == 100.0
        assert trend["cifra_afaceri_neta"]["first_year"] == 2021
        assert trend["cifra_afaceri_neta"]["last_year"] == 2023

    def test_missing_metric_in_some_years(self):
        data = {
            2022: {"cifra_afaceri_neta": 1000000},
            2023: {},  # no CA data
        }
        trend = _calculate_trends(data)
        # Only 1 data point for CA, so no trend
        assert "cifra_afaceri_neta" not in trend

    def test_negative_values_profit_loss(self):
        data = {
            2022: {"profit_net": -50000},
            2023: {"profit_net": 100000},
        }
        trend = _calculate_trends(data)
        assert trend["profit_net"]["direction"] == "crestere"
        assert trend["profit_net"]["growth_percent"] is not None
