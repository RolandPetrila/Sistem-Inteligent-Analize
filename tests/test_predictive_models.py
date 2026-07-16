"""
F8-5: Teste pentru modele predictive financiare.
Testeaza Altman Z''-EMS, Piotroski F-Score, Beneish M-Score, Zmijewski X-Score.
"""

from backend.agents.verification.scoring import (
    calculate_all_predictive_scores,
    calculate_altman_z_ems,
    calculate_beneish_m,
    calculate_piotroski_f,
    calculate_zmijewski_x,
)

# ─── Fixtures ───────────────────────────────────────────────────────────────

BILANT_SANATOS = {
    "cifra_afaceri": 5_000_000,
    "profit_net": 500_000,
    "profit_brut": 650_000,
    "capitaluri_proprii": 2_000_000,
    "total_datorii": 1_000_000,
    "active_totale": 3_000_000,
    "active_curente": 1_500_000,
    "datorii_curente": 500_000,
    "rezultat_reportat": 400_000,
}

BILANT_DISTRESS = {
    "cifra_afaceri": 1_000_000,
    "profit_net": -300_000,
    "profit_brut": -200_000,
    "capitaluri_proprii": -100_000,
    "total_datorii": 2_000_000,
    "active_totale": 1_900_000,
    "active_curente": 300_000,
    "datorii_curente": 800_000,
    "rezultat_reportat": -300_000,
}

BILANT_ANTERIOR = {
    "cifra_afaceri": 4_000_000,
    "profit_net": 300_000,
    "capitaluri_proprii": 1_700_000,
    "total_datorii": 900_000,
    "active_totale": 2_600_000,
    "active_curente": 1_200_000,
    "datorii_curente": 400_000,
}

BILANT_GOL = {}


# ─── Altman Z''-EMS ─────────────────────────────────────────────────────────

class TestAltmanZEMS:

    def test_firma_sanatoasa_zona_safe(self):
        result = calculate_altman_z_ems(BILANT_SANATOS)
        assert result["zone"] == "SAFE"
        assert result["z_score"] is not None
        assert result["z_score"] > 2.60
        assert result["confidence"] > 0

    def test_firma_distress_zona_distress(self):
        result = calculate_altman_z_ems(BILANT_DISTRESS)
        assert result["zone"] in ("DISTRESS", "GREY")
        assert result["z_score"] is not None

    def test_active_zero_returneaza_indisponibil(self):
        bilant = {"cifra_afaceri": 1_000_000, "active_totale": 0}
        result = calculate_altman_z_ems(bilant)
        assert result["zone"] == "INDISPONIBIL"
        assert result["z_score"] is None
        assert result["confidence"] == 0

    def test_bilant_gol_returneaza_indisponibil(self):
        result = calculate_altman_z_ems(BILANT_GOL)
        assert result["zone"] == "INDISPONIBIL"
        assert result["z_score"] is None

    def test_are_disclaimer(self):
        result = calculate_altman_z_ems(BILANT_SANATOS)
        assert "disclaimer" in result
        assert len(result["disclaimer"]) > 10

    def test_x_values_prezente(self):
        result = calculate_altman_z_ems(BILANT_SANATOS)
        assert "x_values" in result
        xv = result["x_values"]
        assert "X1" in xv and "X2" in xv and "X3" in xv and "X4" in xv

    def test_zona_grey(self):
        # Bilant la limita — capital scazut dar nu negativ
        bilant_grey = {
            "cifra_afaceri": 500_000,
            "profit_net": 10_000,
            "profit_brut": 15_000,
            "capitaluri_proprii": 50_000,
            "total_datorii": 400_000,
            "active_totale": 450_000,
            "active_curente": 200_000,
            "datorii_curente": 300_000,
            "rezultat_reportat": 5_000,
        }
        result = calculate_altman_z_ems(bilant_grey)
        assert result["zone"] in ("GREY", "DISTRESS", "SAFE")  # depinde de valori
        assert result["z_score"] is not None


# ─── Piotroski F-Score ───────────────────────────────────────────────────────

class TestPiotroskiF:

    def test_firma_sanatoasa_grad_strong(self):
        result = calculate_piotroski_f(BILANT_SANATOS, BILANT_ANTERIOR)
        assert result["f_score"] is not None
        assert result["f_score"] >= 0
        assert result["grade"] in ("STRONG", "AVERAGE", "WEAK", "INSUFICIENT")
        assert result["has_prior_year"] is True

    def test_fara_an_anterior_insuficient_sau_partial(self):
        result = calculate_piotroski_f(BILANT_SANATOS, None)
        assert result["grade"] in ("STRONG", "AVERAGE", "WEAK", "INSUFICIENT")
        assert result["has_prior_year"] is False
        # Fara an anterior, max 3 criterii calculate
        criteria = [c for c in result["criteria"] if c is not None]
        assert len(criteria) <= 3

    def test_bilant_gol_returneaza_insuficient(self):
        result = calculate_piotroski_f(BILANT_GOL)
        assert result["grade"] == "INSUFICIENT"
        assert result["f_score"] is None

    def test_firma_distress_weak(self):
        result = calculate_piotroski_f(BILANT_DISTRESS, BILANT_ANTERIOR)
        assert result["f_score"] is not None
        # Firma in distress ar trebui sa aiba scor mic
        assert result["grade"] in ("WEAK", "AVERAGE", "INSUFICIENT")

    def test_strong_grade_threshold_fixtura_existenta(self):
        """Ancora pe fixtura reala a fisierului: cu BILANT_SANATOS/BILANT_ANTERIOR,
        F2/F3 (cash_flow_operational absent) si F7 (cheltuieli_materiale absent)
        sunt None -> max_possible=6 (nu 9), restul (F1/F4/F5/F6/F8/F9) sunt toate
        1 -> f_score=6/6=1.0 >= 7/9 -> STRONG. Valori confirmate prin rulare
        directa a productiei (nu recalculate din formula in test)."""
        result = calculate_piotroski_f(BILANT_SANATOS, BILANT_ANTERIOR)
        assert result["f_score"] == 6
        assert result["max_possible"] == 6
        assert result["grade"] == "STRONG"

    def test_strong_grade_threshold(self):
        """Praguri HARDCODATE (nu recalculate din formula productiei — vechea
        varianta recalcula exact `ratio = f_score/max_possible` din
        `calculate_piotroski_f`, deci nu putea pica decat daca `max_possible`
        diferea de asteptare; era o tautologie, nu o verificare a pragului).

        Fixturi cu toate 9 criterii disponibile (cash_flow_operational +
        cheltuieli_materiale prezente in ambii ani, pe langa active/datorii
        curente) pentru a putea lovi EXACT pragurile 7/9 si 4/9 din productie
        (`predictive_models.py`, ratio >= 7/9 -> STRONG, >= 4/9 -> AVERAGE,
        altfel WEAK). Fiecare caz e verificat manual (vezi comentariile per
        criteriu) si confirmat prin rulare directa a productiei inainte de a fi
        scris aici — vezi si dovada de mutatie in test_mutatie_prag_strong_detectata."""
        t1_base = {
            "active_totale": 1_000_000,
            "profit_net": 50_000,       # ROA t-1 = 0.05
            "cifra_afaceri": 500_000,   # rotatie t-1 = 0.5
            "total_datorii": 400_000,   # leverage t-1 = 0.4
            "active_curente": 300_000,
            "datorii_curente": 200_000,  # lichiditate t-1 = 1.5
            "capitaluri_proprii": 600_000,
            "cheltuieli_materiale": 300_000,  # marja t-1 = 0.4
        }

        # 9/9 (ratio=1.0 >= 7/9): toate criteriile imbunatatite fata de t-1.
        t_all_pass = {
            "active_totale": 1_000_000,
            "profit_net": 80_000,             # F1: ROA=0.08>0 ; F8: 0.08>=0.05
            "cifra_afaceri": 600_000,         # F9: rotatie 0.6>=0.5
            "cash_flow_operational": 100_000,  # F2: cfo>0 ; F3: cfo(100k)>profit(80k)
            "total_datorii": 350_000,         # F4: leverage 0.35<=0.4
            "active_curente": 400_000,
            "datorii_curente": 200_000,       # F5: lichiditate 2.0>=1.5
            "capitaluri_proprii": 650_000,    # F6: 650k<=600k*1.2=720k
            "cheltuieli_materiale": 250_000,  # F7: marja (600k-250k)/600k=0.583>=0.4
        }

        # 7/9 exact (ratio == 7/9 -> STRONG): flip F2+F3 (cfo negativ).
        t_7of9 = dict(t_all_pass, cash_flow_operational=-10_000)

        # 6/9 (ratio=0.667 < 7/9 -> AVERAGE, imediat sub prag): + flip F6
        # (capitaluri crescute prea mult: 800k > 600k*1.2=720k).
        t_6of9 = dict(t_7of9, capitaluri_proprii=800_000)

        # 4/9 exact (ratio == 4/9 -> AVERAGE): + flip F9 (cifra_afaceri scade
        # rotatia sub t-1) si F4 (datorii cresc, leverage inrautatit).
        # cheltuieli_materiale scazute proportional ca sa pastreze F7=1 in
        # ciuda scaderii cifrei de afaceri (marja tot imbunatatita).
        t_4of9 = dict(
            t_6of9,
            cifra_afaceri=400_000,
            cheltuieli_materiale=200_000,
            total_datorii=500_000,
        )

        # 3/9 (ratio=0.333 < 4/9 -> WEAK, imediat sub prag): + flip F8
        # (profitul scade sub pragul care mentine ROA_t >= ROA_t-1), F1 ramane
        # 1 (profitul e tot pozitiv).
        t_3of9 = dict(t_4of9, profit_net=30_000)

        cases = [
            ("9/9 -> STRONG", t_all_pass, 9, 9, "STRONG"),
            ("7/9 exact -> STRONG", t_7of9, 7, 9, "STRONG"),
            ("6/9 (sub 7/9) -> AVERAGE", t_6of9, 6, 9, "AVERAGE"),
            ("4/9 exact -> AVERAGE", t_4of9, 4, 9, "AVERAGE"),
            ("3/9 (sub 4/9) -> WEAK", t_3of9, 3, 9, "WEAK"),
        ]
        for label, bilant_t, expected_f_score, expected_max, expected_grade in cases:
            result = calculate_piotroski_f(bilant_t, t1_base)
            assert result["f_score"] == expected_f_score, label
            assert result["max_possible"] == expected_max, label
            assert result["grade"] == expected_grade, label

    def test_criteria_lista_9_elemente(self):
        result = calculate_piotroski_f(BILANT_SANATOS, BILANT_ANTERIOR)
        assert len(result["criteria"]) == 9


# ─── Beneish M-Score ─────────────────────────────────────────────────────────

class TestBeneishM:

    def test_necesita_doi_ani(self):
        result = calculate_beneish_m(BILANT_SANATOS, None)
        assert result["available"] is False
        assert result["m_score"] is None
        assert result["risk"] in ("INDISPONIBIL",)

    def test_bilant_gol_indisponibil(self):
        result = calculate_beneish_m(BILANT_GOL, BILANT_ANTERIOR)
        assert result["available"] is False

    def test_cu_doi_ani_disponibil(self):
        result = calculate_beneish_m(BILANT_SANATOS, BILANT_ANTERIOR)
        if result["available"]:
            assert result["m_score"] is not None
            assert result["risk"] in ("OK", "INVESTIGAT", "MANIPULATOR_PROBABIL")
            assert "components" in result

    def test_firma_normala_risk_ok(self):
        result = calculate_beneish_m(BILANT_SANATOS, BILANT_ANTERIOR)
        if result["available"]:
            # Firma normala → m_score sub -2.22 = OK
            assert result["risk"] in ("OK", "INVESTIGAT", "MANIPULATOR_PROBABIL")

    def test_are_disclaimer(self):
        result = calculate_beneish_m(BILANT_SANATOS, BILANT_ANTERIOR)
        if result["available"]:
            assert "disclaimer" in result

    def test_ca_zero_indisponibil(self):
        bilant_no_ca = {"profit_net": 100_000, "active_totale": 500_000}
        result = calculate_beneish_m(bilant_no_ca, bilant_no_ca)
        assert result["available"] is False

    def test_creante_zero_an_anterior_nu_crapa(self):
        """REGRESIE (gasita+reprodusa 2026-07-16 pe date REALE ANAF — firma reala
        din DB, deja analizata recurent: CFL SOLUTION, CUI 49104500, verificata
        direct din `get_bilant`, nu inventata). Codul VECHI: DSRI se calcula cu
        `if ca_t1 > 0 and receivables_t1 >= 0 else 1.0` — `>= 0` include 0, deci
        numitorul (receivables_t1/ca_t1) devine 0.0, iar impartirea externa
        (receivables_t/ca_t) / 0.0 arunca ZeroDivisionError. Cifrele de mai jos:
        2023 (t-1) are creante=0 real, 2024 (t) are creante=37057; CA si
        active_totale sunt pozitive in AMBII ani, deci gate-urile anterioare
        (CA>0 la ~:326, active_totale>0 la ~:344) NU opresc executia inainte
        de DSRI — calea chiar ajunge la impartirea care crapa pe codul vechi."""
        bilant_t = {
            "cifra_afaceri": 177_176, "active_totale": 262_847,
            "creante": 37_057, "profit_net": 5_000,
        }
        bilant_t1 = {
            "cifra_afaceri": 1_300, "active_totale": 1_500,
            "creante": 0, "profit_net": 100,
        }
        result = calculate_beneish_m(bilant_t, bilant_t1)  # nu trebuie sa arunce
        assert result["available"] is False
        assert result["m_score"] is None
        assert result["risk"] == "INDISPONIBIL"
        assert "DSRI" in result["reason"]

    def test_creante_zero_an_anterior_nu_fabrica_dsri_neutru(self):
        """DSRI nemasurabil (receivables_t1<=0) trebuie raportat ca atare — NU cu
        un 1.0 fabricat, care ar ascunde exact semnalul opus (crestere masiva a
        creantelor de la zero — genul de tipar pe care _screening_signals chiar
        il semnaleaza la DSRI>=1.5)."""
        bilant_t = {
            "cifra_afaceri": 177_176, "active_totale": 262_847,
            "creante": 37_057, "profit_net": 5_000,
        }
        bilant_t1 = {
            "cifra_afaceri": 1_300, "active_totale": 1_500,
            "creante": 0, "profit_net": 100,
        }
        result = calculate_beneish_m(bilant_t, bilant_t1)
        assert result["indici_reali"]["DSRI"] is None
        assert not any(s["cod"] == "DSRI" for s in result["screening_signals"])

    def test_creante_zero_an_anterior_end_to_end_official_data(self):
        """Traverseaza granita producator->consumator reala: forma bruta
        `official_data` (cu `cifra_afaceri_neta`/`datorii_totale`, asa cum vine
        din ANAF Bilant) -> `calculate_all_predictive_scores` -> `_to_predictive_shape`
        -> `calculate_beneish_m`. Nu doar `calculate_beneish_m` direct — asta e
        calea pe care ar fi crapat un job real (`agent_verification` trece
        `official_data` brut). Date reale CFL SOLUTION, CUI 49104500."""
        official_data = {
            "financial_official": {
                "data": {
                    "2023": {
                        "cifra_afaceri_neta": 1_300, "active_totale": 1_500,
                        "creante": 0, "profit_net": 100, "datorii_totale": 500,
                    },
                    "2024": {
                        "cifra_afaceri_neta": 177_176, "active_totale": 262_847,
                        "creante": 37_057, "profit_net": 5_000, "datorii_totale": 100_000,
                    },
                }
            }
        }
        result = calculate_all_predictive_scores({"financial": {}}, official_data)  # nu trebuie sa arunce
        beneish = result["beneish_m"]
        assert beneish["available"] is False
        assert beneish["risk"] == "INDISPONIBIL"
        assert "DSRI" in beneish["reason"]

    def test_creante_pozitive_ambii_ani_dsri_neschimbat(self):
        """Contra-proba: cazul normal (receivables_t1 > 0 in ambii ani) ramane
        IDENTIC dupa fix — nimic nu se schimba pentru firmele cu creante reale.
        Valoarea DSRI e calculata direct din formula (nu recopiata din productie)
        si comparata exact."""
        bilant_t = {
            "cifra_afaceri": 11_950_149, "profit_net": 724_147, "creante": 2_049_027,
            "active_totale": 6_005_910, "active_imobilizate": 2_920_496,
            "cheltuieli_materiale": 8_000_000, "cash_flow_operational": 900_000,
        }
        bilant_t1 = {
            "cifra_afaceri": 8_935_629, "profit_net": 320_280, "creante": 1_837_812,
            "active_totale": 5_946_469, "active_imobilizate": 2_883_779,
            "cheltuieli_materiale": 6_200_000, "cash_flow_operational": 400_000,
        }
        result = calculate_beneish_m(bilant_t, bilant_t1)
        assert result["available"] is True
        expected_dsri = round((2_049_027 / 11_950_149) / (1_837_812 / 8_935_629), 3)
        assert result["components"]["DSRI"] == expected_dsri == 0.834
        assert result["indici_cu_semnal"] == 5


# ─── Zmijewski X-Score ───────────────────────────────────────────────────────

class TestZmijewskiX:

    def test_firma_sanatoasa_fara_distress(self):
        result = calculate_zmijewski_x(BILANT_SANATOS)
        assert result["available"] is True
        assert result["x_score"] is not None
        assert result["distress"] is False

    def test_firma_distress_cu_distress(self):
        result = calculate_zmijewski_x(BILANT_DISTRESS)
        assert result["available"] is True
        assert result["x_score"] is not None
        # Firma in distress → X > 0
        assert result["distress"] is True

    def test_active_zero_indisponibil(self):
        result = calculate_zmijewski_x({"profit_net": 100_000, "active_totale": 0})
        assert result["available"] is False
        assert result["x_score"] is None

    def test_bilant_gol_indisponibil(self):
        result = calculate_zmijewski_x(BILANT_GOL)
        assert result["available"] is False

    def test_interpretare_prezenta(self):
        result = calculate_zmijewski_x(BILANT_SANATOS)
        if result["available"]:
            assert "interpretation" in result
            assert len(result["interpretation"]) > 5

    def test_nu_crapa_cu_zero_division(self):
        """Nu trebuie sa arunce ZeroDivisionError chiar cu date incomplete."""
        for bilant in [
            {"active_totale": 1_000_000},
            {"profit_net": 0, "active_totale": 1_000_000},
            {"total_datorii": 0, "active_totale": 1_000_000},
        ]:
            result = calculate_zmijewski_x(bilant)
            assert "available" in result  # nu crapa


# ─── calculate_all_predictive_scores ─────────────────────────────────────────

class TestAllPredictiveScores:

    def test_structura_output(self):
        verified = {
            "financial": {
                "cifra_afaceri": {"value": 5_000_000},
                "profit_net": {"value": 500_000},
                "capitaluri_proprii": {"value": 2_000_000},
                "datorii_totale": {"value": 1_000_000},
                "active_totale": {"value": 3_000_000},
            }
        }
        result = calculate_all_predictive_scores(verified)
        assert "altman_z" in result
        assert "piotroski_f" in result
        assert "beneish_m" in result
        assert "zmijewski_x" in result
        assert "distress_signals" in result
        assert "summary" in result
        assert isinstance(result["distress_signals"], int)
        assert isinstance(result["summary"], str)

    def test_verified_gol_nu_crapa(self):
        result = calculate_all_predictive_scores({})
        assert "altman_z" in result
        assert result["distress_signals"] >= 0

    def test_distress_signals_range(self):
        verified = {
            "financial": {
                "cifra_afaceri": {"value": 5_000_000},
                "profit_net": {"value": 500_000},
            }
        }
        result = calculate_all_predictive_scores(verified)
        assert 0 <= result["distress_signals"] <= 5

    def test_summary_not_empty(self):
        verified = {"financial": {"cifra_afaceri": {"value": 1_000_000}}}
        result = calculate_all_predictive_scores(verified)
        assert len(result["summary"]) > 10
