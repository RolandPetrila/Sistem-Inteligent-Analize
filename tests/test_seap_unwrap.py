"""
Test de regresie: `market["seap"]` e infasurat de `_verify_market()`
(backend/agents/agent_verification.py:616-622) prin `_make_field()` ->
`{"value": {...}, "trust": ..., "source": ..., "timestamp": ...}`.

4 situri citeau `market.get("seap", {})` DIRECT, fara unwrap `.value`, deci
`seap_val.get("total_contracts")` cauta o cheie care nu exista niciodata pe
wrapper-ul in sine (doar pe `wrapper["value"]`) -> mereu None/0, chiar cand
firma are contracte SEAP reale:

  - backend/prompts/section_prompts.py::_adjust_word_count (key="competition")
  - backend/agents/agent_synthesis.py::_has_sufficient_data (key="opportunities")
  - backend/agents/agent_synthesis.py::_extract_bullets_for_section (key="competition")
  - backend/agents/agent_synthesis.py::_build_context_summary (key="competition")

Cel mai grav: `_build_context_summary` injecta neconditionat "Contracte SEAP: 0"
in promptul trimis modelului LLM pentru sectiunea "competition" — informatie
FALSA, nu doar omisiune, cand firma are contracte reale.

Date sintetice (structura reala a wrapper-ului _make_field, valori inventate).
"""
from backend.agents.agent_synthesis import SynthesisAgent
from backend.prompts.section_prompts import _adjust_word_count


def _wrapped_seap(total_contracts: int) -> dict:
    """Forma REALA produsa de _verify_market() -> _make_field()."""
    return {
        "seap": {
            "value": {"total_contracts": total_contracts, "won_cpv_codes": ["7213"]},
            "trust": "VERIFICAT",
            "source": "Tavily",
            "timestamp": "2026-01-01T00:00:00+00:00",
        }
    }


class TestAdjustWordCountSeapUnwrap:
    def test_contracte_seap_reale_cresc_word_count(self):
        """Cu 10 contracte SEAP reale (wrapper .value) si 1 competitor (evita
        ramurile >=3 / ==0 care ar suprascrie factorul SEAP), word count-ul
        trebuie sa creasca fata de cazul fara SEAP — pe codul vechi (fara
        unwrap) rezultatul era IDENTIC in ambele cazuri (branch-ul SEAP nu se
        declansa niciodata, deci factor ramanea 1.0 in ambele)."""
        one_competitor = {"competitors": {"results": [{"name": "X"}]}}
        data_with_seap = {"market": _wrapped_seap(10), "web_presence": one_competitor}
        data_without_seap = {"market": _wrapped_seap(0), "web_presence": one_competitor}

        wc_with = _adjust_word_count("competition", 300, data_with_seap)
        wc_without = _adjust_word_count("competition", 300, data_without_seap)

        assert wc_with > wc_without
        assert wc_with == round(300 * 1.2)
        assert wc_without == 300


class TestHasSufficientDataOpportunitiesSeap:
    def test_seap_real_declanseaza_opportunities_sufficient(self):
        agent = SynthesisAgent()
        verified_data = {
            "funding_programs": {},
            "tender_opportunities": {},
            "web_presence": {},
            "market": _wrapped_seap(3),
        }
        assert agent._has_sufficient_data("opportunities", verified_data) is True

    def test_fara_seap_opportunities_insufficient(self):
        agent = SynthesisAgent()
        verified_data = {
            "funding_programs": {},
            "tender_opportunities": {},
            "web_presence": {},
            "market": {"seap": {"value": {"total_contracts": 0}}},
        }
        assert agent._has_sufficient_data("opportunities", verified_data) is False


class TestExtractBulletsSeapUnwrap:
    def test_bullets_contin_numarul_real_de_contracte(self):
        agent = SynthesisAgent()
        data = {
            "company": {},
            "financial": {},
            "risk_score": {},
            "market": _wrapped_seap(7),
        }
        bullets = agent._extract_bullets_for_section("competition", data)
        assert any("Contracte SEAP: 7" in b for b in bullets)


class TestBuildContextSummarySeapUnwrap:
    def test_context_summary_nu_falsifica_seap_la_zero(self):
        """Cel mai grav sit: promptul catre LLM nu trebuie sa afirme
        'Contracte SEAP: 0' cand firma are contracte reale."""
        agent = SynthesisAgent()
        data = {"market": _wrapped_seap(12)}
        summary = agent._build_context_summary("competition", data)
        assert "Contracte SEAP: 12" in summary
        assert "Contracte SEAP: 0" not in summary
