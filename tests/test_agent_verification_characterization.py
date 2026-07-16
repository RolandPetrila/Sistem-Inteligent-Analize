"""
Test de caracterizare pentru `VerificationAgent.execute()` (Pas 0, refactor #2 --
vezi brief Roland_Opus_Sonnet.md 2026-07-16, acelasi tipar ca
`tests/test_agent_official_characterization.py`).

De ce exista acest test: `execute()` are ~240 linii / peste 30 blocuri secventiale
(mult mai multe decat cele ~10 asumate initial de brief -- vezi harta reala in
raportul de refactor), unele cu dependinte reale de ordine (orphan fields cablate
DUPA risk_score ca sa nu schimbe prefixul JSON trunchiat de synthesis; diagnostics
propagat DUPA osint_historical). O extractie in functii/dataclass-uri mai mici
trebuie sa produca EXACT acelasi dict `verified_data` sub orice combinatie de surse
prezente/absente -- nu doar "nu arunca".

Compara intreg dict-ul de retur (nu doar risk_score/completeness) fata de un golden
snapshot capturat pe codul dinaintea refactorului, pe 4 fixture-uri (surse complet
absente, happy path complet + LEAD_GENERATION, fallback-uri Tavily/listafirme,
caz adversarial concentrat de anomalii + praguri dinamice pe calea score-proxy)
definite in `tests/fixtures/agent_verification_characterization_inputs.py`.

Comparatia e byte-determinista -- toate dependintele I/O sunt mockuite cu raspunsuri
fixe si `datetime.now()`/`date.today()` sunt inghetate, deci NU exista non-determinism
de absorbit.

Daca modifici intentionat un comportament (nu un refactor intern), regenereaza
golden-urile cu `python tools/generate_agent_verification_golden.py` SI
revizuieste diff-ul manual inainte de commit.
"""
import json
from pathlib import Path

import pytest

from tests.fixtures.agent_verification_characterization_inputs import (
    FIXTURES,
    run_execute_with_fixture,
)

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "agent_verification_golden"


def _assert_deep_equal(actual, expected, path: str = "$") -> None:
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{path}: asteptat dict, primit {type(actual)}"
        assert actual.keys() == expected.keys(), (
            f"{path}: chei diferite -- lipsesc {expected.keys() - actual.keys()}, "
            f"in plus {actual.keys() - expected.keys()}"
        )
        for key in expected:
            _assert_deep_equal(actual[key], expected[key], f"{path}.{key}")
    elif isinstance(expected, list):
        assert isinstance(actual, (list, tuple)), f"{path}: asteptat list/tuple, primit {type(actual)}"
        assert len(actual) == len(expected), (
            f"{path}: lungime diferita -- asteptat {len(expected)}, primit {len(actual)}"
        )
        for i, (a_item, e_item) in enumerate(zip(actual, expected)):
            _assert_deep_equal(a_item, e_item, f"{path}[{i}]")
    else:
        assert actual == expected, f"{path}: asteptat {expected!r}, primit {actual!r}"


@pytest.mark.parametrize("fixture_name", sorted(FIXTURES.keys()))
@pytest.mark.asyncio
async def test_execute_matches_golden_snapshot(fixture_name):
    golden_path = GOLDEN_DIR / f"{fixture_name}.json"
    assert golden_path.exists(), (
        f"Golden snapshot lipsa pentru '{fixture_name}' -- ruleaza "
        f"`python tools/generate_agent_verification_golden.py` (DOAR pe cod neatins/verificat manual)."
    )
    expected = json.loads(golden_path.read_text(encoding="utf-8"))

    actual = await run_execute_with_fixture(fixture_name)
    actual_json = json.loads(json.dumps(actual, sort_keys=True, ensure_ascii=False, default=str))

    _assert_deep_equal(actual_json, expected)


def test_all_fixtures_have_golden_snapshot():
    for name in FIXTURES:
        golden_path = GOLDEN_DIR / f"{name}.json"
        assert golden_path.exists(), f"Golden snapshot lipsa pentru fixture-ul '{name}'"
