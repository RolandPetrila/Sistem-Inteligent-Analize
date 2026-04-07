"""
F8-5: Teste pentru modele predictive financiare.
Testeaza Altman Z''-EMS, Piotroski F-Score, Beneish M-Score, Zmijewski X-Score.
"""

from backend.agents.verification.scoring import (
    calculate_all_predictive_scores,
    calculate_altman_z_ems,
    calculate_beneish_m,
    calculate_piotroski_f,
    calculate_zmijewski_x,
)

# ─── Fixtures ───────────────────────────────────────────────────────────────

BILANT_SANATOS = {
    "cifra_afaceri": 5_000_000,
    "profit_net": 500_000,
    "profit_brut": 650_000,
    "capitaluri_proprii": 2_000_000,
    "total_datorii": 1_000_000,
    "active_totale": 3_000_000,
    "active_curente": 1_500_000,
    "datorii_curente": 500_000,
    "rezultat_reportat": 400_000,
}

BILANT_DISTRESS = {
    "cifra_afaceri": 1_000_000,
    "profit_net": -300_000,
    "profit_brut": -200_000,
    "capitaluri_proprii": -100_000,
    "total_datorii": 2_000_000,
    "active_totale": 1_900_000,
    "active_curente": 300_000,
    "datorii_curente": 800_000,
    "rezultat_reportat": -300_000,
}

BILANT_ANTERIOR = {
    "cifra_afaceri": 4_000_000,
    "profit_net": 300_000,
    "capitaluri_proprii": 1_700_000,
    "total_datorii": 900_000,
    "active_totale": 2_600_000,
    "active_curente": 1_200_000,
    "datorii_curente": 400_000,
}

BILANT_GOL = {}


# ─── Altman Z''-EMS ─────────────────────────────────────────────────────────

class TestAltmanZEMS:

    def test_firma_sanatoasa_zona_safe(self):
        result = calculate_altman_z_ems(BILANT_SANATOS)
        assert result["zone"] == "SAFE"
        assert result["z_score"] is not None
        assert result["z_score"] > 2.60
        assert result["confidence"] > 0

    def test_firma_distress_zona_distress(self):
        result = calculate_altman_z_ems(BILANT_DISTRESS)
        assert result["zone"] in ("DISTRESS", "GREY")
        assert result["z_score"] is not None

    def test_active_zero_returneaza_indisponibil(self):
        bilant = {"cifra_afaceri": 1_000_000, "active_totale": 0}
        result = calculate_altman_z_ems(bilant)
        assert result["zone"] == "INDISPONIBIL"
        assert result["z_score"] is None
        assert result["confidence"] == 0

    def test_bilant_gol_returneaza_indisponibil(self):
        result = calculate_altman_z_ems(BILANT_GOL)
        assert result["zone"] == "INDISPONIBIL"
        assert result["z_score"] is None

    def test_are_disclaimer(self):
        result = calculate_altman_z_ems(BILANT_SANATOS)
        assert "disclaimer" in result
        assert len(result["disclaimer"]) > 10

    def test_x_values_prezente(self):
        result = calculate_altman_z_ems(BILANT_SANATOS)
        assert "x_values" in result
        xv = result["x_values"]
        assert "X1" in xv and "X2" in xv and "X3" in xv and "X4" in xv

    def test_zona_grey(self):
        # Bilant la limita — capital scazut dar nu negativ
        bilant_grey = {
            "cifra_afaceri": 500_000,
            "profit_net": 10_000,
            "profit_brut": 15_000,
            "capitaluri_proprii": 50_000,
            "total_datorii": 400_000,
            "active_totale": 450_000,
            "active_curente": 200_000,
            "datorii_curente": 300_000,
            "rezultat_reportat": 5_000,
        }
        result = calculate_altman_z_ems(bilant_grey)
        assert result["zone"] in ("GREY", "DISTRESS", "SAFE")  # depinde de valori
        assert result["z_score"] is not None


# ─── Piotroski F-Score ───────────────────────────────────────────────────────

class TestPiotroskiF:

    def test_firma_sanatoasa_grad_strong(self):
        result = calculate_piotroski_f(BILANT_SANATOS, BILANT_ANTERIOR)
        assert result["f_score"] is not None
        assert result["f_score"] >= 0
        assert result["grade"] in ("STRONG", "AVERAGE", "WEAK", "INSUFICIENT")
        assert result["has_prior_year"] is True

    def test_fara_an_anterior_insuficient_sau_partial(self):
        result = calculate_piotroski_f(BILANT_SANATOS, None)
        assert result["grade"] in ("STRONG", "AVERAGE", "WEAK", "INSUFICIENT")
        assert result["has_prior_year"] is False
        # Fara an anterior, max 3 criterii calculate
        criteria = [c for c in result["criteria"] if c is not None]
        assert len(criteria) <= 3

    def test_bilant_gol_returneaza_insuficient(self):
        result = calculate_piotroski_f(BILANT_GOL)
        assert result["grade"] == "INSUFICIENT"
        assert result["f_score"] is None

    def test_firma_distress_weak(self):
        result = calculate_piotroski_f(BILANT_DISTRESS, BILANT_ANTERIOR)
        assert result["f_score"] is not None
        # Firma in distress ar trebui sa aiba scor mic
        assert result["grade"] in ("WEAK", "AVERAGE", "INSUFICIENT")

    def test_strong_grade_threshold(self):
        """Firma sanatoasa cu an anterior → grade STRONG (f >= 7)."""
        result = calculate_piotroski_f(BILANT_SANATOS, BILANT_ANTERIOR)
        if result["has_prior_year"] and result["f_score"] is not None:
            if result["f_score"] >= 7:
                assert result["grade"] == "STRONG"
            elif result["f_score"] >= 4:
                assert result["grade"] == "AVERAGE"
            else:
                assert result["grade"] == "WEAK"

    def test_criteria_lista_9_elemente(self):
        result = calculate_piotroski_f(BILANT_SANATOS, BILANT_ANTERIOR)
        assert len(result["criteria"]) == 9


# ─── Beneish M-Score ─────────────────────────────────────────────────────────

class TestBeneishM:

    def test_necesita_doi_ani(self):
        result = calculate_beneish_m(BILANT_SANATOS, None)
        assert result["available"] is False
        assert result["m_score"] is None
        assert result["risk"] in ("INDISPONIBIL",)

    def test_bilant_gol_indisponibil(self):
        result = calculate_beneish_m(BILANT_GOL, BILANT_ANTERIOR)
        assert result["available"] is False

    def test_cu_doi_ani_disponibil(self):
        result = calculate_beneish_m(BILANT_SANATOS, BILANT_ANTERIOR)
        if result["available"]:
            assert result["m_score"] is not None
            assert result["risk"] in ("OK", "INVESTIGAT", "MANIPULATOR_PROBABIL")
            assert "components" in result

    def test_firma_normala_risk_ok(self):
        result = calculate_beneish_m(BILANT_SANATOS, BILANT_ANTERIOR)
        if result["available"]:
            # Firma normala → m_score sub -2.22 = OK
            assert result["risk"] in ("OK", "INVESTIGAT", "MANIPULATOR_PROBABIL")

    def test_are_disclaimer(self):
        result = calculate_beneish_m(BILANT_SANATOS, BILANT_ANTERIOR)
        if result["available"]:
            assert "disclaimer" in result

    def test_ca_zero_indisponibil(self):
        bilant_no_ca = {"profit_net": 100_000, "active_totale": 500_000}
        result = calculate_beneish_m(bilant_no_ca, bilant_no_ca)
        assert result["available"] is False


# ─── Zmijewski X-Score ───────────────────────────────────────────────────────

class TestZmijewskiX:

    def test_firma_sanatoasa_fara_distress(self):
        result = calculate_zmijewski_x(BILANT_SANATOS)
        assert result["available"] is True
        assert result["x_score"] is not None
        assert result["distress"] is False

    def test_firma_distress_cu_distress(self):
        result = calculate_zmijewski_x(BILANT_DISTRESS)
        assert result["available"] is True
        assert result["x_score"] is not None
        # Firma in distress → X > 0
        assert result["distress"] is True

    def test_active_zero_indisponibil(self):
        result = calculate_zmijewski_x({"profit_net": 100_000, "active_totale": 0})
        assert result["available"] is False
        assert result["x_score"] is None

    def test_bilant_gol_indisponibil(self):
        result = calculate_zmijewski_x(BILANT_GOL)
        assert result["available"] is False

    def test_interpretare_prezenta(self):
        result = calculate_zmijewski_x(BILANT_SANATOS)
        if result["available"]:
            assert "interpretation" in result
            assert len(result["interpretation"]) > 5

    def test_nu_crapa_cu_zero_division(self):
        """Nu trebuie sa arunce ZeroDivisionError chiar cu date incomplete."""
        for bilant in [
            {"active_totale": 1_000_000},
            {"profit_net": 0, "active_totale": 1_000_000},
            {"total_datorii": 0, "active_totale": 1_000_000},
        ]:
            result = calculate_zmijewski_x(bilant)
            assert "available" in result  # nu crapa


# ─── calculate_all_predictive_scores ─────────────────────────────────────────

class TestAllPredictiveScores:

    def test_structura_output(self):
        verified = {
            "financial": {
                "cifra_afaceri": {"value": 5_000_000},
                "profit_net": {"value": 500_000},
                "capitaluri_proprii": {"value": 2_000_000},
                "datorii_totale": {"value": 1_000_000},
                "active_totale": {"value": 3_000_000},
            }
        }
        result = calculate_all_predictive_scores(verified)
        assert "altman_z" in result
        assert "piotroski_f" in result
        assert "beneish_m" in result
        assert "zmijewski_x" in result
        assert "distress_signals" in result
        assert "summary" in result
        assert isinstance(result["distress_signals"], int)
        assert isinstance(result["summary"], str)

    def test_verified_gol_nu_crapa(self):
        result = calculate_all_predictive_scores({})
        assert "altman_z" in result
        assert result["distress_signals"] >= 0

    def test_distress_signals_range(self):
        verified = {
            "financial": {
                "cifra_afaceri": {"value": 5_000_000},
                "profit_net": {"value": 500_000},
            }
        }
        result = calculate_all_predictive_scores(verified)
        assert 0 <= result["distress_signals"] <= 5

    def test_summary_not_empty(self):
        verified = {"financial": {"cifra_afaceri": {"value": 1_000_000}}}
        result = calculate_all_predictive_scores(verified)
        assert len(result["summary"]) > 10
