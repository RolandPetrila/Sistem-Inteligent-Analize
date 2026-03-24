"""F15: Tests for html_generator — _render_content (headers, lists, tables, bold)."""

from backend.reports.html_generator import _render_content, _render_inline, _build_table


class TestRenderInline:
    def test_bold_converted(self):
        result = _render_inline("Valoare **importanta** aici")
        assert "<strong>importanta</strong>" in result
        assert "**" not in result

    def test_trust_labels(self):
        result = _render_inline("Data [OFICIAL] si [ESTIMAT]")
        assert 'class="trust-oficial"' in result
        assert 'class="trust-estimat"' in result

    def test_html_escape(self):
        result = _render_inline("<script>alert(1)</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


class TestRenderContent:
    def test_paragraph(self):
        result = _render_content("Text simplu.")
        assert "<p>" in result
        assert "Text simplu." in result

    def test_h3_header_hash(self):
        result = _render_content("### Titlu sectiune")
        assert '<h3 class="subsection">' in result
        assert "Titlu sectiune" in result

    def test_h3_header_bold(self):
        result = _render_content("**Titlu bold**")
        assert '<h3 class="subsection">' in result
        assert "Titlu bold" in result

    def test_ul_list(self):
        result = _render_content("- Item 1\n- Item 2")
        assert "<ul" in result
        assert "<li>" in result
        assert "Item 1" in result
        assert "</ul>" in result

    def test_ol_list(self):
        result = _render_content("1. Primul\n2. Al doilea")
        assert "<ol" in result
        assert "<li>" in result
        assert "Primul" in result
        assert "</ol>" in result

    def test_bold_in_list_item(self):
        result = _render_content("- Item cu **bold** text")
        assert "<strong>bold</strong>" in result
        assert "**" not in result

    def test_table_rendering(self):
        md = "| Col A | Col B |\n| --- | --- |\n| val1 | val2 |"
        result = _render_content(md)
        assert "<table" in result
        assert "<thead>" in result
        assert "<th>" in result
        assert "Col A" in result
        assert "<td>" in result
        assert "val1" in result

    def test_table_no_header(self):
        md = "| a | b |\n| c | d |"
        result = _render_content(md)
        assert "<table" in result
        assert "<thead>" not in result
        assert "a" in result

    def test_mixed_content(self):
        md = "### Titlu\n\nText.\n\n- Item 1\n- Item 2\n\n1. Ordered"
        result = _render_content(md)
        assert '<h3 class="subsection">' in result
        assert "<ul" in result
        assert "</ul>" in result
        assert "<ol" in result
        assert "</ol>" in result

    def test_empty_lines_as_br(self):
        result = _render_content("Line 1\n\nLine 2")
        assert "<br>" in result


class TestBuildTable:
    def test_with_header(self):
        rows = [["A", "B"], ["1", "2"]]
        result = _build_table(rows, has_header=True)
        assert "<thead>" in result
        assert "<th>" in result
        assert "<td>" in result

    def test_without_header(self):
        rows = [["x", "y"]]
        result = _build_table(rows, has_header=False)
        assert "<thead>" not in result
        assert "<td>" in result

    def test_empty_rows(self):
        assert _build_table([], has_header=False) == ""

    def test_column_count_normalization(self):
        """HTML-03: Short rows padded to max column count."""
        rows = [["A", "B", "C"], ["1", "2"]]
        result = _build_table(rows, has_header=True)
        # Row 2 should be padded to 3 cells
        assert result.count("<td>") >= 3


class TestRenderEdgeCases:
    """TEST-03: Edge case tests for _render_content."""

    def test_separator_after_data_rows(self):
        """HTML-01: Separator after data rows should not set header flag."""
        content = "| A | B |\n| 1 | 2 |\n|---|---|\n| 3 | 4 |"
        result = _render_content(content)
        assert "<table" in result
        # Should NOT have a header (separator was after data)
        assert "<thead>" not in result

    def test_xss_in_table_cell(self):
        """HTML-02: Script tags in table cells must be escaped."""
        content = "| Header |\n|---|\n| <script>alert(1)</script> |"
        result = _render_content(content)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_xss_in_paragraph(self):
        """HTML-02: HTML tags in paragraphs must be escaped (no raw tags)."""
        result = _render_content('<img src=x onerror="alert(1)">')
        # The important thing: <img is escaped so browser won't execute it
        assert "&lt;img" in result
        assert "<img " not in result  # no raw img tag

    def test_valid_separator_requires_dashes(self):
        """HTML-05: Separator must have dashes, not just pipes and spaces."""
        content = "| A | B |\n|   |   |\n| 1 | 2 |"
        result = _render_content(content)
        # |   |   | should NOT be treated as separator
        # It should be rendered as data row
        assert "<td>" in result

    def test_empty_table(self):
        """Empty table rows produce no output."""
        assert _build_table([], has_header=True) == ""

    def test_single_row_no_header(self):
        """Single row table without separator has no header."""
        content = "| A | B |"
        result = _render_content(content)
        assert "<table" in result
        assert "<thead>" not in result
