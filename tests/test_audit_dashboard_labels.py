"""CERINTA #2 — M2: dashboard-ul de audit marca fals Claude "NEACTIV in productie".

Claude Code CLI scrie efectiv sectiunile de calitate in productie (dovedit live E7,
job bd69a5d7 2026-07-25: executive_summary + financial_analysis provider=claude, fara
FALLBACK). Eticheta veche `active=False` + nota cu 2 premise false ("SYNTHESIS_MODE=
autonomous" — de fapt claude_code; "ruleaza ca SYSTEM" — de fapt .\\ALIENWARE) era o
"regula care minte".

E-M2.1: garda TEXT-LEVEL pe scriptul-sursa (NU importa modulul — evita side-effectul
        `backend.main.app.routes`): tuplul "Claude Code CLI" are al 3-lea element True SI
        nota nu contine NEACTIV/autonomous/SYSTEM. Non-vac.: pe HEAD PICA (False + string-uri).
E-M2.2: dupa regenerare, AUDIT_FUNCTII.html (root, tracked) nu mai contine NEACTIV/autonomous.
"""

import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools" / "generate_audit_dashboard.py"
HTML = ROOT / "AUDIT_FUNCTII.html"

_FORBIDDEN = ("NEACTIV", "autonomous", "SYSTEM")


def _claude_provider_line() -> str:
    text = SCRIPT.read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if '"Claude Code CLI"' in ln]
    assert len(lines) == 1, f"astept exact o intrare 'Claude Code CLI' in script, gasit {len(lines)}"
    return lines[0]


class TestM2ScriptLabel:
    def test_claude_marked_active(self):
        line = _claude_provider_line()
        # Tuplul: ("Claude Code CLI", "SYNTHESIS_MODE=claude_code", True, "...")
        # al 3-lea element (dupa cele doua string-uri) trebuie sa fie True.
        assert ", True," in line, "Claude nu e marcat activ (al 3-lea element != True)"
        assert ", False," not in line, "Claude inca marcat inactiv (False)"

    def test_note_has_no_false_premises(self):
        line = _claude_provider_line()
        for bad in _FORBIDDEN:
            assert bad not in line, f"nota Claude inca contine premisa falsa '{bad}'"


class TestM2GeneratedHtml:
    def test_html_has_no_false_premises(self):
        assert HTML.exists(), "AUDIT_FUNCTII.html lipseste — regenereaza cu tools/generate_audit_dashboard.py"
        html = HTML.read_text(encoding="utf-8")
        # Doar NEACTIV/autonomous (azi ×1 fiecare, in randul Claude). NU "SYSTEM": e prea generic
        # pt un HTML intreg (risc de fals pozitiv la continut viitor legitim); premisa "SYSTEM"
        # e prinsa la nivel de linie in scriptul-sursa (test de mai sus).
        for bad in ("NEACTIV", "autonomous"):
            assert bad not in html, (
                f"AUDIT_FUNCTII.html inca contine '{bad}' — regenereaza dupa fixul din script"
            )


class TestM2ClaudeTestWired:
    """Consecinta lui active=True (deviatie justificata): butonul din dashboard tinteste
    `POST /api/settings/test/claude`. Fara branch, endpoint-ul intorcea null -> JS-ul arunca
    la `data.ok` -> "EROARE retea" fals pe un Claude functional (noua minciuna in locul celei
    vechi). Cablat la `_claude_preflight()` existent. NU atinge subprocesul de sinteza."""

    def test_claude_in_testable_services(self):
        from backend.routers.settings import TESTABLE_SERVICES

        assert "claude" in TESTABLE_SERVICES

    @pytest.mark.asyncio
    async def test_claude_test_returns_preflight_shape(self):
        # Non-vac.: pe HEAD, run_service_test("claude") ridica RISError ("Serviciu necunoscut")
        # -> NU returneaza dict {ok, message}. Aici returneaza forma preflight (indiferent de
        # valoarea ok, care depinde de mediu — dovedeste cablarea, nu setup-ul masinii).
        from backend.routers.settings import run_service_test

        res = await run_service_test("claude")
        assert isinstance(res, dict)
        assert "ok" in res and "message" in res
