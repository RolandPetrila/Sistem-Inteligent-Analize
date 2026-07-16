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

FIX 2026-07-16: al doilea bug de granita, gasit in ACELASI `_calculate_compare_score` —
scria `verified["financial"]["numar_mediu_salariati"]`, dar consumatorul canonic
`_score_operational` (scoring.py) citeste `financial["numar_angajati"]`. Efect: dimensiunea
operationala (15% din scor) era oarba la angajati pentru ORICE firma comparata — vezi
`TestCompareScoreAngajatiiContract` mai jos. `numar_mediu_salariati` din testul de echivalenta
de mai jos (linia cu "numar_angajati" acum) a fost aliniat la acelasi fix — inainte,
testul isi construia manual acelasi `verified` cu ACEEASI cheie gresita ca si codul,
deci cele doua se confirmau reciproc fara sa prinda bug-ul (clasa de bug documentata in
CLAUDE.md: fixture-urile codifica aceeasi presupunere gresita ca si codul).
"""
from backend.agents.verification.scoring import risk_bucket
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
                "numar_angajati": {"value": company["angajati"]},
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


class TestCompareScoreAngajatiiContract:
    """FIX 2026-07-16: `_calculate_compare_score` scria cheia `numar_mediu_salariati`
    in `verified["financial"]`, dar `_score_operational` (scoring.py) citeste
    `numar_angajati`. Efect: dimensiunea operationala (15% din scor) era mereu
    oarba la angajati pe calea Comparatorului — bonusul "forta de munca
    semnificativa" nu se aplica NICIODATA, indiferent de firma.

    Datele de mai jos au fost alese prin RULARE reala (nu calcul mental) astfel
    incat bug-ul sa produca un flip de culoare vizibil pentru utilizator:
    Galben (69.7, <70) pe codul vechi vs Verde (72.8, >=70) cu cheia corecta.
    """

    @staticmethod
    def _company_pe_granita_verde() -> dict:
        return {
            "cifra_afaceri": 8_000_000,
            "profit_net": 100_000,
            "profit_brut": 150_000,
            "capitaluri": 2_000_000,
            "angajati": 9_000,
            "inactiv": False,
            "platitor_tva": True,
            "data_inregistrare": "2015-05-10",
            "stare": "ACTIVA",
        }

    def test_angajatii_trec_pragul_de_culoare_verde(self):
        """PICA pe codul vechi (`numar_mediu_salariati`): scorul ramane 69.7 /
        Galben, pentru ca bonusul de angajati nu ajunge niciodata la scoring.
        Cu cheia corecta (`numar_angajati`), bonusul se aplica si scorul trece
        la 72.8 / Verde — exact flip-ul vizibil in Comparator."""
        company = self._company_pe_granita_verde()
        score = _calculate_compare_score(company)

        assert score >= 70, (
            f"scor {score} sub pragul Verde — dimensiunea operationala nu vede "
            f"angajatii (cheia scrisa de compare.py nu coincide cu cea citita "
            f"de _score_operational din scoring.py)"
        )
        assert risk_bucket(score) == "Verde", (
            f"culoare {risk_bucket(score)} in loc de Verde — bug-ul de cheie "
            f"'numar_mediu_salariati' vs 'numar_angajati' schimba culoarea "
            f"afisata utilizatorului in Comparator"
        )
