"""CERINTA #16 (E3) — garda de doc-drift, functia PURA.

Testeaza `doc_drift_verdict` pe liste sintetice de cai (fara git, fara working tree) —
per advisor: NU un pytest care inspecteaza `git diff` (ar pica pe orice commit legitim
cod-only si s-ar comporta diferit local vs CI). Non-vac: pica pe un diff cod-fara-doc.
"""
from tools.check_doc_drift import doc_drift_verdict, is_code_path


class TestVerdictDocDrift:
    def test_cod_fara_doc_e_drift(self):
        v = doc_drift_verdict(["backend/agents/agent_synthesis.py"])
        assert v["drift"] is True
        assert v["code_changed"] is True and v["doc_changed"] is False

    def test_cod_cu_doc_nu_e_drift(self):
        v = doc_drift_verdict(["backend/agents/agent_synthesis.py", "CLAUDE.md"])
        assert v["drift"] is False
        assert v["doc_changed"] is True

    def test_doar_teste_nu_e_drift(self):
        # testele NU sunt cod de productie care trebuie reflectat in doc
        v = doc_drift_verdict(["tests/test_x.py", "backend/agents/tools/__pycache__/x.pyc"])
        assert v["drift"] is False
        assert v["code_changed"] is False

    def test_doar_docuri_nu_e_drift(self):
        v = doc_drift_verdict(["CLAUDE.md", "docs/FUNCTII_SISTEM.md"])
        assert v["drift"] is False
        assert v["code_changed"] is False

    def test_frontend_sursa_conteaza(self):
        v = doc_drift_verdict(["frontend/src/pages/Dashboard.tsx"])
        assert v["drift"] is True

    def test_cai_windows_backslash(self):
        v = doc_drift_verdict(["backend\\config.py"])
        assert v["drift"] is True


class TestIsCodePath:
    def test_backend_py_e_cod(self):
        assert is_code_path("backend/config.py") is True

    def test_test_file_nu_e_cod(self):
        assert is_code_path("tests/test_config.py") is False
        assert is_code_path("backend/agents/test_helper.py") is False

    def test_doc_nu_e_cod(self):
        assert is_code_path("CLAUDE.md") is False
        assert is_code_path("backend/README.md") is False
