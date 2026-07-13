"""
Golden snapshot / characterization test pentru `calculate_risk_score`
(Pas 0, PLAN_REFACTOR_SCORING_2026-07-13.md — CRITICA #4 din audit).

De ce exista acest test separat de `test_scoring.py`:
`test_scoring.py` are 27 teste dar acopera doar 39% din liniile scoring.py
(verificat cu --cov-report=term-missing) — ramuri intregi (trend decomposition,
solvency matrix, zombie detection, early warnings, Portal Just SOAP, Monitorul
Oficial) nu sunt atinse de niciun test. Un refactor care sparge una din acele
ramuri ar trece testele existente oricum.

Acest test compara INTREG dict-ul de retur (nu doar {score, color}) pe 6
fixture-uri care acopera deliberat acele ramuri, fata de un golden snapshot
capturat pe codul dinaintea refactorului. Bug-urile din clasa `litigation`
(UnboundLocalError reparat 2026-07-13) nu sunt vizibile in scorul final — sunt
in blocurile derivate (confidence per dimensiune, zombie, anomalies,
early_warnings) pe care le compara explicit acest test.

Comparatia e tolerabila la precizie de float (round la 6 zecimale), nu la
octet — daca refactorul reordoneaza o suma de float-uri fara sa schimbe
rezultatul vizibil, testul tot trece. O diferenta reala de scor (ex: o
dimensiune calculata gresit) tot pica testul, pentru ca depaseste orice
zgomot de virgula mobila.

Daca modifici intentionat o regula de business (nu un refactor intern),
regenereaza golden-urile cu `python tools/generate_scoring_golden.py` SI
revizuieste diff-ul manual inainte de commit, ca sa confirmi ca schimbarea
de scor e intentionata.
"""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.agents.verification.scoring import calculate_risk_score
from tests.fixtures.scoring_golden_inputs import FIXED_REF_DATE, FIXTURES

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "scoring_golden"

FLOAT_TOLERANCE_NDIGITS = 6


def _assert_deep_equal(actual, expected, path: str = "$") -> None:
    """Compara recursiv doua structuri dict/list/scalar. Float-urile se
    compara rotunjite (nu byte-cu-byte), ca sa absoarba reordonari benigne
    de aritmetica in virgula mobila introduse de refactor."""
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{path}: asteptat dict, primit {type(actual)}"
        assert actual.keys() == expected.keys(), (
            f"{path}: chei diferite — lipsesc {expected.keys() - actual.keys()}, "
            f"in plus {actual.keys() - expected.keys()}"
        )
        for key in expected:
            _assert_deep_equal(actual[key], expected[key], f"{path}.{key}")
    elif isinstance(expected, list):
        # `risk_factors` sunt tuple Python in memorie ((text, severity)) dar
        # devin liste dupa round-trip JSON in golden — acceptam ambele
        # containere de secventa, contractul real e ordinea+continutul, nu tipul.
        assert isinstance(actual, (list, tuple)), f"{path}: asteptat list/tuple, primit {type(actual)}"
        assert len(actual) == len(expected), (
            f"{path}: lungime diferita — asteptat {len(expected)}, primit {len(actual)}"
        )
        for i, (a_item, e_item) in enumerate(zip(actual, expected)):
            _assert_deep_equal(a_item, e_item, f"{path}[{i}]")
    elif isinstance(expected, float) or isinstance(actual, float):
        assert round(float(actual), FLOAT_TOLERANCE_NDIGITS) == round(float(expected), FLOAT_TOLERANCE_NDIGITS), (
            f"{path}: float diferit — asteptat {expected}, primit {actual}"
        )
    else:
        assert actual == expected, f"{path}: asteptat {expected!r}, primit {actual!r}"


@pytest.fixture(autouse=True)
def _frozen_reference_date():
    """Fixeaza date.today() folosit de company_age_years — altfel golden
    snapshot-urile ar driftui zilnic independent de orice schimbare de cod."""
    with patch("backend.agents.verification.scoring.date") as mock_date:
        mock_date.today.return_value = FIXED_REF_DATE
        yield


@pytest.mark.parametrize("fixture_name", sorted(FIXTURES.keys()))
def test_scoring_matches_golden_snapshot(fixture_name):
    golden_path = GOLDEN_DIR / f"{fixture_name}.json"
    assert golden_path.exists(), (
        f"Golden snapshot lipsa pentru '{fixture_name}' — ruleaza "
        f"`python tools/generate_scoring_golden.py` (DOAR pe cod neatins/verificat manual)."
    )
    expected = json.loads(golden_path.read_text(encoding="utf-8"))
    actual = calculate_risk_score(FIXTURES[fixture_name])
    _assert_deep_equal(actual, expected)


def test_all_fixtures_have_golden_snapshot():
    """Sanity check: fiecare fixture din scoring_golden_inputs.py are un JSON asociat."""
    missing = [name for name in FIXTURES if not (GOLDEN_DIR / f"{name}.json").exists()]
    assert not missing, f"Fixture-uri fara golden snapshot: {missing}"
