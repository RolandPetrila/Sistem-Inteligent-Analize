"""
Test de regresie: bug real gasit prin audit — `_calculate_compare_score`
(backend/routers/compare.py) citea `result.get("total_score", 70)`, dar
`calculate_risk_score()` (backend/agents/verification/scoring.py) nu
returneaza NICIODATA cheia "total_score" (returneaza "numeric_score").
Efect: Comparatorul afisa scor 70 fix pentru ORICE firma, dintotdeauna.

Acest test verifica cu date sintetice (structura reala, valori inventate —
repo public, zero date reale de firme terte) ca scorul:
  1. NU e mereu 70 (fallback-ul mort)
  2. difera intre o firma sanatoasa si una cu risc ridicat

Rulat pe codul dinaintea fix-ului (git stash), acest test PICA: ambele firme
primesc 70 (fallback declansat de KeyError implicit din .get() -> default).
"""
from backend.routers.compare import _calculate_compare_score


def _healthy_company() -> dict:
    return {
        "cifra_afaceri": 15_000_000,
        "profit_net": 1_800_000,
        "profit_brut": 2_000_000,
        "capitaluri": 6_000_000,
        "angajati": 45,
        "inactiv": False,
        "platitor_tva": True,
        "data_inregistrare": "2005-03-10",
        "stare": "ACTIVA",
    }


def _risky_company() -> dict:
    return {
        "cifra_afaceri": 40_000,
        "profit_net": -120_000,
        "profit_brut": -110_000,
        "capitaluri": -50_000,
        "angajati": 1,
        "inactiv": True,
        "platitor_tva": False,
        "data_inregistrare": "2025-01-05",
        "stare": "ACTIVA",
    }


class TestCalculateCompareScore:
    def test_scor_nu_e_mereu_70_fallback(self):
        healthy_score = _calculate_compare_score(_healthy_company())
        risky_score = _calculate_compare_score(_risky_company())

        assert healthy_score != 70, "scorul firmei sanatoase a picat pe fallback-ul mort (70)"
        assert risky_score != 70, "scorul firmei cu risc a picat pe fallback-ul mort (70)"

    def test_scor_difera_intre_firme_diferite(self):
        healthy_score = _calculate_compare_score(_healthy_company())
        risky_score = _calculate_compare_score(_risky_company())

        assert healthy_score != risky_score
        assert healthy_score > risky_score, (
            f"firma sanatoasa ({healthy_score}) ar trebui sa aiba scor mai mare "
            f"decat firma cu risc ridicat ({risky_score})"
        )

    def test_scor_coincide_cu_numeric_score_din_calculate_risk_score(self):
        """Legatura directa fix -> sursa: scorul returnat trebuie sa fie EXACT
        `numeric_score` din calculate_risk_score(), nu un camp inexistent."""
        from backend.agents.verification.scoring import calculate_risk_score

        company = _healthy_company()
        verified = {
            "financial": {
                "cifra_afaceri": {"value": company["cifra_afaceri"]},
                "profit_net": {"value": company["profit_net"]},
                "profit_brut": {"value": company["profit_brut"]},
                "capitaluri_proprii": {"value": company["capitaluri"]},
                "numar_mediu_salariati": {"value": company["angajati"]},
            },
            "risk": {
                "inactiv": {"value": company["inactiv"]},
                "platitor_tva": {"value": company["platitor_tva"]},
            },
            "company": {
                "data_inregistrare": {"value": company["data_inregistrare"]},
                "stare_inregistrare": {"value": company["stare"]},
            },
        }
        expected = calculate_risk_score(verified)["numeric_score"]
        actual = _calculate_compare_score(company)
        assert actual == expected
