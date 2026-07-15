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

    def test_risk_factors_rendered_with_diacritics_and_severity_order(self):
        """BUG2 (2026-07-16): risk_score['factors'] was never rendered in DOCX — the
        score's actual drivers (BPI insolvency, litigation, Monitorul Oficial cesiuni)
        were invisible in this format. Fixture is 100% synthetic (repo public) and
        includes diacritics; assert CONTENT (not just 'does not raise'), and assert
        CRITICAL factors are ordered before HIGH regardless of input list order."""
        from docx import Document

        from backend.reports.docx_generator import generate_docx

        verified_data = {
            "risk_score": {
                "numeric_score": 15,
                "score": "Rosu",
                "factors": [
                    ("Firma inactiva la ANAF", "HIGH"),
                    ("ZOMBIE: CA=0 + angajati=0 + status activ - firma nu opereaza", "CRITICAL"),
                    ("Firma in insolvență - dosar deschis la Tribunalul Târgoviște", "CRITICAL"),
                    ("Litigii găsite - cauțiune și garanție reală mobiliară", "MEDIUM"),
                    ("Dosare judecătorești multiple", "LOW"),
                ],
            }
        }
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            path = f.name
        try:
            generate_docx(_make_sections(), _make_meta(), path, verified_data)
            doc = Document(path)
            paragraphs = [p.text for p in doc.paragraphs]
            full_text = "\n".join(paragraphs)

            assert "Factori de Risc" in full_text
            assert "[CRITICAL]" in full_text
            assert "[HIGH]" in full_text
            assert "ZOMBIE" in full_text
            assert "Tribunalul Târgoviște" in full_text
            assert "Dosare judecătorești multiple" in full_text

            # Severity ordering: both CRITICAL paragraphs before the HIGH paragraph,
            # regardless of the order they appear in the input list.
            idx_zombie = next(i for i, t in enumerate(paragraphs) if "ZOMBIE" in t)
            idx_insolventa = next(i for i, t in enumerate(paragraphs) if "Tribunalul Târgoviște" in t)
            idx_high = next(i for i, t in enumerate(paragraphs) if t.startswith("[HIGH]"))
            assert idx_zombie < idx_high
            assert idx_insolventa < idx_high
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_docx_content_all_rich_sections_rendered(self):
        """DRY #3 (2026-07-14): verifica CONTINUTUL randat (nu doar 'nu arunca'),
        pe fixture-ul populat -- companion la TestRichFields (html) + TestRichFieldsPdf."""
        from docx import Document

        from backend.reports.docx_generator import generate_docx

        verified_data = {
            "predictive_scores": {
                "altman_z": {"z_score": 2.9, "zone": "SAFE"},
                "piotroski_f": {"f_score": 7, "max_possible": 9, "grade": "STRONG"},
                "beneish_m": {"m_score": -2.5, "risk": "OK"},
                "zmijewski_x": {"x_score": -1.2, "distress": False, "available": True},
                "distress_signals": 0,
                "summary": "Indicatori in zona normala",
            },
            "benchmark": {
                "available": True, "caen_code": "6201", "caen_section_name": "IT",
                "nr_firme_sector": 1200,
                "comparisons": [{"metric": "Cifra de afaceri", "firma": 500000,
                                 "media_sector": 450000, "ratio": 1.1, "pozitie": "Peste medie"}],
            },
            "actionariat": {"available": True, "asociati": [{"nume": "Ion Popescu"}],
                            "administratori": ["Maria Ionescu"], "capital_social": 200, "stare": "activa"},
            "relations": {"flags": [{"type": "ONE_PERSON", "detail": "Admin = asociat", "severity": "INFO"}]},
            "risk": {"aegrm_guarantees": {"value": {"has_data": True, "count": 1,
                     "has_guarantees": True, "details": [
                         {"nr_inregistrare": "2024-000123", "data": "2024-03-11",
                          "creditor": "Banca Exemplu SA", "tip_bun": "Gaj auto", "status": "ACTIV"},
                     ]}}},
            "historical_flags": [{"type": "cesiune_parti_sociale",
                                  "label": "Cesiune parti sociale detectata", "severity": "HIGH",
                                  "snippet": "cesiune 60% parti sociale catre o terta persoana"}],
            "funding_programs": {"eligible": [{"nume": "Start-Up Nation", "suma_max_eur": 200000,
                                "termen": "2026-12-31", "link": "https://example.ro"}],
                                "count": 1, "summary": "1 program eligibil"},
        }
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            path = f.name
        try:
            generate_docx(_make_sections(), _make_meta(), path, verified_data)
            doc = Document(path)
            text_parts = [p.text for p in doc.paragraphs]
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text_parts.append(cell.text)
            full_text = "\n".join(text_parts)

            assert "Scoruri Predictive Faliment" in full_text
            assert "Altman" in full_text
            assert "Benchmark Sector CAEN" in full_text
            assert "Actionariat si Relatii" in full_text
            assert "Ion Popescu" in full_text
            assert "Gaj auto" in full_text
            # osint_client shape {type, label, severity, snippet}: human label + snippet
            # must be rendered, not the raw slug (regression guard, bug fixat 2026-06-27).
            assert "Cesiune parti sociale detectata" in full_text
            assert "cesiune 60% parti sociale catre o terta persoana" in full_text
            assert "cesiune_parti_sociale" not in full_text
            assert "Start-Up Nation" in full_text
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
                        "details": [
                            {"nr_inregistrare": "2024-000456", "data": "2024-06-02",
                             "creditor": "Exemplu Leasing SA", "tip_bun": "Autovehicul", "status": "ACTIV"},
                            {"nr_inregistrare": "2023-000789", "data": "2023-11-20",
                             "creditor": "Banca Transilvania S.A.", "tip_bun": "Ipoteca mobiliara", "status": "RADIAT"},
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

    def test_web_intelligence_content_rendered_with_diacritics_and_dedup(self):
        """verified["web_intelligence"] (Brave Search + Jina enrichment, real quota
        spent on EVERY analysis) was rendered NOWHERE in DOCX before this fix (grep
        in backend/reports/ = 0 hits). Assert actual CONTENT (not just 'does not
        raise'), on a fixture matching the real DB shape confirmed in
        data/ris.db reports.full_data (a duplicate title+url entry observed live)."""
        from docx import Document

        from backend.reports.docx_generator import generate_docx

        verified_data = {"web_intelligence": {"categories": {
            "stiri": [
                {"title": "Compania își extinde activitatea în Târgoviște",
                 "url": "https://exemplu-stiri.ro/articol", "sentiment": "positive"},
                {"title": "Compania își extinde activitatea în Târgoviște",
                 "url": "https://exemplu-stiri.ro/articol", "sentiment": "positive"},
            ],
            "juridic": [
                {"title": "Litigiu comercial înregistrat pentru societate",
                 "url": "https://exemplu-just.ro/dosar", "sentiment": "negative"},
            ],
            "recenzii": [],
        }}}
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            path = f.name
        try:
            generate_docx(_make_sections(), _make_meta(), path, verified_data)
            doc = Document(path)
            full_text = "\n".join(p.text for p in doc.paragraphs)

            assert "Prezenta Online (OSINT)" in full_text
            assert "Compania își extinde activitatea în Târgoviște" in full_text
            assert "[POZITIV]" in full_text
            assert "Litigiu comercial înregistrat pentru societate" in full_text
            assert "[NEGATIV]" in full_text
            # Dedup: identical stiri entry appears exactly once.
            assert full_text.count("Compania își extinde activitatea în Târgoviște") == 1
            # Categoria goala ("recenzii") nu apare deloc.
            assert "Recenzii" not in full_text
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_web_intelligence_absent_omits_section(self):
        from docx import Document

        from backend.reports.docx_generator import generate_docx

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            path = f.name
        try:
            generate_docx(_make_sections(), _make_meta(), path, {})
            doc = Document(path)
            full_text = "\n".join(p.text for p in doc.paragraphs)
            assert "Prezenta Online" not in full_text
        finally:
            if os.path.exists(path):
                os.remove(path)
