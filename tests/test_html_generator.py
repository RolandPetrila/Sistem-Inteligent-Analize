"""F15: Tests for html_generator — _render_content (headers, lists, tables, bold)."""

from backend.reports.html_generator import (
    _build_rich_fields_html,
    _build_table,
    _render_content,
    _render_inline,
)


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


class TestRichFields:
    """Wave C: previously-dropped rich fields now rendered in HTML reports."""

    def _sample(self):
        return {
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
            "risk": {"aegrm_guarantees": {"value": {"has_data": True, "count": 2,
                     "has_guarantees": True, "guarantees": [{"descriere": "Gaj auto"}]}}},
            "historical_flags": [{"type": "CESIUNE", "detail": "Cesiune 2023",
                                  "date": "2023-05", "severity": "YELLOW"}],
            "funding_programs": {"eligible": [{"nume": "Start-Up Nation", "suma_max_eur": 200000,
                                "termen": "2026-12-31", "link": "https://example.ro"}],
                                "count": 1, "summary": "1 program eligibil"},
        }

    def test_all_sections_rendered(self):
        html, nav = _build_rich_fields_html(self._sample())
        for marker in ['id="predictive"', 'id="benchmark"', 'id="actionariat"',
                       'id="garantii"', 'id="funding"']:
            assert marker in html
        assert "Start-Up Nation" in html
        assert "Altman" in html
        assert "Gaj auto" in html
        assert "CESIUNE" in html
        assert 'href="#predictive"' in nav
        assert 'href="#funding"' in nav

    def test_empty_when_no_rich_data(self):
        html, nav = _build_rich_fields_html({})
        assert html == ""
        assert nav == ""

    def test_funding_link_xss_safe(self):
        data = {"funding_programs": {"eligible": [
            {"nume": "<script>alert(1)</script>", "suma_max_eur": 1000,
             "termen": "", "link": "javascript:alert(1)"}], "count": 1, "summary": "x"}}
        html, _ = _build_rich_fields_html(data)
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html
        assert 'href="javascript:' not in html

    def test_aegrm_skipped_when_no_data(self):
        data = {"risk": {"aegrm_guarantees": {"value": {"has_data": False}}}}
        html, nav = _build_rich_fields_html(data)
        assert 'id="garantii"' not in html

    def test_sanctions_clean_rendered(self):
        data = {"sanctions": {"status": "clean", "hits": [],
                              "checked": ["FIRMA SRL", "Ion Popescu"],
                              "lists_checked": ["OFAC", "EU", "UN"],
                              "data_date": "2026-07-11T00:00:00Z", "total_entries": 53000}}
        html, nav = _build_rich_fields_html(data)
        assert 'id="sanctions"' in html
        assert "CURAT" in html
        assert "OFAC" in html
        assert "PEP" in html  # limitarea explicita e mentionata
        assert 'href="#sanctions"' in nav

    def test_sanctions_hit_rendered_and_xss_safe(self):
        data = {"sanctions": {"status": "hit",
                              "hits": [{"query": "<script>x</script>", "matched_name": "IONESCU, Ștefan",
                                        "source": "OFAC", "type": "individual"}],
                              "checked": ["x"], "lists_checked": ["OFAC"],
                              "data_date": "2026-07-11", "total_entries": 100}}
        html, _ = _build_rich_fields_html(data)
        assert 'id="sanctions"' in html
        assert "verificare manuala" in html
        assert "IONESCU" in html
        assert "<script>x</script>" not in html  # escapat

    def test_sanctions_skipped_when_absent(self):
        html, nav = _build_rich_fields_html({})
        assert 'id="sanctions"' not in html

    def test_historical_flags_real_osint_shape(self):
        """TASK 2: osint_client emits {type(slug), label(human), severity, snippet}.
        The OSINT section MUST render the human label + snippet, not the raw slug —
        regression guard for the field-mapping fix (renderers prefer label/snippet)."""
        data = {"historical_flags": [{
            "type": "cesiune_parti_sociale",
            "label": "Cesiune parti sociale detectata",
            "severity": "HIGH",
            "snippet": "cesiune 60% parti sociale catre o terta persoana",
        }]}
        html, nav = _build_rich_fields_html(data)
        assert 'id="garantii"' in html
        assert "Cesiune parti sociale detectata" in html  # human label
        assert "cesiune 60%" in html                       # snippet, not dropped
        assert 'href="#garantii"' in nav
