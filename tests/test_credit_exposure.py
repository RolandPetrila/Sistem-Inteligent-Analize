"""
P1-4: Teste pentru Bonitate & Expunere comerciala recomandata (RON).
Metrica derivata, determinista (ZERO LLM) — verifica formula (media a 3
metode de trade-credit), multiplicatorul de culoare si cele 3 kill-switch-uri
(inactiv ANAF / insolventa BPI / Altman DISTRESS).
"""

from backend.agents.verification.credit_exposure import commercial_exposure_ron


def _field(value):
    return {"value": value}


def _verified(
    ca=None,
    profit=None,
    capitaluri=None,
    color="Verde",
    inactiv=False,
    insolventa=False,
    altman_zone="SAFE",
):
    financial = {}
    if ca is not None:
        financial["cifra_afaceri"] = _field(ca)
    if profit is not None:
        financial["profit_net"] = _field(profit)
    if capitaluri is not None:
        financial["capitaluri_proprii"] = _field(capitaluri)

    return {
        "financial": financial,
        "risk": {
            "anaf_inactive": _field(inactiv),
            "bpi_insolventa": _field({"found": insolventa}),
        },
        "risk_score": {"score": color},
        "predictive_scores": {"altman_z": {"zone": altman_zone}},
    }


class TestAllMethodsAvailable:
    def test_three_methods_average(self):
        # m1 = 0.10*(1_200_000/12) = 10_000
        # m2 = 0.10*500_000 = 50_000
        # m3 = 0.50*100_000 = 50_000
        # base = 110_000/3 = 36_666.67 ; mult(Verde)=1.0 -> round(-2) = 36_700
        verified = _verified(ca=1_200_000, profit=100_000, capitaluri=500_000, color="Verde")
        result = commercial_exposure_ron(verified)
        assert result["metode_folosite"] == 3
        assert result["expunere_ron"] == 36_700
        assert result["kill_switch"] is False
        assert result["disclaimer"]
        assert "medie" in result["formula"]


class TestSingleMethod:
    def test_only_ca_when_profit_negative_and_capital_missing(self):
        # profit negativ (exclus, nu >0) + capitaluri lipsa -> doar metoda 1
        # m1 = 0.10*(1_200_000/12) = 10_000 ; mult(Galben)=0.5 -> 5_000
        verified = _verified(ca=1_200_000, profit=-5_000, capitaluri=None, color="Galben")
        result = commercial_exposure_ron(verified)
        assert result["metode_folosite"] == 1
        assert result["expunere_ron"] == 5_000
        assert result["kill_switch"] is False


class TestKillSwitch:
    """Baseline (fara kill-switch) ar da 36_700 RON — fiecare trigger, izolat, trebuie sa anuleze la 0."""

    def test_inactiv_anaf_zeroes_exposure(self):
        verified = _verified(ca=1_200_000, profit=100_000, capitaluri=500_000, color="Verde", inactiv=True)
        result = commercial_exposure_ron(verified)
        assert result["expunere_ron"] == 0
        assert result["kill_switch"] is True
        assert "inactiva" in result["formula"].lower()

    def test_insolventa_bpi_zeroes_exposure(self):
        verified = _verified(ca=1_200_000, profit=100_000, capitaluri=500_000, color="Verde", insolventa=True)
        result = commercial_exposure_ron(verified)
        assert result["expunere_ron"] == 0
        assert result["kill_switch"] is True
        assert "insolventa" in result["formula"].lower()

    def test_altman_distress_zeroes_exposure(self):
        verified = _verified(ca=1_200_000, profit=100_000, capitaluri=500_000, color="Verde", altman_zone="DISTRESS")
        result = commercial_exposure_ron(verified)
        assert result["expunere_ron"] == 0
        assert result["kill_switch"] is True
        assert "distress" in result["formula"].lower()

    def test_kill_switch_does_not_touch_scoring_inputs(self):
        """Kill-switch anuleaza DOAR expunerea, nu are voie sa modifice verified["risk_score"]."""
        verified = _verified(ca=1_200_000, profit=100_000, capitaluri=500_000, color="Verde", inactiv=True)
        before = dict(verified["risk_score"])
        commercial_exposure_ron(verified)
        assert verified["risk_score"] == before


class TestNoDataAvailable:
    def test_all_missing_gives_zero(self):
        verified = _verified(ca=None, profit=None, capitaluri=None, color="Rosu")
        result = commercial_exposure_ron(verified)
        assert result["metode_folosite"] == 0
        assert result["expunere_ron"] == 0
        assert result["kill_switch"] is False

    def test_zero_values_excluded_same_as_missing(self):
        verified = _verified(ca=0, profit=0, capitaluri=0, color="Verde")
        result = commercial_exposure_ron(verified)
        assert result["metode_folosite"] == 0
        assert result["expunere_ron"] == 0


class TestRounding:
    def test_rounds_to_nearest_100(self):
        # m1 = 0.10*(123_456/12) = 1_028.8 ; mult(Verde)=1.0 -> round(-2) = 1_000
        verified = _verified(ca=123_456, color="Verde")
        result = commercial_exposure_ron(verified)
        assert result["metode_folosite"] == 1
        assert result["expunere_ron"] == 1_000
        assert result["expunere_ron"] % 100 == 0
