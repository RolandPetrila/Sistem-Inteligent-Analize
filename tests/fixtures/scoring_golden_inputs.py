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
}
