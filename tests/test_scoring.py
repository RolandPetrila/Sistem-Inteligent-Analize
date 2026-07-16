"""Tests for risk scoring and completeness check logic."""
import pytest

from backend.agents.agent_verification import VerificationAgent
from backend.agents.verification.scoring import COLOR_MAP, _resolve_caen_section, risk_bucket


@pytest.fixture
def agent():
    return VerificationAgent()


class TestResolveCaenSection:
    """Refactor _score_financiar Etapa 2 (2026-07-16): _resolve_caen_section a
    fost extras VERBATIM (nu tabelizat) din codul original, ca sa nu schimbe
    comportament pe cazuri de margine. Golden-ul (Pas 0) acopera doar 3 din
    cele 14 ramuri numerice ale mapei (F, J, DEFAULT-fallthrough) — testele
    de mai jos acopera DIRECT toate cele 14, plus goluri intre intervale,
    coduri alfanumerice mixte si precedenta alpha-inainte-de-digit, asa cum
    a fost promis in Pas 0/raportul refactorului.

    Asteptarile sunt derivate din structura reala NACE Rev.2 (nu copiate din
    outputul codului nou): A=Agricultura(01-03), B=Extractiva(05-09),
    C=Prelucratoare(10-33), D=Energie(35), E=Apa/Salubritate(36-39),
    F=Constructii(41-43), G=Comert(45-47), H=Transport(49-53),
    I=Hoteluri/Restaurante(55-56), J=Info/Comunicatii(58-63),
    K=Financiar(64-66), L=Imobiliare(68), M=Profesional/Stiintific(69-75),
    N=Administrativ(77-82) — coincide cu mapa din scoring.py, ceea ce
    confirma independent ca implementarea respecta standardul real."""

    @pytest.mark.parametrize("caen_num,expected", [
        (1, "A"), (2, "A"), (3, "A"),
        (5, "B"), (7, "B"), (9, "B"),
        (10, "C"), (20, "C"), (33, "C"),
        (35, "D"),
        (36, "E"), (38, "E"), (39, "E"),
        (41, "F"), (42, "F"), (43, "F"),
        (45, "G"), (46, "G"), (47, "G"),
        (49, "H"), (52, "H"), (53, "H"),
        (55, "I"), (56, "I"),
        (58, "J"), (60, "J"), (63, "J"),
        (64, "K"), (65, "K"), (66, "K"),
        (68, "L"),
        (69, "M"), (72, "M"), (75, "M"),
        (77, "N"), (80, "N"), (82, "N"),
    ])
    def test_numeric_ranges_map_to_correct_section(self, caen_num, expected):
        assert _resolve_caen_section(str(caen_num), {}) == expected

    @pytest.mark.parametrize("caen_num", [0, 4, 34, 40, 44, 48, 54, 57, 67, 76, 83, 999])
    def test_gap_numbers_fall_to_default(self, caen_num):
        """Numere intre intervalele definite (sau peste 82) -> "DEFAULT",
        prin ramura explicita else a lantului elif (nu prin lipsa de match)."""
        assert _resolve_caen_section(str(caen_num), {}) == "DEFAULT"

    def test_alpha_first_char_takes_precedence_over_digit_check(self):
        """caen_code care incepe cu litera foloseste litera direct, fara sa
        mai ajunga la ramura .isdigit()."""
        assert _resolve_caen_section("J6201", {}) == "J"
        assert _resolve_caen_section("f4120", {}) == "F"  # lowercase -> upper()

    def test_mixed_alnum_not_alpha_first_not_all_digit_falls_to_empty_string(self):
        """"6A": primul caracter NU e litera (e cifra) -> nu intra pe ramura
        alpha; dar .isdigit() e False (are litera in coada) -> nu intra nici
        pe ramura numerica. Rezultat: caen_section ramane "" (NU "DEFAULT" —
        distinctie reala: "" nu e cheie in SECTOR_VOLATILITY_BASELINE, deci
        _score_trend_decomposition cade oricum pe baseline DEFAULT prin
        `.get(caen_section, ...["DEFAULT"])`, dar valoarea INTERMEDIARA
        difera de "DEFAULT" explicit — comportament pastrat verbatim din
        codul original, nu introdus de refactor)."""
        assert _resolve_caen_section("6A", {}) == ""

    def test_empty_caen_code_falls_to_empty_string(self):
        assert _resolve_caen_section("", {}) == ""
        assert _resolve_caen_section(None, {}) == ""

    def test_toplevel_takes_priority_over_company_dict(self):
        company = {"caen_code": {"value": "4120"}}  # would resolve to F
        assert _resolve_caen_section("62", company) == "J"

    def test_falls_back_to_company_dict_when_toplevel_falsy(self):
        """Forma REALA de productie: verified["caen_code"] top-level nu e
        niciodata setat de agent_verification.py — codul cade mereu pe
        company["caen_code"] (dict _make_field-wrapped, cu cheia "value").
        NOTA: "41" (sectiune cu 2 cifre), NU "4120" (codul CAEN complet cu 4
        cifre) — int("4120")=4120 nu se incadreaza in niciun interval
        (max 82), deci ar cadea pe DEFAULT. Asta confirma independent
        gasirea din raport: codurile CAEN reale (4 cifre) NU se potrivesc
        niciodata cu aceasta mapa numerica — doar sectiuni scurte (1-2
        cifre) o fac."""
        company = {"caen_code": {"value": "41", "trust": "OFICIAL"}}
        assert _resolve_caen_section("", company) == "F"
        assert _resolve_caen_section(None, company) == "F"

    def test_company_dict_without_wrapper_falsy_value_falls_to_empty(self):
        company = {"caen_code": {"value": ""}}
        assert _resolve_caen_section("", company) == ""


class TestRiskBucketBoundaries:
    """DRY #2 (2026-07-14): risk_bucket() e sursa unica a pragului scor->eticheta,
    folosita de engine (scoring.py:1130) si de toti cei 25 de consumatori identificati
    in audit. Blocheaza granitele exacte (70/69.99/40/39.99) — daca cineva muta un prag
    aici, testul de mai jos trebuie actualizat explicit, nu poate trece din greseala."""

    def test_verde_at_exactly_70(self):
        assert risk_bucket(70) == "Verde"

    def test_galben_just_below_70(self):
        assert risk_bucket(69.99) == "Galben"

    def test_galben_at_exactly_40(self):
        assert risk_bucket(40) == "Galben"

    def test_rosu_just_below_40(self):
        assert risk_bucket(39.99) == "Rosu"

    def test_rosu_at_zero(self):
        assert risk_bucket(0) == "Rosu"

    def test_verde_at_100(self):
        assert risk_bucket(100) == "Verde"

    def test_backed_by_color_map_not_hardcoded_twice(self):
        """risk_bucket() trebuie sa citeasca din COLOR_MAP, nu sa re-hardcodeze
        pragurile — altfel ramanem cu 2 surse (exact ce DRY #2 a vrut sa elimine)."""
        assert risk_bucket(COLOR_MAP["Verde"]) == "Verde"
        assert risk_bucket(COLOR_MAP["Galben"]) == "Galben"


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


class TestZombieDetection:
    """FIX 2026-07-16: `_detect_zombie_and_anomalies` citea `company["stare_firma"]`,
    o cheie NICIODATA scrisa de `agent_verification.py` (verificat: 0
    assignment-uri in tot backend-ul) -> orice firma cu CA=0+angajati=0 era
    etichetata ZOMBIE necontitionat, INCLUSIV una legal RADIATA/DIZOLVATA
    (carve-out-ul pt firme inchise era cod mort). Cheia reala e
    `stare_inregistrare` (ANAF)/`stare_onrc` (ONRC), emisa ca text liber CU
    data ("INREGISTRAT din data 09.12.2009", verificat direct in DB) — NU un
    token curat, deci un simplu rename pastrand egalitate EXACTA ar fi
    omorat detectia complet (nicio valoare reala nu mai e egala exact cu
    "ACTIVA"). Matching-ul e deci pe substring case-insensitive."""

    @staticmethod
    def _verified(stare_inregistrare_value, ca=0, angajati=0):
        return {
            "company": {
                "stare_inregistrare": {
                    "value": stare_inregistrare_value, "trust": "OFICIAL", "source": "ANAF",
                },
            },
            "financial": {
                "cifra_afaceri": {"value": ca},
                "numar_angajati": {"value": angajati},
            },
        }

    def test_real_active_status_text_still_flags_zombie(self):
        """Formatul REAL de status 'activ' ("INREGISTRAT din data ...") +
        CA=0 + angajati=0 -> ramane ZOMBIE. NOTA de non-vacuitate: pe codul
        VECHI, acest caz producea deja True (cheia gresita `stare_firma`
        lipsea -> `not stare_val` -> zombie necontitionat) — testul asta NU
        proveaza singur fix-ul, doar confirma ca noul cod nu a inversat
        comportamentul asteptat pt cazul 'activ'. Proba reala de
        non-vacuitate e testul urmator (`..._is_not_zombie`)."""
        from backend.agents.verification.scoring import calculate_risk_score
        result = calculate_risk_score(self._verified("INREGISTRAT din data 09.12.2009"))
        assert any("ZOMBIE" in text for text, _ in result["factors"])
        assert any("Firma zombie" in a for a in result["anomalies"])
        assert result["dimensions"]["operational"]["score"] == 10

    def test_explicit_radiata_status_is_not_zombie(self):
        """PROBA REALA de non-vacuitate: pe codul vechi (`stare_firma`
        niciodata scrisa in productie), acelasi input producea ZOMBIE=True
        gresit — carve-out-ul pt firme legal inchise era cod mort. Dupa fix,
        cheia corecta + matching pe substring detecteaza "RADIAT" in text
        si NU marcheaza zombie (presupunere NEVERIFICATA in productie —
        nicio firma radiata reala in DB la data fix-ului — dar format
        consistent cu cel confirmat pt statusuri active)."""
        from backend.agents.verification.scoring import calculate_risk_score
        result = calculate_risk_score(self._verified("RADIATA din data 01.01.2020"))
        assert not any("ZOMBIE" in text for text, _ in result["factors"])
        assert not any("Firma zombie" in a for a in result["anomalies"])

    def test_control_active_company_with_real_ca_unaffected(self):
        """Control: firma cu activitate reala (CA>0, angajati>0) nu intra
        deloc pe poarta CA=0+angajati=0 -> zombie detection complet ocolita,
        indiferent de textul de status."""
        from backend.agents.verification.scoring import calculate_risk_score
        result = calculate_risk_score(
            self._verified("INREGISTRAT din data 09.12.2009", ca=500_000, angajati=10)
        )
        assert not any("ZOMBIE" in text for text, _ in result["factors"])
        assert not any("Firma zombie" in a for a in result["anomalies"])

    def test_fallback_to_stare_onrc_when_anaf_value_is_none(self):
        """FIX 2026-07-16 (a treia capcana, gasita la review): `_make_field()`
        (agent_verification.py) produce un dict cu 4 chei (`value`/`trust`/
        `source`/`timestamp`) chiar si cand ANAF nu are camp de stare
        (`value=None`) -> acel dict e TRUTHY, deci un `or` pe DICT-uri brute
        (`company.get("stare_inregistrare") or company.get("stare_onrc")`)
        alege mereu primul si nu cade NICIODATA pe ONRC. Reachable: ANAF
        raspunde fara status, ONRC are status real -> ONRC era ignorat,
        firma etichetata ZOMBIE degeaba. Forma exacta a `value=None` de mai
        jos e cea produsa real de `_make_field(None, "ANAF")` (inspectata la
        sursa, nu inventata)."""
        from backend.agents.verification.scoring import calculate_risk_score
        verified = {
            "company": {
                "stare_inregistrare": {
                    "value": None, "trust": "OFICIAL", "source": "ANAF",
                    "timestamp": "2026-07-16T12:00:00+00:00",
                },
                "stare_onrc": {
                    "value": "RADIATA din data 01.01.2020", "trust": "OFICIAL", "source": "ONRC",
                    "timestamp": "2026-07-16T12:00:00+00:00",
                },
            },
            "financial": {
                "cifra_afaceri": {"value": 0},
                "numar_angajati": {"value": 0},
            },
        }
        result = calculate_risk_score(verified)
        assert not any("ZOMBIE" in text for text, _ in result["factors"])
        assert not any("Firma zombie" in a for a in result["anomalies"])
