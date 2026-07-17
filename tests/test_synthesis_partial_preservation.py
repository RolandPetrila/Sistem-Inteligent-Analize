"""
Regresie pt bug-ul real 2026-07-17 (job TAROM 646s -> "AGENT_SYNTHESIS | END | 0 sections"
-> Report formats: none): timeout-ul global (base.py::run -> asyncio.wait_for(total_timeout))
ANULA execute() la depasire si ARUNCA cele 4-6 sectiuni deja scrise -> raport zero.

Fix: execute() gestioneaza un DEADLINE INTERN si, cand il depaseste, randeaza sectiunile
ramase DETERMINIST (fara AI) in loc sa lase timeout-ul extern sa anuleze tot. Proprietatea
garantata: **execute() returneaza MEREU un report_sections cu TOATE cheile de sectiune** —
o sectiune lenta nu mai poate zero-iza raportul, indiferent de timp.

Non-vacuitate: testul forteaza deadline-ul depasit dupa prima sectiune (prin monkeypatch pe
time.monotonic din modul) si verifica atat ca nimic nu se pierde (toate cheile prezente), cat
si ca sectiunile de dupa deadline sunt marcate degradate (word_count 0). Pe codul VECHI
(bucla fara verificare de deadline, fara ramura de degradare) acest test nu ar putea exista —
nu exista `over_budget`/randare determinista de umplere.
"""
import pytest

import backend.agents.agent_synthesis as m
from backend.prompts.section_prompts import get_sections_for_analysis


def _minimal_verified_data() -> dict:
    return {
        "company": {
            "denumire": {"value": "TEST SRL"},
            "cui": {"value": "123456"},
            "caen_code": {"value": "5110"},
            "caen_description": {"value": "Transporturi"},
            "stare_firma": {"value": "activa"},
            "adresa": {"value": "Bucuresti"},
        },
        "financial": {
            "cifra_afaceri": {"value": 1_000_000},
            "profit_net": {"value": 50_000},
            "numar_angajati": {"value": 10},
            "capitaluri_proprii": {"value": 200_000},
        },
        "risk_score": {"numeric_score": 80, "score": "Verde", "factors": []},
        "completeness": {"score": 90, "gaps": []},
        "market": {}, "legal": {}, "due_diligence": {},
    }


@pytest.mark.asyncio
async def test_execute_preserves_all_sections_when_deadline_exceeded(monkeypatch):
    agent = m.SynthesisAgent()
    vd = _minimal_verified_data()
    state = {
        "verified_data": vd,
        "analysis_type": "FULL_COMPANY_PROFILE",
        "report_level": 3,
        "job_id": "",
    }
    expected_keys = {s["key"] for s in get_sections_for_analysis("FULL_COMPANY_PROFILE", 3, vd)}

    # generate_section mockuit: instant, nu apeleaza niciun provider AI real
    real_written = []

    async def fake_generate_section(section, verified_data, job_id=""):
        real_written.append(section["key"])
        return {"title": section["title"], "content": "TEXT REAL", "word_count": 5}

    monkeypatch.setattr(agent, "generate_section", fake_generate_section)

    async def fake_takeaways(_):
        return ""

    monkeypatch.setattr(agent, "_generate_key_takeaways", fake_takeaways)

    # Forteaza deadline depasit DUPA prima sectiune reala:
    #   call #1 = calcul deadline (t=base) ; call #2 = check sectiunea 0 (t=base, < deadline -> reala)
    #   call #3+ = check sectiunilor urmatoare (t=base+1e9, > deadline -> degradate)
    base = 1000.0
    seq = [base, base]

    def fake_monotonic():
        return seq.pop(0) if seq else base + 1e9

    monkeypatch.setattr(m.time, "monotonic", fake_monotonic)

    result = await agent.execute(state)
    sections = result["report_sections"]

    # 1. NIMIC pierdut: toate cheile de sectiune prezente (proprietatea centrala)
    assert set(sections.keys()) == expected_keys, (
        f"Sectiuni pierdute! asteptat {expected_keys}, primit {set(sections.keys())}"
    )
    # 2. Fiecare intrare are forma corecta (title/content/word_count)
    for key, sec in sections.items():
        assert set(sec.keys()) >= {"title", "content", "word_count"}, f"forma gresita pt {key}"
        assert sec["content"], f"continut gol pt {key}"
    # 3. Exact prima sectiune a fost scrisa real; restul degradate (word_count 0)
    assert len(real_written) == 1, f"asteptat 1 sectiune reala inainte de deadline, {len(real_written)}"
    degraded = [k for k, s in sections.items() if s["word_count"] == 0]
    assert len(degraded) == len(expected_keys) - 1, "restul sectiunilor ar trebui degradate"


@pytest.mark.asyncio
async def test_execute_no_degradation_when_within_budget(monkeypatch):
    """Non-regresie: cand totul incape in buget, NICIO sectiune nu e degradata —
    comportament identic cu bucla veche (toate merg prin generate_section)."""
    agent = m.SynthesisAgent()
    vd = _minimal_verified_data()
    state = {
        "verified_data": vd,
        "analysis_type": "FULL_COMPANY_PROFILE",
        "report_level": 3,
        "job_id": "",
    }
    written = []

    async def fake_generate_section(section, verified_data, job_id=""):
        written.append(section["key"])
        return {"title": section["title"], "content": "TEXT REAL", "word_count": 100}

    monkeypatch.setattr(agent, "generate_section", fake_generate_section)

    async def fake_takeaways(_):
        return ""

    monkeypatch.setattr(agent, "_generate_key_takeaways", fake_takeaways)

    # time.monotonic normal (nedepasit) — deadline foarte in viitor
    result = await agent.execute(state)
    sections = result["report_sections"]
    expected_keys = {s["key"] for s in get_sections_for_analysis("FULL_COMPANY_PROFILE", 3, vd)}

    assert set(sections.keys()) == expected_keys
    assert len(written) == len(expected_keys), "toate sectiunile trebuie generate real (nimic degradat)"
    assert all(s["word_count"] > 0 for s in sections.values())
