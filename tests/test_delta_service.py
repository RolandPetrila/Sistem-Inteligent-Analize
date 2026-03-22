"""Tests for Delta Service — change detection logic between reports."""
import pytest
from backend.services.delta_service import (
    _compute_change,
    _extract_ca,
    _extract_profit,
    _extract_employees,
    _extract_risk_score,
    _get_field_value,
)


class TestComputeChange:
    """Test numeric change calculation between two values."""

    def test_increase(self):
        result = _compute_change("CA", 1000000, 1200000, "RON")
        assert result is not None
        assert result["direction"] == "crestere"
        assert result["percent_change"] == 20.0
        assert result["diff"] == 200000

    def test_decrease(self):
        result = _compute_change("CA", 1000000, 700000, "RON")
        assert result["direction"] == "scadere"
        assert result["percent_change"] == -30.0

    def test_no_change(self):
        result = _compute_change("CA", 1000000, 1000000, "RON")
        assert result is None  # diff < 0.01

    def test_zero_old_value(self):
        result = _compute_change("Angajati", 0, 10, "")
        assert result is not None
        assert result["percent_change"] is None  # can't compute % from 0

    def test_invalid_values(self):
        result = _compute_change("CA", "N/A", 1000000, "RON")
        assert result is None

    def test_none_values(self):
        result = _compute_change("CA", None, 1000000, "RON")
        assert result is None

    def test_display_format_ron(self):
        result = _compute_change("CA", 1000000, 2000000, "RON")
        assert "RON" in result["display"]
        assert "100.0%" in result["display"]

    def test_small_change_still_reported(self):
        result = _compute_change("Scor", 72, 73, "/100")
        assert result is not None
        assert result["diff"] == 1

    def test_negative_to_positive(self):
        result = _compute_change("Profit", -50000, 100000, "RON")
        assert result["direction"] == "crestere"


class TestExtractors:
    """Test data extraction from verified_data structure."""

    def test_extract_ca_dict_format(self):
        data = {"financial": {"cifra_afaceri": {"value": 1500000, "trust": "OFICIAL"}}}
        assert _extract_ca(data) == 1500000

    def test_extract_ca_empty(self):
        assert _extract_ca({}) is None
        assert _extract_ca({"financial": {}}) is None

    def test_extract_profit(self):
        data = {"financial": {"profit_net": {"value": 250000, "trust": "OFICIAL"}}}
        assert _extract_profit(data) == 250000

    def test_extract_employees(self):
        data = {"financial": {"numar_angajati": {"value": 42, "trust": "OFICIAL"}}}
        assert _extract_employees(data) == 42

    def test_extract_risk_score(self):
        data = {"risk_score": {"numeric_score": 78, "score": "Verde"}}
        assert _extract_risk_score(data) == 78

    def test_extract_risk_score_missing(self):
        assert _extract_risk_score({}) is None

    def test_get_field_value_dict(self):
        assert _get_field_value({"value": "ACTIV"}) == "ACTIV"

    def test_get_field_value_plain(self):
        assert _get_field_value("ACTIV") == "ACTIV"

    def test_get_field_value_none(self):
        assert _get_field_value(None) is None
