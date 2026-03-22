"""Tests for ANAF Bilant client — trend calculation and data parsing logic."""
import pytest
from backend.agents.tools.anaf_bilant_client import _calculate_trends


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
