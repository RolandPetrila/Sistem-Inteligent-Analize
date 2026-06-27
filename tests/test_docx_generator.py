"""
Teste pentru docx_generator — generare document Word din report_sections.
"""
import os
import tempfile


def _make_sections() -> dict:
    return {
        "executive_summary": {"title": "Rezumat Executiv", "content": "Firma este stabila."},
        "financial_analysis": {"title": "Analiza Financiara", "content": "Cifra de afaceri a crescut."},
    }


def _make_meta() -> dict:
    return {
        "title": "Raport RIS",
        "company_name": "Test SRL",
        "report_level": 2,
        "generated_at": "2026-04-08T10:00:00",
        "sources_count": 3,
        "risk_score": {"score": 72, "label": "Verde"},
        "sources": ["ANAF", "ONRC"],
    }


class TestGenerateDocx:
    def test_creeaza_fisier_docx(self):
        from backend.reports.docx_generator import generate_docx

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            path = f.name
        try:
            generate_docx(_make_sections(), _make_meta(), path)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_functioneaza_cu_sectiuni_goale(self):
        from backend.reports.docx_generator import generate_docx

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            path = f.name
        try:
            generate_docx({}, _make_meta(), path)
            assert os.path.exists(path)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_functioneaza_cu_verified_data_due_diligence(self):
        from backend.reports.docx_generator import generate_docx

        verified_data = {
            "due_diligence": [
                {"check": "Firma activa", "status": "DA"},
                {"check": "Platitor TVA", "status": "DA"},
            ],
            "early_warnings": [
                {"warning": "Scadere CA > 30%"},
            ],
        }

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            path = f.name
        try:
            generate_docx(_make_sections(), _make_meta(), path, verified_data)
            assert os.path.exists(path)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_functioneaza_cu_meta_incomplet(self):
        from backend.reports.docx_generator import generate_docx

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            path = f.name
        try:
            generate_docx(_make_sections(), {"title": "Minimal"}, path)
            assert os.path.exists(path)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_functioneaza_cu_rich_fields_aegrm_historical(self):
        """TASK 2: populated AEGRM + historical OSINT flags (cu diacritice) prin DOCX.
        Sectiunea 'Garantii si Istoric (OSINT)' nu e atinsa de firme curate (fara
        semnale), deci asta e singura acoperire pentru calea populata DOCX."""
        from backend.reports.docx_generator import generate_docx

        verified_data = {
            "risk": {
                "aegrm_guarantees": {
                    "value": {
                        "has_data": True,
                        "count": 2,
                        "has_guarantees": True,
                        "guarantees": [
                            {"descriere": "Gaj mobiliar — autovehicul, garanție către BCR"},
                            {"creditor": "Banca Transilvania S.A. — ipotecă mobiliară"},
                        ],
                    }
                }
            },
            "historical_flags": [
                {
                    "type": "cesiune_parti_sociale",
                    "label": "Cesiune părți sociale detectată",
                    "severity": "HIGH",
                    "detail": "Schimbare asociați — cesiune 60% părți sociale",
                    "date": "2023-05-12",
                },
                {
                    "type": "dizolvare_lichidare",
                    "label": "Dizolvare / Lichidare / Radiere",
                    "severity": "CRITICAL",
                    "detail": "Mențiune privind dizolvarea voluntară înregistrată la ONRC",
                    "date": "2024-01-08",
                },
            ],
        }

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            path = f.name
        try:
            generate_docx(_make_sections(), _make_meta(), path, verified_data)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
        finally:
            if os.path.exists(path):
                os.remove(path)
