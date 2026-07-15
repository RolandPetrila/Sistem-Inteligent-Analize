"""Tests for detect_early_warnings — F13/DF5, regression for the reinvived
'pierdere consecutiva' path (2026-07-16).

Context: pana la fix-ul commit 9324e0a, `profit_net` era mereu 0 si
`pierdere_neta` mereu None pentru firmele pe pierdere (bug separat, reparat
azi). `is_loss` (linia 49 din early_warnings.py) era deci mereu False, iar
blocul "Pierdere consecutiva 2+ ani" (liniile 54-70) nu rulase NICIODATA cu
succes. Fix-ul de azi a reinviat acea cale — care era rupta: `loss_years`
contine ANI (int, chei din `bilant.get("data", {})`), dar codul facea
`', '.join(loss_years[...])`, ceea ce cere STRING-uri -> TypeError garantat
pe orice firma reala pe pierdere 2+ ani consecutivi (dovedit live pe job
real, CUI 477647 / TAROM).
"""

from backend.agents.verification.early_warnings import detect_early_warnings


def _bilant(years_data: dict) -> dict:
    """Construieste shape-ul REAL emis de anaf_bilant_client.get_bilant_multi_year:
    official['financial_official']['data'] = {year(int): {...}}."""
    return {"financial_official": {"data": years_data}}


class TestConsecutiveLossWarning:
    """Fixture 100% sintetica (repo public) — cifre inventate, forma reala
    (chei int, profit_net negativ)."""

    def test_two_consecutive_loss_years_no_typeerror(self):
        official = _bilant({
            2021: {"cifra_afaceri_neta": 500_000, "profit_net": -50_000},
            2022: {"cifra_afaceri_neta": 480_000, "profit_net": -80_000},
        })

        warnings = detect_early_warnings(official)

        loss_warnings = [w for w in warnings if w["signal"] == "Pierdere consecutiva 2+ ani"]
        assert len(loss_warnings) == 1
        assert loss_warnings[0]["severity"] == "HIGH"
        assert loss_warnings[0]["detail"] == "Pierdere neta in anii: 2021, 2022"
        assert loss_warnings[0]["years"] == "2021-2022"

    def test_three_consecutive_loss_years_via_pierdere_neta_field(self):
        """Acopera si campul `pierdere_neta` (nu doar profit_net negativ) —
        cealalta ramura a `is_loss` (linia 49)."""
        official = _bilant({
            2020: {"cifra_afaceri_neta": 1_000_000, "pierdere_neta": 20_000},
            2021: {"cifra_afaceri_neta": 900_000, "pierdere_neta": 60_000},
            2022: {"cifra_afaceri_neta": 850_000, "pierdere_neta": 90_000},
        })

        warnings = detect_early_warnings(official)

        loss_warnings = [w for w in warnings if w["signal"] == "Pierdere consecutiva 2+ ani"]
        assert len(loss_warnings) == 1
        assert loss_warnings[0]["detail"] == "Pierdere neta in anii: 2020, 2021, 2022"
        assert loss_warnings[0]["years"] == "2020-2022"

    def test_loss_streak_ending_before_last_year_still_detected(self):
        """Streak-ul de pierdere NU e ultimii ani din serie — verifica ramura
        din interiorul buclei (linia 54-60), nu doar coada post-bucla."""
        official = _bilant({
            2020: {"cifra_afaceri_neta": 500_000, "profit_net": -10_000},
            2021: {"cifra_afaceri_neta": 520_000, "profit_net": -5_000},
            2022: {"cifra_afaceri_neta": 700_000, "profit_net": 30_000},
        })

        warnings = detect_early_warnings(official)

        loss_warnings = [w for w in warnings if w["signal"] == "Pierdere consecutiva 2+ ani"]
        assert len(loss_warnings) == 1
        assert loss_warnings[0]["detail"] == "Pierdere neta in anii: 2020, 2021"
        assert loss_warnings[0]["years"] == "2020-2021"

    def test_single_loss_year_not_flagged(self):
        official = _bilant({
            2021: {"cifra_afaceri_neta": 500_000, "profit_net": 10_000},
            2022: {"cifra_afaceri_neta": 480_000, "profit_net": -5_000},
        })

        warnings = detect_early_warnings(official)

        assert not any(w["signal"] == "Pierdere consecutiva 2+ ani" for w in warnings)
