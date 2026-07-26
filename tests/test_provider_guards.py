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
from backend.agents.agent_synthesis import SynthesisAgent
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
        self.last_url = None
        self.last_kwargs = {}

    async def post(self, *args, **kwargs):
        self.post_calls += 1
        self.last_url = args[0] if args else kwargs.get("url")
        self.last_kwargs = kwargs
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


# ═══════ CERINTA #6 — OpenRouter multi-model (fallback adanc) ═══════

_OK_200 = {"choices": [{"message": {"content": "proza de raport"}}]}


class TestE3DispatchInvariant:
    """E3: FIECARE cheie din QUALITY_CHAIN si SPEED_CHAIN are metoda in _provider_method_map().
    Prinde 'cheie in lant fara dispatch' (skip tacut in _sequential_fallback). Non-vacuitate:
    pe HEAD openrouter_gpt4o_mini/openrouter_r1 sunt in lant (ai_models nou) dar NU in map -> PICA."""

    def test_every_chain_key_has_dispatch(self):
        methods = _Bare()._provider_method_map()
        for provider in list(ai_models.QUALITY_CHAIN) + list(ai_models.SPEED_CHAIN):
            assert provider in methods, f"'{provider}' e in lant dar NU are metoda in _provider_method_map"
            assert callable(methods[provider])


class TestE4PerProviderTimeout:
    """E4 (C.1): timeout per provider din config. Non-vacuitate: pe codul vechi
    `req_timeout = 90 if provider == 'openrouter' else 60` -> openrouter_r1 (!= 'openrouter')
    ar fi primit 60 -> asertiunea >= 150 PICA."""

    @pytest.mark.asyncio
    async def test_r1_uses_generous_timeout(self, monkeypatch):
        monkeypatch.setattr(settings, "openrouter_api_key", "test-key", raising=False)
        fake = _install_fake_client(monkeypatch, _FakeResp(200, json_data=_OK_200))
        out = await _Bare()._generate_with_openrouter_r1("prompt scurt")
        assert out == "proza de raport"
        assert fake.last_kwargs.get("timeout", 60) >= 150, "R1 (reasoning lent) trebuie timeout generos, nu 60s"

    @pytest.mark.asyncio
    async def test_gpt4o_mini_uses_90(self, monkeypatch):
        monkeypatch.setattr(settings, "openrouter_api_key", "test-key", raising=False)
        fake = _install_fake_client(monkeypatch, _FakeResp(200, json_data=_OK_200))
        await _Bare()._generate_with_openrouter_gpt4o_mini("p")
        assert fake.last_kwargs.get("timeout") == 90

    @pytest.mark.asyncio
    async def test_non_openrouter_stays_60(self, monkeypatch):
        # Santinela: providerii fara request_timeout raman la default 60 (comportament neschimbat).
        monkeypatch.setattr(settings, "groq_api_key", "test-key", raising=False)
        fake = _install_fake_client(monkeypatch, _FakeResp(200, json_data=_OK_200))
        await _Bare()._generate_with_groq("p")
        assert fake.last_kwargs.get("timeout") == 60


class TestE5OpenRouterFamilyRequest:
    """E5: cei 2 provideri noi trimit headerele de routing OpenRouter; R1 trimite si capul
    de reasoning (extra_payload). Non-vacuitate: pe HEAD n-au dispatch (AttributeError) -> PICA."""

    @pytest.mark.asyncio
    async def test_both_send_routing_headers(self, monkeypatch):
        for method_name in ("_generate_with_openrouter_gpt4o_mini", "_generate_with_openrouter_r1"):
            monkeypatch.setattr(settings, "openrouter_api_key", "test-key", raising=False)
            fake = _install_fake_client(monkeypatch, _FakeResp(200, json_data=_OK_200))
            await getattr(_Bare(), method_name)("prompt")
            headers = fake.last_kwargs.get("headers", {})
            assert headers.get("HTTP-Referer"), f"{method_name}: lipseste HTTP-Referer"
            assert "RIS" in headers.get("X-Title", ""), f"{method_name}: lipseste X-Title"

    @pytest.mark.asyncio
    async def test_r1_sends_reasoning_cap(self, monkeypatch):
        monkeypatch.setattr(settings, "openrouter_api_key", "test-key", raising=False)
        fake = _install_fake_client(monkeypatch, _FakeResp(200, json_data=_OK_200))
        await _Bare()._generate_with_openrouter_r1("prompt")
        payload = fake.last_kwargs.get("json", {})
        assert payload.get("reasoning", {}).get("max_tokens") == 1024, "R1 nu trimite capul de reasoning"

    @pytest.mark.asyncio
    async def test_gpt4o_mini_no_reasoning_cap(self, monkeypatch):
        # Santinela: doar R1 are extra_payload; gpt-4o-mini nu trebuie sa trimita `reasoning`.
        monkeypatch.setattr(settings, "openrouter_api_key", "test-key", raising=False)
        fake = _install_fake_client(monkeypatch, _FakeResp(200, json_data=_OK_200))
        await _Bare()._generate_with_openrouter_gpt4o_mini("prompt")
        assert "reasoning" not in fake.last_kwargs.get("json", {})


class TestReasoningEmptyContentDistinctLog:
    """Advisor: content GOL de la un provider cu cap de reasoning e logat DISTINCT (nu ca pana
    generica). R1 fara/insuficient cap -> content GOL (masurat live). Non-vacuitate: pe HEAD
    ramura empty logheaza 'returned empty response' generic -> asertiunea PICA."""

    @pytest.mark.asyncio
    async def test_r1_empty_content_names_reasoning_cause(self, monkeypatch, loglines, record_spy):
        monkeypatch.setattr(settings, "openrouter_api_key", "test-key", raising=False)
        _install_fake_client(monkeypatch, _FakeResp(200, json_data={"choices": [{"message": {"content": ""}}]}))
        out = await _Bare()._generate_with_openrouter_r1("prompt")
        assert out is None
        assert any("content GOL" in m and "reasoning" in m for m in loglines), \
            "content GOL de la R1 nu e logat cu cauza (reasoning) — esec tacut nediferentiat"


class TestE6ThinkStripSentinel:
    """E6 (C.2): _strip_scratchpad elimina si <think>...</think> (santinela defensiva pt drift
    de rutare — content R1 e curat AZI via OpenRouter, dar e o proprietate de rutare, nu de model).
    Non-vacuitate: pe HEAD strip DOAR <analiza_secreta> -> <think> ramane -> PICA.
    Metoda nu foloseste `self` (doar `re`) -> apel ca functie neData cu self dummy (fara __init__)."""

    def _strip(self, text):
        return SynthesisAgent._strip_scratchpad(object(), text)

    def test_think_block_removed(self):
        out = self._strip("<think>rationament intern lung</think>Proza curata de raport.")
        assert out == "Proza curata de raport."
        assert "<think>" not in out

    def test_analiza_secreta_still_removed(self):
        out = self._strip("<analiza_secreta>gandire</analiza_secreta>Text final.")
        assert out == "Text final."

    def test_clean_text_unchanged(self):
        # Santinela: cazul de AZI (OpenRouter -> content curat) trece neatins.
        clean = "Firma are lichiditate buna si profit stabil."
        assert self._strip(clean) == clean
