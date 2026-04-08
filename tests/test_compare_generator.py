"""
Teste pentru compare_generator — generare PDF comparativ 2 firme.
"""
import os
import tempfile


def _make_company(name: str = "Test SRL", cui: str = "12345678") -> dict:
    return {
        "denumire": name,
        "cui": cui,
        "an_financiar": 2023,
        "stare": "ACTIVA",
        "cifra_afaceri": 1_000_000,
        "profit_net": 50_000,
        "angajati": 10,
        "capitaluri": 200_000,
        "scor_risc": 72,
        "label_risc": "Verde",
        "caen_code": "6201",
        "caen_descriere": "Activitati IT",
        "platitor_tva": True,
        "inactiv": False,
        "ratios": {
            "profit_margin": 5.0,
            "roe": 25.0,
            "roa": 10.0,
            "lichiditate": 1.5,
        },
    }


class TestGenerateComparePdf:
    def test_creeaza_fisier_pdf(self):
        from backend.reports.compare_generator import generate_compare_pdf

        a = _make_company("Alpha SRL", "11111111")
        b = _make_company("Beta SRL", "22222222")

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            generate_compare_pdf(a, b, path)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_functioneaza_cu_date_minimale(self):
        from backend.reports.compare_generator import generate_compare_pdf

        a = {"denumire": "A SRL", "cui": "1", "scor_risc": 50, "label_risc": "Galben"}
        b = {"denumire": "B SRL", "cui": "2", "scor_risc": 30, "label_risc": "Rosu"}

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            generate_compare_pdf(a, b, path)
            assert os.path.exists(path)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_functioneaza_cu_valori_none(self):
        from backend.reports.compare_generator import generate_compare_pdf

        a = _make_company()
        a["cifra_afaceri"] = None
        a["profit_net"] = None
        b = _make_company("Beta SRL", "99999999")

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            generate_compare_pdf(a, b, path)
            assert os.path.exists(path)
        finally:
            if os.path.exists(path):
                os.remove(path)
