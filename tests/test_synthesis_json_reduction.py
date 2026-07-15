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
