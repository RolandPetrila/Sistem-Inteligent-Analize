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
                    "guarantees": [
                        {"descriere": "Gaj mobiliar — autovehicul, garanție către BCR"},
                        {"creditor": "Banca Transilvania S.A. — ipotecă mobiliară"},
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
