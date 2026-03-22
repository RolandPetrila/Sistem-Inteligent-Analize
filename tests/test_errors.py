"""Tests for structured error codes and RISError exception."""
import pytest
from backend.errors import ErrorCode, RISError, ERROR_HTTP_STATUS


class TestErrorCode:
    """Test ErrorCode enum completeness and consistency."""

    def test_all_codes_are_strings(self):
        for code in ErrorCode:
            assert isinstance(code.value, str)
            assert code.value == code.name

    def test_critical_codes_exist(self):
        assert ErrorCode.CUI_INVALID
        assert ErrorCode.ANAF_TIMEOUT
        assert ErrorCode.DB_ERROR
        assert ErrorCode.RATE_LIMITED
        assert ErrorCode.AI_ALL_PROVIDERS_FAILED

    def test_no_duplicate_values(self):
        values = [code.value for code in ErrorCode]
        assert len(values) == len(set(values))


class TestRISError:
    """Test RISError exception class."""

    def test_basic_creation(self):
        err = RISError(ErrorCode.CUI_INVALID, "CUI format gresit")
        assert err.code == ErrorCode.CUI_INVALID
        assert err.message == "CUI format gresit"
        assert err.details == {}

    def test_with_details(self):
        err = RISError(ErrorCode.ANAF_TIMEOUT, "Timeout", {"cui": "12345678"})
        assert err.details["cui"] == "12345678"

    def test_to_dict(self):
        err = RISError(ErrorCode.DB_ERROR, "Connection failed")
        d = err.to_dict()
        assert d["error_code"] == "DB_ERROR"
        assert d["message"] == "Connection failed"
        assert isinstance(d["details"], dict)

    def test_str_representation(self):
        err = RISError(ErrorCode.RATE_LIMITED, "Too many requests")
        assert "[RATE_LIMITED]" in str(err)

    def test_is_exception(self):
        err = RISError(ErrorCode.CUI_INVALID, "test")
        assert isinstance(err, Exception)
        with pytest.raises(RISError):
            raise err


class TestErrorHttpStatus:
    """Test HTTP status code mapping."""

    def test_validation_errors_are_400(self):
        assert ERROR_HTTP_STATUS[ErrorCode.CUI_INVALID] == 400
        assert ERROR_HTTP_STATUS[ErrorCode.CUI_CHECKSUM_FAILED] == 400
        assert ERROR_HTTP_STATUS[ErrorCode.INPUT_MISSING_REQUIRED] == 400

    def test_not_found_errors_are_404(self):
        assert ERROR_HTTP_STATUS[ErrorCode.JOB_NOT_FOUND] == 404
        assert ERROR_HTTP_STATUS[ErrorCode.REPORT_NOT_FOUND] == 404

    def test_rate_limit_is_429(self):
        assert ERROR_HTTP_STATUS[ErrorCode.RATE_LIMITED] == 429

    def test_timeout_errors_are_504(self):
        assert ERROR_HTTP_STATUS[ErrorCode.ANAF_TIMEOUT] == 504

    def test_service_unavailable_are_503(self):
        assert ERROR_HTTP_STATUS[ErrorCode.AI_ALL_PROVIDERS_FAILED] == 503

    def test_all_mapped_codes_exist_in_enum(self):
        for code in ERROR_HTTP_STATUS:
            assert code in ErrorCode
