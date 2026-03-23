"""F17: Tests for pdf_generator — _sanitize latin-1 encoding."""

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
