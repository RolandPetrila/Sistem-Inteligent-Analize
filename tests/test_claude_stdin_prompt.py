"""
Bug real (2026-07-17, diagnosticat de Roland pana la capat): sinteza cu Claude
Opus (SYNTHESIS_MODE=claude_code, abonament Max) NU functiona NICIODATA in
productie. Logul de productie spunea:

    [synthesis] Claude CLI not found at 'C:\\Users\\ALIENWARE\\.local\\bin\\claude.exe'
    — falling back to Gemini

Mesajul MINTE: executabilul exista (253MB, verificat), calea e corecta,
drepturile sunt OK, serviciul ruleaza ca user.

CAUZA REALA (reprodusa cu apelul EXACT al RIS): promptul era pasat ca ultim
argument de linie de comanda ("-p", prompt). Windows CreateProcess taie linia
de comanda la ~32.767 caractere (ERROR_FILENAME_EXCED_RANGE / WinError 206) —
iar Python ridica acest esec drept FileNotFoundError (identic cu "executabil
lipsa"), pe care `except FileNotFoundError` din `_generate_with_claude` il
eticheta gresit "not found". Prompturile RIS reale au 20.000-28.000+ caractere
(ex. log real: "Nucleul analitic (27704 chars)") — peste limita cu tot cu
restul argumentelor fixe.

FIX dovedit live de Roland, cu acelasi executabil:
    prompt  32.000 caractere -> rc=0, merge
    prompt  40.000 caractere -> FileNotFoundError: [WinError 206] ... (cod vechi)
    prompt  40.000 caractere -> rc=0, OK (cod nou, input=prompt prin stdin)
    prompt  80.000 caractere -> rc=0, OK (cod nou)

Acest fisier dovedeste:
1. Non-vacuitate: subprocess.run primeste promptul prin kwarg-ul `input=`
   (stdin), NU ca element in argv (linia de comanda). Verificat empiric ca
   PICA pe codul vechi — vezi raportul agentului pentru output-ul real
   capturat prin swap temporar al fisierului (backup propriu + sha256, FARA
   git stash — stash-ul e stack global si poate fi falsificat de alti agenti
   activi in acelasi repo).
2. Regresie pt bug-ul concret: cu un prompt de ~40.000 caractere (dimensiunea
   reala din log-urile RIS), argv NU contine promptul si nici lungimea totala
   a argv-ului nu se apropie de limita Windows — altfel WinError 206 s-ar
   intoarce pe orice rulare reala cu prompt de dimensiune normala.
3. Mesajele de eroare disting WinError 2 (cale/executabil lipsa -> hint
   CLAUDE_CLI_PATH) de WinError 206 (linie de comanda prea lunga -> hint
   despre lungimea promptului si stdin) — inainte ambele cadeau in acelasi
   mesaj "not found", care minte pe cazul 206 (asta a costat ore azi).

NU se trimit prompturi reale catre Claude in aceste teste — subprocess.run e
mockuit integral in toate cazurile, deci nu se consuma NIMIC din abonamentul
Max al userului.

Limita a acestor teste (onestitate, nu proba supra-extinsa): ele dovedesc ca
promptul e RUTAT catre stdin in loc de argv. NU dovedesc ca `claude --print`
chiar CITESTE promptul din stdin cu succes — asta a fost verificat separat,
live, de Roland (rc=0 pe prompt 40k/80k), in afara acestei suite (ar consuma
din abonamentul Max daca ar rula aici).
"""

import subprocess

import pytest
from loguru import logger

from backend.agents.agent_synthesis import SynthesisAgent
from backend.config import settings


@pytest.fixture
def agent():
    return SynthesisAgent()


@pytest.fixture(autouse=True)
def _isolate_claude_settings():
    """Izoleaza testele de starea reala din .env local.

    Fara asta: daca SYNTHESIS_MODE local != 'claude_code', `_generate_with_claude`
    iese devreme (primul `if` din functie) si `subprocess.run` nu e apelat
    NICIODATA — testul ar trece "verde" fara sa verifice nimic. Capcana deja
    documentata in acest proiect (CLAUDE.md): "testele verzi nu dovedesc ca
    feature-ul ruleaza".
    """
    original_path = settings.claude_cli_path
    original_mode = settings.synthesis_mode
    settings.synthesis_mode = "claude_code"
    yield
    settings.claude_cli_path = original_path
    settings.synthesis_mode = original_mode


class _FakeCompletedProcess:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestPromptViaStdinNotArgv:
    """Non-vacuitate: promptul ajunge prin input=, nu in argv."""

    @pytest.mark.asyncio
    async def test_prompt_passed_via_input_kwarg(self, agent, monkeypatch):
        captured = {}
        prompt = "Analizeaza aceasta firma pe baza datelor financiare. " * 30  # prompt "normal"

        def fake_run(args, **kwargs):
            captured["argv"] = args
            captured["kwargs"] = kwargs
            return _FakeCompletedProcess(returncode=0, stdout="Raspuns Claude. " * 10)

        monkeypatch.setattr(subprocess, "run", fake_run)
        # Hermetic explicit: NU ne bazam pe absenta CLAUDE_CLI_PATH din .env-ul real
        # (mediul curent chiar il are setat — vezi test_claude_cli_path.py) — altfel
        # argv[0] ar fi calea absoluta din .env in loc de "claude", si testul ar
        # trece/pica in functie de mediu, nu de cod.
        settings.claude_cli_path = ""

        result = await agent._generate_with_claude(prompt)

        assert result is not None
        assert captured["kwargs"].get("input") == prompt, (
            "promptul trebuie transmis prin kwarg-ul input= (stdin) catre subprocess.run — "
            f"gasit input={captured['kwargs'].get('input')!r}"
        )
        assert prompt not in captured["argv"], (
            "promptul NU trebuie sa mai apara ca element in argv (linia de comanda) — "
            f"argv capturat: {captured['argv']!r}"
        )
        assert "-p" not in captured["argv"], (
            "flag-ul '-p' trebuie eliminat complet din argv — promptul trece prin stdin"
        )
        # Restul argumentelor NESCHIMBATE (brief: 'Restul identic').
        assert captured["argv"] == [
            "claude",
            "--print",
            "--model", "claude-opus-4-8",
            "--effort", "max",
        ]


class TestLongPromptRegressionWinError206:
    """Regresie pt bug-ul concret: prompt de ~40.000 caractere (marimea reala
    raportata in log-urile RIS: 'Nucleul analitic (27704 chars)' + restul
    sectiunilor insumate) NU mai loveste limita Windows de linie de comanda,
    pentru ca nu mai e transmis prin argv."""

    @pytest.mark.asyncio
    async def test_40k_char_prompt_not_in_argv(self, agent, monkeypatch):
        captured = {}
        long_prompt = "Text de analiza financiara detaliata pentru firma. " * 800

        assert len(long_prompt) > 40_000, "fixture-ul trebuie sa reproduca dimensiunea reala a bug-ului"

        def fake_run(args, **kwargs):
            captured["argv"] = args
            captured["kwargs"] = kwargs
            return _FakeCompletedProcess(returncode=0, stdout="OK")

        monkeypatch.setattr(subprocess, "run", fake_run)

        result = await agent._generate_with_claude(long_prompt)

        assert result is not None
        # Dovada directa a regresiei: promptul de 40k caractere NU e in argv.
        assert long_prompt not in captured["argv"]
        total_argv_chars = sum(len(a) for a in captured["argv"])
        assert total_argv_chars < 1000, (
            f"argv total ar trebui sa fie doar flag-urile fixe (scurte), nu {total_argv_chars} "
            "caractere — daca promptul s-a strecurat inapoi in argv, WinError 206 revine pe "
            "orice prompt real din productie (20.000-28.000+ caractere)"
        )
        assert captured["kwargs"].get("input") == long_prompt


class TestErrorMessageDistinguishesWinError2From206:
    """WinError 2 (cale/executabil lipsa) si WinError 206 (linie de comanda
    prea lunga) ajung AMANDOUA ca FileNotFoundError pe Windows — mesajul
    trebuie sa numeasca problema REALA in fiecare caz, nu 'not found' pentru
    amandoua (asta a mascat bug-ul de mai sus ore intregi)."""

    @pytest.mark.asyncio
    async def test_winerror_2_reports_path_not_found(self, agent, monkeypatch):
        def fake_run(args, **kwargs):
            raise FileNotFoundError(2, "The system cannot find the file specified", args[0], 2)

        monkeypatch.setattr(subprocess, "run", fake_run)
        settings.claude_cli_path = r"C:\nonexistent\claude.exe"

        records: list[str] = []
        sink_id = logger.add(lambda msg: records.append(str(msg)), level="WARNING", format="{message}")
        try:
            result = await agent._generate_with_claude("prompt scurt")
        finally:
            logger.remove(sink_id)

        assert result is None
        joined = "\n".join(records)
        assert "not found" in joined.lower()
        assert "CLAUDE_CLI_PATH" in joined
        assert "206" not in joined
        assert "prea lung" not in joined.lower()

    @pytest.mark.asyncio
    async def test_winerror_206_reports_command_line_too_long(self, agent, monkeypatch):
        def fake_run(args, **kwargs):
            raise FileNotFoundError(2, "The filename or extension is too long", args[0], 206)

        monkeypatch.setattr(subprocess, "run", fake_run)
        settings.claude_cli_path = r"C:\Users\ALIENWARE\.local\bin\claude.exe"

        records: list[str] = []
        sink_id = logger.add(lambda msg: records.append(str(msg)), level="WARNING", format="{message}")
        try:
            result = await agent._generate_with_claude("prompt oarecare")
        finally:
            logger.remove(sink_id)

        assert result is None
        joined = "\n".join(records)
        assert "206" in joined
        assert "prea lung" in joined.lower() or "lunga" in joined.lower()
        assert "not found" not in joined.lower(), (
            "mesajul pt WinError 206 NU trebuie sa spuna 'not found' — cauza reala e "
            "lungimea liniei de comanda, nu un executabil lipsa"
        )
