"""
Genereaza (sau regenereaza) golden snapshot-urile pentru `OfficialAgent.execute()`
(Pas 0, refactor #1 -- vezi Roland_Opus_Sonnet.md 2026-07-14).

Ruleaza execute() DIN CODUL CURENT pe fiecare fixture din
`tests/fixtures/agent_official_characterization_inputs.py`, cu toate dependintele
externe mockuite (fara retea/DB reala, `datetime.now()` inghetat), si salveaza
output-ul complet ca JSON (chei sortate) in
`tests/fixtures/agent_official_golden/<nume>.json`.

Foloseste-l DOAR:
- acum, o singura data, pe codul NEATINS (Pas 0) -- pentru a stabili baseline-ul.
- daca in viitor se schimba intentionat un comportament (nu un refactor intern) --
  caz in care golden-urile TREBUIE regenerate si diff-ul revizuit manual inainte
  de commit.

NU il rula in timpul extractiei (Faza A/B/C/D) -- scopul e ca golden-urile sa
ramana IDENTICE fara regenerare.
"""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures.agent_official_characterization_inputs import (  # noqa: E402
    FIXTURES,
    run_execute_with_fixture,
)

OUTPUT_DIR = ROOT / "tests" / "fixtures" / "agent_official_golden"


async def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for name, fixture in FIXTURES.items():
        result = await run_execute_with_fixture(fixture)
        out_path = OUTPUT_DIR / f"{name}.json"
        out_path.write_text(
            json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        completeness = result.get("official_data", {}).get("diagnostics", {}).get("completeness_score")
        print(f"[golden] {name} -> {out_path.relative_to(ROOT)} (completeness={completeness})")

    print(f"\n{len(FIXTURES)} golden snapshot-uri generate in {OUTPUT_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    asyncio.run(main())
