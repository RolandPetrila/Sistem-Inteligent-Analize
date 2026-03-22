"""Tests for CUI validator — MOD 11 algorithm."""
import pytest
from backend.agents.tools.cui_validator import validate_cui, extract_and_validate_cui


class TestValidateCUI:
    """Test CUI validation with known-good and known-bad CUIs."""

    def test_valid_cui_mosslein(self):
        result = validate_cui("26313362")
        assert result["valid"] is True
        assert result["cui_clean"] == "26313362"
        assert result["error"] is None

    def test_valid_cui_with_ro_prefix(self):
        result = validate_cui("RO26313362")
        assert result["valid"] is True
        assert result["cui_clean"] == "26313362"

    def test_valid_cui_with_spaces(self):
        result = validate_cui("  RO 26313362  ")
        assert result["valid"] is True

    def test_valid_cui_bitdefender(self):
        # Bitdefender CUI: 18189442
        result = validate_cui("18189442")
        assert result["valid"] is True

    def test_invalid_cui_wrong_check_digit(self):
        result = validate_cui("26313363")  # last digit wrong
        assert result["valid"] is False
        assert "Cifra de control" in result["error"]

    def test_empty_cui(self):
        result = validate_cui("")
        assert result["valid"] is False
        assert "gol" in result["error"]

    def test_non_numeric_cui(self):
        result = validate_cui("ABC123")
        assert result["valid"] is False
        assert "non-numerice" in result["error"]

    def test_too_short_cui(self):
        result = validate_cui("1")
        assert result["valid"] is False
        assert "2-10" in result["error"]

    def test_too_long_cui(self):
        result = validate_cui("12345678901")
        assert result["valid"] is False
        assert "2-10" in result["error"]

    def test_two_digit_cui(self):
        # Minimal valid length
        result = validate_cui("17")
        assert isinstance(result["valid"], bool)

    def test_lowercase_ro_prefix(self):
        result = validate_cui("ro26313362")
        assert result["valid"] is True


class TestExtractAndValidateCUI:
    """Test CUI extraction from free text."""

    def test_extract_plain_cui(self):
        result = extract_and_validate_cui("CUI-ul firmei este 26313362")
        assert result["valid"] is True

    def test_extract_ro_prefix(self):
        result = extract_and_validate_cui("RO26313362 este codul fiscal")
        assert result["valid"] is True

    def test_extract_no_cui(self):
        result = extract_and_validate_cui("nu contine niciun cod")
        assert result["valid"] is False

    def test_extract_with_spaces(self):
        result = extract_and_validate_cui("RO 26313362")
        assert result["valid"] is True
