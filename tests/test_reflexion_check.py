"""
Test de regresie: SynthesisAgent._reflexion_check() (backend/agents/agent_synthesis.py)
citea risk_score.get("risk_factors", [])[:5], dar calculate_risk_score()
(backend/agents/verification/scoring.py:1171) scrie factorii de risc sub
cheia "factors" — NICIODATA "risk_factors". Acelasi fisier foloseste cheia
corecta ("factors") in alte 2 locuri (_extract_bullets_for_section,
_build_context_summary), doar reflexion-ul avea typo-ul.

Impact: cand reflexion-ul detecteaza o contradictie ton/scor si cere Groq
sa corecteze textul, promptul de corectie trimis modelului avea sectiunea
"FACTORI DETERMINANTI" mereu goala ("N/A"), chiar cand existau factori reali
de risc in date.
"""
import pytest

from backend.agents.agent_synthesis import SynthesisAgent


@pytest.fixture
def agent():
    return SynthesisAgent()


def _verified_data_with_factors():
    return {
        "risk_score": {
            "numeric_score": 25,
            "score": "Rosu",
            "factors": [
                ("Litigii multiple active pe portal.just.ro", "HIGH"),
                ("Pierdere neta raportata 2 ani consecutivi", "HIGH"),
            ],
        }
    }


class TestReflexionCheckFactorsKey:
    @pytest.mark.asyncio
    async def test_prompt_contine_factorii_reali_nu_na(self, agent, monkeypatch):
        """Contradictie declansata: scor Rosu + text cu limbaj pozitiv.
        Promptul trimis catre Groq trebuie sa contina factorii reali din
        risk_score['factors'], nu 'FACTORI DETERMINANTI:\\nN/A'."""
        captured_prompts = []

        async def fake_groq(prompt: str) -> str:
            captured_prompts.append(prompt)
            # Text suficient de lung ca sa treaca pragul de acceptare din _reflexion_check.
            return "Text corectat " * 40

        monkeypatch.setattr(agent, "_generate_with_groq", fake_groq)

        text = "Compania este stabila si solida, cu o traiectorie excelenta si performanta."
        section = {"key": "risk_assessment", "title": "Evaluare Risc"}

        await agent._reflexion_check(text, _verified_data_with_factors(), section)

        assert len(captured_prompts) == 1, "reflexion nu a declansat corectia Groq (contradictia nu a fost detectata)"
        prompt = captured_prompts[0]
        assert "Litigii multiple active pe portal.just.ro" in prompt
        assert "Pierdere neta raportata 2 ani consecutivi" in prompt
        assert "FACTORI DETERMINANTI:\nN/A" not in prompt

    @pytest.mark.asyncio
    async def test_fara_factori_reali_prompt_are_na_explicit(self, agent, monkeypatch):
        """Contrast: daca risk_score chiar nu are factori, N/A e comportamentul
        corect (nu un fallback mascat de cheia gresita)."""
        captured_prompts = []

        async def fake_groq(prompt: str) -> str:
            captured_prompts.append(prompt)
            return "Text corectat " * 40

        monkeypatch.setattr(agent, "_generate_with_groq", fake_groq)

        text = "Compania este stabila si solida, cu o traiectorie excelenta si performanta."
        section = {"key": "risk_assessment", "title": "Evaluare Risc"}
        verified_data = {"risk_score": {"numeric_score": 25, "score": "Rosu", "factors": []}}

        await agent._reflexion_check(text, verified_data, section)

        assert len(captured_prompts) == 1
        assert "FACTORI DETERMINANTI:\nN/A" in captured_prompts[0]
