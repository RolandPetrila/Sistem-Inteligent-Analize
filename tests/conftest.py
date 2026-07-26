"""
Fixtures globale pytest — izoleaza testele de starea reala din .env local.
"""

import hashlib
from pathlib import Path

import pytest

# Rezolvat o singura data, la import (cwd = root proiect cand ruleaza pytest),
# ca sa nu depinda de eventuale os.chdir() facute de alte teste in timpul rularii.
_ENV_PATH_FOR_GUARD = Path(".env").resolve()


def _env_snapshot() -> str | None:
    """Hash SHA-256 al continutului .env, sau None daca fisierul nu exista."""
    if not _ENV_PATH_FOR_GUARD.exists():
        return None
    return hashlib.sha256(_ENV_PATH_FOR_GUARD.read_bytes()).hexdigest()


@pytest.fixture(scope="session", autouse=True)
def _env_integrity_guard():
    """Garda anti-regresie MECANICA: .env-ul de PRODUCTIE nu trebuie NICIODATA
    modificat de suita de teste, indiferent CARE test face asta.

    Motiv (bug real, reprodus empiric): `test_update_settings` apela endpointul
    REAL `PUT /api/settings`, care rescria .env-ul de productie (SYNTHESIS_MODE
    claude_code -> autonomous) — invizibil, fara restaurare. Userul ruleaza
    RIS_TEST.bat prin dublu-click (procedura recomandata in CLAUDE.md); fiecare
    rulare schimba tacut configuratia de sinteza a sistemului. Un test care doar
    verifica status_code == 200 nu prinde asta.

    Aceasta garda compara hash SHA-256 al .env-ului INAINTE de primul test si
    DUPA ultimul test din sesiune — daca difera, suita PICA cu un mesaj explicit,
    indiferent care test anume a facut scrierea (acopera si teste viitoare, nu
    doar pe cel de azi).

    Limite cunoscute (documentate explicit, nu bug):
    - Daca .env NU exista (ex. CI fara fisier local) -> NO-OP, fara fals-pozitiv
      (nimic de protejat).
    - Daca UTILIZATORUL editeaza .env manual (Settings UI / alt terminal) chiar
      in timpul rularii suitei -> garda VA pica, e un fals-pozitiv real. Considerat
      acceptabil: scrierea concurenta pe fisierul de productie e oricum un risc
      independent de teste, iar fereastra de coliziune e ingusta (durata unei
      rulari pytest).
    """
    before = _env_snapshot()
    yield
    if before is None:
        return
    after = _env_snapshot()
    assert after == before, (
        "\n\n[GARDA CRITICA] .env-ul de PRODUCTIE a fost MODIFICAT in timpul "
        "rularii suitei de teste!\n"
        f"  Hash SHA-256 INAINTE : {before}\n"
        f"  Hash SHA-256 DUPA    : {after}\n\n"
        "Un test a scris in .env-ul real (cel mai probabil printr-un apel REAL la "
        "endpointul PUT /api/settings, sau prin scriere directa in fisier). Acesta "
        "a fost deja un incident real: SYNTHESIS_MODE a fost schimbat tacut din "
        "'claude_code' in 'autonomous' de fiecare rulare a RIS_TEST.bat.\n\n"
        "FIX: gaseste testul vinovat (ruleaza pytest cu -k pe subseturi ca sa "
        "il izolezi) si izoleaza-l de starea reala — monkeypatch pe calea .env "
        "folosita de cod (ex. ENV_PATH) catre tmp_path, NU lasa efectul sa se "
        "propage in fisierul real. Vezi "
        "tests/test_routers.py::TestSettingsEndpoints::test_update_settings "
        "pentru un exemplu de izolare corecta."
    )


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


@pytest.fixture(autouse=True)
def _no_provider_api_keys_in_tests():
    """CERINTA #7 — inchide clasa F1 (scurgere de BANI in pytest): cheile de PROVIDER AI
    (openrouter/groq/cerebras/mistral/sambanova/google_ai) NU trebuie sa fie LIVE in teste.
    Altfel orice test care ruleaza lantul de sinteza NEMOCKAT face un apel PLATIT REAL — s-a
    intamplat in CERINTA #6: OpenRouter a fost facturat pana s-au reparat 2 teste chain-driven.
    `_no_api_key_in_tests` (de mai sus) golea DOAR `ris_api_key`, lasand cheile de provider vii.

    Setul de chei e DERIVAT din `ai_models.AI_PROVIDERS` (NU lista hardcodata) — auto-acopera
    providerii viitori, exact ca stubbing-ul chain-driven din #6. save->empty->restore per cheie,
    cu teardown LIFO. Compatibil cu testele care au nevoie legitim de o cheie: ele si-o seteaza
    LOCAL via `monkeypatch` in corpul testului (ex. test_provider_guards.py) — fixture-ul ruleaza
    la SETUP, monkeypatch-ul suprascrie, iar teardown-ul restaureaza valoarea reala.

    Fail-LOUD (nu skip tacut): daca un `api_key_attr` din config nu are camp in Settings (typo /
    provider nou fara field), o garda care il sare tacut ar reintroduce EXACT clasa F1 pe care o
    inchide — asta e semnatura de bug a proiectului ("verificarea care nu poate pica"). Ridica in loc.

    NU atinge `ris_api_key` (gestionat separat mai sus) si NICI garda `.env` hash (`_env_integrity_guard`):
    mutam DOAR obiectul `settings` in memorie, nu scriem in fisierul .env de pe disc.
    """
    from backend.agents.ai_models import AI_PROVIDERS
    from backend.config import settings

    attrs = sorted(
        {cfg["api_key_attr"] for cfg in AI_PROVIDERS.values() if cfg.get("api_key_attr")}
    )
    assert attrs, (
        "Niciun api_key_attr derivat din AI_PROVIDERS — derivarea s-a rupt (import/shape). "
        "Fara ea, garda F1 ar trece VACUU peste zero chei."
    )
    missing = [a for a in attrs if not hasattr(settings, a)]
    assert not missing, (
        f"api_key_attr fara camp in Settings (typo config / provider nou fara field): {missing}. "
        "NU golesc doar restul — asta ar lasa un provider cu cheia vie (F1). Repara config-ul."
    )

    originals = {a: getattr(settings, a) for a in attrs}
    for a in attrs:
        setattr(settings, a, "")
    yield
    for a, v in originals.items():
        setattr(settings, a, v)
