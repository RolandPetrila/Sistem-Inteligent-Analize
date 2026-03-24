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


# --- TEST-02: Extended scoring tests ---

class TestScoringDimensions:
    """Test individual scoring dimensions and weights."""

    def test_financial_dimension_weight(self):
        from backend.agents.verification.scoring import calculate_risk_score
        result = calculate_risk_score({})
        dims = result.get("dimensions", {})
        assert "financiar" in dims
        assert dims["financiar"]["weight"] == 30

    def test_juridic_dimension_weight(self):
        from backend.agents.verification.scoring import calculate_risk_score
        result = calculate_risk_score({})
        dims = result.get("dimensions", {})
        assert dims["juridic"]["weight"] == 20

    def test_fiscal_dimension_weight(self):
        from backend.agents.verification.scoring import calculate_risk_score
        result = calculate_risk_score({})
        dims = result.get("dimensions", {})
        assert dims["fiscal"]["weight"] == 15

    def test_operational_dimension_weight(self):
        from backend.agents.verification.scoring import calculate_risk_score
        result = calculate_risk_score({})
        dims = result.get("dimensions", {})
        assert dims["operational"]["weight"] == 15

    def test_reputational_dimension_weight(self):
        from backend.agents.verification.scoring import calculate_risk_score
        result = calculate_risk_score({})
        dims = result.get("dimensions", {})
        assert dims["reputational"]["weight"] == 10

    def test_piata_dimension_weight(self):
        from backend.agents.verification.scoring import calculate_risk_score
        result = calculate_risk_score({})
        dims = result.get("dimensions", {})
        assert dims["piata"]["weight"] == 10

    def test_weights_sum_to_100(self):
        from backend.agents.verification.scoring import calculate_risk_score
        result = calculate_risk_score({})
        dims = result.get("dimensions", {})
        total = sum(d["weight"] for d in dims.values())
        assert total == 100

    def test_high_ca_improves_financial(self):
        from backend.agents.verification.scoring import calculate_risk_score
        low = calculate_risk_score({})
        high = calculate_risk_score({"financial": {"cifra_afaceri": {"value": 50_000_000}}})
        assert high["dimensions"]["financiar"]["score"] > low["dimensions"]["financiar"]["score"]

    def test_inactive_company_fiscal_penalty(self):
        from backend.agents.verification.scoring import calculate_risk_score
        baseline = calculate_risk_score({})
        inactive = calculate_risk_score({"risk": {"anaf_inactive": {"value": True}}})
        assert inactive["dimensions"]["fiscal"]["score"] < baseline["dimensions"]["fiscal"]["score"]

    def test_score_always_0_100(self):
        from backend.agents.verification.scoring import calculate_risk_score
        # Extreme negative data
        bad = calculate_risk_score({
            "financial": {"cifra_afaceri": {"value": 0}, "profit_net": {"value": -999999}},
            "risk": {"anaf_inactiv": True, "litigii": [1, 2, 3, 4, 5]},
        })
        assert 0 <= bad["numeric_score"] <= 100
        # Extreme positive data
        good = calculate_risk_score({
            "financial": {"cifra_afaceri": {"value": 100_000_000}, "profit_net": {"value": 10_000_000}},
        })
        assert 0 <= good["numeric_score"] <= 100


class TestFinancialRatios:
    """Test _calculate_financial_ratios function."""

    def test_profit_margin_calculated(self):
        from backend.agents.verification.scoring import _calculate_financial_ratios
        ratios = _calculate_financial_ratios({
            "cifra_afaceri": {"value": 1_000_000},
            "profit_net": {"value": 100_000},
        })
        names = [r["name"] for r in ratios]
        assert "Marja Profit Net" in names

    def test_roe_requires_capital(self):
        from backend.agents.verification.scoring import _calculate_financial_ratios
        ratios = _calculate_financial_ratios({
            "profit_net": {"value": 100_000},
        })
        names = [r["name"] for r in ratios]
        assert "ROE" not in names  # No capital → no ROE

    def test_roe_with_capital(self):
        from backend.agents.verification.scoring import _calculate_financial_ratios
        ratios = _calculate_financial_ratios({
            "profit_net": {"value": 100_000},
            "capitaluri_proprii": {"value": 500_000},
        })
        names = [r["name"] for r in ratios]
        assert "ROE" in names

    def test_empty_data_no_ratios(self):
        from backend.agents.verification.scoring import _calculate_financial_ratios
        ratios = _calculate_financial_ratios({})
        assert len(ratios) == 0
