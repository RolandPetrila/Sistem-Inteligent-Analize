"""
Runda 2 / C: `_reduce_verified_data_for_json` inlocuieste slice-ul orb de caractere
din `_build_section_prompt` (care taia JSON-ul la mijloc si producea text sintactic
invalid) cu o reducere PE CHEI INTREGI — rezultatul trebuie sa fie mereu JSON valid.

Non-vacuitate: `test_blind_slice_on_old_code_produces_invalid_json` documenteaza
exact ce producea codul VECHI (slice orb) — verificat separat cu `git stash` ca
noul cod NU se comporta asa (vezi raportul Sonnet in Roland_Opus_Sonnet.md).
"""

import json

import pytest

from backend.agents.agent_synthesis import _CORE_JSON_FIELDS, SynthesisAgent


@pytest.fixture
def agent():
    return SynthesisAgent()


def _big_verified_data() -> dict:
    """Nucleu mic + campuri optionale voluminoase — suficient de mare incat sa
    depaseasca limite mici de test, dar cu structura reala (chei cunoscute)."""
    return {
        "company": {"denumire": {"value": "Test SRL"}, "cui": {"value": "12345678"}},
        "financial": {"cifra_afaceri": {"value": 1_000_000}},
        "risk": {"insolvency": {"value": {"found": False}}},
        "risk_score": {"score": "Verde", "numeric_score": 87.3, "dimensions": {}},
        "completeness": {"score": 80, "gaps": []},
        "credit_exposure": {"expunere_ron": 100000},
        "predictive_scores": {"altman_z": {"zone": "safe"}},
        # Optionale, voluminoase — candidati de eliminat in ordinea _JSON_DROP_PRIORITY.
        "market": {"seap": {"value": {"contracts": ["x" * 500 for _ in range(20)]}}},
        "web_presence": {"blob": "y" * 5000},
        "tender_opportunities": {"opportunities": ["z" * 500 for _ in range(20)]},
    }


class TestReduceVerifiedDataForJson:
    def test_small_data_passes_through_unchanged(self, agent):
        data = {"company": {"denumire": "Test"}}
        data_json, omitted = agent._reduce_verified_data_for_json(data, json_limit=50000)
        assert omitted == []
        assert json.loads(data_json) == data

    def test_reduction_drops_optional_keys_and_stays_valid_json(self, agent):
        data = _big_verified_data()
        full_json = json.dumps(data, ensure_ascii=False, default=str, indent=2)
        assert len(full_json) > 5000  # confirma ca fixture-ul chiar depaseste limita de test

        data_json, omitted = agent._reduce_verified_data_for_json(data, json_limit=5000)

        assert len(data_json) <= 5000 + 200  # tolereaza eticheta de comprimare nucleu, daca apare
        parsed = json.loads(data_json)  # NU trebuie sa arunce — JSON mereu valid
        assert omitted, "Ar fi trebuit sa elimine cel putin o cheie optionala"
        # Nucleul supravietuieste — niciodata eliminat ca bloc intreg.
        for core_key in ("company", "financial", "risk_score", "completeness"):
            assert core_key in parsed, f"{core_key} nu ar trebui eliminat niciodata"

    def test_core_fields_never_dropped_as_whole_keys(self, agent):
        """Chiar la o limita foarte mica (sub marimea campurilor optionale insele),
        cheile din _CORE_JSON_FIELDS raman prezente (eventual comprimate, nu sterse)."""
        data = _big_verified_data()
        data_json, omitted = agent._reduce_verified_data_for_json(data, json_limit=800)
        parsed = json.loads(data_json)
        present_core = _CORE_JSON_FIELDS & parsed.keys()
        assert present_core, "Nucleul nu ar trebui sa dispara complet nici la limite mici"
        assert omitted  # ceva a fost omis/comprimat — nu poate fi liniste completa

    def test_omission_is_never_silent(self, agent):
        data = _big_verified_data()
        _, omitted = agent._reduce_verified_data_for_json(data, json_limit=3000)
        # Fiecare element din omitted e ori un nume de cheie reala, ori o eticheta
        # descriptiva de comprimare a nucleului — niciodata un marker gol.
        assert all(isinstance(o, str) and o for o in omitted)

    def test_extreme_limit_falls_back_to_headline_but_stays_valid_json(self, agent):
        """Limita absurd de mica (sub orice camp de nucleu comprimat) -> fallback
        la headline (company/risk_score/completeness), dar JSON mereu valid."""
        data = _big_verified_data()
        data_json, omitted = agent._reduce_verified_data_for_json(data, json_limit=50)
        parsed = json.loads(data_json)  # nu trebuie sa arunce nici la limita absurda
        assert isinstance(parsed, dict)
        assert omitted


def _opportunities_fixture() -> dict:
    """Fixture SINTETIC (repo public — zero date reale de firme): nucleu mic + 4
    campuri optionale de care sectiunea 'opportunities' DEPINDE (verificat la sursa:
    `_has_sufficient_data('opportunities')` + `section_data_map['opportunities']` din
    `_extract_raw_dict_for_section`) + 2 campuri optionale mari dar IRELEVANTE pentru
    ea (`agent_diagnostics`, `due_diligence`). Dimensionat astfel incat, la
    json_limit=4000, ordinea VECHE (dupa marime, fara constienta de sectiune) taie
    exact campurile relevante primele (tender_opportunities e primul din
    `_JSON_DROP_PRIORITY`), inainte de campurile irelevante."""
    return {
        "company": {"denumire": {"value": "Test SRL"}, "cui": {"value": "12345678"}},
        "financial": {"cifra_afaceri": {"value": 1_000_000}},
        "risk": {"insolvency": {"value": {"found": False}}},
        "risk_score": {"score": "Verde", "numeric_score": 87.3, "dimensions": {}},
        "completeness": {"score": 80, "gaps": []},
        "credit_exposure": {"expunere_ron": 100000},
        "predictive_scores": {"altman_z": {"zone": "safe"}},
        "tender_opportunities": {"opportunities": [{"title": "Licitatie SEAP X"}]},
        "market": {"seap": {"value": {"contracts_verified": True, "total_contracts": 3}}},
        "funding_programs": {"eligible": [{"name": "PNRR"}]},
        "web_presence": {"opportunities": ["oportunitate web"]},
        # Irelevante pt "opportunities", dar voluminoase -> ar trebui taiate INAINTEA
        # campurilor de mai sus, o data ce sectiunea e constienta de nevoile ei.
        "agent_diagnostics": {"blob": "d" * 3000},
        "due_diligence": {"blob": "e" * 3000},
    }


class TestSectionAwareProtection:
    """Bug confirmat pe date reale (2026-07-16, masurat pe data/ris.db, 72 rapoarte):
    82% aveau nucleul JSON pt route 'fast' (limita 20000) suficient de mare incat
    `_JSON_DROP_PRIORITY` taia efectiv tender_opportunities/market/funding_programs —
    exact campurile care alimenteaza sectiunea 'opportunities' (route 'fast' —
    `SECTION_PROVIDER_PREFERENCE`), taiate INAINTEA unor campuri irelevante pt ea
    (ex. agent_diagnostics). Fix: `_reduce_verified_data_for_json` accepta
    `section_key` si muta campurile din `_SECTION_PROTECTED_OPTIONAL_FIELDS[section_key]`
    la finalul ordinii de taiere (nu le scoate din ea)."""

    def test_opportunities_section_protects_its_own_fields(self, agent):
        data = _opportunities_fixture()
        data_json, omitted = agent._reduce_verified_data_for_json(
            data, json_limit=4000, section_key="opportunities")
        parsed = json.loads(data_json)

        # Campul care da bug-ul numele lui — supravietuieste taierii.
        assert "tender_opportunities" in parsed
        assert "tender_opportunities" not in omitted
        # Restul campurilor de care sectiunea depinde REAL supravietuiesc si ele.
        for needed in ("market", "funding_programs", "web_presence"):
            assert needed in parsed, f"{needed} ar fi trebuit protejat pt 'opportunities'"

        # Campul mare dar IRELEVANT pentru sectiune e cel taiat, nu cele relevante.
        assert "agent_diagnostics" in omitted
        assert "agent_diagnostics" not in parsed

    def test_other_sections_keep_the_original_size_based_order(self, agent):
        """Non-regresie: o sectiune fara intrare in _SECTION_PROTECTED_OPTIONAL_FIELDS
        (ex. 'financial_analysis') taie EXACT in ordinea veche — tender_opportunities
        tot primul, la fel ca inainte de fix (section_key=None == comportament vechi)."""
        data = _opportunities_fixture()

        data_json_no_section, omitted_no_section = agent._reduce_verified_data_for_json(
            data, json_limit=4000)
        data_json_unmapped, omitted_unmapped = agent._reduce_verified_data_for_json(
            data, json_limit=4000, section_key="financial_analysis")

        assert omitted_unmapped == omitted_no_section
        assert data_json_unmapped == data_json_no_section
        # Documenteaza explicit bug-ul original (fara protectie de sectiune):
        # tender_opportunities e taiat PRIMUL, inaintea campurilor irelevante.
        assert omitted_no_section[0] == "tender_opportunities"
        assert "tender_opportunities" not in json.loads(data_json_no_section)


class TestBlindSliceRegressionDocumentation:
    """Documenteaza exact defectul codului VECHI (pastrat aici ca proba, verificat
    separat cu `git stash` ca noul `_reduce_verified_data_for_json` NU-l reproduce —
    vezi non-vacuitatea raportata in Roland_Opus_Sonnet.md)."""

    def test_blind_slice_on_old_code_produces_invalid_json(self):
        big = {"a": "x" * 10000}
        full_json = json.dumps(big, ensure_ascii=False, default=str, indent=2)
        json_limit = 100
        # Comportamentul VECHI, exact cum era in _build_section_prompt inainte de fix:
        old_behavior = full_json[:json_limit] + f"\n... [date trunchiate la {json_limit} chars pt test]"
        with pytest.raises(json.JSONDecodeError):
            json.loads(old_behavior)
