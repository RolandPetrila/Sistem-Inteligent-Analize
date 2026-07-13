"""DRY #2 (2026-07-14): boundary proof for the report-format color helpers that
consume risk_bucket() (excel_generator._risk_fill, pptx_generator._risk_color).
Zero test coverage existed for these functions before this DRY pass -- these tests
close that gap and prove the exact literal (hex / RGBColor) is unchanged per bucket."""
from openpyxl.styles import PatternFill
from pptx.dml.color import RGBColor

from backend.reports.excel_generator import GREEN as XL_GREEN
from backend.reports.excel_generator import RED as XL_RED
from backend.reports.excel_generator import YELLOW as XL_YELLOW
from backend.reports.excel_generator import _risk_fill
from backend.reports.pptx_generator import GRAY_TEXT, RED, YELLOW, _risk_color
from backend.reports.pptx_generator import GREEN as PPTX_GREEN


class TestExcelRiskFillBoundaries:
    def _fill_color(self, fill: PatternFill) -> str:
        return fill.start_color.rgb[-6:]  # strip alpha prefix if present

    def test_verde_at_70(self):
        assert self._fill_color(_risk_fill(70)) == XL_GREEN

    def test_galben_just_below_70(self):
        assert self._fill_color(_risk_fill(69.99)) == XL_YELLOW

    def test_galben_at_40(self):
        assert self._fill_color(_risk_fill(40)) == XL_YELLOW

    def test_rosu_just_below_40(self):
        assert self._fill_color(_risk_fill(39.99)) == XL_RED


class TestPptxRiskColorBoundaries:
    def test_numeric_verde_at_70(self):
        assert _risk_color(70) == PPTX_GREEN

    def test_numeric_galben_just_below_70(self):
        assert _risk_color(69.99) == YELLOW

    def test_numeric_galben_at_40(self):
        assert _risk_color(40) == YELLOW

    def test_numeric_rosu_just_below_40(self):
        assert _risk_color(39.99) == RED

    def test_string_labels_unchanged(self):
        """Ramura de string (label deja calculat) nu trece prin risk_bucket -- ramane
        un consumator direct de eticheta, neatins de aceasta extractie."""
        assert _risk_color("Verde") == PPTX_GREEN
        assert _risk_color("Galben") == YELLOW
        assert _risk_color("Rosu") == RED
        assert _risk_color("necunoscut") == GRAY_TEXT
        assert isinstance(_risk_color(70), RGBColor)
