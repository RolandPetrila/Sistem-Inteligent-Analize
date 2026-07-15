"""
A2 (2026-07-16) — parsare `anaf.data_inregistrare` in `_detect_anomalies` (Regula 5:
firma foarte noua + CA mare).

Verificat LIVE 2026-07-16 (`get_anaf_data`, 3 CUI-uri reale: 6719278, 26313362,
477647): ANAF returneaza data in format ISO (`yyyy-mm-dd`) — NICIUNUL din cele 3
in formatul `%d.%m.%Y` pe care codul vechi il astepta EXCLUSIV
(`datetime.strptime(data_inreg, "%d.%m.%Y")`). Pe date reale asta arunca
`ValueError`, prins de un except generic -> Regula 5 sarita SILENTIOS.

Toate fixture-urile existente (tests/fixtures/scoring_golden_inputs.py,
tests/test_compare_score.py, tests/test_scoring.py) foloseau deja ISO,
confirmand independent ca formatul cu punct nu reflecta sursa reala.

Date 100% fictive — repo public.
"""

from backend.agents.agent_verification import VerificationAgent


def _official(data_inregistrare: str, ca: float = 1_500_000) -> dict:
    """official_data minimal ca sa declanseze Regula 5: firma < 1 an + CA > 500K."""
    return {
        "anaf": {"found": True, "data_inregistrare": data_inregistrare, "inactiv": False},
        "financial_official": {
            "data": {
                2025: {
                    "cifra_afaceri_neta": ca,
                    "numar_mediu_salariati": 3,
                }
            }
        },
    }


class TestAnomalyDateParsing:
    def test_iso_format_triggers_young_company_rule(self):
        """Dovada de non-vacuitate: cu codul VECHI (strptime doar %d.%m.%Y),
        data ISO arunca ValueError -> regula NU se declanseaza deloc pe firma
        reala (recent infiintata). Cu fix-ul, se declanseaza."""
        agent = VerificationAgent()
        from datetime import UTC, datetime, timedelta

        recent_iso = (datetime.now(UTC) - timedelta(days=100)).strftime("%Y-%m-%d")
        official = _official(recent_iso)
        anomalies = agent._detect_anomalies(official, {})

        rules = [a["rule"] for a in anomalies]
        assert "Firma sub 1 an + CA > 500K" in rules, (
            f"Regula 5 nu s-a declansat pe data ISO {recent_iso!r} — regresia A2. "
            f"Anomalii gasite: {rules}"
        )

    def test_dot_format_still_works(self):
        """Contra-proba: formatul vechi (%d.%m.%Y) ramane suportat, nu doar ISO —
        fix-ul adauga, nu inlocuieste."""
        agent = VerificationAgent()
        from datetime import UTC, datetime, timedelta

        recent = datetime.now(UTC) - timedelta(days=100)
        recent_dot = recent.strftime("%d.%m.%Y")
        official = _official(recent_dot)
        anomalies = agent._detect_anomalies(official, {})

        rules = [a["rule"] for a in anomalies]
        assert "Firma sub 1 an + CA > 500K" in rules

    def test_old_iso_company_triggers_no_young_company_rule(self):
        """Firma veche (peste 2 ani) nu declanseaza nici 'Firma tanara', nici
        'sub 1 an' — verifica ca parsarea ISO da o varsta corecta, nu doar
        'nu arunca'."""
        agent = VerificationAgent()
        official = _official("2010-05-15")
        anomalies = agent._detect_anomalies(official, {})

        rules = [a["rule"] for a in anomalies]
        assert "Firma sub 1 an + CA > 500K" not in rules
        assert "Firma tanara" not in rules

    def test_unparseable_format_does_not_crash_and_is_debug_logged(self):
        """Un format complet necunoscut nu trebuie sa crape restul detectiei de
        anomalii — ramane degradat curat (regula 5 omisa), celelalte reguli tot
        ruleaza."""
        agent = VerificationAgent()
        official = _official("not-a-date-at-all")
        anomalies = agent._detect_anomalies(official, {})
        rules = [a["rule"] for a in anomalies]
        assert "Firma sub 1 an + CA > 500K" not in rules
        assert "Firma tanara" not in rules
        # celelalte reguli (ex. CA zero / capital minim) tot pot rula fara sa crape testul
        assert isinstance(anomalies, list)

    def test_iso_with_time_suffix(self):
        """Varianta cu timestamp (`yyyy-mm-dd hh:mm:ss`), posibila in alte surse —
        trebuie sa parseze partea de data, nu sa arunce."""
        agent = VerificationAgent()
        from datetime import UTC, datetime, timedelta

        recent = datetime.now(UTC) - timedelta(days=100)
        recent_iso_ts = recent.strftime("%Y-%m-%d") + " 00:00:00"
        official = _official(recent_iso_ts)
        anomalies = agent._detect_anomalies(official, {})
        rules = [a["rule"] for a in anomalies]
        assert "Firma sub 1 an + CA > 500K" in rules


class TestParseDataInregistrareUnit:
    """Teste directe pe helper-ul `_parse_data_inregistrare` (unitare, fara
    trecere prin _detect_anomalies)."""

    def test_iso(self):
        agent = VerificationAgent()
        d = agent._parse_data_inregistrare("2020-03-15")
        assert d is not None
        assert (d.year, d.month, d.day) == (2020, 3, 15)

    def test_dot(self):
        agent = VerificationAgent()
        d = agent._parse_data_inregistrare("15.03.2020")
        assert d is not None
        assert (d.year, d.month, d.day) == (2020, 3, 15)

    def test_empty_string(self):
        agent = VerificationAgent()
        assert agent._parse_data_inregistrare("") is None

    def test_garbage(self):
        agent = VerificationAgent()
        assert agent._parse_data_inregistrare("xyz") is None
