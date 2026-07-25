"""Teste pentru CERINTA #1 (reconfigurare provideri AI) — partea de CONFIG + §6.

Acopera:
- E1: ZERO nume de model literale in logica de sinteza (toate din ai_models)
- E6: rutele noi active cu numele corecte (compunerea lantului)
- E5: §6 testul lunar prinde un model inexistent injectat (non-vacuitate in test)
- unitati: clasificare erori (§3/§4/§5) + garda de context (§4)

Pereche: tests/test_provider_guards.py (comportamentul §3/§4/§5 in calea de apel).
"""

import pathlib

from backend.agents import ai_models
from tools.check_ai_models import catalog_url_for, check_model_against_catalog

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Numele de model care NU trebuie sa apara ca literale in logica de sinteza.
_MODEL_LITERALS = [
    "llama-3.1-8b-instant",
    "gpt-oss-120b",
    "mistral-small-latest",
    "deepseek/deepseek-chat",
    "gemini-2.5-flash",
    "Meta-Llama-3.3-70B-Instruct",
    "claude-opus-4-8",
    "llama-4-scout",  # retras — nu trebuie sa reapara nicaieri
]


class TestE1NoHardcodedModelLiterals:
    def test_synthesis_files_have_zero_model_literals(self):
        """E1: singura sursa de nume de model e ai_models.py. Non-vacuitate: pe codul vechi
        `synthesis_providers.py` continea 'meta-llama/llama-4-scout...' + 'gpt-oss-120b' etc.
        direct in `_PROVIDERS`, iar `agent_synthesis.py` avea `_PROVIDER_MAX_CONTEXT` + un
        `max_json_chars` cu comentariu 'Llama 4 Scout' -> testul ar fi picat pe ambele."""
        for fname in ("backend/agents/synthesis_providers.py", "backend/agents/agent_synthesis.py"):
            text = (ROOT / fname).read_text(encoding="utf-8")
            for model in _MODEL_LITERALS:
                assert model not in text, f"{fname}: model literal '{model}' — trebuie citit din ai_models"

    def test_ai_models_is_the_single_source(self):
        # ai_models.py CHIAR contine numele (e sursa) — altfel testul de mai sus ar fi vacuu.
        text = (ROOT / "backend/agents/ai_models.py").read_text(encoding="utf-8")
        assert "llama-3.1-8b-instant" in text
        assert "gpt-oss-120b" in text


class TestE6ChainComposition:
    def test_quality_chain_order(self):
        assert ai_models.QUALITY_CHAIN == ["claude", "openrouter", "sambanova", "gemini"]

    def test_speed_chain_order(self):
        assert ai_models.SPEED_CHAIN == ["groq", "cerebras", "mistral", "gemini"]

    def test_quality_primary_is_claude_pillar(self):
        assert ai_models.QUALITY_CHAIN[0] == "claude"

    def test_quality_second_is_openrouter_deepseek(self):
        assert ai_models.QUALITY_CHAIN[1] == "openrouter"
        assert ai_models.get_model("openrouter") == "deepseek/deepseek-chat"

    def test_groq_uses_new_instant_model(self):
        assert ai_models.get_model("groq") == "llama-3.1-8b-instant"

    def test_sambanova_marked_temporary_free(self):
        assert ai_models.AI_PROVIDERS["sambanova"]["temporary_free"] is True

    def test_every_chain_member_has_full_config(self):
        for provider in set(ai_models.QUALITY_CHAIN) | set(ai_models.SPEED_CHAIN):
            cfg = ai_models.AI_PROVIDERS[provider]
            for field in ("model", "max_context", "temporary_free", "endpoint_kind"):
                assert field in cfg, f"{provider} lipseste campul obligatoriu {field}"


class TestE5MonthlyValidityCatchesMissingModel:
    """§6: testul lunar trebuie sa prinda un model care NU mai e in catalog.
    Non-vacuitate PROBATA IN TEST: injectam un nume fals si dovedim ca e marcat lipsa,
    iar unul real e marcat prezent (altfel checker-ul ar spune mereu 'OK')."""

    def test_fake_model_flagged_missing(self):
        catalog = ["gpt-oss-120b", "gemma-4-31b", "zai-glm-4.7"]
        verdict = check_model_against_catalog("cerebras", "MODEL-INEXISTENT-999", catalog)
        assert verdict["present"] is False
        assert verdict["status"] == "LIPSA_IN_CATALOG"

    def test_real_model_flagged_present(self):
        catalog = ["gpt-oss-120b", "gemma-4-31b"]
        verdict = check_model_against_catalog("cerebras", "gpt-oss-120b", catalog)
        assert verdict["present"] is True
        assert verdict["status"] == "OK"

    def test_catalog_url_derivation(self):
        # openai_compat: chat/completions -> models
        assert catalog_url_for(ai_models.AI_PROVIDERS["groq"]).endswith("/models")
        # claude CLI: fara catalog REST
        assert catalog_url_for(ai_models.AI_PROVIDERS["claude"]) is None
        # gemini: endpoint dedicat
        assert "generativelanguage" in catalog_url_for(ai_models.AI_PROVIDERS["gemini"])


class TestErrorClassificationUnits:
    def test_404_is_gone(self):
        assert ai_models.classify_http_error(404, "") == "gone"

    def test_model_not_found_body_is_gone(self):
        assert ai_models.classify_http_error(400, '{"error":{"code":"model_not_found"}}') == "gone"

    def test_429_is_quota(self):
        assert ai_models.classify_http_error(429, "") == "quota"

    def test_resource_exhausted_is_quota(self):
        assert ai_models.classify_http_error(400, "RESOURCE_EXHAUSTED") == "quota"

    def test_context_overflow_is_overflow(self):
        assert ai_models.classify_http_error(400, "context_length_exceeded") == "overflow"

    def test_generic_500_is_fail(self):
        assert ai_models.classify_http_error(500, "internal error") == "fail"


class TestContextGuardUnit:
    def test_small_prompt_fits(self):
        over, _est, _lim = ai_models.exceeds_context("gemini", "scurt")
        assert over is False

    def test_huge_prompt_exceeds_small_context(self, monkeypatch):
        monkeypatch.setitem(ai_models.AI_PROVIDERS["cerebras"], "max_context", 100)
        over, est, limit = ai_models.exceeds_context("cerebras", "cuvant " * 500)
        assert over is True
        assert limit == 90  # 90% din 100
        assert est > limit
