"""
A1 (2026-07-16) — teste NON-VACUE pentru granita de eroare din
`VerificationAgent._compute_predictive_scores` / `_compute_credit_exposure`.

Bug reparat: `except Exception: logger.debug(...)` inghitea orice exceptie
(ImportError/TypeError/AttributeError = BUG DE PROGRAMARE, nu date lipsa —
`calculate_all_predictive_scores`/`commercial_exposure_ron` sunt deja defensive
fata de date lipsa si returneaza INDISPONIBIL, nu arunca) fara nicio urma
vizibila si fara sa lase cheia `predictive_scores`/`credit_exposure` in
`verified` — raportul pierdea sectiunea complet, in tacere.

Precedent dovedit de 2 ori in acest proiect: un `ImportError` (functie
inexistenta `get_caen_info`) si un `TypeError` (comparatie string vs numar)
ascunse la `logger.debug` au stat nedescoperite zile intregi.

Aceste teste dovedesc DOUA lucruri, ambele necesare simultan:
1. cheia ramane prezenta in `verified`, marcata explicit INDISPONIBIL/eroare
   (nu disparitie tacuta a sectiunii din raport);
2. exceptia e vizibila in log la nivel WARNING+ (nu doar DEBUG).

Date 100% fictive — repo public.
"""

from backend.agents.agent_verification import VerificationAgent, logger


def _state() -> dict:
    return {"official_data": {}, "web_data": {}, "market_data": {}}


class _LogCapture:
    """Capteaza inregistrarile loguru (nu se leaga la stdlib logging / caplog)."""

    def __init__(self):
        self.records: list = []
        self._sink_id: int | None = None

    def __enter__(self):
        self._sink_id = logger.add(
            lambda msg: self.records.append(msg.record), level="DEBUG"
        )
        return self

    def __exit__(self, *exc):
        logger.remove(self._sink_id)

    def has_level_at_or_above(self, min_level_no: int, containing: str | None = None) -> bool:
        """`containing`: filtreaza intai dupa un fragment din mesaj, ca sa nu
        se confunde cu ALTE inregistrari WARNING+ care apar oricum in `execute()`
        (ex. "DATE LIPSA" e emis la WARNING indiferent de crash-ul injectat aici
        — un test care nu filtreaza pe continut ar trece VACUU si pe codul vechi,
        exact modul de vacuitate impotriva caruia ne apara asta)."""
        candidates = self.records
        if containing is not None:
            candidates = [r for r in candidates if containing in r["message"]]
        return any(r["level"].no >= min_level_no for r in candidates)


class TestPredictiveScoresErrorBoundary:
    async def test_crash_leaves_explicit_indisponibil_not_missing_key(self, monkeypatch):
        """Dovada de non-vacuitate #1: cu codul VECHI, o exceptie in
        `calculate_all_predictive_scores` lasa `predictive_scores` ABSENT din
        `verified` (assignment-ul insusi esueaza inauntrul try). Cu fix-ul,
        cheia ramane prezenta, marcata explicit ca eroare."""

        def _boom(*a, **kw):
            raise TypeError("boom sintetic — simuleaza un bug de programare real")

        monkeypatch.setattr(
            "backend.agents.verification.predictive_models.calculate_all_predictive_scores",
            _boom,
        )

        result = await VerificationAgent().execute(_state())
        verified = result["verified_data"]

        assert "predictive_scores" in verified, (
            "predictive_scores a disparut complet din raport dupa o exceptie — "
            "exact regresia A1 (cheia trebuie sa ramana, marcata INDISPONIBIL)"
        )
        ps = verified["predictive_scores"]
        assert ps["error"] is True
        assert ps["models_available"] == 0
        assert ps["altman_z"]["zone"] == "INDISPONIBIL"
        assert ps["piotroski_f"]["grade"] == "INSUFICIENT"
        assert ps["beneish_m"]["available"] is False
        assert ps["zmijewski_x"]["available"] is False
        assert "eroare interna" in ps["summary"].lower()

    async def test_crash_is_loud_in_logs_not_debug_only(self, monkeypatch):
        """Dovada de non-vacuitate #2: exceptia trebuie sa produca un log la
        WARNING+ (loguru ERROR pt logger.exception), nu doar DEBUG. Cu codul
        vechi (`logger.debug`), un filtru la WARNING+ nu gaseste nimic."""
        import logging as _logging

        def _boom(*a, **kw):
            raise TypeError("boom sintetic — simuleaza un bug de programare real")

        monkeypatch.setattr(
            "backend.agents.verification.predictive_models.calculate_all_predictive_scores",
            _boom,
        )

        with _LogCapture() as cap:
            await VerificationAgent().execute(_state())

        assert cap.has_level_at_or_above(_logging.WARNING, containing="predictive scores"), (
            "Nicio inregistrare WARNING+ care sa mentioneze 'predictive scores' — "
            "exceptia a ramas ascunsa la nivel DEBUG (regresia A1). NU se numara "
            "alte WARNING-uri neinrudite (ex. 'DATE LIPSA') care apar oricum."
        )

    async def test_happy_path_unaffected(self):
        """Contra-proba: fara nicio exceptie, comportamentul normal (deja
        acoperit de test_predictive_models_wiring.py) nu se schimba —
        predictive_scores ramane populat normal, fara `error`."""
        result = await VerificationAgent().execute(_state())
        verified = result["verified_data"]
        assert "predictive_scores" in verified
        assert "error" not in verified["predictive_scores"]


class TestCreditExposureErrorBoundary:
    async def test_crash_leaves_explicit_error_not_missing_key(self, monkeypatch):
        def _boom(*a, **kw):
            raise AttributeError("boom sintetic — simuleaza un bug de programare real")

        monkeypatch.setattr(
            "backend.agents.verification.credit_exposure.commercial_exposure_ron",
            _boom,
        )

        result = await VerificationAgent().execute(_state())
        verified = result["verified_data"]

        assert "credit_exposure" in verified, (
            "credit_exposure a disparut complet din raport dupa o exceptie — "
            "exact regresia A1"
        )
        ce = verified["credit_exposure"]
        assert ce["error"] is True
        assert ce["expunere_ron"] == 0
        assert ce["kill_switch"] is True

    async def test_crash_is_loud_in_logs_not_debug_only(self, monkeypatch):
        import logging as _logging

        def _boom(*a, **kw):
            raise AttributeError("boom sintetic — simuleaza un bug de programare real")

        monkeypatch.setattr(
            "backend.agents.verification.credit_exposure.commercial_exposure_ron",
            _boom,
        )

        with _LogCapture() as cap:
            await VerificationAgent().execute(_state())

        assert cap.has_level_at_or_above(_logging.WARNING, containing="credit exposure"), (
            "Nicio inregistrare WARNING+ care sa mentioneze 'credit exposure' — "
            "exceptia a ramas ascunsa la nivel DEBUG (regresia A1). NU se numara "
            "alte WARNING-uri neinrudite (ex. 'DATE LIPSA') care apar oricum."
        )
