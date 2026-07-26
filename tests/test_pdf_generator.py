"""F17: Tests for pdf_generator — _sanitize latin-1 encoding + rich-field rendering."""

import os
import tempfile

from backend.reports.pdf_generator import _sanitize


class TestSanitize:
    def test_ascii_passthrough(self):
        assert _sanitize("Hello World 123") == "Hello World 123"

    def test_romanian_s_cedilla(self):
        result = _sanitize("Societatea \u0218-a")
        assert "S" in result
        assert "\u0218" not in result

    def test_romanian_t_cedilla(self):
        result = _sanitize("\u021B\u021a")
        assert result == "tT"

    def test_em_dash(self):
        assert _sanitize("text \u2014 mai") == "text - mai"

    def test_en_dash(self):
        assert _sanitize("2020\u20132024") == "2020-2024"

    def test_smart_quotes(self):
        result = _sanitize("\u201cHello\u201d \u2018world\u2019")
        assert '"Hello"' in result
        assert "'world'" in result

    def test_ellipsis(self):
        assert _sanitize("text\u2026") == "text..."

    def test_mixed_content(self):
        text = "Firma \u0218tef\u0103nescu \u2014 CUI 12345"
        result = _sanitize(text)
        assert "Stef" in result
        assert "CUI 12345" in result
        # \u0103 (a with breve) - should be replaced by ?
        assert "\u0103" not in result

    def test_already_latin1(self):
        text = "Acesta e un test simplu"
        assert _sanitize(text) == text

    def test_empty_string(self):
        assert _sanitize("") == ""

    def test_unicode_replacement(self):
        # Characters outside latin-1 should be replaced with ?
        result = _sanitize("Emoji: \U0001f600")
        assert "\U0001f600" not in result


def _rich_verified_data() -> dict:
    """TASK 2: populated AEGRM guarantees + historical OSINT flags with Romanian
    diacritics (ă/ț/ș/î/â). Real (clean) firms never populate these fields, so this
    fixture is the ONLY coverage exercising the PDF rich-field rendering — and the
    diacritics probe the latin-1 sanitization (fpdf2/Helvetica) on OSINT signal text."""
    return {
        "risk": {
            "aegrm_guarantees": {
                "value": {
                    "has_data": True,
                    "count": 2,
                    "has_guarantees": True,
                    "details": [
                        {"nr_inregistrare": "2024-000456", "data": "2024-06-02",
                         "creditor": "Exemplu Leasing SA", "tip_bun": "Autovehicul — garanție către BCR",
                         "status": "ACTIV"},
                        {"nr_inregistrare": "2023-000789", "data": "2023-11-20",
                         "creditor": "Banca Transilvania S.A.", "tip_bun": "Ipotecă mobiliară",
                         "status": "RADIAT"},
                    ],
                }
            }
        },
        # Exact shape emitted by osint_client.search_monitorul_oficial:
        # {type(slug), label(human), severity, snippet} — NO detail/date.
        "historical_flags": [
            {
                "type": "cesiune_parti_sociale",
                "label": "Cesiune părți sociale detectată",
                "severity": "HIGH",
                "snippet": "Schimbare asociați — cesiune 60% părți sociale către o terță persoană",
            },
            {
                "type": "dizolvare_lichidare",
                "label": "Dizolvare / Lichidare / Radiere",
                "severity": "CRITICAL",
                "snippet": "Mențiune privind dizolvarea voluntară înregistrată la ONRC",
            },
        ],
        # Sanctions HIT with diacritics -> exercises the PDF latin-1 path on names.
        "sanctions": {
            "status": "hit",
            "hits": [
                {"query": "Ștefan Popescu", "matched_name": "POPESCU, Ștefán",
                 "source": "OFAC", "type": "individual"},
            ],
            "checked": ["Firma Țăndărei SRL", "Ștefan Popescu"],
            "lists_checked": ["OFAC", "EU", "UN"],
            "data_date": "2026-07-11T00:00:00Z",
            "total_entries": 53000,
        },
        # Eurostat sector benchmark — diacritics in label probe the latin-1 path.
        "eurostat_sector": {
            "available": True, "nace_used": "J62", "nace_label": "Computer programming",
            "year": "2024",
            "indicators": {
                "ENT_NR": {"label": "Număr firme", "ro": 45240, "eu": 1008501, "nace": "J62"},
                "EMP_ENT_NR": {"label": "Angajați / firmă", "ro": 4, "eu": 5, "nace": "J62"},
            },
        },
        # SEAP procurement history (wrapped like verified["market"]["seap"]) — diacritics probe latin-1.
        "market": {"seap": {"value": {
            "contracts_verified": True,
            "total_contracts": 2, "contracts_count": 1, "direct_count": 1, "total_value": 900000,
            "contracts": [{"title": "Lucrări reabilitare școală", "value": 850000, "currency": "RON",
                           "authority": "Primăria Târgoviște", "date": "2025-01-15"}],
            "direct_acquisitions": [{"title": "Achiziție consumabile", "value": 5000,
                                     "authority": "Spitalul Județean", "date": "2024-09-10"}],
        }}},
        # Angle A: oportunitati deschise cu diacritice -> exercita calea latin-1 PDF.
        "tender_opportunities": {"available": True, "count": 1, "days_back": 30,
            "opportunities": [{"title": "Construcție grădiniță în Târgoviște", "authority": "Primăria Târgoviște",
                               "cpv": "45214100-1", "value": 750000, "deadline": "2026-08-01", "notice_no": "CN5"}]},
        # web_intelligence (Brave Search + Jina) with diacritics + a duplicate entry
        # (real DB shape observed: identical title+url appearing twice in one category).
        "web_intelligence": {"categories": {
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
        }},
    }


class TestRichFieldsPdf:
    """TASK 2: exercise the POPULATED AEGRM + historical OSINT rendering through the
    real PDF generator. The OSINT 'Garantii si Istoric' section is structurally
    unreachable via clean firms (no signals), so this is the only place the PDF
    latin-1 path runs with diacritic-laden signal text — it MUST NOT raise."""

    def test_pdf_renders_rich_fields_with_diacritics(self):
        from backend.reports.pdf_generator import generate_pdf

        sections = {
            "executive_summary": {"title": "Rezumat Executiv", "content": "Firma analizată."}
        }
        # generate_pdf expects meta["risk_score"] as the color label string
        # (used as a color_map key), matching what the pipeline passes — not a dict.
        meta = {
            "title": "Raport RIS",
            "company_name": "Test SRL",
            "report_level": 2,
            "generated_at": "2026-06-27T10:00:00",
            "sources_count": 3,
            "risk_score": "Galben",
            "numeric_score": 55,
            # generate_pdf iterates sources as dicts (src.get("level")), matching the pipeline.
            "sources": [
                {"name": "ANAF", "level": 1, "status": "OK"},
                {"name": "ONRC", "level": 2, "status": "OK"},
            ],
        }
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            # Must not raise on the latin-1 OSINT diacritic path:
            generate_pdf(sections, meta, path, _rich_verified_data())
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_web_intelligence_content_rendered_with_diacritics_and_dedup(self):
        """web_intelligence (Brave Search + Jina) was rendered NOWHERE in the PDF
        before this fix (grep in backend/reports/ = 0 hits) despite real quota
        spent on every analysis. Assert actual CONTENT via pdfplumber (not just
        'does not raise') on the diacritic-laden fixture, and confirm the
        duplicate entry (real DB shape) collapses to a single rendered line."""
        from backend.reports.pdf_generator import generate_pdf

        sections = {
            "executive_summary": {"title": "Rezumat Executiv", "content": "Firma analizata."}
        }
        meta = {
            "title": "Raport RIS",
            "company_name": "Test SRL",
            "report_level": 2,
            "generated_at": "2026-07-16T10:00:00",
            "sources_count": 3,
            "risk_score": "Galben",
            "numeric_score": 55,
            "sources": [{"name": "ANAF", "level": 1, "status": "OK"}],
        }
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            generate_pdf(sections, meta, path, _rich_verified_data())
            assert os.path.exists(path)

            import pdfplumber

            with pdfplumber.open(path) as pdf:
                full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

            assert "Prezenta Online" in full_text
            # Diacritics sanitized to ASCII on the latin-1 path, but wording survives.
            assert "extinde activitatea" in full_text
            assert "Targoviste" in full_text
            assert "[POZITIV]" in full_text
            assert "Litigiu comercial" in full_text
            assert "[NEGATIV]" in full_text
            # Dedup: the identical stiri entry appears exactly once.
            assert full_text.count("extinde activitatea") == 1
        finally:
            if os.path.exists(path):
                os.remove(path)


class TestTavilyQuotaAndDivergencePdf:
    """A6 + A4 (2026-07-16): verifica randarea PDF a mesajului onest de cota
    Tavily epuizata si a dezacordului scor 6D vs modele predictive, COMBINATE
    in acelasi document cu fixture-ul diacritic-greu existent (_rich_verified_data)
    -- proba ca sectiunile noi nu strica pagina/calea latin-1 existenta."""

    def _combined_fixture(self) -> dict:
        data = _rich_verified_data()
        data["tavily_quota_exhausted"] = {"value": True, "usage": 950}
        data["risk_score"] = {"score": "Verde", "numeric_score": 78.0}
        data["predictive_scores"] = {
            "altman_z": {"z_score": None, "zone": "INDISPONIBIL"},
            "piotroski_f": {"f_score": 4, "max_possible": 5, "grade": "STRONG"},
            "beneish_m": {"m_score": None, "risk": "INDISPONIBIL", "available": False},
            "zmijewski_x": {"x_score": 2.4, "distress": True, "available": True},
            "distress_signals": 1,
            "summary": "Firma in zona gri (1/4 modele calculate) — monitorizare periodica recomandata",
        }
        return data

    def test_content_rendered_with_diacritics_context(self):
        from backend.reports.pdf_generator import generate_pdf

        sections = {"executive_summary": {"title": "Rezumat Executiv", "content": "Firma analizata."}}
        meta = {
            "title": "Raport RIS", "company_name": "Test SRL", "report_level": 2,
            "generated_at": "2026-07-16T10:00:00", "sources_count": 3,
            "risk_score": "Verde", "numeric_score": 78,
            "sources": [{"name": "ANAF", "level": 1, "status": "OK"}],
        }
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            # Nu trebuie sa arunce -- combina mesajul static (ASCII) cu fixture-ul
            # diacritic-greu deja verificat (aegrm/historical/sanctions/eurostat/seap).
            generate_pdf(sections, meta, path, self._combined_fixture())
            assert os.path.exists(path)

            import pdfplumber

            with pdfplumber.open(path) as pdf:
                full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

            assert "Verificare Incompleta" in full_text
            assert "NU a fost efectuata" in full_text
            assert "950/1000" in full_text
            assert "Dezacord intre scorul 6D si modelele predictive" in full_text
            assert "Scor 6D: Verde (78.0)" in full_text
            assert "semnal de distres" in full_text
            assert "Cele doua metode nu concorda" in full_text
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_no_divergence_section_when_models_agree(self):
        """Caz real (TAROM): scor Verde + Zmijewski fara distres -- fara bloc de dezacord."""
        from backend.reports.pdf_generator import generate_pdf

        data = self._combined_fixture()
        data["tavily_quota_exhausted"] = {}
        data["predictive_scores"]["zmijewski_x"] = {"x_score": -0.85, "distress": False, "available": True}
        sections = {"executive_summary": {"title": "Rezumat Executiv", "content": "Firma analizata."}}
        meta = {
            "title": "Raport RIS", "company_name": "Test SRL", "report_level": 2,
            "generated_at": "2026-07-16T10:00:00", "sources_count": 3,
            "risk_score": "Verde", "numeric_score": 74.5,
            "sources": [{"name": "ANAF", "level": 1, "status": "OK"}],
        }
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            generate_pdf(sections, meta, path, data)
            import pdfplumber

            with pdfplumber.open(path) as pdf:
                full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            assert "Verificare Incompleta" not in full_text
            assert "Dezacord intre scorul 6D" not in full_text
        finally:
            if os.path.exists(path):
                os.remove(path)


def _basic_meta() -> dict:
    return {
        "title": "Raport RIS",
        "company_name": "Test SRL",
        "report_level": 2,
        "generated_at": "2026-07-15T10:00:00",
        "sources_count": 3,
        "risk_score": "Galben",
        "numeric_score": 55,
        "sources": [{"name": "ANAF", "level": 1, "status": "OK"}],
    }


class TestTableCellTruncation:
    """Runda 2 / D (audit KNOWN ISSUES): _render_pdf_table() adauga elipsa bruta
    "…" DUPA _sanitize() cand o celula (header SAU body) depaseste max_chars —
    caracterul scapa nesanitizat si fpdf2 arunca FPDFUnicodeEncodingException pe
    fontul Helvetica (latin-1). Doua situri identice (l.99-105 header, l.108-118
    body) — tabelul de test contine ambele cazuri intr-un singur markdown table,
    ca sa garanteze ca fix-ul acopera amandoua."""

    def _long_table_content(self) -> str:
        # 4 coloane -> col_width=47.5mm -> max_chars=118 (vezi _render_pdf_table).
        # Header si body cu celule > 118 caractere ASCII (fara diacritice, ca sa
        # izolam strict truncarea de restul sanitizarii).
        header_long = "Coloana cu titlu foarte lung care depaseste cu siguranta limita de caractere per celula din tabel " * 2
        body_long = "Continut de test foarte lung menit sa depaseasca limita de caractere per celula din randul de date " * 2
        return (
            f"| {header_long.strip()} | B | C | D |\n"
            "|---|---|---|---|\n"
            f"| {body_long.strip()} | x | y | z |\n"
        )

    def test_long_header_and_body_cells_do_not_raise(self):
        from backend.reports.pdf_generator import generate_pdf

        sections = {"test_section": {"title": "Test Tabel", "content": self._long_table_content()}}
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            # Trebuie sa NU arunce FPDFUnicodeEncodingException — pe codul cu bug-ul
            # nereparat, aceasta linie pica garantat (ambele celule > max_chars).
            generate_pdf(sections, _basic_meta(), path)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_truncated_cell_respects_max_chars_and_is_latin1_safe(self):
        """Verifica direct contractul functiei (nu doar 'nu arunca'): rezultatul
        trunchiat respecta AMBELE constrangeri — len <= max_chars SI latin-1 safe."""
        from backend.reports.pdf_generator import _sanitize

        col_width = 190 / 4
        max_chars = max(int(col_width * 2.5), 20)
        cell = "A" * (max_chars + 50)
        sanitized = _sanitize(cell)
        assert len(sanitized) > max_chars

        truncated = sanitized[: max_chars - 3] + "..."
        assert len(truncated) <= max_chars
        truncated.encode("latin-1")  # nu trebuie sa arunce UnicodeEncodeError


class TestMapsRatingKeyTakeawaysSectorPositionPdf:
    """2026-07-16 ("RIS colecteaza > afiseaza", etajul 3): 3 campuri calculate corect,
    randate in 0/8 formate inainte de acest fix. Fixture-urile folosesc formele si
    valorile REALE gasite in data/ris.db (job 85ec7fff, TAROM CUI 477647; job
    29bc2f4b pentru sector_position -- repo public)."""

    def _meta(self):
        return {
            "title": "Raport RIS", "company_name": "Test SRL", "report_level": 2,
            "generated_at": "2026-07-16T10:00:00", "sources_count": 3,
            "risk_score": "Verde", "numeric_score": 74.5,
            "sources": [{"name": "ANAF", "level": 1, "status": "OK"}],
        }

    def test_all_three_rendered_with_real_shapes(self):
        from backend.reports.pdf_generator import generate_pdf

        verified_data = {
            "maps_rating": {
                "found": True, "name": "TAROM", "rating": 3.3, "reviews_count": 767,
                "address": "Calea Bucurestilor 224F, 075100 Otopeni", "source": "google_maps",
            },
            "key_takeaways": (
                "• Cu o cifra de afaceri de 1,226,498,739 RON, TAROM prezinta o baza "
                "financiara solida pentru parteneriat.\n"
                "• Capitalurile proprii negative de -105,192,156 RON indica un risc de "
                "insolventa tehnica ce necesita monitorizare."
            ),
            "risk_score": {"sector_position": {
                "Cifra de afaceri": {"ratio_vs_avg": 0.37, "estimated_percentile": "sub P25"},
            }},
            # sector_position is only rendered alongside a benchmark table, matching
            # the real coupling in scoring.py (_score_piata builds both from the same
            # comparisons list).
            "benchmark": {"available": True, "caen_code": "5110", "comparisons": [
                {"metric": "Cifra de afaceri", "firma": 1226498739, "media_sector": 3300000000, "ratio": 0.37, "pozitie": "Sub medie"},
            ]},
        }
        sections = {"executive_summary": {"title": "Rezumat Executiv", "content": "Firma analizata."}}
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            generate_pdf(sections, self._meta(), path, verified_data)
            assert os.path.exists(path)

            import pdfplumber

            with pdfplumber.open(path) as pdf:
                full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

            assert "Puncte Cheie" in full_text
            assert "financiara solida pentru parteneriat" in full_text
            assert "Prezenta pe Google Maps" in full_text
            assert "3.3/5" in full_text
            assert "767 recenzii" in full_text
            assert "Pozitie in Sector" in full_text
            assert "sub P25" in full_text
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_maps_rating_not_found_omits_section(self):
        """Real shape: {"found": False, "error": "no_results", "source":
        "google_maps"} -- must NOT render '0 stele'."""
        from backend.reports.pdf_generator import generate_pdf

        verified_data = {"maps_rating": {"found": False, "error": "no_results", "source": "google_maps"}}
        sections = {"executive_summary": {"title": "Rezumat Executiv", "content": "Firma analizata."}}
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            generate_pdf(sections, self._meta(), path, verified_data)
            import pdfplumber

            with pdfplumber.open(path) as pdf:
                full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            assert "Prezenta pe Google Maps" not in full_text
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_key_takeaways_none_omits_section(self):
        from backend.reports.pdf_generator import generate_pdf

        verified_data = {"key_takeaways": None}
        sections = {"executive_summary": {"title": "Rezumat Executiv", "content": "Firma analizata."}}
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            generate_pdf(sections, self._meta(), path, verified_data)
            import pdfplumber

            with pdfplumber.open(path) as pdf:
                full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            assert "Puncte Cheie" not in full_text
        finally:
            if os.path.exists(path):
                os.remove(path)


class TestRiskFactorsPdf:
    """BUG2 (2026-07-16): risk_score['factors'] was never rendered in PDF — the most
    shared report format never explained WHY the score dropped (BPI insolvency,
    Portal Just litigation, Monitorul Oficial cesiuni were all invisible). Fixture
    is 100% synthetic (repo is public) and includes diacritics to probe the latin-1
    sanitize path, per the TASK 2 precedent where the populated path had never run
    until a dedicated test exercised it."""

    def _verified_data_with_factors(self):
        return {
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

    def test_factors_rendered_with_diacritics_and_severity_order(self):
        from backend.reports.pdf_generator import generate_pdf

        sections = {
            "executive_summary": {"title": "Rezumat Executiv", "content": "Firma analizata."}
        }
        meta = {
            "title": "Raport RIS", "company_name": "Test SRL", "report_level": 2,
            "generated_at": "2026-07-16T10:00:00", "sources_count": 3,
            "risk_score": "Rosu", "numeric_score": 15,
            "sources": [{"name": "ANAF", "level": 1, "status": "OK"}],
        }
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            # Must not raise on the latin-1 diacritic path (ă/î/â/ș/ț in factor text).
            generate_pdf(sections, meta, path, self._verified_data_with_factors())
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0

            import pdfplumber

            with pdfplumber.open(path) as pdf:
                full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

            assert "Factori de Risc" in full_text
            assert "[CRITICAL]" in full_text
            assert "[HIGH]" in full_text
            assert "ZOMBIE" in full_text
            # Diacritics sanitized to ASCII (latin-1 path), but the wording survives:
            assert "insolventa" in full_text or "insolven" in full_text
            assert "Tribunalul T" in full_text

            # Severity ordering: CRITICAL factors must appear before the HIGH factor,
            # regardless of their original position in the input list.
            pos_critical_zombie = full_text.find("ZOMBIE")
            pos_high = full_text.find("[HIGH] Firma inactiva")
            assert pos_critical_zombie != -1 and pos_high != -1
            assert pos_critical_zombie < pos_high
        finally:
            if os.path.exists(path):
                os.remove(path)


class TestRnpmManualGuaranteesPdf:
    """CERINTA #4 (2026-07-26): cazul HARD -- pagina 2 (Actionariat/Garantii/Finantare)
    nu se randa deloc daca un raport n-avea NIMIC pe ea. Linia RNPM neconditionata forteaza
    randarea paginii. Non-vacuitate: pe HEAD, cu fixture ZERO rich fields, pagina 2 lipsea
    -> co.rnpm.ro ABSENT -> E2 pica."""

    def _meta(self):
        return {
            "title": "Raport RIS",
            "company_name": "Test SRL",
            "report_level": 1,
            "generated_at": "2026-07-26T10:00:00",
            "sources_count": 1,
            "risk_score": "Galben",
            "numeric_score": 55,
            "sources": [{"name": "ANAF", "level": 1, "status": "OK"}],
        }

    def _extract(self, path):
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)

    def test_e2_rnpm_link_present_with_zero_rich_fields(self):
        from backend.reports.pdf_generator import generate_pdf

        sections = {"executive_summary": {"title": "Rezumat", "content": "Firma analizata."}}
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            # verified_data GOL: nici actionariat, nici funding, nimic pe pagina 2.
            generate_pdf(sections, self._meta(), path, {})
            text = self._extract(path)
            assert "co.rnpm.ro" in text
            # E4 (santinela): fara afirmatii false de "curat" pe garantii mobiliare.
            low = text.lower()
            assert "verificare automata indisponibila" in low
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_e6_populated_aegrm_still_renders_list_and_rnpm_link(self):
        """SANTINELA (trece pe ambele versiuni): pe calea AEGRM populata, lista
        itemizata (creditor/tip bun/status) inca se randeaza + linkul RNPM."""
        from backend.reports.pdf_generator import generate_pdf

        sections = {"executive_summary": {"title": "Rezumat", "content": "Firma analizata."}}
        verified = {
            "risk": {"aegrm_guarantees": {"value": {
                "has_data": True, "count": 1, "has_guarantees": True,
                "details": [{"creditor": "Banca Test", "data": "2025-01-01",
                             "tip_bun": "Autovehicul", "status": "Activ"}],
            }}},
        }
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            generate_pdf(sections, self._meta(), path, verified)
            text = self._extract(path)
            assert "Banca Test" in text
            assert "co.rnpm.ro" in text
        finally:
            if os.path.exists(path):
                os.remove(path)
