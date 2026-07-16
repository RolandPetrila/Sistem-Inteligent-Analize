"""
Genereaza (sau regenereaza) golden snapshot-urile pentru `VerificationAgent.execute()`
(Pas 0, refactor #2 -- vezi brief Roland_Opus_Sonnet.md 2026-07-16, acelasi tipar ca
`tools/generate_agent_official_golden.py`).

Ruleaza execute() DIN CODUL CURENT pe fiecare fixture din
`tests/fixtures/agent_verification_characterization_inputs.py`, cu toate
dependintele I/O mockuite (fara retea/DB reala, `datetime.now()`/`date.today()`
inghetate), si salveaza output-ul complet ca JSON (chei sortate) in
`tests/fixtures/agent_verification_golden/<nume>.json`.

Foloseste-l DOAR:
- acum, o singura data, pe codul NEATINS (Pas 0) -- pentru a stabili baseline-ul.
- daca in viitor se schimba intentionat un comportament (nu un refactor intern) --
  caz in care golden-urile TREBUIE regenerate si diff-ul revizuit manual inainte
  de commit.

NU il rula in timpul extractiei -- scopul e ca golden-urile sa ramana IDENTICE
fara regenerare.
"""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures.agent_verification_characterization_inputs import (  # noqa: E402
    FIXTURES,
    run_execute_with_fixture,
)

OUTPUT_DIR = ROOT / "tests" / "fixtures" / "agent_verification_golden"


async def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for name in FIXTURES:
        result = await run_execute_with_fixture(name)
        out_path = OUTPUT_DIR / f"{name}.json"
        out_path.write_text(
            json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        vd = result.get("verified_data", {})
        print(
            f"[golden] {name} -> {out_path.relative_to(ROOT)} "
            f"(risk_score={vd.get('risk_score', {}).get('score')}, "
            f"completeness={vd.get('completeness', {}).get('score')}%)"
        )

    print(f"\n{len(FIXTURES)} golden snapshot-uri generate in {OUTPUT_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    asyncio.run(main())
