"""Tests for CAEN context — code lookup and sector classification."""
import pytest
from backend.agents.tools.caen_context import CAEN_DESCRIPTIONS, CAEN_SECTIONS


class TestCAENDescriptions:
    """Test CAEN code dictionary completeness."""

    def test_common_codes_present(self):
        assert "6201" in CAEN_DESCRIPTIONS  # IT software
        assert "4711" in CAEN_DESCRIPTIONS  # magazine alimentare
        assert "4120" in CAEN_DESCRIPTIONS  # constructii
        assert "4941" in CAEN_DESCRIPTIONS  # transport marfuri

    def test_descriptions_not_empty(self):
        for code, desc in CAEN_DESCRIPTIONS.items():
            assert len(desc) > 5, f"CAEN {code} has too short description"

    def test_codes_are_4_digits(self):
        for code in CAEN_DESCRIPTIONS:
            assert len(code) == 4, f"CAEN code {code} is not 4 digits"
            assert code.isdigit(), f"CAEN code {code} contains non-digits"

    def test_minimum_codes_count(self):
        assert len(CAEN_DESCRIPTIONS) >= 100


class TestCAENSections:
    """Test CAEN section classification."""

    def test_sections_exist(self):
        assert len(CAEN_SECTIONS) > 0

    def test_section_keys_are_strings(self):
        for key in CAEN_SECTIONS:
            assert isinstance(key, str)

    def test_it_section_present(self):
        it_found = any("software" in str(v).lower() or "IT" in str(v) or "informati" in str(v).lower()
                       for v in CAEN_SECTIONS.values())
        assert it_found, "IT section not found in CAEN_SECTIONS"
