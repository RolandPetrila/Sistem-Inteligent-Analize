"""
Finding 7.7 (99_Plan_vs_Audit/PLAN_ANTI_DERIVA_2026-07-16.md): `log_synthesis()`
(backend/services/job_logger.py) exista de mult dar NU era apelata NICIODATA din
tot backend-ul (verificat prin grep) — exact functia care ar raspunde la "cine a
generat sectiunea X" era cod mort. Motivul practic: Roland trece serviciul RIS sa
ruleze ca USER (nu SYSTEM) ca sa deblocheze SYNTHESIS_MODE=claude_code (rapoarte
scrise de Claude Opus, cost API zero) — dar fara aceasta cablare nu exista nicio
dovada, dupa schimbare, care provider a scris fiecare sectiune (doar deductie din
timpi, nu dovada).

Acest fisier verifica ca `SynthesisAgent.generate_section()` cheama acum
`log_synthesis(job_id, section_key, provider, word_count, elapsed_ms, success,
fallback)` EXACT o data per sectiune, cu providerul REAL care a castigat cascada
(primary -> concurrent fallback -> plasa cerebras -> degradare non-AI), indiferent
pe care cale a castigat.

Non-vacuitate (verificata manual, nu doar prin construct de test): pe codul VECHI
(inainte de acest wiring), `backend.agents.agent_synthesis` NU importa deloc
`log_synthesis` — `monkeypatch.setattr(agent_synthesis_module, "log_synthesis",
fake)` arunca AttributeError direct (attribute nu exista), inaintea oricarei
asertiuni. Verificat manual prin restaurare temporara a codului vechi din git HEAD
(vezi raportul agentului — NU git stash, care e stack global si poate fi
falsificat de alti agenti activi).
"""


import time as _time

import pytest

from backend.agents import agent_synthesis as agent_synthesis_module
from backend.agents import circuit_breaker
from backend.agents.agent_synthesis import SynthesisAgent
from backend.services.job_logger import finish_job_log, get_log_file_path, start_job_log


@pytest.fixture
def agent():
    return SynthesisAgent()


@pytest.fixture(autouse=True)
def _reset_circuit_breaker():
    """Izoleaza testele de starea globala a circuit breaker-ului (module-level dict)."""
    circuit_breaker._provider_failures.clear()
    yield
    circuit_breaker._provider_failures.clear()


@pytest.fixture
def log_calls(monkeypatch):
    """Capteaza toate apelurile log_synthesis facute din agent_synthesis.py.

    IMPORTANT: raising=True (default) — pe codul VECHI, care nu importa deloc
    `log_synthesis` in acest modul, acest monkeypatch.setattr insusi arunca
    AttributeError, inaintea oricarei asertiuni din test. Asta e proba de
    non-vacuitate: testul nu doar "pica pe assert", ci nu poate nici macar
    porni pe codul vechi.
    """
    calls = []

    def _fake(job_id, section_key, provider, word_count, elapsed_ms, success, fallback=False):
        calls.append({
            "job_id": job_id,
            "section_key": section_key,
            "provider": provider,
            "word_count": word_count,
            "elapsed_ms": elapsed_ms,
            "success": success,
            "fallback": fallback,
        })

    monkeypatch.setattr(agent_synthesis_module, "log_synthesis", _fake)
    return calls


def _minimal_verified_data() -> dict:
    return {
        "company": {"denumire": {"value": "Test SRL"}, "cui": {"value": "12345678"}},
        "financial": {"cifra_afaceri": {"value": 1_000_000}},
    }


class TestLogSynthesisPrimaryWins:
    """Ruta 'quality': Claude (primary) raspunde direct — fara fallback."""

    @pytest.mark.asyncio
    async def test_primary_claude_logs_correct_provider(self, agent, log_calls):
        async def fake_claude(prompt: str) -> str:
            return "Text generat de Claude despre firma. " * 10

        agent._generate_with_claude = fake_claude

        section = {
            "key": "executive_summary",
            "title": "Rezumat Executiv",
            "word_count": 300,  # >200 -> ramane pe ruta "quality"
            "prompt": "Scrie un rezumat.",
        }

        result = await agent.generate_section(section, _minimal_verified_data(), job_id="job-primary-123")

        assert result["content"]  # sectiunea chiar s-a generat
        assert len(log_calls) == 1, f"log_synthesis ar fi trebuit apelat exact o data, gasit {len(log_calls)}"
        call = log_calls[0]
        assert call["job_id"] == "job-primary-123"
        assert call["section_key"] == "executive_summary"
        assert call["provider"] == "claude"
        assert call["success"] is True
        assert call["fallback"] is False
        assert call["word_count"] > 0
        assert isinstance(call["elapsed_ms"], int)
        assert call["elapsed_ms"] >= 0


class TestLogSynthesisConcurrentFallbackWins:
    """Ruta 'fast': Groq (primary) pica -> concurrent fallback castiga.

    Determinism: 2 din cei 3 candidati (cerebras, mistral) sunt scosi din cursa
    prin trip-ul circuit breaker-ului INAINTE de apel — evita cursa reala
    asyncio.wait(FIRST_COMPLETED) intre task-uri (_concurrent_fallback anuleaza
    TOATE task-urile pending imediat ce PRIMUL se termina, indiferent daca a
    reusit — comportament pre-existent, nemodificat aici; il ocolim prin
    proiectare de test, nu il schimbam)."""

    @pytest.mark.asyncio
    async def test_fallback_winner_logged_with_fallback_true(self, agent, log_calls):
        async def fake_groq(prompt: str) -> str:
            return None  # primary pica

        async def fake_gemini(prompt: str) -> str:
            return "Text generat de Gemini ca fallback. " * 10

        agent._generate_with_groq = fake_groq
        agent._generate_with_gemini = fake_gemini

        # Scoate cerebras + mistral din cursa concurrent_fallback (nu raman candidati activi).
        for _ in range(3):
            circuit_breaker.record_provider_failure("cerebras")
            circuit_breaker.record_provider_failure("mistral")

        section = {
            "key": "executive_summary",
            "title": "Rezumat Executiv",
            "word_count": 100,  # <=200 -> forteaza ruta "fast"
            "prompt": "Scrie un rezumat scurt.",
        }

        result = await agent.generate_section(section, _minimal_verified_data(), job_id="job-fallback-456")

        assert result["content"]
        assert len(log_calls) == 1, f"log_synthesis ar fi trebuit apelat exact o data, gasit {len(log_calls)}"
        call = log_calls[0]
        assert call["job_id"] == "job-fallback-456"
        assert call["provider"] == "gemini", "providerul logat trebuie sa fie CASTIGATORUL real, nu 'groq' (initial)"
        assert call["success"] is True
        assert call["fallback"] is True
        assert call["word_count"] > 0


class TestLogSynthesisAllFailDegraded:
    """Ruta 'quality': Claude + toti cei din concurrent fallback + plasa cerebras
    pica -> degradare non-AI (_degraded_fallback). Nimeni nu reuseste sa raceze
    aici (toti returneaza falsy), deci ordinea reala de completare a task-urilor
    nu afecteaza rezultatul (vezi nota din clasa de mai sus)."""

    @pytest.mark.asyncio
    async def test_degraded_fallback_logged_as_failure(self, agent, log_calls):
        async def fail(prompt: str) -> str:
            return None

        agent._generate_with_claude = fail
        agent._generate_with_gemini = fail
        agent._generate_with_groq = fail
        agent._generate_with_mistral = fail
        agent._generate_with_cerebras = fail

        section = {
            "key": "executive_summary",
            "title": "Rezumat Executiv",
            "word_count": 300,  # ruta "quality"
            "prompt": "Scrie un rezumat.",
        }

        result = await agent.generate_section(section, _minimal_verified_data(), job_id="job-degraded-789")

        assert result["content"]  # degraded fallback tot produce continut (non-AI)
        assert len(log_calls) == 1, f"log_synthesis ar fi trebuit apelat exact o data, gasit {len(log_calls)}"
        call = log_calls[0]
        assert call["job_id"] == "job-degraded-789"
        assert call["provider"] == "degraded"
        assert call["success"] is False, "toti providerii AI au esuat — success trebuie sa reflecte asta onest"
        assert call["fallback"] is True


class TestLogSynthesisSkippedWithoutJobId:
    """Fara job_id (apelant care nu are unul la indemana), log_synthesis NU trebuie
    apelat deloc — nu se inventeaza un job_id fals."""

    @pytest.mark.asyncio
    async def test_no_job_id_means_no_log_call(self, agent, log_calls):
        async def fake_claude(prompt: str) -> str:
            return "Text generat de Claude. " * 10

        agent._generate_with_claude = fake_claude

        section = {
            "key": "executive_summary",
            "title": "Rezumat Executiv",
            "word_count": 300,
            "prompt": "Scrie un rezumat.",
        }

        result = await agent.generate_section(section, _minimal_verified_data())  # job_id implicit ""

        assert result["content"]
        assert len(log_calls) == 0, "fara job_id nu trebuie sa se apeleze log_synthesis"


class TestLogSynthesisWritesToRealJobLogFile:
    """Diferenta fata de clasele de mai sus: acolo `log_synthesis` era mockuit, deci
    testele dovedeau doar ca e APELAT cu argumentele corecte — nu ca linia chiar
    ajunge in fisierul de log al jobului (deliverable-ul REAL cerut: "in job log sa
    apara cine a scris-o"). `log_synthesis` era cod mort (zero apelanti) inainte de
    acest task — nu era niciodata EXECUTAT, deci risc de "testul si codul se
    confirma reciproc fara sa confrunte producatorul real" daca ne oprim la mock.

    Acest test foloseste `log_synthesis` REAL (neinlocuit) + sink-ul loguru REAL
    (`start_job_log`/`finish_job_log`) si citeste fisierul de pe disc."""

    @pytest.mark.asyncio
    async def test_synthesis_line_lands_in_real_job_log_file(self, agent):
        job_id = f"test-log-synth-{int(_time.time() * 1000)}"
        start_job_log(job_id, analysis_type="TEST", cui="00000000", company_name="Test SRL")
        try:
            async def fake_claude(prompt: str) -> str:
                return "Text generat de Claude despre firma. " * 10

            agent._generate_with_claude = fake_claude

            section = {
                "key": "executive_summary",
                "title": "Rezumat Executiv",
                "word_count": 300,
                "prompt": "Scrie un rezumat.",
            }

            result = await agent.generate_section(section, _minimal_verified_data(), job_id=job_id)
            assert result["content"]

            log_path = get_log_file_path(job_id)
            assert log_path is not None, "fisierul de log al jobului ar trebui sa existe pe disc"
            content = log_path.read_text(encoding="utf-8")
            assert "SYNTHESIS" in content, "linia SYNTHESIS nu a ajuns in fisierul de log real"
            assert "executive_summary" in content
            assert "provider=claude" in content, "providerul real (claude) trebuie sa apara in linia din log"
        finally:
            finish_job_log(job_id, success=True)
            leftover = get_log_file_path(job_id)
            if leftover:
                leftover.unlink(missing_ok=True)


class TestConcurrentFallbackReturnsWinnerName:
    """Test unitar direct pe `_concurrent_fallback`: trebuie sa intoarca tuplul
    (text, provider_name), nu doar text — apelantul are nevoie de nume ca sa
    poata loga cine a castigat."""

    @pytest.mark.asyncio
    async def test_returns_tuple_with_winning_provider(self, agent):
        async def fake_mistral(prompt: str) -> str:
            return "Continut Mistral"

        agent._generate_with_mistral = fake_mistral
        for _ in range(3):
            circuit_breaker.record_provider_failure("cerebras")
            circuit_breaker.record_provider_failure("gemini")

        section = {"key": "executive_summary", "title": "Rezumat", "word_count": 100, "prompt": "x"}
        text, provider = await agent._concurrent_fallback(
            section, _minimal_verified_data(), providers=["cerebras", "mistral", "gemini"]
        )

        assert text == "Continut Mistral"
        assert provider == "mistral"

    @pytest.mark.asyncio
    async def test_all_fail_returns_none_none(self, agent):
        async def fail(prompt: str) -> str:
            return None

        agent._generate_with_cerebras = fail
        agent._generate_with_mistral = fail
        agent._generate_with_gemini = fail

        section = {"key": "executive_summary", "title": "Rezumat", "word_count": 100, "prompt": "x"}
        text, provider = await agent._concurrent_fallback(
            section, _minimal_verified_data(), providers=["cerebras", "mistral", "gemini"]
        )

        assert text is None
        assert provider is None
