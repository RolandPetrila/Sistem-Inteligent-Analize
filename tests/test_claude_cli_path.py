"""
Bug real (2026-07-17, raportat de Roland): SYNTHESIS_MODE=claude_code e setat, dar
serviciul Windows RIS-Backend nu genereaza NICIODATA sectiuni cu Claude — toate
cad instant (~2s) pe fallback (Groq/Cerebras). Root cause dovedita din
logs/ris_runtime.log: `FileNotFoundError` in `_generate_with_claude`
(subprocess.run(["claude", ...])) — "claude" nu e gasit in PATH-ul procesului.

Cauza reala: `claude.exe` EXISTA (`%USERPROFILE%\\.local\\bin\\claude.exe`) si e
in PATH (User + Machine) — dar a fost instalat DUPA ultimul boot Windows. Service
Control Manager (SCM) cacheaza blocul de mediu (inclusiv PATH) la BOOT, deci
serviciul (pornit inainte de instalare) nu vede noul PATH pana la reboot — desi
orice shell nou deschis dupa instalare il gaseste instant. Un reboot ar repara
temporar, dar problema revine tacut la orice viitoare schimbare de PATH.

Fix: `settings.claude_cli_path` (config.py, CLAUDE_CLI_PATH in .env) — cale
absoluta explicita catre claude.exe, folosita ca argv[0] in loc de "claude" cand
e setata. Elimina complet dependenta de PATH pentru acest subprocess.

Acest fisier dovedeste:
1. Non-vacuitate: cu `claude_cli_path` setat, `subprocess.run` primeste ACEA cale
   ca argv[0] (nu "claude" hardcodat). PICA pe codul vechi — verificat manual prin
   restaurare temporara a versiunii pre-edit din backup propriu (NU git stash,
   care e stack global si poate fi falsificat de alti agenti activi; NU nici
   `git show HEAD:...` — la momentul acestui task, HEAD era DEJA in urma
   working-tree-ului pe acest fisier, cu o alta modificare necomisa in curs
   (wiring log_synthesis / bump model claude-opus-4-6 -> 4-8); a folosi HEAD ar fi
   riscat sa ascunda/rescrie tranzitoriu acea munca in loc sa testeze exact
   schimbarea din acest task). Vezi raportul agentului pentru output-ul real
   capturat din acest swap.
2. Non-regresie: fara setare (`claude_cli_path == ""`, default), argv[0] ramane
   exact "claude" — comportament identic cu inainte de acest task.
3. Mesajul de eroare la FileNotFoundError e util: contine calea incercata SI
   mentioneaza `CLAUDE_CLI_PATH` ca solutie — inainte nu spunea niciuna din ele.
"""

import subprocess

import pytest
from loguru import logger

from backend.agents import synthesis_providers as synthesis_providers_module
from backend.agents.agent_synthesis import SynthesisAgent
from backend.config import settings


@pytest.fixture
def agent():
    return SynthesisAgent()


@pytest.fixture(autouse=True)
def _isolate_claude_settings():
    """Izoleaza testele de starea reala din .env local (claude_cli_path/synthesis_mode)."""
    original_path = settings.claude_cli_path
    original_mode = settings.synthesis_mode
    settings.synthesis_mode = "claude_code"  # forteaza ruta testata, indiferent de .env local
    yield
    settings.claude_cli_path = original_path
    settings.synthesis_mode = original_mode


class _FakeCompletedProcess:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestClaudeCliPathConfigured:
    """Dovada de non-vacuitate: cu claude_cli_path setat, argv[0] e calea configurata."""

    @pytest.mark.asyncio
    async def test_subprocess_receives_configured_path_as_argv0(self, agent, monkeypatch):
        captured = {}

        def fake_run(args, **kwargs):
            captured["argv"] = args
            captured["kwargs"] = kwargs
            return _FakeCompletedProcess(returncode=0, stdout="Text generat de Claude. " * 10)

        monkeypatch.setattr(subprocess, "run", fake_run)
        settings.claude_cli_path = r"C:\Users\ALIENWARE\.local\bin\claude.exe"

        result = await agent._generate_with_claude("Scrie un rezumat.")

        assert result is not None, "rezultatul nu ar trebui sa fie None cu fake_run reusit"
        assert "argv" in captured, "subprocess.run nu a fost apelat deloc"
        assert captured["argv"][0] == r"C:\Users\ALIENWARE\.local\bin\claude.exe", (
            f"argv[0] ar fi trebuit sa fie calea configurata din settings.claude_cli_path, "
            f"gasit: {captured['argv'][0]!r}"
        )
        # 2026-07-17: promptul NU mai e argument de linie de comanda ("-p", prompt) —
        # trece prin stdin (input=). Vezi tests/test_claude_stdin_prompt.py pt non-vacuitate
        # + regresie dedicate (WinError 206 pe linie de comanda prea lunga).
        assert captured["argv"][1:] == [
            "--print",
            "--model", "claude-opus-4-8",
            "--effort", "max",
        ]
        assert captured["kwargs"].get("input") == "Scrie un rezumat.", (
            "promptul trebuie transmis prin kwarg-ul input= (stdin), nu prin argv"
        )


class TestClaudeCliPathDefaultUnchanged:
    """Non-regresie: fara CLAUDE_CLI_PATH, comportamentul e identic cu inainte."""

    @pytest.mark.asyncio
    async def test_subprocess_falls_back_to_bare_claude_when_unset(self, agent, monkeypatch):
        captured = {}

        def fake_run(args, **kwargs):
            captured["argv"] = args
            return _FakeCompletedProcess(returncode=0, stdout="Text generat de Claude. " * 10)

        monkeypatch.setattr(subprocess, "run", fake_run)
        settings.claude_cli_path = ""  # default, neschimbat

        result = await agent._generate_with_claude("Scrie un rezumat.")

        assert result is not None
        assert captured["argv"][0] == "claude", (
            "fara CLAUDE_CLI_PATH, argv[0] trebuie sa ramana exact 'claude' — "
            "comportament vechi pastrat"
        )


class TestClaudeCliPathErrorMessage:
    """Mesajul de eroare la FileNotFoundError trebuie sa fie util: calea incercata +
    mentiunea setarii care rezolva — inainte nu spunea niciuna din ele (doar
    'Claude CLI not found — falling back to Gemini')."""

    @pytest.mark.asyncio
    async def test_file_not_found_message_includes_path_and_hint(self, agent, monkeypatch):
        attempted_path = r"D:\nonexistent\claude.exe"

        def fake_run(args, **kwargs):
            raise FileNotFoundError(2, "No such file or directory", args[0])

        monkeypatch.setattr(subprocess, "run", fake_run)
        settings.claude_cli_path = attempted_path

        records: list[str] = []
        sink_id = logger.add(lambda msg: records.append(str(msg)), level="WARNING", format="{message}")
        try:
            result = await agent._generate_with_claude("Scrie un rezumat.")
        finally:
            logger.remove(sink_id)

        assert result is None
        joined = "\n".join(records)
        assert attempted_path in joined, (
            f"mesajul de eroare trebuie sa contina calea incercata ({attempted_path!r}), "
            f"log capturat: {joined!r}"
        )
        assert "CLAUDE_CLI_PATH" in joined, (
            f"mesajul trebuie sa mentioneze CLAUDE_CLI_PATH ca solutie, log capturat: {joined!r}"
        )

    @pytest.mark.asyncio
    async def test_file_not_found_message_default_path_still_useful(self, agent, monkeypatch):
        """Chiar si fara claude_cli_path setat (cazul din bug-ul original), mesajul
        trebuie sa arate 'claude' ca fiind calea incercata + hint-ul CLAUDE_CLI_PATH."""

        def fake_run(args, **kwargs):
            raise FileNotFoundError(2, "No such file or directory", args[0])

        monkeypatch.setattr(subprocess, "run", fake_run)
        settings.claude_cli_path = ""

        records: list[str] = []
        sink_id = logger.add(lambda msg: records.append(str(msg)), level="WARNING", format="{message}")
        try:
            result = await agent._generate_with_claude("Scrie un rezumat.")
        finally:
            logger.remove(sink_id)

        assert result is None
        joined = "\n".join(records)
        assert "'claude'" in joined
        assert "CLAUDE_CLI_PATH" in joined


class TestClaudeCliPathModuleReference:
    """Verifica ca editarea a atins modulul asteptat (synthesis_providers.py), nu o
    copie/alt loc — SynthesisAgent trebuie sa mosteneasca metoda din acest mixin."""

    def test_generate_with_claude_defined_in_synthesis_providers_module(self):
        assert (
            SynthesisAgent._generate_with_claude.__module__
            == synthesis_providers_module.__name__
        )
