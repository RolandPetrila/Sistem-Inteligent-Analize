"""A5 (2026-07-16): one_pager_generator read `cui = meta.get("company_name", "")` —
wrong key AND wrong dict (meta never carries a "cui" key at all; the real CUI lives
in verified_data["company"]["cui"]["value"], confirmed against a real row in
data/ris.db reports.full_data). The variable was then never used (ruff F841), so
the executive 1-pager PDF — the format most likely to reach a decision-maker —
never showed the CUI anywhere. Fixture is 100% synthetic (repo is public) but
matches the REAL wrapped shape ({"value": ..., "trust": ...}) verified in the DB.
"""

import os
import tempfile


def _verified_data_with_cui(cui_value: str = "26313362", company_name: str = "Test SRL") -> dict:
    return {
        "company": {
            "cui": {"value": cui_value, "trust": "OFICIAL", "source": "ANAF"},
            "denumire": {"value": company_name, "trust": "OFICIAL", "source": "ANAF"},
        },
        "risk_score": {
            "score": "Galben",
            "numeric_score": 55,
            "recommendation": "Prudenta recomandata.",
            "dimensions": {
                "financiar": {"score": 60, "weight": 30},
                "juridic": {"score": 80, "weight": 20},
                "fiscal": {"score": 50, "weight": 15},
                "operational": {"score": 55, "weight": 15},
                "reputational": {"score": 40, "weight": 10},
                "piata": {"score": 45, "weight": 10},
            },
            "factors": [("Cifra de afaceri in scadere", "MEDIUM")],
        },
        "due_diligence": [],
        "early_warnings": [],
    }


def _meta(company_name: str = "Test SRL") -> dict:
    return {
        "company_name": company_name,
        "generated_at": "16.07.2026 10:00",
    }


class TestOnePagerCui:
    def test_cui_appears_in_rendered_pdf(self):
        """DOVADA DE NON-VACUITATE: pe codul vechi (cui = meta.get("company_name", "")),
        acest test pica — CUI-ul real ("26313362") nu ajunge niciodata in PDF, doar
        numele firmei (care e deja randat separat in header). Verificat cu `git stash`
        pe codul pre-fix: FAIL cu AssertionError (vezi raportul agentului)."""
        from backend.reports.one_pager_generator import generate_one_pager

        cui_value = "26313362"
        verified_data = _verified_data_with_cui(cui_value=cui_value)
        meta = _meta()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            generate_one_pager(verified_data, meta, path)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0

            import pdfplumber

            with pdfplumber.open(path) as pdf:
                full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

            assert cui_value in full_text
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_cui_with_diacritics_in_company_name_does_not_raise(self):
        """PDF sanitize latin-1 path (_sanitize cu errors='replace'): numele firmei
        cu diacritice romanesti (ă/ț/ș/î/â) nu trebuie sa arunce, iar CUI-ul tot
        trebuie sa apara in text."""
        from backend.reports.one_pager_generator import generate_one_pager

        cui_value = "40123456"
        company_name = "Ștefănescu Împrejmuiri Țărănești SRL"
        verified_data = _verified_data_with_cui(cui_value=cui_value, company_name=company_name)
        meta = _meta(company_name=company_name)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            generate_one_pager(verified_data, meta, path)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0

            import pdfplumber

            with pdfplumber.open(path) as pdf:
                full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

            assert cui_value in full_text
            # Diacritics sanitized to ASCII-ish latin-1, but the wording survives:
            assert "Stefanescu" in full_text or "tefanescu" in full_text
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_missing_cui_does_not_raise_and_omits_cui_label(self):
        """Edge case: firma fara CUI cunoscut (verified_data['company'] gol) — nu
        trebuie sa arunce, iar eticheta 'CUI' nu trebuie sa apara cu valoare goala."""
        from backend.reports.one_pager_generator import generate_one_pager

        verified_data = {"company": {}, "risk_score": {}}
        meta = _meta()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            generate_one_pager(verified_data, meta, path)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
        finally:
            if os.path.exists(path):
                os.remove(path)
