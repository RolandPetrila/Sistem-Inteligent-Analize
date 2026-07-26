"""F15: Tests for html_generator — _render_content (headers, lists, tables, bold)."""

from backend.reports.html_generator import (
    _build_alarm_warnings_html,
    _build_company_network_html,
    _build_executive_summary,
    _build_rich_fields_html,
    _build_table,
    _escape,
    _render_content,
    _render_inline,
    generate_html,
)


class TestAlarmWarningsHtml:
    """D11 follow-up (2026-07-16): verified_data["early_warnings"] (real business
    signals) was rendered in PDF/DOCX but NEVER in HTML (grep = 0 hits). Real shape
    verified in data/ris.db (job 85ec7fff, TAROM CUI 477647, full_data['early_warnings']):
    list of dicts {signal, severity, detail, years} -- fixture below uses that exact
    real shape (values are the real TAROM ones, repo is public)."""

    def _tarom_early_warnings(self):
        return [
            {
                "signal": "Scadere CA > 30%",
                "severity": "HIGH",
                "detail": "CA a scazut cu 74% din 2019 (1,354,514,118 RON) in 2020 (355,310,102 RON)",
                "years": "2019-2020",
            },
            {
                "signal": "Pierdere consecutiva 2+ ani",
                "severity": "HIGH",
                "detail": "Pierdere neta in anii: 2019, 2020, 2021, 2022, 2023",
                "years": "2019-2023",
            },
        ]

    def test_real_tarom_signals_rendered(self):
        """DOVADA DE NON-VACUITATE: pe codul vechi, verified_data["early_warnings"]
        nu era citit nicaieri in html_generator.py -> aceasta functie nu exista si
        acest test ar pica la import. Pe codul reparat, "Scadere CA" trebuie sa
        apara in HTML (exact bug-ul semnalat: 0 potriviri in raport.html real,
        1 potrivire in raport.pdf real, pt job-ul TAROM 85ec7fff)."""
        html = _build_alarm_warnings_html({"early_warnings": self._tarom_early_warnings()})
        assert 'id="alarm-warnings"' in html
        assert "Semnale de Alarma" in html
        assert "Scadere CA &gt; 30%" in html or "Scadere CA" in html
        assert "Pierdere consecutiva 2+ ani" in html
        assert "CA a scazut cu 74%" in html
        assert "[HIGH]" in html

    def test_empty_list_omits_section(self):
        assert _build_alarm_warnings_html({"early_warnings": []}) == ""

    def test_absent_key_omits_section(self):
        assert _build_alarm_warnings_html({}) == ""

    def test_string_items_rendered_without_crashing(self):
        html = _build_alarm_warnings_html({"early_warnings": ["Semnal simplu, fara structura"]})
        assert "Semnal simplu, fara structura" in html

    def test_full_report_includes_alarm_warnings_section(self, tmp_path):
        """End-to-end: generate_html() on the real TAROM shape must render the
        section AND a working nav link -- this is what the brief's grep-on-real-
        file evidence checks, not just the helper function in isolation."""
        meta = {
            "company_name": "TAROM", "title": "Raport Test",
            "generated_at": "2026-07-16", "risk_score": "Verde", "numeric_score": 74.5,
            "risk_recommendation": "", "report_level": 2, "sources": [],
        }
        verified = {
            "company": {}, "financial": {}, "risk_score": {},
            "early_warnings": self._tarom_early_warnings(),
        }
        out = tmp_path / "report.html"
        generate_html({}, meta, verified, str(out))
        html = out.read_text(encoding="utf-8")
        assert "Scadere CA" in html
        assert "Pierdere consecutiva 2+ ani" in html
        assert '<a href="#alarm-warnings" class="nav-link">Semnale de Alarma</a>' in html


class TestExecutiveSummaryRiskFactorSeverity:
    """BUG1 (2026-07-16): 'Risc principal' used to filter strictly on severity ==
    "HIGH", silently excluding CRITICAL (BPI insolvency, ZOMBIE detection — the
    2 most severe verdicts scoring.py emits) and picking the FIRST HIGH in list
    order even when a CRITICAL factor was present later in the list."""

    def _verified_data(self, factors):
        return {
            "company": {"denumire": {"value": "Test SRL"}, "cui": {"value": "12345678"}},
            "financial": {},
            "risk_score": {"numeric_score": 20, "score": "Rosu", "factors": factors},
        }

    def test_critical_factor_is_shown_not_dropped(self):
        """On unpatched code this line was silently empty for insolvent firms."""
        factors = [("Firma in procedura insolventa BPI (deschisa)", "CRITICAL")]
        html = _build_executive_summary(self._verified_data(factors), {})
        assert "Risc principal" in html
        assert "Firma in procedura insolventa BPI" in html

    def test_critical_outranks_high_regardless_of_list_order(self):
        """A HIGH factor appears BEFORE the CRITICAL one in the list — the strict
        '== HIGH' filter used to grab the HIGH one, showing a less severe risk
        than the one actually driving the low score."""
        factors = [
            ("Firma inactiva la ANAF", "HIGH"),
            ("ZOMBIE: CA=0 + angajati=0 + status activ - firma nu opereaza", "CRITICAL"),
        ]
        html = _build_executive_summary(self._verified_data(factors), {})
        assert "ZOMBIE" in html
        assert "Firma inactiva la ANAF" not in html

    def test_high_still_shown_when_no_critical(self):
        factors = [("Firma inactiva la ANAF", "HIGH")]
        html = _build_executive_summary(self._verified_data(factors), {})
        assert "Firma inactiva la ANAF" in html

    def test_medium_and_low_never_shown_as_principal_risk(self):
        factors = [("Numar ridicat de litigii (5+)", "MEDIUM"), ("Litigii gasite", "LOW")]
        html = _build_executive_summary(self._verified_data(factors), {})
        assert "Risc principal" not in html


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
            "risk": {"aegrm_guarantees": {"value": {"has_data": True, "count": 1,
                     "has_guarantees": True, "details": [
                         {"nr_inregistrare": "2024-000123", "data": "2024-03-11",
                          "creditor": "Banca Exemplu SA", "tip_bun": "Gaj auto", "status": "ACTIV"},
                     ]}}},
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

    def test_only_rnpm_garantii_when_no_rich_data(self):
        # CERINTA #4 (2026-07-26): linia de verificare manuala RNPM apare NECONDITIONAT,
        # deci pe date goale se randeaza DOAR sectiunea garantii (co.rnpm.ro), nimic
        # altceva. (Inainte de #4 acest test cerea html == "" -- premisa "sectiune
        # absenta fara date", exact ce a schimbat cerinta.)
        html, nav = _build_rich_fields_html({})
        assert "co.rnpm.ro" in html
        assert 'id="garantii"' in html
        assert '<a href="#garantii" class="nav-link">' in nav
        for other in ('id="sanctions"', 'id="eurostat"', 'id="funding"',
                      'id="benchmark"', 'id="bonitate"', 'id="tavily-quota"'):
            assert other not in html

    def test_funding_link_xss_safe(self):
        data = {"funding_programs": {"eligible": [
            {"nume": "<script>alert(1)</script>", "suma_max_eur": 1000,
             "termen": "", "link": "javascript:alert(1)"}], "count": 1, "summary": "x"}}
        html, _ = _build_rich_fields_html(data)
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html
        assert 'href="javascript:' not in html

    def test_aegrm_data_line_skipped_when_no_data_but_rnpm_present(self):
        # has_data=False -> linia "Garantii reale mobiliare (AEGRM): N" NU se randeaza,
        # dar sectiunea + linia RNPM neconditionata SUNT prezente (CERINTA #4). Inainte
        # de #4 testul cerea 'id="garantii"' not in html (sectiune complet absenta).
        data = {"risk": {"aegrm_guarantees": {"value": {"has_data": False}}}}
        html, nav = _build_rich_fields_html(data)
        assert 'id="garantii"' in html
        assert "co.rnpm.ro" in html
        assert "Garantii reale mobiliare (AEGRM):" not in html

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

    def test_eurostat_section_rendered(self):
        data = {"eurostat_sector": {"available": True, "nace_used": "J62",
                "nace_label": "Computer programming", "year": "2024",
                "indicators": {
                    "ENT_NR": {"label": "Numar firme", "ro": 45240, "eu": 1008501, "nace": "J62"},
                    "EMP_ENT_NR": {"label": "Angajati / firma", "ro": 4.3, "eu": 5.7, "nace": "J62"}}}}
        html, nav = _build_rich_fields_html(data)
        assert 'id="eurostat"' in html
        assert "Eurostat" in html
        assert "J62" in html
        assert "4.3" in html  # rata cu zecimale pastrata, NU rotunjita la "4"
        assert 'href="#eurostat"' in nav

    def test_sanctions_partial_completeness_warning(self):
        data = {"sanctions": {"status": "clean", "hits": [], "checked": ["Firma SRL"],
                              "lists_checked": ["OFAC"], "lists_missing": ["EU", "UN"],
                              "complete": False, "data_date": "2026-07-11", "total_entries": 100}}
        html, _ = _build_rich_fields_html(data)
        assert 'id="sanctions"' in html
        assert "Screening partial" in html
        assert "neautoritar" in html

    def test_eurostat_skipped_when_unavailable(self):
        data = {"eurostat_sector": {"available": False, "reason": "fara date"}}
        html, _ = _build_rich_fields_html(data)
        assert 'id="eurostat"' not in html

    def test_seap_procurement_history_rendered(self):
        # SEAP data is wrapped by _make_field -> {"value": {...}} in verified["market"]["seap"]
        data = {"market": {"seap": {"value": {
            "contracts_verified": True,
            "total_contracts": 3, "contracts_count": 2, "direct_count": 1, "total_value": 1500000,
            "contracts": [{"title": "Reparatii drum judetean", "value": 800000, "currency": "RON",
                           "authority": "Primaria Cluj", "date": "2025-03-01"}],
            "direct_acquisitions": [{"title": "Consumabile birou", "value": 12000,
                                     "authority": "Spitalul X", "date": "2024-11-01"}],
        }}}}
        html, nav = _build_rich_fields_html(data)
        assert 'id="achizitii"' in html
        assert "contracte publice castigate" in html
        assert "Primaria Cluj" in html
        assert 'href="#achizitii"' in nav

    def test_seap_skipped_when_no_contracts(self):
        data = {"market": {"seap": {"value": {"total_contracts": 0, "contracts": [], "direct_acquisitions": []}}}}
        html, _ = _build_rich_fields_html(data)
        assert 'id="achizitii"' not in html

    def test_tender_opportunities_rendered(self):
        data = {"tender_opportunities": {"available": True, "count": 2, "days_back": 30,
                "opportunities": [
                    {"title": "Constructie scoala", "authority": "Primaria Cluj", "cpv": "45210000-2",
                     "value": 500000, "deadline": "2026-08-01", "notice_no": "CN1"},
                    {"title": "Reabilitare drum", "authority": "CJ Cluj", "cpv": "45233120-6",
                     "value": 1200000, "deadline": "2026-08-15", "notice_no": "CN2"}]}}
        html, nav = _build_rich_fields_html(data)
        assert 'id="oportunitati"' in html
        assert "licitatii deschise" in html
        assert "45210000-2" in html
        assert "Primaria Cluj" in html
        assert 'href="#oportunitati"' in nav

    def test_tender_opportunities_skipped_when_unavailable(self):
        data = {"tender_opportunities": {"available": False, "reason": "CAEN necunoscut"}}
        html, _ = _build_rich_fields_html(data)
        assert 'id="oportunitati"' not in html

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


class TestWebIntelligenceHtml:
    """verified["web_intelligence"] (Brave Search + Jina enrichment, real quota
    spent on every analysis) was rendered NOWHERE before this fix (grep in
    backend/reports/ = 0 hits). Shape confirmed in data/ris.db reports.full_data.
    Fixtures are 100% synthetic (repo public)."""

    def _sample(self):
        return {"web_intelligence": {"categories": {
            "stiri": [
                {"title": "Firma Exemplu SRL lanseaza un produs nou",
                 "url": "https://example-news.ro/articol", "sentiment": "positive"},
                {"title": "Firma Exemplu SRL lanseaza un produs nou",
                 "url": "https://example-news.ro/articol", "sentiment": "positive"},
            ],
            "juridic": [
                {"title": "Dosar juridic Firma Exemplu SRL",
                 "url": "https://example-just.ro/dosar", "sentiment": "negative"},
            ],
            "recenzii": [],
        }}}

    def test_section_rendered_with_categories_and_dedup(self):
        html, nav = _build_rich_fields_html(self._sample())
        assert 'id="web_intelligence"' in html
        assert "Firma Exemplu SRL lanseaza un produs nou" in html
        # Deduplicat: 2 intrari identice -> 1 randata.
        assert html.count("Firma Exemplu SRL lanseaza un produs nou") == 1
        assert "Dosar juridic Firma Exemplu SRL" in html
        assert 'href="#web_intelligence"' in nav
        # Categoria goala ("recenzii") nu apare deloc.
        assert "Recenzii" not in html

    def test_sentiment_badges_rendered(self):
        html, _ = _build_rich_fields_html(self._sample())
        assert "[Pozitiv]" in html
        assert "[Negativ]" in html

    def test_url_rendered_as_link(self):
        html, _ = _build_rich_fields_html(self._sample())
        assert 'href="https://example-news.ro/articol"' in html

    def test_empty_categories_hides_section(self):
        data = {"web_intelligence": {"categories": {"stiri": [], "recenzii": []}}}
        html, nav = _build_rich_fields_html(data)
        assert 'id="web_intelligence"' not in html
        assert 'href="#web_intelligence"' not in nav

    def test_absent_hides_section(self):
        html, nav = _build_rich_fields_html({})
        assert 'id="web_intelligence"' not in html

    def test_xss_in_title_and_url_escaped(self):
        data = {"web_intelligence": {"categories": {"stiri": [
            {"title": "<script>alert(1)</script>", "url": "javascript:alert(1)", "sentiment": "neutral"},
        ]}}}
        html, _ = _build_rich_fields_html(data)
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html
        assert 'href="javascript:' not in html


class TestCompanyNetworkHtml:
    """Bug real: gate-ul citea stats.total_persons/stats.total_firms, chei care nu
    exista NICIODATA pe raspunsul real al network_client.get_company_network()
    (backend/agents/tools/network_client.py) -- sectiunea afisa mereu "Date retea
    indisponibile" chiar cu has_data=True si date reale. Fixate cu forma REALA:
    persons (top-level), total_connected (top-level), related_companies (nu
    related_firms), risk_flags ca LISTA DE DICT-uri (nu strings — crash TypeError
    daca gate-ul era reparat izolat, fara sa se repare si bucla de badge-uri).
    Date sintetice (structura reala, valori inventate — repo public)."""

    def _empty_network(self):
        return {"company_network": {
            "has_data": True, "persons": [], "related_companies": [],
            "total_connected": 0, "risk_flags": [], "stats": {},
        }}

    def _populated_network(self, risk_flags=None):
        return {"company_network": {
            "has_data": True,
            "persons": [
                {"name": "Ion Popescu", "role": "administrator", "ownership_pct": 60},
                {"name": "Maria Ionescu", "role": "asociat", "ownership_pct": None},
            ],
            "related_companies": [
                {"cui": "11111111", "company_name": "Exemplu Beta SRL", "persons": [],
                 "is_active": 0, "has_profile": True, "depth": 1},
                {"cui": "22222222", "company_name": "Exemplu Gamma SRL", "persons": [],
                 "is_active": 1, "has_profile": True, "depth": 2},
                {"cui": "33333333", "company_name": "Exemplu Delta SRL", "persons": [],
                 "is_active": None, "has_profile": False, "depth": 1},
            ],
            "total_connected": 3,
            "risk_flags": risk_flags if risk_flags is not None else [],
            "network_depth_reached": 2,
            "toxic_persons": [],
            "stats": {"inactive": 1, "unknown_status": 1, "active": 1, "depth_1": 2, "depth_2_plus": 1},
            "nx_stats": {"available": True, "depth_used": 4},
        }}

    def test_no_data_shows_unavailable_message(self):
        html = _build_company_network_html({"company_network": {
            "has_data": False, "persons": [], "related_companies": [], "risk_flags": [],
        }})
        assert "Date retea indisponibile" in html

    def test_empty_company_network_key_returns_empty_string(self):
        assert _build_company_network_html({}) == ""

    def test_populated_network_does_not_show_unavailable_message(self):
        """Regression guard for the actual bug: real data must NOT hit the
        'indisponibile' branch."""
        html = _build_company_network_html(self._populated_network())
        assert "Date retea indisponibile" not in html
        assert 'id="network"' in html

    def test_populated_network_shows_real_counts(self):
        html = _build_company_network_html(self._populated_network())
        # 2 persons, 3 related companies (total_connected), 1 inactive (stats.inactive)
        assert ">2</div>" in html  # persoane comune
        assert ">3</div>" in html  # firme conexe
        assert ">1</div>" in html  # firme inactive

    def test_persons_table_renders_names_and_ownership(self):
        html = _build_company_network_html(self._populated_network())
        assert "Ion Popescu" in html
        assert "60%" in html
        assert "Maria Ionescu" in html

    def test_related_companies_table_uses_company_name_and_is_active(self):
        html = _build_company_network_html(self._populated_network())
        assert "Exemplu Beta SRL" in html
        assert "Exemplu Gamma SRL" in html
        assert "Exemplu Delta SRL" in html
        assert "INACTIV" in html
        assert "ACTIV" in html

    def test_risk_flags_as_dicts_do_not_crash_and_render_detail(self):
        """The critical regression guard: risk_flags are dicts, not strings.
        A gate-only fix (without fixing this loop) raises TypeError here."""
        risk_flags = [
            {"type": "ASOCIAT_FIRMA_INACTIVA", "severity": "YELLOW",
             "detail": "Asociat comun cu 1 firma(e) inactiva(e): Exemplu Beta SRL"},
            {"type": "TOXIC_NETWORK", "severity": "RED",
             "detail": "Persoana(e) cu istoric toxic detectate: Ion Popescu"},
        ]
        html = _build_company_network_html(self._populated_network(risk_flags=risk_flags))
        assert "Asociat comun cu 1 firma(e) inactiva(e)" in html
        assert "Persoana(e) cu istoric toxic detectate" in html

    def test_unknown_risk_flag_type_falls_back_to_default_color(self):
        risk_flags = [{"type": "CONFLICT_INTERESE", "severity": "YELLOW",
                        "detail": "X este asociat la 5 firme active simultan"}]
        html = _build_company_network_html(self._populated_network(risk_flags=risk_flags))
        assert "X este asociat la 5 firme active simultan" in html


class TestDueDiligenceHtml:
    """A3 (2026-07-16): the Due Diligence Checklist (10 DA/NU/INDISPONIBIL checks)
    was rendered in PDF/DOCX/Excel/1-pager but silently absent from HTML — the
    exact format used for the public share link (/api/reports/public/*). Real
    shape confirmed at the producer (backend/agents/verification/due_diligence.py)
    and in data/ris.db reports.full_data: verified["due_diligence"] is a plain
    LIST of dicts {name, status, severity, source} — NOT wrapped in
    {"value": ...} and NOT nested under a "checklist" key (matches the shape
    pdf_generator.py/docx_generator.py already handle). Fixture below uses that
    real shape with synthetic values (repo public)."""

    def _meta(self):
        return {
            "company_name": "Exemplu Test SRL",
            "title": "Raport Test",
            "generated_at": "2026-07-16",
            "risk_score": "Verde",
            "numeric_score": 82,
            "risk_recommendation": "",
            "report_level": 2,
            "sources": [],
        }

    def _checklist(self):
        return [
            {"name": "Firma activa la ANAF", "status": "DA", "severity": "info", "source": "ANAF"},
            {"name": "Platitor TVA", "status": "DA", "severity": "info", "source": "ANAF"},
            {"name": "Fara Split TVA", "status": "DA", "severity": "info", "source": "ANAF"},
            {"name": "Fara insolventa", "status": "NU", "severity": "critical", "source": "BPI"},
            {"name": "Are angajati (>0)", "status": "DA", "severity": "info", "source": "ANAF Bilant"},
            {"name": "Cifra de afaceri > 0", "status": "DA", "severity": "info", "source": "ANAF Bilant"},
            {"name": "Profit pozitiv", "status": "NU", "severity": "warning", "source": "ANAF Bilant"},
            {"name": "Capitaluri proprii pozitive", "status": "INDISPONIBIL", "severity": "info", "source": "-"},
            {"name": "Date ONRC disponibile", "status": "DA", "severity": "info", "source": "openapi.ro"},
            {"name": "Fara anomalii suspecte", "status": "DA", "severity": "info", "source": "Analiza interna"},
        ]

    def test_checklist_rendered_with_all_ten_items_and_states(self, tmp_path):
        verified = {"company": {}, "financial": {}, "due_diligence": self._checklist()}
        out = tmp_path / "report.html"
        generate_html({}, self._meta(), verified, str(out))
        html = out.read_text(encoding="utf-8")

        assert 'id="due-diligence"' in html
        assert "Due Diligence Checklist" in html
        for item in self._checklist():
            assert _escape(item["name"]) in html
        # 7 DA / 2 NU / 1 INDISPONIBIL in the fixture above
        assert "7/10 verificari OK" in html
        # Scope the state-icon counts to the due-diligence section only — other
        # sections (e.g. executive summary "CA: N/A") also emit these tokens.
        section_start = html.index('id="due-diligence"')
        section_end = html.index("</section>", section_start)
        dd_section = html[section_start:section_end]
        assert dd_section.count(">DA<") == 7
        assert dd_section.count(">NU<") == 2
        assert dd_section.count(">N/A<") == 1
        # nav link present so the section is actually reachable
        assert '<a href="#due-diligence" class="nav-link">Due Diligence</a>' in html

    def test_empty_checklist_omits_section_cleanly(self, tmp_path):
        verified = {"company": {}, "financial": {}, "due_diligence": []}
        out = tmp_path / "report.html"
        generate_html({}, self._meta(), verified, str(out))
        html = out.read_text(encoding="utf-8")

        assert 'id="due-diligence"' not in html
        assert "Due Diligence Checklist" not in html

    def test_missing_key_omits_section_cleanly(self, tmp_path):
        verified = {"company": {}, "financial": {}}
        out = tmp_path / "report.html"
        generate_html({}, self._meta(), verified, str(out))
        html = out.read_text(encoding="utf-8")

        assert 'id="due-diligence"' not in html


class TestTavilyQuotaExhaustedHtml:
    """A6 (2026-07-16): official['tavily_quota_exhausted'] (agent_official.py)
    was never read anywhere -- a quota-exhausted analysis rendered IDENTICAL to
    a genuinely clean firm (no litigation/OSINT signals found). Rendered onest."""

    def test_message_rendered_when_flag_set(self):
        data = {"tavily_quota_exhausted": {"value": True, "usage": 950}}
        html, nav = _build_rich_fields_html(data)
        assert 'id="tavily-quota"' in html
        assert "Verificare Incompleta" in html
        assert "NU a fost efectuata" in html
        assert "950/1000 interogari" in html
        assert 'href="#tavily-quota"' in nav

    def test_omitted_when_absent(self):
        html, nav = _build_rich_fields_html({})
        assert 'id="tavily-quota"' not in html
        assert "tavily-quota" not in nav


class TestMapsRatingKeyTakeawaysSectorPositionHtml:
    """2026-07-16 ("RIS colecteaza > afiseaza", etajul 3): 3 campuri calculate corect,
    randate in 0/8 formate inainte de acest fix (grep in backend/reports/ = 0
    potriviri pt fiecare). Fixture-urile folosesc formele si valorile REALE gasite
    in data/ris.db (job 85ec7fff, TAROM CUI 477647) -- repo public."""

    def test_maps_rating_rendered_with_real_tarom_shape(self):
        data = {"maps_rating": {
            "found": True, "name": "TAROM", "rating": 3.3, "reviews_count": 767,
            "place_id": "ChIJP-J_np8cskAR6IF5_IXDPgU",
            "address": "Calea Bucurestilor 224F, 075100 Otopeni", "source": "google_maps",
        }}
        html, nav = _build_rich_fields_html(data)
        assert 'id="maps-rating"' in html
        assert "3.3/5" in html
        assert "767 recenzii" in html
        assert "Otopeni" in html
        assert 'href="#maps-rating"' in nav

    def test_maps_rating_not_found_omits_section(self):
        """Real shape observed: {"found": False, "error": "no_results", "source":
        "google_maps"} -- must NOT render '0 stele', must omit the section entirely."""
        data = {"maps_rating": {"found": False, "error": "no_results", "source": "google_maps"}}
        html, nav = _build_rich_fields_html(data)
        assert 'id="maps-rating"' not in html
        assert "maps-rating" not in nav

    def test_maps_rating_absent_omits_section(self):
        html, _ = _build_rich_fields_html({})
        assert 'id="maps-rating"' not in html

    def test_sector_position_rendered_with_real_bucket_shape(self):
        data = {"risk_score": {"sector_position": {
            "Cifra de afaceri": {"ratio_vs_avg": 0.37, "estimated_percentile": "sub P25"},
            "Numar angajati": {"ratio_vs_avg": 0.12, "estimated_percentile": "sub P25"},
        }}}
        html, nav = _build_rich_fields_html(data)
        assert 'id="sector-position"' in html
        assert "sub P25" in html
        assert "Cifra de afaceri" in html
        assert 'href="#sector-position"' in nav
        # Must render as a categorical label, NOT a fabricated numeric percentage bar.
        assert "37%" not in html

    def test_sector_position_empty_dict_omits_section(self):
        data = {"risk_score": {"sector_position": {}}}
        html, nav = _build_rich_fields_html(data)
        assert 'id="sector-position"' not in html

    def test_key_takeaways_rendered_after_executive_summary(self, tmp_path):
        kt = (
            "• Cu o cifra de afaceri de 1,226,498,739 RON, TAROM prezinta o baza "
            "financiara solida pentru parteneriat.\n"
            "• Capitalurile proprii negative de -105,192,156 RON indica un risc de "
            "insolventa tehnica ce necesita monitorizare.\n"
            "• Avand 709 dosare judecatoresti, decidentii ar trebui sa evalueze "
            "suplimentar riscurile juridice asociate parteneriatului cu TAROM."
        )
        meta = {
            "company_name": "TAROM", "title": "Raport Test", "generated_at": "2026-07-16",
            "risk_score": "Verde", "numeric_score": 74.5, "risk_recommendation": "",
            "report_level": 2, "sources": [],
        }
        verified = {"company": {}, "financial": {}, "risk_score": {}, "key_takeaways": kt}
        out = tmp_path / "report.html"
        generate_html({}, meta, verified, str(out))
        html = out.read_text(encoding="utf-8")
        assert 'id="key-takeaways"' in html
        assert "Puncte Cheie" in html
        assert "Cu o cifra de afaceri de 1,226,498,739 RON" in html
        assert "709 dosare judecatoresti" in html
        assert '<a href="#key-takeaways" class="nav-link">Puncte Cheie</a>' in html
        # Executive summary must appear BEFORE the key takeaways block.
        assert html.index("Executive Summary") < html.index('id="key-takeaways"')

    def test_key_takeaways_none_omits_section(self, tmp_path):
        meta = {
            "company_name": "X", "title": "Raport Test", "generated_at": "2026-07-16",
            "risk_score": "Verde", "numeric_score": 74.5, "risk_recommendation": "",
            "report_level": 2, "sources": [],
        }
        verified = {"company": {}, "financial": {}, "risk_score": {}, "key_takeaways": None}
        out = tmp_path / "report.html"
        generate_html({}, meta, verified, str(out))
        html = out.read_text(encoding="utf-8")
        assert 'id="key-takeaways"' not in html


class TestPredictiveDivergenceHtml:
    """A4 (2026-07-16): dezacordul FAPTIC intre scorul 6D si modelele predictive
    de faliment disponibile, randat ca addendum in sectiunea existenta -- fara
    verdict nou, fara sectiune/nav separate."""

    def _sample_with_risk_score(self, risk_score, zmijewski):
        return {
            "risk_score": risk_score,
            "predictive_scores": {
                "altman_z": {"z_score": None, "zone": "INDISPONIBIL"},
                "piotroski_f": {"f_score": 4, "max_possible": 5, "grade": "STRONG"},
                "beneish_m": {"m_score": None, "risk": "INDISPONIBIL", "available": False},
                "zmijewski_x": zmijewski,
                "distress_signals": 0,
                "summary": "Indicatori financiari in zona normala",
            },
        }

    def test_divergence_rendered_when_present(self):
        data = self._sample_with_risk_score(
            {"score": "Verde", "numeric_score": 78.0},
            {"x_score": 2.4, "distress": True, "available": True},
        )
        html, _ = _build_rich_fields_html(data)
        assert "Dezacord intre scorul 6D si modelele predictive" in html
        assert "Scor 6D: Verde (78.0)" in html
        assert "Cele doua metode nu concorda" in html
        # verdictul original NU e suprascris -- inca apare in randare.
        assert "Verde" in html

    def test_no_divergence_block_when_models_agree(self):
        """Caz real (TAROM): scor Verde, Zmijewski fara semnal de distres -- ambele "ok"."""
        data = self._sample_with_risk_score(
            {"score": "Verde", "numeric_score": 74.5},
            {"x_score": -0.85, "distress": False, "available": True},
        )
        html, _ = _build_rich_fields_html(data)
        assert "Dezacord intre scorul 6D" not in html
        assert "Due Diligence Checklist" not in html


class TestRnpmManualGuaranteesHtml:
    """CERINTA #4 (2026-07-26): linia de verificare manuala RNPM (co.rnpm.ro) apare
    NECONDITIONAT in sectiunea Garantii, chiar cand nu exista date AEGRM/istoric.
    Non-vacuitate: pe HEAD sectiunea garantii se emitea DOAR pe `aegrm_ok or hist_ok`,
    deci pe fixture gol co.rnpm.ro era ABSENT -> E1 pica."""

    def _meta(self):
        return {
            "company_name": "Exemplu Test SRL",
            "title": "Raport Test",
            "generated_at": "2026-07-26",
            "risk_score": "Verde",
            "numeric_score": 82,
            "risk_recommendation": "",
            "report_level": 2,
            "sources": [],
        }

    def test_e1_rnpm_link_present_on_no_data_fixture(self, tmp_path):
        # Fixture FARA risk.aegrm_guarantees SI historical_flags=[] (calea necondiționata).
        verified = {"company": {}, "financial": {}, "historical_flags": []}
        out = tmp_path / "report.html"
        generate_html({}, self._meta(), verified, str(out))
        html = out.read_text(encoding="utf-8")

        assert 'id="garantii"' in html
        assert "co.rnpm.ro" in html
        assert 'href="https://co.rnpm.ro"' in html
        assert '<a href="#garantii" class="nav-link">' in html

    def test_e4_negative_no_false_clean_marker(self, tmp_path):
        # Pe calea no-data, sectiunea NU trebuie sa afirme "0 garantii"/"curat"/
        # "fara garantii" -- doar "indisponibil / verifica manual". [SANTINELA:
        # poate trece si pe HEAD unde sectiunea lipseste; nu e non-vac.]
        verified = {"company": {}, "financial": {}, "historical_flags": []}
        out = tmp_path / "report.html"
        generate_html({}, self._meta(), verified, str(out))
        html = out.read_text(encoding="utf-8")

        start = html.index('id="garantii"')
        end = html.index("</section>", start)
        garantii = html[start:end].lower()
        assert "verificare automata indisponibila" in garantii
        assert "0 garantii" not in garantii
        assert "fara garantii" not in garantii
        assert "curat" not in garantii
        # fara marker verde (#22c55e) pe absenta datelor de garantii
        assert "#22c55e" not in garantii
