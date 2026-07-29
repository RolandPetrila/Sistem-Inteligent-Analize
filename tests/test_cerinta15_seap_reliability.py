"""CERINTA #15 (P4) — surface onest fiabilitate SEAP.

Numarul/valoarea din "Istoric Achizitii Publice (SICAP)" pot fi PARTIALE
(plafon server, itemi trunchiati, valoare = suma doar a itemilor adusi) fara ca
renderul s-o spuna. Producatorul declara flagurile (`total_capped`,
`items_truncated`, `total_value_is_partial`); cele 3 randere le incadreaza acum.

Non-vacuitate: pe HEAD (inainte de fix) niciun renderer nu emite calificativul ->
testele "shown_when_partial" PICA. Fiecare renderer verificat prin CONTINUT REAL
(HTML string / pdfplumber / python-docx), nu doar "nu arunca" (lectia 2026-07-14:
un camp randat html-only lasa bug latent in PDF/DOCX).
"""
import os
import tempfile

from backend.reports.docx_generator import generate_docx
from backend.reports.html_generator import _build_rich_fields_html
from backend.reports.pdf_generator import generate_pdf
from backend.reports.rich_fields import seap_count_caveat, seap_value_caveat


def _seap_verified(*, total_capped=False, items_truncated=False,
                   counts_reliable=True, total_value_is_partial=False, total_value=900000):
    """verified_data cu SEAP `_make_field`-wrapped (ca verified["market"]["seap"]).
    `contracts_verified=True` + `total_contracts>0` -> sectiunea RANDEAZA (has_seap)."""
    return {"market": {"seap": {"value": {
        "contracts_verified": True,
        "total_contracts": 5, "contracts_count": 3, "direct_count": 2, "total_value": total_value,
        "contracts": [{"title": "Reparatii drum", "value": 800000, "currency": "RON",
                       "authority": "Primaria X", "date": "2025-03-01"}],
        "direct_acquisitions": [{"title": "Consumabile", "value": 12000, "currency": "RON",
                                 "authority": "Spitalul Y", "date": "2024-11-01"}],
        "total_capped": total_capped, "items_truncated": items_truncated,
        "counts_reliable": counts_reliable, "total_value_is_partial": total_value_is_partial,
    }}}}


_PDF_META = {
    "title": "Raport RIS", "company_name": "Test SRL", "report_level": 2,
    "generated_at": "2026-07-29T10:00:00", "sources_count": 1, "risk_score": "Verde",
    "numeric_score": 80, "sources": [{"name": "SEAP", "level": 1, "status": "OK"}],
}
_DOCX_META = {
    "title": "Raport RIS", "company_name": "Test SRL", "report_level": 2,
    "generated_at": "2026-07-29T10:00:00", "sources_count": 1,
    "risk_score": {"score": 80, "label": "Verde"}, "sources": ["SEAP"],
}
_SECTIONS = {"executive_summary": {"title": "Rezumat Executiv", "content": "Firma analizata."}}


def _pdf_text(verified):
    import pdfplumber
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        path = f.name
    try:
        generate_pdf(_SECTIONS, _PDF_META, path, verified)
        with pdfplumber.open(path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    finally:
        if os.path.exists(path):
            os.remove(path)


def _docx_text(verified):
    from docx import Document
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name
    try:
        generate_docx(_SECTIONS, _DOCX_META, path, verified)
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    finally:
        if os.path.exists(path):
            os.remove(path)


class TestSeapCaveatHelpers:
    """Unit: calificativul se decide pe FAPTUL-sursa truthy, rezistent la absenta."""

    def test_count_caveat_none_when_reliable(self):
        assert seap_count_caveat({"counts_reliable": True}) is None

    def test_count_caveat_truncated(self):
        msg = seap_count_caveat({"items_truncated": True})
        assert msg and "partiala" in msg.lower()

    def test_count_caveat_capped_differentiated(self):
        msg = seap_count_caveat({"total_capped": True, "items_truncated": True})
        # capped are prioritate si formulare DISTINCTA de "trunchiat"
        assert msg and "plafonata" in msg.lower()

    def test_count_caveat_absent_keys_is_none(self):
        # calea CUI-invalid nu poarta niciun flag -> fara calificativ, nu crash.
        assert seap_count_caveat({}) is None
        assert seap_count_caveat({"total_contracts": 3}) is None

    def test_count_caveat_ignores_counts_reliable_false_alone(self):
        # `counts_reliable is False` NU declanseaza singur (e derivat, poate lipsi/muta);
        # doar faptele-sursa truthy o fac.
        assert seap_count_caveat({"counts_reliable": False}) is None

    def test_value_caveat_partial(self):
        msg = seap_value_caveat({"total_value_is_partial": True})
        assert msg and "cifra de afaceri" in msg.lower()

    def test_value_caveat_none_when_complete(self):
        assert seap_value_caveat({"total_value_is_partial": False}) is None
        assert seap_value_caveat({}) is None

    def test_helpers_tolerate_non_dict(self):
        assert seap_count_caveat(None) is None
        assert seap_value_caveat("x") is None


class TestSeapCaveatsHtml:
    def test_shown_when_partial(self):
        html, _ = _build_rich_fields_html(
            _seap_verified(items_truncated=True, counts_reliable=False, total_value_is_partial=True))
        assert 'id="achizitii"' in html
        assert "Numarare partiala" in html
        assert "Valoare partiala" in html

    def test_capped_wording(self):
        html, _ = _build_rich_fields_html(
            _seap_verified(total_capped=True, items_truncated=True, counts_reliable=False))
        assert "Numarare plafonata" in html

    def test_absent_when_complete(self):
        html, _ = _build_rich_fields_html(_seap_verified())  # totul complet
        assert 'id="achizitii"' in html  # sectiunea tot randeaza
        assert "Numarare partiala" not in html
        assert "Numarare plafonata" not in html
        assert "Valoare partiala" not in html

    def test_count_only_independent(self):
        # numar trunchiat DAR valoare completa -> DOAR count-caveat (gating independent).
        html, _ = _build_rich_fields_html(
            _seap_verified(items_truncated=True, counts_reliable=False, total_value_is_partial=False))
        assert "Numarare partiala" in html
        assert "Valoare partiala" not in html

    def test_value_caveat_without_displayed_value(self):
        # total_value=0 (toti itemii adusi fara valoare) DAR total_value_is_partial=True:
        # linia de valoare lipseste, calificativul TOT apare (nu gate pe valoare afisata).
        html, _ = _build_rich_fields_html(
            _seap_verified(total_value=0, total_value_is_partial=True))
        assert "valoare totala" not in html  # nicio valoare afisata
        assert "Valoare partiala" in html    # dar calificativul e prezent


class TestSeapCaveatsPdf:
    def test_shown_when_partial(self):
        text = _pdf_text(_seap_verified(items_truncated=True, counts_reliable=False,
                                        total_value_is_partial=True))
        assert "Numarare partiala" in text
        assert "Valoare partiala" in text

    def test_absent_when_complete(self):
        text = _pdf_text(_seap_verified())
        assert "contracte publice castigate" in text  # sectiunea tot randeaza
        assert "Numarare partiala" not in text
        assert "Numarare plafonata" not in text
        assert "Valoare partiala" not in text

    def test_count_only_independent(self):
        # gating independent in PDF: numar trunchiat, valoare completa -> doar count-caveat.
        text = _pdf_text(_seap_verified(items_truncated=True, counts_reliable=False,
                                        total_value_is_partial=False))
        assert "Numarare partiala" in text
        assert "Valoare partiala" not in text


class TestSeapCaveatsDocx:
    def test_shown_when_partial(self):
        text = _docx_text(_seap_verified(items_truncated=True, counts_reliable=False,
                                         total_value_is_partial=True))
        assert "Numarare partiala" in text
        assert "Valoare partiala" in text

    def test_absent_when_complete(self):
        text = _docx_text(_seap_verified())
        assert "contracte publice castigate" in text
        assert "Numarare partiala" not in text
        assert "Numarare plafonata" not in text
        assert "Valoare partiala" not in text

    def test_count_only_independent(self):
        # gating independent in DOCX: numar trunchiat, valoare completa -> doar count-caveat.
        text = _docx_text(_seap_verified(items_truncated=True, counts_reliable=False,
                                         total_value_is_partial=False))
        assert "Numarare partiala" in text
        assert "Valoare partiala" not in text
