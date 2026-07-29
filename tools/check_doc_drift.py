"""Garda de DOC-DRIFT (CERINTA #16 E3, directiva proprietar doc-currency).

Avertizeaza cand un ciclu de lucru schimba COD (backend/*.py, frontend/src/*) dar NU
actualizeaza niciun doc-cheie (CLAUDE.md, TODO_ROLAND.md, docs/FUNCTII_SISTEM.md, ...).
Scopul: disciplina „docurile mereu la zi" devine parte din workflow, semnalata mecanic —
NU un generator automat de proza (statusul se scrie cu judecata, R3).

Design (per advisor): logica de decizie e o FUNCTIE PURA `doc_drift_verdict(changed_paths)`,
testabila pe liste sintetice, fara sa atinga git. CLI-ul de mai jos e doar un wrapper care
extrage caile schimbate dintr-un range git si cheama functia pura.

Utilizare:
    python tools/check_doc_drift.py                 # working tree + staged vs HEAD (ciclu curent)
    python tools/check_doc_drift.py HEAD~1..HEAD     # un range deja comis
    python tools/check_doc_drift.py --strict         # exit 1 la drift (implicit: exit 0 = doar avertizare)

Iesire: cod 0 daca nu e drift SAU nu e --strict; cod 1 doar cu --strict si drift detectat.
Gandit sa fie apelat NON-fatal din RIS_TEST.bat (avertizare), sau ca gate in CI cu --strict.
"""
import subprocess
import sys

# Docurile-cheie a caror actualizare "acopera" o schimbare de cod in acelasi ciclu.
DOC_FILES = frozenset({
    "CLAUDE.md", "TODO_ROLAND.md", "docs/FUNCTII_SISTEM.md", "README.md", "START_PWA.md",
})


def _is_test_path(p: str) -> bool:
    base = p.rsplit("/", 1)[-1]
    return (
        p.startswith("tests/") or "/tests/" in p
        or base.startswith("test_") or base.endswith(("_test.py", ".test.ts", ".test.tsx"))
    )


def is_code_path(p: str) -> bool:
    """Sursa de PRODUCTIE care ar trebui reflectata in doc (exclude testele)."""
    p = p.replace("\\", "/")
    if _is_test_path(p):
        return False
    if p.startswith("backend/") and p.endswith(".py"):
        return True
    return p.startswith("frontend/src/") and p.endswith((".ts", ".tsx"))


def doc_drift_verdict(changed_paths) -> dict:
    """Functie PURA: lista de cai schimbate -> verdict de doc-drift.

    drift = s-a schimbat cod de productie DAR niciun doc-cheie. Testele si docurile
    non-cheie nu conteaza in niciun sens.
    """
    norm = [str(p).replace("\\", "/") for p in changed_paths]
    code_files = sorted({p for p in norm if is_code_path(p)})
    doc_changed = any(p in DOC_FILES for p in norm)
    code_changed = bool(code_files)
    drift = code_changed and not doc_changed
    if drift:
        msg = (
            "DOC-DRIFT: s-a schimbat cod de productie fara actualizarea niciunui doc-cheie "
            f"({', '.join(sorted(DOC_FILES))}). Fisiere cod: {', '.join(code_files)}."
        )
    elif code_changed:
        msg = "OK: cod schimbat SI doc-cheie actualizat in acelasi ciclu."
    else:
        msg = "OK: niciun cod de productie schimbat (sau doar teste/docuri non-cheie)."
    return {"drift": drift, "code_changed": code_changed, "doc_changed": doc_changed,
            "code_files": code_files, "message": msg}


def _changed_paths_from_git(rng: str | None) -> list[str]:
    if rng:
        args = ["git", "diff", "--name-only", rng]
    else:
        # working tree + staged vs HEAD = ciclul curent, inainte de commit
        args = ["git", "diff", "--name-only", "HEAD"]
    out = subprocess.run(args, capture_output=True, text=True, check=False)
    return [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]


def main(argv: list[str]) -> int:
    strict = "--strict" in argv
    rng = next((a for a in argv if not a.startswith("-")), None)
    verdict = doc_drift_verdict(_changed_paths_from_git(rng))
    prefix = "[doc-drift] "
    print(prefix + verdict["message"])
    if verdict["drift"]:
        print(prefix + "REMINDER: actualizeaza CLAUDE.md (Status) + docurile-cheie relevante "
                       "si include-le in commit-ul ciclului (regula HARD doc-currency).")
        return 1 if strict else 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
