"""CERINTA #2 — rider AI: M1 (402/plata) + M1b (log quota status real).

Non-vacuitate (dovada mecanica separata in raport): pe codul de la HEAD 1993ce3
`classify_http_error(402, "Insufficient Balance")` intoarce "fail" -> call-site cheama
`record_provider_failure` (circuit) + logul e dump-ul generic "HTTP 402: ...". Iar logul
de quota hardcoda "(429)" indiferent de statusul real. Delta testate aici:
  M1  (E-M1.1/E-M1.2): 402 + "Insufficient Balance" -> categorie "payment" (≠ fail);
       log DISTINCT+truthful (NU "HTTP 402:" generic, NU "COTA EPUIZATA (429)"); FARA circuit.
  M1.3 (santinela over-breadth): 403 "insufficient permissions" SI 500 -> raman "fail" +
       declanseaza record_provider_failure (trece pe AMBELE versiuni — gardă contra markerului lat).
  M1b (E-M1b): un outcome "quota" venit dintr-un status ≠429 (400 + resource_exhausted) ->
       logul reflecta statusul REAL (HTTP 400), nu "(429)".

Perechi: tests/test_provider_guards.py (§3/§4/§5, CERINTA #1) — pattern de fixtures identic.
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


# ── M1 — clasificator (E-M1.1) ────────────────────────────────────────────────
class TestPaymentClassification:
    def test_402_insufficient_balance_is_payment(self):
        # Cazul REAL masurat 2026-07-25 (DeepSeek direct). Non-vac.: pe HEAD -> "fail".
        assert ai_models.classify_http_error(402, "Insufficient Balance") == "payment"

    @pytest.mark.parametrize(
        "body",
        [
            "insufficient balance",
            '{"error":{"message":"Insufficient_Balance"}}',
            "insufficient credit",
            "You have insufficient credits remaining",
            "402 Payment Required",
            '{"error":{"code":"payment_required"}}',
        ],
    )
    def test_payment_markers_matched(self, body):
        # Marker pe body, indiferent de status (aici 402, dar si un 400 cu marker ar prinde).
        assert ai_models.classify_http_error(402, body) == "payment"

    @pytest.mark.parametrize(
        "body",
        [
            # Forma EXACTA masurata live la SambaNova 2026-07-27 (CERINTA #8, balance_units:0).
            '{"code":"PAYMENT_METHOD_REQUIRED","message":"A payment method is required to access this model"}',
            # Doar codul (unele gateway-uri trimit doar `code`).
            "payment_method_required",
            # Doar mesajul in proza (marker `payment method` substring).
            "A payment method is required",
        ],
    )
    def test_sambanova_payment_method_required_is_payment(self, body):
        # CERINTA #9/B — gapul MASURAT: forma SambaNova nu o prindea niciun marker vechi
        # ("payment required" ≠ "payment method is required"). Non-vac.: pe HEAD -> "fail".
        assert ai_models.classify_http_error(402, body) == "payment"

    def test_openrouter_402_verbatim_is_payment(self):
        # CERINTA #10/B — REGRESSION-LOCK, NU non-vacuitate. Mesajul VERBATIM din docs
        # OpenRouter (openrouter.ai/docs/api-reference/errors, re-fetch 2026-07-27: o
        # SINGURA forma 402, type `payment_required`). ONEST: trece SI pe HEAD — deja
        # acoperit de markerii `insufficient credits` + `payment_required` din
        # _PAYMENT_MARKERS; nu e un fix, ci o garda care PICA daca cineva sterge vreun
        # marker de credit. Docs-confirmat, non-verbatim-live (creditul platit ~$9.9 NU
        # se goleste ca sa-l masor — decizia proprietarului, partea B non-destructiva).
        msg = "Your account or API key has insufficient credits. Add more credits and retry the request."
        assert ai_models.classify_http_error(402, msg) == "payment"

    def test_bare_402_no_marker_is_fail_not_payment(self):
        # Consecvent cu §3 (marker-required): un 402 GOL fara marker NU e plata -> "fail".
        assert ai_models.classify_http_error(402, "") == "fail"

    def test_insufficient_quota_stays_quota_not_payment(self):
        # `insufficient_quota` e marker de COTA (verificat inaintea platii) — nu-l muta.
        assert ai_models.classify_http_error(429, "insufficient_quota") == "quota"

    def test_insufficient_permissions_stays_fail(self):
        # SANTINELA over-breadth: markerul nud "insufficient" ar prinde auth-ul -> INTERZIS.
        # "insufficient permissions" (auth) trebuie sa ramana "fail". Trece pe AMBELE versiuni.
        assert ai_models.classify_http_error(403, "insufficient permissions") == "fail"

    def test_payment_word_without_billing_marker_stays_fail(self):
        # SANTINELA over-breadth pt markerii noi (#9/B): markerul e "payment method" /
        # "payment_method_required", NU cuvantul nud "payment". Un mesaj cu "payment" fara forma
        # de billing (aici un mesaj de auth/config) trebuie sa ramana "fail".
        assert ai_models.classify_http_error(403, "your payment plan lacks permission for this model") == "fail"


# ── M1 — comportamental (E-M1.2) + santinela (E-M1.3) ─────────────────────────
class TestPaymentBehavior:
    @pytest.mark.asyncio
    async def test_402_payment_logs_distinct_and_no_circuit(self, monkeypatch, loglines, record_spy):
        monkeypatch.setattr(settings, "openrouter_api_key", "test-key", raising=False)
        resp = _FakeResp(402, text="Insufficient Balance")
        _install_fake_client(monkeypatch, resp)

        out = await _Bare()._generate_with_openai_compat("prompt", "openrouter")
        assert out is None
        # (a) log DISTINCT de plata — fraza RO proprie, absenta din orice body de provider
        assert any("CREDIT/PLATA EPUIZAT" in m for m in loglines), "lipseste log-ul distinct de plata"
        # (a2) NU dump-ul generic "HTTP 402: <body>" (forma de la HEAD)
        assert not any("HTTP 402:" in m for m in loglines), "plata logata ca dump generic (forma veche)"
        # (a3) NU minte cu "(429)" (nu e cota)
        assert not any("(429)" in m for m in loglines), "plata logata fals ca 429"
        # (b) FARA circuit — plata nu e esec de continut
        assert "openrouter" not in record_spy, "402 plata NU trebuie sa cheme record_provider_failure"

    @pytest.mark.asyncio
    async def test_403_insufficient_permissions_still_records_failure(self, monkeypatch, record_spy):
        # SANTINELA comportamentala: auth-ul (403 insufficient permissions) ramane "fail" ->
        # inca declanseaza circuit. Trece pe AMBELE versiuni (gardă contra markerului lat).
        monkeypatch.setattr(settings, "openrouter_api_key", "test-key", raising=False)
        _install_fake_client(monkeypatch, _FakeResp(403, text="insufficient permissions"))
        await _Bare()._generate_with_openai_compat("prompt", "openrouter")
        assert "openrouter" in record_spy, "403 auth trebuie sa ramana esec real (circuit breaker)"

    @pytest.mark.asyncio
    async def test_500_still_records_failure(self, monkeypatch, record_spy):
        # A 2-a santinela: un 500 nud ramane "fail" -> circuit (garzile nu inghit esecuri reale).
        monkeypatch.setattr(settings, "openrouter_api_key", "test-key", raising=False)
        _install_fake_client(monkeypatch, _FakeResp(500, text="internal server error"))
        await _Bare()._generate_with_openai_compat("prompt", "openrouter")
        assert "openrouter" in record_spy


# ── M1b — logul de quota reflecta statusul REAL (E-M1b) ───────────────────────
class TestQuotaLogRealStatus:
    @pytest.mark.asyncio
    async def test_quota_from_non_429_logs_real_status(self, monkeypatch, loglines):
        # Un marker de cota pe alt status decat 429 (400 + resource_exhausted) -> "quota",
        # dar logul trebuie sa spuna HTTP 400, nu "(429)" hardcodat.
        monkeypatch.setattr(settings, "mistral_api_key", "test-key", raising=False)
        _install_fake_client(monkeypatch, _FakeResp(400, text="RESOURCE_EXHAUSTED"))
        out = await _Bare()._generate_with_openai_compat("prompt", "mistral")
        assert out is None
        quota_lines = [m for m in loglines if "COTA EPUIZATA" in m]
        assert quota_lines, "lipseste log-ul de cota"
        assert any("HTTP 400" in m for m in quota_lines), "logul de cota nu reflecta statusul real (400)"
        assert not any("(429)" in m for m in quota_lines), "logul de cota inca hardcodeaza (429)"
