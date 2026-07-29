"""CERINTA #16 (D) — tokenii foarte lungi in PDF nu mai pierd continut.

Vechiul `w[:55]+'-'+w[55:110]` ARUNCA tot ce trece de caracterul 110 (pierdere tacuta) si
putea declansa `multi_cell` "Not enough horizontal space" -> `[paragraf nerandat]`. Noul
`_soft_wrap_long_words` sparge tokenul in bucati infasurabile, pastrand TOATE caracterele.

Non-vacuitate: un token de 388 caractere cu marcajul `ZZZ` la coada (char 385). Pe HEAD
marcajul e ARUNCAT (truncat la 110) -> absent din PDF. Dupa fix e prezent.
"""
import os
import tempfile

from backend.reports.pdf_generator import _soft_wrap_long_words, generate_pdf

_META = {
    "title": "Raport RIS", "company_name": "Test SRL", "report_level": 2,
    "generated_at": "2026-07-30T10:00:00", "sources_count": 1, "risk_score": "Verde",
    "numeric_score": 80, "sources": [{"name": "X", "level": 1, "status": "OK"}],
}
# 385 = 7*55 -> "ZZZ" cade ca ultima bucata INTREAGA (nu spart de chunking)
LONG_TOKEN = "A" * 385 + "ZZZ"


def _pdf_text(content: str) -> str:
    import pdfplumber
    sections = {"executive_summary": {"title": "Rezumat", "content": content}}
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        path = f.name
    try:
        generate_pdf(sections, _META, path, {})
        with pdfplumber.open(path) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)
    finally:
        if os.path.exists(path):
            os.remove(path)


class TestSoftWrapUnit:
    def test_noop_sub_prag(self):
        assert _soft_wrap_long_words("cuvinte scurte normale") == "cuvinte scurte normale"

    def test_pastreaza_toate_caracterele(self):
        out = _soft_wrap_long_words(LONG_TOKEN)
        # nicio pierdere: toate 'A'-urile + marcajul, doar spatii inserate
        assert out.replace(" ", "") == LONG_TOKEN
        assert "ZZZ" in out

    def test_bucati_infasurabile(self):
        out = _soft_wrap_long_words("B" * 200)
        assert max(len(tok) for tok in out.split()) <= 55


class TestPdfPastreazaTokenLung:
    def test_coada_tokenului_e_randata(self):
        text = _pdf_text(f"Referinta lunga: {LONG_TOKEN} sfarsit.")
        assert "ZZZ" in text, "coada tokenului lung a fost pierduta (truncare la char 110)"
        assert "[paragraf nerandat]" not in text
