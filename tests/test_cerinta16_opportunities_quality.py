"""CERINTA #16 (B) — sectiunea "Oportunitati" pe chain-ul de CALITATE.

Pana la #16, `SECTION_PROVIDER_PREFERENCE["opportunities"] == "fast"` -> pe
FULL_COMPANY_PROFILE cu focus pe licitatii, sectiunea-cheie a proprietarului mergea
pe SPEED_CHAIN (cerebras masurat live). #16 o muta pe "quality" (ca `lead_candidates`),
pt fidelitate la transcrierea licitatiilor/finantarilor/CPV reale.

Non-vacuitate: pe HEAD (inainte de fix) route_preference=="fast" -> chain=SPEED_CHAIN ->
ambele teste "quality" PICA. Se extrage lantul REAL (`ai_models.QUALITY_CHAIN`, prin
`get_sections_for_analysis` + `generate_section`), nu se mock-uieste constanta.
"""
import pytest

import backend.agents.agent_synthesis as m
from backend.agents import ai_models
from backend.prompts.section_prompts import get_sections_for_analysis


def _opportunities_section() -> dict:
    """Sectiunea REALA, cum o produce pipeline-ul. `verified_data=None` -> fara
    `_adjust_word_count` -> word_count = 800 (nivel 3, deci > 200)."""
    secs = get_sections_for_analysis("FULL_COMPANY_PROFILE", 3)
    opp = [s for s in secs if s["key"] == "opportunities"]
    assert opp, "opportunities lipseste din FULL_COMPANY_PROFILE nivel 3"
    return opp[0]


def _vd_with_tenders() -> dict:
    """Trece de `_has_sufficient_data('opportunities')` -> generate_section AJUNGE la
    selectia de chain (altfel ar returna fallback-ul de date insuficiente inainte)."""
    return {
        "completeness": {"score": 90},
        "tender_opportunities": {"opportunities": [
            {"title": "Reparatii drum judetean", "authority": "Primaria X",
             "cpv": "45233142", "value": 500000, "deadline": "2026-08-01"}]},
    }


class TestOpportunitiesRoutedToQuality:
    def test_registry_route_preference_is_quality(self):
        # din sectiunea reala emisa de pipeline, nu doar din constanta
        assert _opportunities_section()["route_preference"] == "quality"

    def test_word_target_peste_gardul_fast(self):
        # gardul "<=200 -> fast" (agent_synthesis:262) NU trebuie sa forteze fast:
        # la nivel 3 opportunities are 800w.
        assert _opportunities_section()["word_count"] > 200

    @pytest.mark.asyncio
    async def test_generate_section_foloseste_quality_chain(self):
        agent = m.SynthesisAgent()
        section = _opportunities_section()
        captured: dict = {}

        async def _spy(sec, vd, chain):
            captured["chain"] = chain
            return ("Continut de oportunitati generat.", "claude")

        async def _reflexion_passthrough(text, verified_data, sec):
            return text

        # izolare de retea: capteaza lantul, sari reflexion (poate apela un provider)
        agent._sequential_fallback = _spy            # type: ignore[assignment]
        agent._reflexion_check = _reflexion_passthrough  # type: ignore[assignment]

        out = await agent.generate_section(section, _vd_with_tenders())

        # lantul REAL de calitate, prin identitate de obiect (nu constanta mock-uita)
        assert captured.get("chain") is ai_models.QUALITY_CHAIN
        assert captured["chain"] is not ai_models.SPEED_CHAIN
        assert out["content"], "sectiunea a trecut de gate si a generat continut"
