"""Teste comportamentale pentru garzile de durabilitate §3/§4/§5 (CERINTA #1).

Miezul non-vacuitatii (advisor): pe codul VECHI, `_generate_with_openai_compat` prindea
orice eroare cu un `except` generic dupa `raise_for_status()` -> 404 SI 429 curgeau AMANDOUA
identic (record_provider_failure + None). Deci un test care doar verifica "lantul continua"
ar fi trecut si pe codul vechi. Delta REALE testate aici:
  §3 (E2): un 404/model_not_found marcheaza providerul INDISPONIBIL pe sesiune -> urmatorul
           apel NU mai loveste API-ul (pe codul vechi il reapela la fiecare sectiune).
  §5 (E4): un 429 NU cheama record_provider_failure (pe codul vechi il chema -> cota epuizata
           tripla circuit breaker-ul exact ca un esec de continut). Plus logheaza retry-after.
  §4 (E3): un prompt > 90% din max_context SARE providerul inainte de apel (skip + log);
           PLUS overflow detectat la RUNTIME (400 context_length_exceeded) -> skip, nu esec.
"""

import pytest
from loguru import logger

from backend.agents import ai_models, circuit_breaker
from backend.agents import synthesis_providers as sp
from backend.agents.synthesis_providers import SynthesisProvidersMixin
from backend.config import settings


class _Bare(SynthesisProvidersMixin):
    """Doar mixin-ul cu providerii — suficient pt _generate_with_openai_compat."""


class _FakeResp:
    def __init__(self, status_code, text="", headers=None, json_data=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}
        self._json = json_data if json_data is not None else {}

    def json(self):
        return self._json


class _FakeClient:
    def __init__(self, resp):
        self._resp = resp
        self.post_calls = 0

    async def post(self, *args, **kwargs):
        self.post_calls += 1
        return self._resp


@pytest.fixture(autouse=True)
def _reset_state():
    circuit_breaker._provider_failures.clear()
    ai_models.clear_unavailable()
    yield
    circuit_breaker._provider_failures.clear()
    ai_models.clear_unavailable()


@pytest.fixture
def loglines():
    msgs = []
    sink_id = logger.add(lambda m: msgs.append(str(m)), level="DEBUG")
    yield msgs
    logger.remove(sink_id)


@pytest.fixture
def record_spy(monkeypatch):
    """Spioneaza record_provider_failure (fara sa depinda de structura interna a circuit-ului)."""
    calls = []
    monkeypatch.setattr(sp, "record_provider_failure", lambda provider: calls.append(provider))
    return calls


def _install_fake_client(monkeypatch, resp):
    fake = _FakeClient(resp)
    monkeypatch.setattr(sp, "get_client", lambda: fake)
    return fake


class TestSection3ModelGone:
    """E2 — §3: model retras (404 / model_not_found)."""

    @pytest.mark.asyncio
    async def test_404_marks_unavailable_logs_and_skips_second_call(self, monkeypatch, loglines, record_spy):
        monkeypatch.setattr(settings, "groq_api_key", "test-key", raising=False)
        resp = _FakeResp(404, text='{"error":{"code":"model_not_found","message":"does not exist"}}')
        fake = _install_fake_client(monkeypatch, resp)
        agent = _Bare()

        out = await agent._generate_with_openai_compat("prompt scurt", "groq")
        assert out is None
        assert ai_models.is_unavailable("groq") is True
        assert any("INDISPONIBIL" in m for m in loglines), "lipseste log-ul distinct '[ai] ... INDISPONIBIL'"
        assert fake.post_calls == 1

        # §3: al 2-lea apel NU mai loveste API-ul (provider indisponibil pe sesiune)
        out2 = await agent._generate_with_openai_compat("prompt scurt", "groq")
        assert out2 is None
        assert fake.post_calls == 1, "modelul retras a fost REAPELAT — §3 nu a marcat indisponibil"

    @pytest.mark.asyncio
    async def test_gone_does_not_record_failure(self, monkeypatch, record_spy):
        # 'gone' != esec de continut -> NU record_provider_failure
        monkeypatch.setattr(settings, "groq_api_key", "test-key", raising=False)
        _install_fake_client(monkeypatch, _FakeResp(404, text="model_not_found"))
        await _Bare()._generate_with_openai_compat("prompt", "groq")
        assert "groq" not in record_spy, "404 (model retras) nu trebuie tratat ca esec de continut"

    @pytest.mark.asyncio
    async def test_bare_404_no_marker_is_transient_not_permanent(self, monkeypatch, record_spy):
        # Advisor: un 404 GOL fara marker (ex. OpenRouter "No endpoints found" = indisponibilitate
        # TRANZITORIE upstream) NU trebuie sa dezactiveze PERMANENT providerul pe sesiune -> il
        # tratam ca "fail" (circuit breaker cu TTL, recuperabil). Altfel un blip upstream ar
        # ucide un slot de lant pana la restart.
        monkeypatch.setattr(settings, "groq_api_key", "test-key", raising=False)
        _install_fake_client(monkeypatch, _FakeResp(404, text="No endpoints found"))
        out = await _Bare()._generate_with_openai_compat("prompt", "groq")
        assert out is None
        assert ai_models.is_unavailable("groq") is False, "404 gol tranzitoriu NU trebuie sa dezactiveze permanent"
        assert "groq" in record_spy, "404 gol = fail tranzitoriu (circuit breaker), nu gone permanent"


class TestSection5QuotaCanary:
    """E4 — §5: cota epuizata (429) distincta de esec de continut."""

    @pytest.mark.asyncio
    async def test_429_does_not_record_failure_and_logs_rate_info(self, monkeypatch, loglines, record_spy):
        monkeypatch.setattr(settings, "mistral_api_key", "test-key", raising=False)
        resp = _FakeResp(
            429,
            text='{"error":"rate limit exceeded"}',
            headers={"retry-after": "30", "x-ratelimit-remaining": "0"},
        )
        _install_fake_client(monkeypatch, resp)

        out = await _Bare()._generate_with_openai_compat("prompt", "mistral")
        assert out is None
        # Delta cheie fata de codul vechi: 429 NU e tratat ca esec (nu tripleaza circuit breaker-ul)
        assert "mistral" not in record_spy, "429 (cota) NU trebuie sa cheme record_provider_failure"
        assert any("COTA EPUIZATA" in m for m in loglines), "lipseste log-ul distinct de cota"
        assert any("retry-after" in m.lower() for m in loglines), "retry-after nu a fost logat"


class TestSection4ContextGuard:
    """E3 — §4: garda de context (pre-apel) + overflow la runtime."""

    @pytest.mark.asyncio
    async def test_prompt_over_limit_skips_before_call(self, monkeypatch, loglines, record_spy):
        # Injectam un max_context mic din config (non-vacuitate structurala: pe codul vechi
        # garda era la call-site cu prag 70% si REROUTA la alt provider; metoda insasi
        # posta MEREU, indiferent de dimensiune -> asertiunea post_calls==0 ar fi picat).
        monkeypatch.setattr(settings, "cerebras_api_key", "test-key", raising=False)
        monkeypatch.setitem(ai_models.AI_PROVIDERS["cerebras"], "max_context", 100)
        fake = _install_fake_client(monkeypatch, _FakeResp(200, json_data={"choices": [{"message": {"content": "x"}}]}))

        out = await _Bare()._generate_with_openai_compat("cuvant " * 500, "cerebras")
        assert out is None
        assert fake.post_calls == 0, "providerul NU a fost sarit — s-a facut apel desi promptul depaseste contextul"
        assert any("sarit — prompt" in m for m in loglines), "lipseste log-ul '[ai] ... sarit — prompt N > limita M'"

    @pytest.mark.asyncio
    async def test_runtime_overflow_400_is_skipped_not_failure(self, monkeypatch, loglines, record_spy):
        monkeypatch.setattr(settings, "cerebras_api_key", "test-key", raising=False)
        resp = _FakeResp(400, text='{"error":{"message":"context_length_exceeded: too many tokens"}}')
        _install_fake_client(monkeypatch, resp)

        out = await _Bare()._generate_with_openai_compat("prompt normal", "cerebras")
        assert out is None
        assert "cerebras" not in record_spy, "overflow la runtime nu e esec de provider"
        assert any("context depasit la RUNTIME" in m for m in loglines)


class TestGenericFailStillRecords:
    """Santinela: un esec REAL (500) TREBUIE inca sa cheme record_provider_failure —
    altfel garzile ar fi 'inghitit' si esecurile legitime (circuit breaker mort)."""

    @pytest.mark.asyncio
    async def test_500_records_failure(self, monkeypatch, record_spy):
        monkeypatch.setattr(settings, "groq_api_key", "test-key", raising=False)
        _install_fake_client(monkeypatch, _FakeResp(500, text="internal server error"))
        await _Bare()._generate_with_openai_compat("prompt", "groq")
        assert "groq" in record_spy, "un 500 real trebuie inca sa contorizeze esecul (circuit breaker)"
