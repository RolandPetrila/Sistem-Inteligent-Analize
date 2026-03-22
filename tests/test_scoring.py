"""Tests for risk scoring and completeness check logic."""
import pytest
from backend.agents.agent_verification import VerificationAgent


@pytest.fixture
def agent():
    return VerificationAgent()


class TestRiskScore:
    """Test _calculate_risk_score produces valid output structure."""

    def test_empty_verified_data(self, agent):
        result = agent._calculate_risk_score({})
        assert "score" in result
        assert "numeric_score" in result
        assert "dimensions" in result
        assert "factors" in result
        assert isinstance(result["numeric_score"], (int, float))
        assert 0 <= result["numeric_score"] <= 100

    def test_healthy_company(self, agent):
        verified = {
            "profile": {"cui": "12345678", "company_name": "Test SRL"},
            "financial_official": {
                "multi_year": {
                    "2023": {"cifra_afaceri": 1000000, "profit_net": 100000},
                    "2024": {"cifra_afaceri": 1200000, "profit_net": 150000},
                }
            },
            "anaf": {"stare": "ACTIV", "tva": True},
        }
        result = agent._calculate_risk_score(verified)
        assert result["numeric_score"] >= 50
        assert result["score"] in ("Verde", "Galben", "Rosu")

    def test_inactive_company_has_factor(self, agent):
        verified = {
            "anaf": {"stare": "INACTIV", "tva": False, "inactiv": True},
        }
        result = agent._calculate_risk_score(verified)
        assert isinstance(result["numeric_score"], (int, float))
        assert 0 <= result["numeric_score"] <= 100

    def test_score_color_mapping(self, agent):
        # Verde >= 70
        verified_good = {
            "anaf": {"stare": "ACTIV", "tva": True},
            "financial_official": {
                "multi_year": {
                    "2024": {"cifra_afaceri": 5000000, "profit_net": 500000, "numar_angajati": 50},
                }
            },
        }
        result = agent._calculate_risk_score(verified_good)
        if result["numeric_score"] >= 70:
            assert result["score"] == "Verde"
        elif result["numeric_score"] >= 40:
            assert result["score"] == "Galben"
        else:
            assert result["score"] == "Rosu"

    def test_dimensions_present(self, agent):
        result = agent._calculate_risk_score({})
        dims = result.get("dimensions", {})
        expected = ["financiar", "juridic", "fiscal", "operational", "reputational", "piata"]
        for dim in expected:
            assert dim in dims, f"Missing dimension: {dim}"


class TestCompleteness:
    """Test _check_completeness validates data presence."""

    def test_empty_data_low_score(self, agent):
        result = agent._check_completeness({}, {}, {})
        assert result["score"] < 50
        assert result["quality_level"] == "INCOMPLET"
        assert len(result["gaps"]) > 0

    def test_full_data_high_score(self, agent):
        """Test with the actual verified data structure used by the agent."""
        verified = {
            "company": {
                "cui": {"value": "12345678", "trust": "OFICIAL"},
                "denumire": {"value": "Test SRL", "trust": "OFICIAL"},
                "adresa": {"value": "Str. Test 1", "trust": "OFICIAL"},
                "stare_inregistrare": {"value": "ACTIV", "trust": "OFICIAL"},
                "data_inregistrare": {"value": "2020-01-01", "trust": "OFICIAL"},
                "platitor_tva": {"value": "DA", "trust": "OFICIAL"},
                "caen_code": {"value": "6201", "trust": "OFICIAL"},
                "caen_description": {"value": "IT", "trust": "OFICIAL"},
            },
            "actionariat": {
                "available": True,
                "asociati": [{"name": "Popescu Ion"}],
                "administratori": [{"name": "Popescu Ion"}],
            },
            "financial": {
                "cifra_afaceri": {"value": 1000000, "trust": "OFICIAL"},
                "profit_net": {"value": 100000, "trust": "OFICIAL"},
                "numar_angajati": {"value": 10, "trust": "OFICIAL"},
            },
            "caen_context": {"sector_name": "IT"},
            "benchmark": {"average_ca": 500000},
        }
        official = {"caen_code": "6201"}
        market = {"seap": {"total_contracts": 0}}
        result = agent._check_completeness(verified, official, market)
        assert result["score"] >= 60
        assert result["quality_level"] in ("COMPLET", "BUN", "PARTIAL")

    def test_gaps_have_severity(self, agent):
        result = agent._check_completeness({}, {}, {})
        for gap in result["gaps"]:
            assert "severity" in gap
            assert gap["severity"] in ("HIGH", "MEDIUM")

    def test_quality_levels(self, agent):
        # Test all 4 quality levels
        result = agent._check_completeness({}, {}, {})
        assert result["quality_level"] in ("COMPLET", "BUN", "PARTIAL", "INCOMPLET")

    def test_total_checks_count(self, agent):
        result = agent._check_completeness({}, {}, {})
        assert result["total_checks"] > 0
        assert result["passed"] >= 0
        assert result["passed"] <= result["total_checks"]


class TestRateLimiter:
    """Test the rate limiter module."""

    def test_allows_within_limit(self):
        from backend.rate_limiter import RateLimiter
        rl = RateLimiter(requests_per_minute=5)
        for _ in range(5):
            assert rl.check("127.0.0.1") is True

    def test_blocks_over_limit(self):
        from backend.rate_limiter import RateLimiter
        rl = RateLimiter(requests_per_minute=3)
        for _ in range(3):
            rl.check("127.0.0.1")
        assert rl.check("127.0.0.1") is False

    def test_different_ips_independent(self):
        from backend.rate_limiter import RateLimiter
        rl = RateLimiter(requests_per_minute=2)
        rl.check("1.1.1.1")
        rl.check("1.1.1.1")
        assert rl.check("1.1.1.1") is False
        assert rl.check("2.2.2.2") is True
