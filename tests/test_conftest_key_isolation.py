"""CERINTA #7 — garda de izolare: conftest goleste cheile de provider AI in pytest.

Inchide clasa F1 (scurgere de BANI in teste): un test care ruleaza lantul de sinteza NEMOCKAT
ar face un apel PLATIT REAL cu cheia ambientala din .env. Fixture-ul autouse
`_no_provider_api_keys_in_tests` (conftest.py) le goleste, DERIVAT din ai_models.AI_PROVIDERS.

Non-vacuitate (DOVADA MECANICA, in raportul din JURNAL_AUDIT): git-show-HEAD swap pe conftest.py
(fara fixture-ul nou) -> E1 PICA (cheia reala len 73 prezenta) + E2 structural PICA (spy apelat
fiindca cheia e prezenta; spy-ul previne orice apel real chiar si in fereastra de dovada).

Pereche: tests/test_provider_guards.py (pattern _FakeClient + monkeypatch cheie locala).
"""

import pytest

from backend.agents import ai_models, circuit_breaker
from backend.agents import synthesis_providers as sp
from backend.agents.synthesis_providers import SynthesisProvidersMixin
from backend.config import settings


class _Bare(SynthesisProvidersMixin):
    """Doar mixin-ul cu providerii — suficient pt _generate_with_openai_compat."""


class _SpyResp:
    status_code = 200
    text = ""
    headers: dict = {}

    def json(self):
        # 200 cu content -> daca s-ar ajunge aici, functia ar returna text. Dar E2 aserteaza ca
        # NU se ajunge (cheia goala blocheaza inainte de get_client).
        return {"choices": [{"message": {"content": "NU-AR-TREBUI-SA-AJUNGA-AICI"}}]}


class _SpyClient:
    """Daca `post` e apelat vreodata -> apelul (potential PLATIT) NU a fost blocat structural."""

    def __init__(self):
        self.post_calls = 0

    async def post(self, *args, **kwargs):
        self.post_calls += 1
        return _SpyResp()


# Setul DERIVAT (nu hardcodat) — aceeasi sursa ca fixture-ul din conftest.
_PROVIDER_KEY_ATTRS = sorted(
    {cfg["api_key_attr"] for cfg in ai_models.AI_PROVIDERS.values() if cfg.get("api_key_attr")}
)


class TestE1KeysEmptiedDuringSession:
    """E1: in timpul sesiunii, TOATE cheile de provider AI sunt golite de conftest."""

    def test_derived_set_non_empty(self):
        # Daca derivarea s-ar rupe (import/shape) -> setul gol -> restul testelor ar trece VACUU.
        assert _PROVIDER_KEY_ATTRS, "setul derivat de api_key_attr e gol — derivarea s-a rupt"

    def test_all_provider_keys_empty(self):
        # Bucla pe setul DERIVAT -> acopera si providerii viitori (non-hardcodat, ca B.1 din cerinta).
        # R-SEC: colectam NUMELE cheilor negolite, NU valorile — asa nici pe PICARE (conftest gresit)
        # assertion-rewrite-ul pytest nu tipareste o cheie reala in output. Doar bool + nume.
        non_empty = [attr for attr in _PROVIDER_KEY_ATTRS if getattr(settings, attr) != ""]
        assert not non_empty, (
            f"chei de provider NEGOLITE (clasa F1 deschisa — scurgere de bani): {non_empty}. "
            "Valorile NU se afiseaza (R-SEC)."
        )

    def test_openrouter_key_empty_literal_anchor(self):
        # Ancora LITERALA discriminanta: openrouter_api_key are valoare reala masurata (len 73) in
        # .env local -> pe conftest VECHI (fara fixture) ar fi non-goala -> PICA. Garanteaza ca E1
        # nu e vacuu chiar daca setul derivat s-ar schimba candva.
        # R-SEC: comparam intr-un bool LOCAL, ca assertion-rewrite sa tipareasca `assert False`,
        # NU valoarea cheii (altfel o PICARE ar scurge cheia reala in output-ul de test).
        is_empty = settings.openrouter_api_key == ""
        assert is_empty, (
            "openrouter_api_key NU e golit (conftest fara fixture-ul F1) — valoarea nu se afiseaza (R-SEC)"
        )


class TestE2StructuralBlockNoPaidCall:
    """E2: cu cheia golita, apelul e blocat STRUCTURAL inainte de get_client (nu doar mockat)."""

    @pytest.fixture(autouse=True)
    def _reset_provider_state(self):
        # Advisor: reset circuit + indisponibil, altfel get_client ar putea fi neapelat pt motivul
        # GRESIT (circuit deschis / provider marcat indisponibil de un test anterior) -> E2
        # ar "trece" nediscriminant, si pe conftest vechi. Izolam ca singura variabila sa fie cheia.
        circuit_breaker._provider_failures.clear()
        ai_models.clear_unavailable()
        yield
        circuit_breaker._provider_failures.clear()
        ai_models.clear_unavailable()

    @pytest.mark.asyncio
    async def test_empty_key_blocks_call_before_get_client(self, monkeypatch):
        # FARA cheie locala: conftest a golit-o -> `if not api_key: return None` (linia ~189)
        # se declanseaza INAINTE de get_client (linia ~218). Spy dovedeste ca niciun apel nu pleaca.
        spy = _SpyClient()
        monkeypatch.setattr(sp, "get_client", lambda: spy)

        out = await _Bare()._generate_with_openai_compat("prompt scurt", "openrouter")
        assert out is None
        assert spy.post_calls == 0, (
            "get_client apelat cu cheia goala — apelul (potential PLATIT) NU e blocat structural"
        )

    @pytest.mark.asyncio
    async def test_local_key_reenables_call(self, monkeypatch):
        # Jumatatea POZITIVA (advisor): singura diferenta fata de testul de mai sus e cheia. Cu ea
        # setata LOCAL, ACELASI apel AJUNGE la get_client -> dovedeste ca motivul blocarii de mai sus
        # e cheia goala, NU circuit/indisponibil. Dubleaza ca santinela E3 (compat cu monkeypatch local).
        monkeypatch.setattr(settings, "openrouter_api_key", "test-key-local", raising=False)
        spy = _SpyClient()
        monkeypatch.setattr(sp, "get_client", lambda: spy)

        await _Bare()._generate_with_openai_compat("prompt scurt", "openrouter")
        assert spy.post_calls == 1, (
            "cu cheie locala apelul TREBUIE sa ajunga la get_client — altfel E2 nu e discriminant"
        )
