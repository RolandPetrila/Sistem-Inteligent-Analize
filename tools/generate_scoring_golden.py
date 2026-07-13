"""
Genereaza (sau regenereaza) golden snapshot-urile pentru `calculate_risk_score`
(Pas 0, PLAN_REFACTOR_SCORING_2026-07-13.md).

Ruleaza `calculate_risk_score()` DIN CODUL CURENT pe fiecare fixture din
`tests/fixtures/scoring_golden_inputs.py`, cu `date.today()` fixata (altfel
company_age_years driftuieste odata cu trecerea timpului, independent de orice
schimbare de cod), si salveaza output-ul complet ca JSON (chei sortate) in
`tests/fixtures/scoring_golden/<nume>.json`.

Foloseste-l DOAR:
- acum, o singura data, pe codul NEATINS (Pas 0) — pentru a stabili baseline-ul.
- daca in viitor se schimba intentionat o regula de business (nu un refactor
  intern) — caz in care golden-urile TREBUIE regenerate si diff-ul revizuit
  manual inainte de commit, ca sa confirmi ca schimbarea de scor e intentionata.

NU il rula in timpul refactorului de extragere (Optiunea A) — scopul acelui
refactor e ca golden-urile sa ramana IDENTICE fara regenerare.
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.agents.verification.scoring import calculate_risk_score  # noqa: E402
from tests.fixtures.scoring_golden_inputs import FIXED_REF_DATE, FIXTURES  # noqa: E402

OUTPUT_DIR = ROOT / "tests" / "fixtures" / "scoring_golden"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with patch("backend.agents.verification.scoring.date") as mock_date:
        mock_date.today.return_value = FIXED_REF_DATE
        for name, verified in FIXTURES.items():
            result = calculate_risk_score(verified)
            out_path = OUTPUT_DIR / f"{name}.json"
            out_path.write_text(
                json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"[golden] {name} -> {out_path.relative_to(ROOT)} "
                  f"(score={result.get('score')}, numeric={result.get('numeric_score')})")

    print(f"\n{len(FIXTURES)} golden snapshot-uri generate in {OUTPUT_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
