"""CERINTA #14 (P2): perioade financiare personalizate CONECTATE.

NON-VACUITATE (pica pe HEAD 71d1a44):
  - `_parse_period_custom` si `_build_period_note` NU exista pe HEAD -> importul de mai
    jos arunca ImportError -> TOT fisierul pica pe codul vechi.
  - `_resolve_bilant_years` avea UN singur parametru pe HEAD -> apelul cu 2 argumente
    (test_custom_has_precedence_over_select) ar arunca TypeError.
  - Testul de onestitate (raw cerut != interval livrat, ambele prezente) nu are cum sa
    treaca pe HEAD (nu exista captura raw-ului inainte de clamp).
Dovada mecanica a swap-ului la HEAD e in raportul executorului din JURNAL_AUDIT.md.
"""

import os
import tempfile
from datetime import date

from backend.agents.agent_official import (
    _ANAF_BILANT_FLOOR,
    _build_period_note,
    _parse_period_custom,
    _resolve_bilant_years,
)

CUR_END = date.today().year - 1  # ultimul an complet disponibil (an curent - 1)


class TestResolveBilantYearsSignature:
    """B2 + non-vac: semnatura noua (period, period_custom), precedenta + clamp."""

    def test_custom_has_precedence_over_select(self):
        # PICA pe HEAD: _resolve_bilant_years avea 1 param -> TypeError la 2 args.
        assert _resolve_bilant_years("Ultimii 3 ani", "2016-2020") == (2016, 2020)

    def test_custom_clamped_to_anaf_limits(self):
        assert _resolve_bilant_years(None, "2010-2099") == (_ANAF_BILANT_FLOOR, CUR_END)

    def test_empty_custom_falls_to_select_no_regression(self):
        assert _resolve_bilant_years("Ultimii 5 ani", "") == (CUR_END - 4, CUR_END)

    def test_invalid_text_custom_falls_to_select(self):
        assert _resolve_bilant_years("Ultimii 5 ani", "text invalid") == (CUR_END - 4, CUR_END)

    def test_future_only_interval_falls_to_select(self):
        # "2030-2099" -> post-clamp start(2030) > end(CUR_END) -> invalid -> cade pe select.
        assert _resolve_bilant_years("Ultimii 3 ani", "2030-2099") == (CUR_END - 2, CUR_END)

    def test_backward_compat_single_arg_identical(self):
        # Calea #12 (un singur argument) ramane valida + IDENTICA (zero regresie).
        assert _resolve_bilant_years("Ultimii 3 ani") == (CUR_END - 2, CUR_END)
        assert _resolve_bilant_years("Ultimii 5 ani") == (CUR_END - 4, CUR_END)
        assert _resolve_bilant_years(None) == (2019, CUR_END)


class TestParsePeriodCustom:
    def test_basic_hyphen(self):
        assert _parse_period_custom("2016-2020") == (2016, 2020)

    def test_tolerant_separators_and_spaces(self):
        assert _parse_period_custom(" 2016 - 2019 ") == (2016, 2019)
        assert _parse_period_custom("2016—2019") == (2016, 2019)  # em-dash
        assert _parse_period_custom("2016–2019") == (2016, 2019)  # en-dash
        assert _parse_period_custom("2016/2019") == (2016, 2019)

    def test_inverse_order_invalid(self):
        assert _parse_period_custom("2020-2016") is None

    def test_empty_and_non_string(self):
        assert _parse_period_custom("") is None
        assert _parse_period_custom(None) is None
        assert _parse_period_custom(2020) is None

    def test_no_two_years(self):
        assert _parse_period_custom("doar 2020") is None
        assert _parse_period_custom("2020") is None


class TestBuildPeriodNoteHonesty:
    """B4: onestitate cerut-vs-livrat. Nota se declanseaza DOAR pe clamp sau goluri."""

    def _bilant(self, data_found=True, years=None):
        return {"data_found": data_found, "data": {"years_found": years or []}}

    def test_clamp_captures_raw_distinct_from_resolved(self):
        # NON-VAC onestitate: raw cerut != interval livrat, ambele prezente, distincte.
        note = _build_period_note(
            "Ultimii 3 ani", "2010-2099", self._bilant(True, [2024, 2023, 2022, 2021, 2020])
        )
        assert note is not None
        assert note["requested"] == [2010, 2099]
        assert note["resolved"] == [_ANAF_BILANT_FLOOR, CUR_END]
        assert note["requested"] != note["resolved"]
        assert note["clamped"] is True
        assert "2010-2099" in note["message"]  # raw cerut apare in mesaj
        assert f"{_ANAF_BILANT_FLOOR}-{CUR_END}" in note["message"]  # intervalul livrat apare

    def test_concordance_returns_none(self):
        # Cerut == livrat, fara goluri -> fara nota (fara zgomot).
        note = _build_period_note(
            None, "2020-2024", self._bilant(True, [2024, 2023, 2022, 2021, 2020])
        )
        assert note is None

    def test_no_custom_returns_none_zero_regression(self):
        # Calea `period` select (fara period_custom) nu capata nicio nota.
        assert _build_period_note("Ultimii 5 ani", None, self._bilant(True, [2024])) is None
        assert _build_period_note("Ultimii 5 ani", "", self._bilant(True, [2024])) is None

    def test_source_failed_no_availability_claim(self):
        # advisor item 3: "sursa a esuat" != "ANAF n-are date pt anii ceruti".
        note = _build_period_note(None, "2010-2099", self._bilant(False, []))
        assert note is not None
        assert note["clamped"] is True
        assert note["data_found"] is False
        assert "Date disponibile" not in note["message"]  # NU afirma disponibilitate
        assert "nu au putut fi obtinute" in note["message"]

    def test_source_failed_no_clamp_returns_none(self):
        # Fara clamp + sursa picata -> nu inventam o nota (missing nu se calculeaza).
        assert _build_period_note("Ultimii 3 ani", "2016-2018", self._bilant(False, [])) is None

    def test_gaps_reported_within_resolved(self):
        # Cerut valid (fara clamp) dar ANAF are goluri -> nota cu anii lipsa.
        note = _build_period_note(None, "2016-2020", self._bilant(True, [2020, 2019, 2018]))
        assert note is not None
        assert note["clamped"] is False
        assert note["missing_years"] == [2016, 2017]
        assert "2016, 2017" in note["message"]

    def test_str_years_found_normalized_no_false_gaps(self):
        # advisor item 1: cache-hit JSON poate da str -> normalizat la int; concordanta,
        # NU goluri false pe fiecare an (ar fi fost bug fixture-vs-producator).
        note = _build_period_note(
            None, "2018-2020", self._bilant(True, ["2020", "2019", "2018"])
        )
        assert note is None


class TestRichFieldsGate:
    def test_gate_shown_when_message_present(self):
        from backend.reports.rich_fields import build_rich_fields_model
        note = {"message": "Interval financiar cerut: 2010-2099.", "requested": [2010, 2099]}
        model = build_rich_fields_model({"financial_period_note": note})
        assert model["financial_period_note"]["shown"] is True
        assert model["financial_period_note"]["data"] is note

    def test_gate_hidden_when_absent_or_no_message(self):
        from backend.reports.rich_fields import build_rich_fields_model
        assert build_rich_fields_model({})["financial_period_note"]["shown"] is False
        # dict fara `message` -> nu se randeaza (gate pe continut real, nu pe prezenta cheii)
        model = build_rich_fields_model({"financial_period_note": {"requested": [1, 2]}})
        assert model["financial_period_note"]["shown"] is False


class TestRenderAcrossFormats:
    """Lectia rich-fields (2026-07-14): un camp randat DOAR in HTML lasa bug latent in
    PDF/DOCX (calea populata nu ruleaza niciodata acolo). Nota de perioada se randeaza in
    toate 3 formatele narative -> testata efectiv in toate 3, cu extractie de continut."""

    MSG = ("Interval financiar cerut: 2010-2099. Ajustat la limitele ANAF Bilant "
           "(2014-2025): interogat 2014-2025.")

    def _verified(self):
        return {"financial_period_note": {
            "message": self.MSG, "requested": [2010, 2099],
            "resolved": [2014, 2025], "clamped": True, "data_found": True,
            "years_found": [2024, 2023], "missing_years": [], "floor": 2014,
        }}

    def test_html_renders_message_and_nav(self):
        from backend.reports.html_generator import _build_rich_fields_html
        html, nav = _build_rich_fields_html(self._verified())
        assert "Interval financiar cerut: 2010-2099" in html
        assert "period-note" in nav
        # absent cand campul lipseste
        _, nav2 = _build_rich_fields_html({})
        assert "period-note" not in nav2

    def test_docx_renders_message(self):
        from docx import Document

        from backend.reports.docx_generator import _add_rich_fields_docx
        doc = Document()
        _add_rich_fields_docx(doc, self._verified())
        full = "\n".join(p.text for p in doc.paragraphs)
        assert "Interval financiar cerut: 2010-2099" in full

    def test_pdf_renders_message(self):
        # Direct pe _add_rich_fields_pdf (functia exacta care randeaza nota), nu prin
        # generate_pdf complet (care cere un verified_data bogat pt celelalte sectiuni).
        import pdfplumber

        from backend.reports.pdf_generator import RISPdf, _add_rich_fields_pdf
        meta = {"title": "Raport RIS", "company_name": "Test SRL", "report_level": 2,
                "generated_at": "2026-07-29T10:00:00", "risk_score": "Verde"}
        pdf = RISPdf(meta)
        pdf.add_page()
        _add_rich_fields_pdf(pdf, self._verified())
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "r.pdf")
            pdf.output(path)
            with pdfplumber.open(path) as doc:
                text = "\n".join(p.extract_text() or "" for p in doc.pages)
        assert "Interval financiar cerut: 2010-2099" in text
