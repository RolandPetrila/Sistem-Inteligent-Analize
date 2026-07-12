"""
Fixtures globale pytest — izoleaza testele de starea reala din .env local.
"""

import pytest


@pytest.fixture(autouse=True)
def _no_api_key_in_tests():
    """RIS_API_KEY poate fi setat in .env local (protectie productie, vezi
    backend/middlewares.py ApiKeyMiddleware) — testele NU trebuie sa depinda
    de asta. Fara acest fixture, TestClient(app) din test_routers.py ar primi
    401 pe orice request de indata ce developerul seteaza o cheie locala."""
    from backend.config import settings

    original = settings.ris_api_key
    settings.ris_api_key = ""
    yield
    settings.ris_api_key = original
