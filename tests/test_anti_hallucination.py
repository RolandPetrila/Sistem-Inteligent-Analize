"""
AH-05: Tests for anti-hallucination logic in SynthesisAgent.
Covers: _has_sufficient_data(), _validate_output(), completeness gate.
"""

import pytest
from backend.agents.agent_synthesis import SynthesisAgent


@pytest.fixture
def agent():
    return SynthesisAgent()


class TestHasSufficientData:
    """Tests for _has_sufficient_data() completeness checks."""

    def test_empty_verified_data_financial(self, agent):
        """Financial section with 0 fields → insufficient."""
        assert agent._has_sufficient_data("financial_analysis", {}) is False

    def test_minimal_financial_data(self, agent):
        """Financial with only 1 field → insufficient (needs >= 2)."""
        data = {"financial": {"cifra_afaceri": {"value": 1000000}}}
        assert agent._has_sufficient_data("financial_analysis", data) is False

    def test_sufficient_financial_data(self, agent):
        """Financial with 2+ fields → sufficient."""
        data = {"financial": {
            "cifra_afaceri": {"value": 1000000},
            "profit_net": {"value": 50000},
        }}
        assert agent._has_sufficient_data("financial_analysis", data) is True

    def test_executive_summary_always_allowed(self, agent):
        """Executive summary allowed when completeness >= 30%."""
        data = {"completeness": {"score": 50}}
        assert agent._has_sufficient_data("executive_summary", data) is True

    def test_executive_summary_blocked_low_completeness(self, agent):
        """AH-02: Executive summary blocked when completeness < 30%."""
        data = {"completeness": {"score": 15}}
        assert agent._has_sufficient_data("executive_summary", data) is False

    def test_recommendations_blocked_low_completeness(self, agent):
        """AH-02: Recommendations blocked when completeness < 30%."""
        data = {"completeness": {"score": 10}}
        assert agent._has_sufficient_data("recommendations", data) is False

    def test_competition_no_web_data(self, agent):
        """Competition with no web data → insufficient."""
        assert agent._has_sufficient_data("competition", {}) is False

    def test_company_profile_empty(self, agent):
        """Company profile with < 3 fields → insufficient."""
        data = {"company": {"denumire": {"value": "Test SRL"}}}
        assert agent._has_sufficient_data("company_profile", data) is False

    def test_unknown_section_allowed(self, agent):
        """Unknown section key → default allowed."""
        assert agent._has_sufficient_data("some_custom_section", {}) is True


class TestValidateOutput:
    """Tests for _validate_output() hallucination detection."""

    def test_suspicious_percentage_stripped(self, agent):
        """Percentages > 999% should be replaced."""
        text = "Crestere de 50000% in ultimul an."
        section = {"key": "financial_analysis", "word_count": 10}
        result = agent._validate_output(text, {}, section)
        assert "50000%" not in result
        assert "neverificat" in result.lower()

    def test_valid_percentage_kept(self, agent):
        """Normal percentages should remain."""
        text = "Marja de profit de 12.5% este buna."
        section = {"key": "financial_analysis", "word_count": 10}
        result = agent._validate_output(text, {}, section)
        assert "12.5%" in result

    def test_invented_cui_replaced(self, agent):
        """CUI not matching input should be replaced."""
        text = "Firma concurenta CUI: 99999999 are avantaj."
        data = {"company": {"cui": {"value": "12345678"}}}
        section = {"key": "competition", "word_count": 10}
        result = agent._validate_output(text, data, section)
        assert "99999999" not in result
        assert "12345678" in result

    def test_empty_text_passthrough(self, agent):
        """Empty text returns as-is."""
        result = agent._validate_output("", {}, {"key": "test", "word_count": 10})
        assert result == ""

    def test_fallback_text_passthrough(self, agent):
        """Fallback text starting with '[Sectiunea' returned as-is."""
        text = "[Sectiunea nu a putut fi generata]"
        result = agent._validate_output(text, {}, {"key": "test", "word_count": 10})
        assert result == text
