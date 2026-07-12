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

    def test_sanctions_hit_rendered(self):
        """Screening sanctiuni HIT cu diacritice — nu trebuie sa arunce, fisier valid."""
        from backend.reports.docx_generator import generate_docx

        verified_data = {
            "sanctions": {
                "status": "hit",
                "hits": [{"query": "Ștefan Popescu", "matched_name": "POPESCU, Ștefán",
                          "source": "OFAC", "type": "individual"}],
                "checked": ["Firma Țăndărei SRL", "Ștefan Popescu"],
                "lists_checked": ["OFAC", "EU", "UN"],
                "data_date": "2026-07-11T00:00:00Z", "total_entries": 53000,
            }
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

    def test_eurostat_sector_rendered(self):
        """Benchmark sector UE (Eurostat) — nu trebuie sa arunce, fisier valid."""
        from backend.reports.docx_generator import generate_docx

        verified_data = {
            "eurostat_sector": {
                "available": True, "nace_used": "J62", "nace_label": "Computer programming",
                "year": "2024",
                "indicators": {
                    "ENT_NR": {"label": "Numar firme", "ro": 45240, "eu": 1008501, "nace": "J62"},
                    "EMP_ENT_NR": {"label": "Angajati / firma", "ro": 4, "eu": 5, "nace": "J62"},
                },
            }
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

    def test_seap_procurement_history_rendered(self):
        """Istoric achizitii publice SEAP cu diacritice — nu trebuie sa arunce."""
        from backend.reports.docx_generator import generate_docx

        verified_data = {"market": {"seap": {"value": {
            "total_contracts": 2, "contracts_count": 1, "direct_count": 1, "total_value": 900000,
            "contracts": [{"title": "Lucrări reabilitare școală", "value": 850000, "currency": "RON",
                           "authority": "Primăria Târgoviște", "date": "2025-01-15"}],
            "direct_acquisitions": [{"title": "Achiziție consumabile", "value": 5000,
                                     "authority": "Spitalul Județean", "date": "2024-09-10"}],
        }}}}
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            path = f.name
        try:
            generate_docx(_make_sections(), _make_meta(), path, verified_data)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_tender_opportunities_rendered(self):
        """Angle A: oportunitati SICAP cu diacritice — nu trebuie sa arunce."""
        from backend.reports.docx_generator import generate_docx

        verified_data = {"tender_opportunities": {"available": True, "count": 1, "days_back": 30,
            "opportunities": [{"title": "Construcție grădiniță", "authority": "Primăria Târgoviște",
                               "cpv": "45214100-1", "value": 750000, "deadline": "2026-08-01", "notice_no": "CN5"}]}}
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            path = f.name
        try:
            generate_docx(_make_sections(), _make_meta(), path, verified_data)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
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
            # Exact shape emitted by osint_client: {type, label, severity, snippet}.
            "historical_flags": [
                {
                    "type": "cesiune_parti_sociale",
                    "label": "Cesiune părți sociale detectată",
                    "severity": "HIGH",
                    "snippet": "Schimbare asociați — cesiune 60% părți sociale",
                },
                {
                    "type": "dizolvare_lichidare",
                    "label": "Dizolvare / Lichidare / Radiere",
                    "severity": "CRITICAL",
                    "snippet": "Mențiune privind dizolvarea voluntară înregistrată la ONRC",
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
