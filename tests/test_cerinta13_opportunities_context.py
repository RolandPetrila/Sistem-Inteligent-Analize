"""CERINTA #13 (P1): sectiunea narativa "Oportunitati" era OARBA la propriile date.

Bug real (audit raport MOSSLEIN, job 1eabf5ab, 2026-07-26): `report_sections
["opportunities"]` spunea "Nu au fost identificate oportunitati concrete ...
[INDISPONIBIL]" desi acelasi `full_data` avea 15 licitatii deschise + 1 program de
finantare + 526 contracte SEAP (randate STRUCTURAT in aceeasi pagina) -> raportul se
contrazicea pe sine. Cauza: `_build_context_summary` NU avea ramura "opportunities",
iar pe ruta SPEED (buget JSON mic) datele ajungeau doar via dump-ul JSON brut, care le
evicta / nu le scotea la suprafata.

Non-vacuitate (regula proiectului: testul PICA pe codul vechi de la HEAD):
  - TEST A: pe HEAD, `_build_context_summary("opportunities", ...)` NU randeaza nicio
            licitatie -> titlul lipseste din output.
  - TEST B: pe HEAD, cand bugetul JSON evacueaza `tender_opportunities`, titlul licitatiei
            NU mai ajunge la model (context_summary nu-l are, JSON-ul l-a taiat) -> lipseste
            din promptul asamblat. E chiar modul de esec de PRODUCTIE (ruta fast, buget mic).

NOTA (non-vacuitate): se importa DOAR `SynthesisAgent` la nivel de modul (exista si pe
HEAD). `ai_models` se importa lazy in TEST B — pe swap-ul de non-vacuitate se schimba
`agent_synthesis.py`, nu `ai_models.py`, deci importul lazy nu poate esua la colectare si
masca esecul comportamental (lectia #12).
"""

from backend.agents.agent_synthesis import SynthesisAgent

# Forme verificate la PRODUCATOR (rich_fields.py / html_generator.py — sursele care le
# randeaza deja structurat), nu inventate:
#   tender_opportunities.opportunities = list[{title, authority, cpv, value, deadline, ...}]
#   funding_programs.eligible          = list[{nume, suma_max_eur, termen, ...}]
#   market.seap                        = (posibil wrapped .value) {total_contracts, ...}
_TENDER_TITLE = "Reabilitare retea de apa si canalizare Sector 3"
_FUNDING_NAME = "Granturi IMM 200K EUR"


def _data_with_opportunities() -> dict:
    return {
        "company": {"denumire": {"value": "MOSSLEIN"}, "cui": {"value": "26313362"}},
        "risk_score": {"numeric_score": 87, "score": "Verde"},
        "completeness": {"score": 94},
        "tender_opportunities": {
            "available": True,
            "count": 2,
            "opportunities": [
                {"title": _TENDER_TITLE, "authority": "Primaria Sector 3",
                 "cpv": "45231300", "value": 1_200_000, "deadline": "2026-08-15"},
                {"title": "Furnizare pompe submersibile", "authority": " APA NOVA",
                 "cpv": "42122130", "value": 350_000, "deadline": "2026-09-01"},
            ],
        },
        "funding_programs": {
            "eligible": [
                {"nume": _FUNDING_NAME, "suma_max_eur": 200_000, "termen": "2026-12-31"},
            ],
            "summary": "1 program eligibil pe profil",
        },
        "market": {"seap": {"value": {"total_contracts": 526}}},
    }


def test_context_summary_opportunities_surfaces_real_data():
    """TEST A: ramura noua randeaza cel putin UN titlu de licitatie REAL + suma unui
    program de finantare + istoricul SEAP. Pe HEAD (fara ramura opportunities) PICA."""
    agent = SynthesisAgent()
    out = agent._build_context_summary("opportunities", _data_with_opportunities())

    # (a) >= 1 titlu de licitatie real
    assert _TENDER_TITLE in out
    # (b) programul de finantare cu suma (verificam si suma formatata, nu doar numele)
    assert _FUNDING_NAME in out
    assert "200,000 EUR" in out
    # (c) rezumat SEAP
    assert "526" in out
    # detalii utile pt naratiune (autoritate + CPV) prezente
    assert "Primaria Sector 3" in out
    assert "45231300" in out


def test_context_summary_opportunities_empty_is_graceful():
    """Fara date de oportunitati -> ramura nu adauga nimic (nu arunca, nu inventeaza).
    Legitim: cand chiar nu exista licitatii, naratiunea "nimic gasit" e CORECTA."""
    agent = SynthesisAgent()
    data = {
        "company": {"denumire": {"value": "ACME"}, "cui": {"value": "123"}},
        "risk_score": {}, "completeness": {},
    }
    out = agent._build_context_summary("opportunities", data)
    # nu apare niciun antet de oportunitati (dar nici nu crapa — context comun ramane)
    assert "Licitatii deschise" not in out
    assert "Programe de finantare" not in out
    assert "ACME" in out  # contextul comun tot se randeaza


def test_opportunity_title_survives_json_eviction(monkeypatch):
    """TEST B (modul real de esec, PRODUCTIE): pe ruta fast bugetul JSON mic evacueaza
    `tender_opportunities` din dump. Titlul licitatiei TREBUIE sa ajunga totusi la model
    via CONTEXT STRUCTURAT. Pe HEAD PICA: fara ramura opportunities in context_summary,
    titlul lipseste din prompt cand JSON-ul il taie."""
    from backend.agents import ai_models

    agent = SynthesisAgent()
    # Buget mic -> _reduce_verified_data_for_json evacueaza campurile optionale (inclusiv
    # tender_opportunities, care NU e in _CORE_JSON_FIELDS) din blocul JSON.
    monkeypatch.setattr(ai_models, "get_json_char_budget", lambda provider: 120)

    section = {"key": "opportunities", "title": "Oportunitati",
               "prompt": "Prezinta oportunitatile.", "word_count": 400}
    prompt = agent._build_section_prompt(section, _data_with_opportunities(), provider="groq")

    # (a) titlul e prezent in prompt (via CONTEXT STRUCTURAT) ...
    assert _TENDER_TITLE in prompt
    # (b) ... DAR blocul JSON de mai jos NU-l contine (a fost evacuat de bugetul mic) ->
    #     dovedeste ca vizibilitatea vine din context_summary, nu din dump-ul JSON.
    json_block = prompt.split("--- DATE VERIFICATE (JSON) ---", 1)[1]
    assert _TENDER_TITLE not in json_block
    # santinela: eticheta de omitere confirma ca tender_opportunities chiar a fost taiat
    assert "tender_opportunities" in json_block  # apare in nota "[omise pt limita...]"
