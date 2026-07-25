"""Tests for CUI validator — MOD 11 algorithm."""
from backend.agents.tools.cui_validator import extract_and_validate_cui, validate_cui


class TestValidateCUI:
    """Test CUI validation with known-good and known-bad CUIs."""

    def test_valid_cui_mosslein(self):
        result = validate_cui("26313362")
        assert result["valid"] is True
        assert result["cui_clean"] == "26313362"
        assert result["error"] is None

    def test_valid_cui_with_ro_prefix(self):
        result = validate_cui("RO26313362")
        assert result["valid"] is True
        assert result["cui_clean"] == "26313362"

    def test_valid_cui_with_spaces(self):
        result = validate_cui("  RO 26313362  ")
        assert result["valid"] is True

    def test_valid_cui_bitdefender(self):
        # Bitdefender CUI: 18189442
        result = validate_cui("18189442")
        assert result["valid"] is True

    def test_invalid_cui_wrong_check_digit(self):
        result = validate_cui("26313363")  # last digit wrong
        assert result["valid"] is False
        assert "Cifra de control" in result["error"]

    def test_empty_cui(self):
        result = validate_cui("")
        assert result["valid"] is False
        assert "gol" in result["error"]

    def test_non_numeric_cui(self):
        result = validate_cui("ABC123")
        assert result["valid"] is False
        assert "non-numerice" in result["error"]

    def test_too_short_cui(self):
        result = validate_cui("1")
        assert result["valid"] is False
        assert "2-10" in result["error"]

    def test_too_long_cui(self):
        result = validate_cui("12345678901")
        assert result["valid"] is False
        assert "2-10" in result["error"]

    def test_two_digit_cui(self):
        # Minimal valid length
        result = validate_cui("17")
        assert isinstance(result["valid"], bool)

    def test_lowercase_ro_prefix(self):
        result = validate_cui("ro26313362")
        assert result["valid"] is True


class TestExtractAndValidateCUI:
    """Test CUI extraction from free text."""

    def test_extract_plain_cui(self):
        result = extract_and_validate_cui("CUI-ul firmei este 26313362")
        assert result["valid"] is True

    def test_extract_ro_prefix(self):
        result = extract_and_validate_cui("RO26313362 este codul fiscal")
        assert result["valid"] is True

    def test_extract_no_cui(self):
        result = extract_and_validate_cui("nu contine niciun cod")
        assert result["valid"] is False

    def test_extract_with_spaces(self):
        result = extract_and_validate_cui("RO 26313362")
        assert result["valid"] is True


class TestExtractCUIAdversarial:
    """Pas 3 — extractie robusta din text liber (multi-candidat + garda ambiguitate).

    Fiecare test PICA pe codul vechi (re.search + \\d{2,10} + primul candidat).
    CUI-uri reale MOD11-valide: 9901265, 26313362 (Mosslein), 18189442 (Bitdefender).
    """

    def test_cui_valid_in_middle_after_decoy(self):
        # Decoy 2500000 (pica MOD11) INAINTE de CUI-ul real. Vechiul re.search prindea
        # 2500000 primul, il pica, si nu mai ajungea la 9901265.
        result = extract_and_validate_cui("investiție de 2500000 lei pentru firma 9901265")
        assert result["valid"] is True
        assert result["cui_clean"] == "9901265"

    def test_phone_decoy_before_real_cui(self):
        result = extract_and_validate_cui("telefon 0721234567, firma 9901265")
        assert result["valid"] is True
        assert result["cui_clean"] == "9901265"

    def test_short_number_not_extracted(self):
        # 3a: "42" (2 cifre) NU mai e extras (bound 6-10). Vechiul \\d{2,10} il prindea
        # ca cui_clean="42". Non-vacuu: assert pe cui_clean, nu doar pe valid.
        result = extract_and_validate_cui("cod 42 pentru firma")
        assert result["valid"] is False
        assert result["cui_clean"] == ""
        assert "neidentificat" in result["error"]

    def test_ambiguous_two_distinct_valid_stops(self):
        # 2 CUI-uri DISTINCTE valide -> STOP. Vechiul re.search alegea primul si-l valida.
        result = extract_and_validate_cui("firma 26313362 si partenerul 18189442")
        assert result["valid"] is False
        assert result["cui_clean"] == ""
        assert "ambiguu" in result["error"]

    def test_same_cui_repeated_is_not_ambiguous(self):
        result = extract_and_validate_cui("CUI 9901265, verificat 9901265")
        assert result["valid"] is True
        assert result["cui_clean"] == "9901265"

    def test_phone_only_no_valid_cui(self):
        result = extract_and_validate_cui("sunati la 0721234567")
        assert result["valid"] is False
        assert "neidentificat" in result["error"]

    def test_postal_code_only_no_valid_cui(self):
        result = extract_and_validate_cui("cod postal 400123 Cluj")
        assert result["valid"] is False
        assert "neidentificat" in result["error"]

    def test_long_number_not_sliced(self):
        # 11+ cifre (telefon fix/CNP) nu se ciopartesc in primele 10 -> zero candidati.
        result = extract_and_validate_cui("cont 12345678901 la banca")
        assert result["valid"] is False
        assert result["cui_clean"] == ""

    def test_empty_text(self):
        result = extract_and_validate_cui("")
        assert result["valid"] is False
