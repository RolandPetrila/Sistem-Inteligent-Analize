"""
Structured error codes — inlocuieste mesaje generice cu coduri specifice.
Folosit in API responses si logging.
"""

from enum import Enum


class ErrorCode(str, Enum):
    # ANAF
    ANAF_TIMEOUT = "ANAF_TIMEOUT"
    ANAF_NOT_FOUND = "ANAF_NOT_FOUND"
    ANAF_RATE_LIMITED = "ANAF_RATE_LIMITED"
    ANAF_BILANT_NO_DATA = "ANAF_BILANT_NO_DATA"

    # openapi.ro
    OPENAPI_TIMEOUT = "OPENAPI_TIMEOUT"
    OPENAPI_QUOTA_EXCEEDED = "OPENAPI_QUOTA_EXCEEDED"
    OPENAPI_AUTH_FAILED = "OPENAPI_AUTH_FAILED"

    # SEAP
    SEAP_TIMEOUT = "SEAP_TIMEOUT"
    SEAP_FORBIDDEN = "SEAP_FORBIDDEN"
    SEAP_NO_CONTRACTS = "SEAP_NO_CONTRACTS"

    # Tavily
    TAVILY_TIMEOUT = "TAVILY_TIMEOUT"
    TAVILY_QUOTA_EXCEEDED = "TAVILY_QUOTA_EXCEEDED"

    # BNR
    BNR_TIMEOUT = "BNR_TIMEOUT"
    BNR_PARSE_ERROR = "BNR_PARSE_ERROR"

    # AI Providers
    AI_ALL_PROVIDERS_FAILED = "AI_ALL_PROVIDERS_FAILED"
    AI_CLAUDE_UNAVAILABLE = "AI_CLAUDE_UNAVAILABLE"
    AI_GROQ_TIMEOUT = "AI_GROQ_TIMEOUT"

    # Validation
    CUI_INVALID = "CUI_INVALID"
    CUI_CHECKSUM_FAILED = "CUI_CHECKSUM_FAILED"
    INPUT_MISSING_REQUIRED = "INPUT_MISSING_REQUIRED"

    # System
    DB_ERROR = "DB_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    REPORT_NOT_FOUND = "REPORT_NOT_FOUND"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    BATCH_MAX_EXCEEDED = "BATCH_MAX_EXCEEDED"

    # Completeness
    COMPLETENESS_LOW = "COMPLETENESS_LOW"
    SYNTHESIS_INCOMPLETE = "SYNTHESIS_INCOMPLETE"


class RISError(Exception):
    """Eroare RIS cu cod structurat."""
    def __init__(self, code: ErrorCode, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code.value}] {message}")

    def to_dict(self) -> dict:
        return {
            "error_code": self.code.value,
            "message": self.message,
            "details": self.details,
        }


# Mapping error codes to HTTP status codes
ERROR_HTTP_STATUS = {
    ErrorCode.CUI_INVALID: 400,
    ErrorCode.CUI_CHECKSUM_FAILED: 400,
    ErrorCode.INPUT_MISSING_REQUIRED: 400,
    ErrorCode.BATCH_MAX_EXCEEDED: 400,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.JOB_NOT_FOUND: 404,
    ErrorCode.REPORT_NOT_FOUND: 404,
    ErrorCode.FILE_NOT_FOUND: 404,
    ErrorCode.ANAF_TIMEOUT: 504,
    ErrorCode.OPENAPI_TIMEOUT: 504,
    ErrorCode.SEAP_TIMEOUT: 504,
    ErrorCode.TAVILY_QUOTA_EXCEEDED: 503,
    ErrorCode.OPENAPI_QUOTA_EXCEEDED: 503,
    ErrorCode.AI_ALL_PROVIDERS_FAILED: 503,
    ErrorCode.DB_ERROR: 500,
}
