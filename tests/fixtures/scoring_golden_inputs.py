"""
Fixture-uri de intrare pentru golden snapshot test-ul lui `calculate_risk_score`
(Pas 0, PLAN_REFACTOR_SCORING_2026-07-13.md).

Date SINTETICE (nu date reale de firme terte) — construite sa respecte EXACT
formatul de output al `agent_verification.py` (_make_field, _verify_risk,
_verify_financial etc.), dar cu valori inventate. Repo-ul e public pe GitHub;
publicarea datelor financiare reale ale unor firme terte (chiar din surse
publice ANAF) nu se face fara verificare explicita — vezi CLAUDE.md.

FIXED_REF_DATE: data de referinta FIXATA folosita la generarea + verificarea
golden snapshot-urilor (patch pe `date.today()` in scoring.py). Fara ea,
`company_age_years` ar driftui la fiecare rulare independent de orice
schimbare de cod, stricand comparatia byte-cu-byte a snapshot-ului.
"""
from datetime import date

FIXED_REF_DATE = date(2026, 7, 13)


FIXTURES: dict[str, dict] = {
    # --- 1. Firma sanatoasa, toate sursele disponibile (happy path complet) ---
    "healthy_complete": {
        "company": {
            "cui": {"value": "11111111", "trust": "OFICIAL", "source": "ANAF"},
            "denumire": {"value": "Exemplu Solutii SRL", "trust": "OFICIAL", "source": "ANAF"},
            "stare_inregistrare": {"value": "ACTIVA", "trust": "OFICIAL", "source": "ANAF"},
            "stare_firma": {"value": "ACTIVA", "trust": "OFICIAL", "source": "ANAF"},
            "data_inregistrare": {"value": "2015-03-10", "trust": "OFICIAL", "source": "ANAF"},
            "platitor_tva": {"value": True, "trust": "OFICIAL", "source": "ANAF"},
            "caen_code": {"value": "6201", "trust": "OFICIAL", "source": "ONRC"},
            "caen_description": {"value": "Activitati de realizare a soft-ului la comanda", "trust": "OFICIAL", "source": "ONRC"},
        },
        "financial": {
            "cifra_afaceri": {"value": 12_000_000},
            "profit_net": {"value": 1_500_000},
            "capitaluri_proprii": {"value": 4_000_000},
            "numar_angajati": {"value": 60},
            "platitor_tva": {"value": True},
            "trend_financiar": {
                "value": {
                    "cifra_afaceri_neta": {
                        "growth_percent": 22,
                        "values": [
                            {"year": "2022", "value": 9_000_000},
                            {"year": "2023", "value": 10_500_000},
                            {"year": "2024", "value": 12_000_000},
                        ],
                    },
                    "profit_net": {"growth_percent": 15},
                    "numar_mediu_salariati": {"growth_percent": 10},
                }
            },
        },
        "risk": {
            "insolvency": {"value": {"found": False}},
            "litigation": {"value": {"found": False, "count": 0}},
            "anaf_inactive": {"value": False},
        },
        "web_presence": {
            "site_oficial": {"value": {"url": "https://exemplu-solutii.example"}},
            "linkedin": {"value": {"followers": 500}},
            "google_business": {"value": {"rating": 4.5}},
        },
        "maps_rating": {"found": True, "rating": 4.6, "reviews_count": 120},
        "market": {
            "seap": {"value": {"total_contracts": 3}},
        },
        "benchmark": {
            "available": True,
            "comparisons": [
                {"metric": "Cifra de afaceri", "ratio": 2.4},
                {"metric": "Angajati", "ratio": 1.8},
            ],
        },
        "caen_code": "6201",
    },

    # --- 2. Date sparse/partiale — multe surse absente (cazul TIPIC real, nu MINIM) ---
    "sparse_partial": {
        "company": {
            "cui": {"value": "22222222", "trust": "OFICIAL", "source": "ANAF"},
            "denumire": {"value": "Firma Partiala SRL", "trust": "OFICIAL", "source": "ANAF"},
            "stare_firma": {"value": "ACTIVA", "trust": "OFICIAL", "source": "ANAF"},
            "caen_code": {"value": "4711", "trust": "OFICIAL", "source": "ANAF"},
            # fara data_inregistrare -> company_age_years ramane None
        },
        "financial": {
            "cifra_afaceri": {"value": 350_000},
            # fara profit_net, fara capitaluri_proprii, fara trend_financiar
        },
        "risk": {
            "anaf_inactive": {"value": False},
            # fara insolvency, litigation, bpi_insolventa, dosare_just, aegrm, risc_fiscal
        },
        # fara web_presence, market, benchmark, maps_rating
        "caen_code": "4711",
    },

    # --- 3. Complet gol (deja partial acoperit de test_empty_verified_data,
    #        dar golden snapshot captureaza intreg contractul, nu doar 2 chei) ---
    "empty": {},

    # --- 4. Adversarial "everything triggers" — zombie + insolventa + BPI +
    #        Portal Just SOAP (dosare_just>10, ramura care a produs bug-ul
    #        litigation, reachable acum dupa fix-ul Portal Just) + AEGRM +
    #        Monitorul Oficial + ANAF inactiv + split TVA + risc fiscal ---
    "adversarial_everything_triggers": {
        "company": {
            "cui": {"value": "33333333", "trust": "OFICIAL", "source": "ANAF"},
            "denumire": {"value": "Firma Risc Maxim SRL", "trust": "OFICIAL", "source": "ANAF"},
            "stare_firma": {"value": "ACTIVA", "trust": "OFICIAL", "source": "ANAF"},
            "data_inregistrare": {"value": "2010-01-01", "trust": "OFICIAL", "source": "ANAF"},
            "caen_code": {"value": "4120", "trust": "OFICIAL", "source": "ANAF"},
        },
        "financial": {
            "cifra_afaceri": {"value": 0},
            "profit_net": {"value": -50_000},
            "capitaluri_proprii": {"value": -20_000},
            "numar_angajati": {"value": 0},
            "platitor_tva": {"value": False},
            "split_tva": {"value": True},
        },
        "risk": {
            "insolvency": {"value": {"found": True}},
            "bpi_insolventa": {"value": {"found": True, "status": "in insolventa"}},
            # Portal Just SOAP — date reale de dosare (ramura bug-ului litigation)
            "dosare_just": {"value": {"total": 15, "reclamant": 5, "parat": 10, "dosare": []}},
            "aegrm_guarantees": {"value": {"has_guarantees": True, "count": 3}},
            "monitorul_oficial": {"value": [{"type": "dizolvare", "label": "Dizolvare", "snippet": "Dizolvare in curs"}]},
            "anaf_inactive": {"value": True},
            "risc_fiscal": {"value": {"risc_fiscal": True, "tip_risc": "risc ridicat nedeclarare"}},
        },
        "caen_code": "4120",
    },

    # --- 5. Trend/volatilitate multi-an — exercita decompozitia (base growth +
    #        volatilitate CV + detectie anomalie) si baseline-ul sectorial (CAEN F) ---
    "trend_volatility_multi_year": {
        "company": {
            "cui": {"value": "44444444", "trust": "OFICIAL", "source": "ANAF"},
            "denumire": {"value": "Constructii Volatile SRL", "trust": "OFICIAL", "source": "ANAF"},
            "stare_firma": {"value": "ACTIVA", "trust": "OFICIAL", "source": "ANAF"},
            "data_inregistrare": {"value": "2019-06-01", "trust": "OFICIAL", "source": "ANAF"},
            "caen_code": {"value": "4120", "trust": "OFICIAL", "source": "ANAF"},
        },
        "financial": {
            "cifra_afaceri": {"value": 4_000_000},
            "profit_net": {"value": 80_000},
            "capitaluri_proprii": {"value": 500_000},
            "numar_angajati": {"value": 25},
            "trend_financiar": {
                "value": {
                    "cifra_afaceri_neta": {
                        "growth_percent": 12,
                        "values": [
                            {"year": "2021", "value": 1_000_000},
                            {"year": "2022", "value": 1_100_000},
                            {"year": "2023", "value": 1_150_000},
                            {"year": "2024", "value": 4_000_000},
                        ],
                    },
                    "profit_net": {"growth_percent": -35},
                    "numar_mediu_salariati": {"growth_percent": 5},
                }
            },
        },
        "risk": {
            "anaf_inactive": {"value": False},
        },
        "caen_code": "4120",
    },

    # --- 6. Disponibilitate MIXTA a surselor (unele prezente, altele absente) —
    #        exercita cuplarea ascunsa din bucla de confidence: fiecare
    #        dimensiune citeste conditional variabile din blocul ei ---
    "mixed_confidence_coupling": {
        "company": {
            "cui": {"value": "55555555", "trust": "OFICIAL", "source": "ANAF"},
            "denumire": {"value": "Firma Mixta SRL", "trust": "OFICIAL", "source": "ANAF"},
            "stare_firma": {"value": "ACTIVA", "trust": "OFICIAL", "source": "ANAF"},
            "caen_code": {"value": "6311", "trust": "OFICIAL", "source": "ANAF"},
            # fara data_inregistrare -> company_age_years absent (dar angajati_val prezent)
        },
        "financial": {
            "cifra_afaceri": {"value": 800_000},
            "profit_net": {"value": 40_000},
            "numar_angajati": {"value": 12},
            # fara capitaluri_proprii, fara trend_financiar -> financiar confidence = 2/4
        },
        "risk": {
            # insolvency PREZENTA (found False) dar litigation ABSENTA -> confidence
            # juridic = 0.5 (exact-una-din-doua), distinct de "empty"/"sparse" (ambele absente -> 0.2)
            "insolvency": {"value": {"found": False}},
            # fara anaf_inactive -> confidence fiscal = 0.3
        },
        "web_presence": {
            # exact 1 categorie -> "Prezenta online limitata", distinct de healthy (3) si sparse (0)
            "site_oficial": {"value": {"url": "https://firma-mixta.example"}},
        },
        "market": {
            # prezent, truthy, dar FARA cheia "seap" -> "Date de piata disponibile"
            # fara bonusul de contracte SEAP (distinct de healthy_complete care are seap)
            "alt_indicator": {"value": "prezent"},
        },
        "caen_code": "6311",
    },

    # --- 7-14: adaugate la refactorul _score_financiar (2026-07-16, PLAN
    #     REFACTOR — sub-task scoring.py). Cele 6 fixture-uri de mai sus
    #     lasau NEACOPERITE ~57 statement-uri din interiorul lui
    #     _score_financiar (verificat cu coverage.py, nu presupus) —
    #     ramurile de mai jos completeaza acoperirea INAINTE de orice
    #     extragere de cod, ca sa nu se refactorizeze orbeste peste cod
    #     nevazut de niciun test.

    # --- 7. Crestere CA exceptionala (>50%) + forma REALA de productie a
    #        caen_code: verified["caen_code"] absent (ca in productie —
    #        agent_verification.py NU seteaza niciodata cheia top-level),
    #        deci fallback la company["caen_code"] dict-wrapped cu litera
    #        de sectiune ("J...") — exercita unwrap-ul dict + ramura alpha,
    #        niciuna atinsa de fixture-urile 1-6 (care foloseau artificial
    #        un string simplu la nivel top-level, forma NEREALA fata de
    #        productie).
    "trend_growth_exceptional_dict_caen": {
        "company": {
            "cui": {"value": "66666666", "trust": "OFICIAL", "source": "ANAF"},
            "denumire": {"value": "Crestere Exceptionala SRL", "trust": "OFICIAL", "source": "ANAF"},
            "stare_firma": {"value": "ACTIVA", "trust": "OFICIAL", "source": "ANAF"},
            "caen_code": {"value": "J6201", "trust": "OFICIAL", "source": "ONRC"},
        },
        "financial": {
            "cifra_afaceri": {"value": 2_000_000},
            "profit_net": {"value": 100_000},
            "trend_financiar": {
                "value": {
                    "cifra_afaceri_neta": {
                        "growth_percent": 65,
                        # valori 3 ani, crestere blanda — doar ca sa intre in
                        # blocul de decompozitie (>=3 valori) si sa ajunga la
                        # rezolvarea sectiunii CAEN; NU declanseaza anomalie
                        # sau trend structural (verificat numeric).
                        "values": [
                            {"year": "2022", "value": 1_800_000},
                            {"year": "2023", "value": 1_900_000},
                            {"year": "2024", "value": 2_000_000},
                        ],
                    },
                }
            },
        },
        "risk": {"anaf_inactive": {"value": False}},
        # NOTA: fara cheia "caen_code" la nivel top-level — forma REALA de
        # productie (verified.get("caen_code","") e mereu falsy acolo).
    },

    # --- 8. Scadere CA CRITICA (<-30%) + trend structural negativ multi-an
    #        (regresie liniara pe 4 ani, panta negativa) + sectiune CAEN
    #        numerica "F" (Constructii, coduri 41-43) — nicio ramura atinsa
    #        de fixture-urile 1-6.
    "trend_decline_critical_structural": {
        "company": {
            "cui": {"value": "77777777", "trust": "OFICIAL", "source": "ANAF"},
            "denumire": {"value": "Constructii In Declin SRL", "trust": "OFICIAL", "source": "ANAF"},
            "stare_firma": {"value": "ACTIVA", "trust": "OFICIAL", "source": "ANAF"},
            "caen_code": {"value": "4120", "trust": "OFICIAL", "source": "ANAF"},
        },
        "financial": {
            "cifra_afaceri": {"value": 5_500_000},
            "profit_net": {"value": 50_000},
            "capitaluri_proprii": {"value": 800_000},
            "trend_financiar": {
                "value": {
                    "cifra_afaceri_neta": {
                        "growth_percent": -35,
                        "values": [
                            {"year": "2021", "value": 10_000_000},
                            {"year": "2022", "value": 8_500_000},
                            {"year": "2023", "value": 7_000_000},
                            {"year": "2024", "value": 5_500_000},
                        ],
                    },
                }
            },
        },
        "risk": {"anaf_inactive": {"value": False}},
        "caen_code": "41",  # sectiune numerica F (41-43), NU codul CAEN complet 4120
    },

    # --- 9. Scadere CA MODERATA (-10% < growth < -30%, adica intre -30 si
    #        -10) — ramura distincta de #8 (critica) si de #10 (minora) —
    #        + sectiune CAEN numerica "C" (Manufacturing, 10-33).
    "trend_decline_moderate": {
        "company": {
            "cui": {"value": "88888888", "trust": "OFICIAL", "source": "ANAF"},
            "denumire": {"value": "Manufactura Moderata SRL", "trust": "OFICIAL", "source": "ANAF"},
            "stare_firma": {"value": "ACTIVA", "trust": "OFICIAL", "source": "ANAF"},
            "caen_code": {"value": "2059", "trust": "OFICIAL", "source": "ANAF"},
        },
        "financial": {
            "cifra_afaceri": {"value": 900_000},
            "trend_financiar": {
                "value": {
                    "cifra_afaceri_neta": {"growth_percent": -15},
                }
            },
        },
        "risk": {"anaf_inactive": {"value": False}},
        "caen_code": "20",  # sectiune numerica C (10-33)
    },

    # --- 10. Scadere CA MINORA (-10% < growth < 0%) — ultima ramura din
    #        lantul de scadere, + sectiune CAEN numerica "N" (77-82).
    "trend_decline_minor": {
        "company": {
            "cui": {"value": "99999999", "trust": "OFICIAL", "source": "ANAF"},
            "denumire": {"value": "Servicii Usor In Scadere SRL", "trust": "OFICIAL", "source": "ANAF"},
            "stare_firma": {"value": "ACTIVA", "trust": "OFICIAL", "source": "ANAF"},
            "caen_code": {"value": "7739", "trust": "OFICIAL", "source": "ANAF"},
        },
        "financial": {
            "cifra_afaceri": {"value": 400_000},
            "trend_financiar": {
                "value": {
                    "cifra_afaceri_neta": {"growth_percent": -3},
                }
            },
        },
        "risk": {"anaf_inactive": {"value": False}},
        "caen_code": "80",  # sectiune numerica N (77-82)
    },

    # --- 11. Anomalie CA (deviatie >2 std fata de trendul liniar pe un an
    #        singular, an 2023 cu spike x8) + volatilitate CA RIDICATA vs
    #        sector (ratio CV/baseline > 2.0, distinct de "moderata" deja
    #        acoperita de fixture-ul 5) — + sectiune CAEN numerica "J" (IT,
    #        58-63), baseline volatilitate cea mai mica (0.25), amplifica
    #        ratio-ul. Valorile au fost verificate numeric (nu ghicite)
    #        inainte de a fi introduse in fixture, cu acelasi algoritm ca
    #        in scoring.py (regresie liniara + std dev).
    "trend_anomaly_and_high_volatility": {
        "company": {
            "cui": {"value": "10101010", "trust": "OFICIAL", "source": "ANAF"},
            "denumire": {"value": "IT Cu Spike Anormal SRL", "trust": "OFICIAL", "source": "ANAF"},
            "stare_firma": {"value": "ACTIVA", "trust": "OFICIAL", "source": "ANAF"},
            "caen_code": {"value": "6201", "trust": "OFICIAL", "source": "ANAF"},
        },
        "financial": {
            "cifra_afaceri": {"value": 1_150_000},
            "profit_net": {"value": 60_000},
            "trend_financiar": {
                "value": {
                    "cifra_afaceri_neta": {
                        "growth_percent": 5,
                        "values": [
                            {"year": "2019", "value": 1_000_000},
                            {"year": "2020", "value": 1_020_000},
                            {"year": "2021", "value": 1_050_000},
                            {"year": "2022", "value": 8_000_000},
                            {"year": "2023", "value": 1_100_000},
                            {"year": "2024", "value": 1_150_000},
                        ],
                    },
                }
            },
        },
        "risk": {"anaf_inactive": {"value": False}},
        "caen_code": "62",  # sectiune numerica J (58-63)
    },

    # --- 12. Capitaluri proprii NEGATIVE (ca_val>0) + cash-flow stress
    #        (marja negativa <-10% SI capital negativ) — ramuri neatinse
    #        de fixture-ul adversarial (acolo ca_val=0, deci garda
    #        `ca_val>0` a blocurilor de solvabilitate nu se activeaza
    #        deloc). Combinatia Pierdere+Subcapitalizat -> risk_level=1
    #        din matricea de solvabilitate (risc HIGH in factors).
    "solvency_negative_capital_cashflow_stress": {
        "company": {
            "cui": {"value": "11223344", "trust": "OFICIAL", "source": "ANAF"},
            "denumire": {"value": "Capital Negativ SRL", "trust": "OFICIAL", "source": "ANAF"},
            "stare_firma": {"value": "ACTIVA", "trust": "OFICIAL", "source": "ANAF"},
            "caen_code": {"value": "4632", "trust": "OFICIAL", "source": "ANAF"},
        },
        "financial": {
            "cifra_afaceri": {"value": 5_000_000},
            "profit_net": {"value": -800_000},
            "capitaluri_proprii": {"value": -300_000},
        },
        "risk": {"anaf_inactive": {"value": False}},
        "caen_code": "4632",
    },

    # --- 13. Capital pozitiv dar sub 5% din CA (subcapitalizare cu capital
    #        POZITIV — ramura distincta de #12, unde capitalul e negativ) +
    #        marja profit sub 1% la CA > 1M (ramura cash-flow separata,
    #        elif mutual-exclusiv fata de stress-ul din #12).
    "solvency_thin_positive_capital": {
        "company": {
            "cui": {"value": "22334455", "trust": "OFICIAL", "source": "ANAF"},
            "denumire": {"value": "Capital Subtire SRL", "trust": "OFICIAL", "source": "ANAF"},
            "stare_firma": {"value": "ACTIVA", "trust": "OFICIAL", "source": "ANAF"},
            "caen_code": {"value": "4941", "trust": "OFICIAL", "source": "ANAF"},
        },
        "financial": {
            "cifra_afaceri": {"value": 10_000_000},
            "profit_net": {"value": -100_000},
            "capitaluri_proprii": {"value": 200_000},
        },
        "risk": {"anaf_inactive": {"value": False}},
        "caen_code": "4941",
    },

    # --- 14. Matrice solvabilitate zona (Pierdere, Solid) -> risk_level=3
    #        (RISC MEDIU-RIDICAT) — singura combinatie cu risk_level exact 3
    #        din harta 3x3; distincta de risk_level<=2 (fixture #12/#13).
    "solvency_pierdere_solid_risk3": {
        "company": {
            "cui": {"value": "33445566", "trust": "OFICIAL", "source": "ANAF"},
            "denumire": {"value": "Capital Solid Pierdere Mica SRL", "trust": "OFICIAL", "source": "ANAF"},
            "stare_firma": {"value": "ACTIVA", "trust": "OFICIAL", "source": "ANAF"},
            "caen_code": {"value": "6820", "trust": "OFICIAL", "source": "ANAF"},
        },
        "financial": {
            "cifra_afaceri": {"value": 5_000_000},
            "profit_net": {"value": -50_000},
            "capitaluri_proprii": {"value": 2_000_000},
        },
        "risk": {"anaf_inactive": {"value": False}},
        "caen_code": "6820",
    },
}
