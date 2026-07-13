"""
Test de caracterizare pentru `OfficialAgent.execute()` (Pas 0, refactor #1 --
vezi Roland_Opus_Sonnet.md 2026-07-14, PLAN aprobat de Opus).

De ce exista acest test: `execute()` are ~570 linii / ~20 blocuri secventiale, unele
cu dependinte reale de ordine (CRITICA #2: cui/company_name setate neconditionat dupa
ANAF; diagnostics calculat INAINTE de ultima sursa OSINT). O extractie in functii mai
mici trebuie sa produca EXACT acelasi dict de retur (`official_data` + `historical_flags`
+ `sources` + `current_step` + `progress`) sub orice combinatie de succes/esec a
surselor -- nu doar "nu arunca".

Compara intreg dict-ul de retur (nu doar cateva chei) fata de un golden snapshot
capturat pe codul dinaintea refactorului, pe 6 fixture-uri (2 branch-uri structurale
+ 4 combinatii de surse) definite in
`tests/fixtures/agent_official_characterization_inputs.py`.

Comparatia e byte-determinista (nu tolerabila la precizie ca la golden-ul de scoring)
-- toate dependintele externe sunt mockuite cu raspunsuri fixe si `datetime.now()`
e inghetat, deci NU exista non-determinism de absorbit.

Daca modifici intentionat un comportament (nu un refactor intern), regenereaza
golden-urile cu `python tools/generate_agent_official_golden.py` SI revizuieste
diff-ul manual inainte de commit.
"""
import json
from pathlib import Path

import pytest

from tests.fixtures.agent_official_characterization_inputs import (
    FIXTURES,
    run_execute_with_fixture,
)

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "agent_official_golden"


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
        f"`python tools/generate_agent_official_golden.py` (DOAR pe cod neatins/verificat manual)."
    )
    expected = json.loads(golden_path.read_text(encoding="utf-8"))

    actual = await run_execute_with_fixture(FIXTURES[fixture_name])
    actual_json = json.loads(json.dumps(actual, sort_keys=True, ensure_ascii=False))

    _assert_deep_equal(actual_json, expected)


def test_all_fixtures_have_golden_snapshot():
    for name in FIXTURES:
        golden_path = GOLDEN_DIR / f"{name}.json"
        assert golden_path.exists(), f"Golden snapshot lipsa pentru fixture-ul '{name}'"
