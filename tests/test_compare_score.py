"""
Test de regresie: bug real gasit prin audit — `_calculate_compare_score`
(backend/routers/compare.py) citea `result.get("total_score", 70)`, dar
`calculate_risk_score()` (backend/agents/verification/scoring.py) nu
returneaza NICIODATA cheia "total_score" (returneaza "numeric_score").
Efect: Comparatorul afisa scor 70 fix pentru ORICE firma, dintotdeauna.

Acest test verifica cu date sintetice (structura reala, valori inventate —
repo public, zero date reale de firme terte) ca scorul:
  1. NU e mereu 70 (fallback-ul mort)
  2. difera intre o firma sanatoasa si una cu risc ridicat

Rulat pe codul dinaintea fix-ului (git stash), acest test PICA: ambele firme
primesc 70 (fallback declansat de KeyError implicit din .get() -> default).

FIX 2026-07-16: al doilea bug de granita, gasit in ACELASI `_calculate_compare_score` —
scria `verified["financial"]["numar_mediu_salariati"]`, dar consumatorul canonic
`_score_operational` (scoring.py) citeste `financial["numar_angajati"]`. Efect: dimensiunea
operationala (15% din scor) era oarba la angajati pentru ORICE firma comparata — vezi
`TestCompareScoreAngajatiiContract` mai jos. `numar_mediu_salariati` din testul de echivalenta
de mai jos (linia cu "numar_angajati" acum) a fost aliniat la acelasi fix — inainte,
testul isi construia manual acelasi `verified` cu ACEEASI cheie gresita ca si codul,
deci cele doua se confirmau reciproc fara sa prinda bug-ul (clasa de bug documentata in
CLAUDE.md: fixture-urile codifica aceeasi presupunere gresita ca si codul).
"""
from backend.agents.verification.scoring import risk_bucket
from backend.routers.compare import _calculate_compare_score


def _healthy_company() -> dict:
    return {
        "cifra_afaceri": 15_000_000,
        "profit_net": 1_800_000,
        "profit_brut": 2_000_000,
        "capitaluri": 6_000_000,
        "angajati": 45,
        "inactiv": False,
        "platitor_tva": True,
        "data_inregistrare": "2005-03-10",
        "stare": "ACTIVA",
    }


def _risky_company() -> dict:
    return {
        "cifra_afaceri": 40_000,
        "profit_net": -120_000,
        "profit_brut": -110_000,
        "capitaluri": -50_000,
        "angajati": 1,
        "inactiv": True,
        "platitor_tva": False,
        "data_inregistrare": "2025-01-05",
        "stare": "ACTIVA",
    }


class TestCalculateCompareScore:
    def test_scor_nu_e_mereu_70_fallback(self):
        healthy_score = _calculate_compare_score(_healthy_company())
        risky_score = _calculate_compare_score(_risky_company())

        assert healthy_score != 70, "scorul firmei sanatoase a picat pe fallback-ul mort (70)"
        assert risky_score != 70, "scorul firmei cu risc a picat pe fallback-ul mort (70)"

    def test_scor_difera_intre_firme_diferite(self):
        healthy_score = _calculate_compare_score(_healthy_company())
        risky_score = _calculate_compare_score(_risky_company())

        assert healthy_score != risky_score
        assert healthy_score > risky_score, (
            f"firma sanatoasa ({healthy_score}) ar trebui sa aiba scor mai mare "
            f"decat firma cu risc ridicat ({risky_score})"
        )

    def test_scor_coincide_cu_numeric_score_din_calculate_risk_score(self):
        """Legatura directa fix -> sursa: scorul returnat trebuie sa fie EXACT
        `numeric_score` din calculate_risk_score(), nu un camp inexistent.

        FIX 2026-07-16: `verified` de mai jos trebuie sa foloseasca EXACT contractul
        canonic citit de `_score_fiscal` (scoring.py:341,347: risk.anaf_inactive +
        financial.platitor_tva) — inainte, acest test isi construia propriul `verified`
        cu ACELEASI chei gresite ca si codul vechi din compare.py (risk.inactiv +
        risk.platitor_tva), deci nu ar fi prins niciodata bug-ul de rutare fiscala
        (pentru firma sanatoasa de mai jos, ambele rutari — corecta si gresita —
        produc coincidental acelasi scor, pentru ca nicio penalizare nu se declanseaza
        in niciun caz). Vezi TestCompareScoreFiscalContract mai jos pentru testul care
        chiar diferentiaza cele doua rutari."""
        from backend.agents.verification.scoring import calculate_risk_score

        company = _healthy_company()
        verified = {
            "financial": {
                "cifra_afaceri": {"value": company["cifra_afaceri"]},
                "profit_net": {"value": company["profit_net"]},
                "profit_brut": {"value": company["profit_brut"]},
                "capitaluri_proprii": {"value": company["capitaluri"]},
                "numar_angajati": {"value": company["angajati"]},
                "platitor_tva": {"value": company["platitor_tva"]},
            },
            "risk": {
                "anaf_inactive": {"value": company["inactiv"]},
            },
            "company": {
                "data_inregistrare": {"value": company["data_inregistrare"]},
                "stare_inregistrare": {"value": company["stare"]},
            },
        }
        expected = calculate_risk_score(verified)["numeric_score"]
        actual = _calculate_compare_score(company)
        assert actual == expected


class TestCompareScoreAngajatiiContract:
    """FIX 2026-07-16: `_calculate_compare_score` scria cheia `numar_mediu_salariati`
    in `verified["financial"]`, dar `_score_operational` (scoring.py) citeste
    `numar_angajati`. Efect: dimensiunea operationala (15% din scor) era mereu
    oarba la angajati pe calea Comparatorului — bonusul "forta de munca
    semnificativa" nu se aplica NICIODATA, indiferent de firma.

    Datele de mai jos au fost alese prin RULARE reala (nu calcul mental) astfel
    incat bug-ul sa produca un flip de culoare vizibil pentru utilizator:
    Galben (69.7, <70) pe codul vechi vs Verde (72.8, >=70) cu cheia corecta.
    """

    @staticmethod
    def _company_pe_granita_verde() -> dict:
        return {
            "cifra_afaceri": 8_000_000,
            "profit_net": 100_000,
            "profit_brut": 150_000,
            "capitaluri": 2_000_000,
            "angajati": 9_000,
            "inactiv": False,
            "platitor_tva": True,
            "data_inregistrare": "2015-05-10",
            "stare": "ACTIVA",
        }

    def test_angajatii_trec_pragul_de_culoare_verde(self):
        """PICA pe codul vechi (`numar_mediu_salariati`): scorul ramane 69.7 /
        Galben, pentru ca bonusul de angajati nu ajunge niciodata la scoring.
        Cu cheia corecta (`numar_angajati`), bonusul se aplica si scorul trece
        la 72.8 / Verde — exact flip-ul vizibil in Comparator."""
        company = self._company_pe_granita_verde()
        score = _calculate_compare_score(company)

        assert score >= 70, (
            f"scor {score} sub pragul Verde — dimensiunea operationala nu vede "
            f"angajatii (cheia scrisa de compare.py nu coincide cu cea citita "
            f"de _score_operational din scoring.py)"
        )
        assert risk_bucket(score) == "Verde", (
            f"culoare {risk_bucket(score)} in loc de Verde — bug-ul de cheie "
            f"'numar_mediu_salariati' vs 'numar_angajati' schimba culoarea "
            f"afisata utilizatorului in Comparator"
        )


class TestCompareScoreFiscalContract:
    """FIX 2026-07-16: al treilea bug de granita in ACELASI `_calculate_compare_score` —
    scria `verified["risk"]["inactiv"]` si `verified["risk"]["platitor_tva"]`, dar
    consumatorul canonic `_score_fiscal` (scoring.py:341,347) citeste
    `risk_data.get("anaf_inactive")` / `financial.get("platitor_tva")` (acelasi
    contract folosit de calea reala Agent 4, vezi agent_verification.py:555-556 + 685).
    Efect: dimensiunea FISCALA (15% din scor) era oarba — nicio firma comparata nu primea
    NICIODATA penalizarea "Firma inactiva la ANAF" (-50) sau "Neplatitor TVA" (-10).

    PICA pe codul vechi (verificat prin `git stash` pe compare.py — vezi raport pentru
    output-ul real): ambele teste de penalizare de mai jos esueaza, pentru ca firma
    inactiva/neplatitoare primeste ACELASI scor ca varianta activa/platitoare —
    penalizarea nu ajunge niciodata la scoring.

    IMPORTANT (gasit prin verificare la sursa, contrazice presupunerea initiala a
    task-ului): scorul unei firme CURATE (activa + platitoare) NU ramane neschimbat
    dupa fix — creste. Motivul e `_compute_confidence` (scoring.py:1036): confidence-ul
    dimensiunii fiscale e 1.0 doar daca `anaf_inactive` e prezent (indiferent de
    valoare), altfel 0.3. Codul vechi nu popula NICIODATA acea cheie -> orice firma
    comparata rula fiscal la confidence 0.3 fix, ceea ce tragea scorul ei real (90 raw)
    spre neutru (50) prin power-law weighting. Fix-ul reface confidence-ul la 1.0
    pentru toate firmele, deci creste scorul si celor curate — nu doar penalizeaza pe
    cele cu probleme. Controlul de mai jos verifica ce chiar ramane neschimbat: scorul
    RAW al dimensiunii fiscale (90 in ambele cazuri — nicio penalizare fantoma), nu
    scorul total ponderat.
    """

    def test_firma_inactiva_la_anaf_e_penalizata(self):
        inactive_co = {**_healthy_company(), "inactiv": True}
        active_co = _healthy_company()
        score_inactive = _calculate_compare_score(inactive_co)
        score_active = _calculate_compare_score(active_co)
        assert score_inactive < score_active, (
            f"firma inactiva la ANAF ({score_inactive}) nu e penalizata fata de "
            f"varianta activa ({score_active}) — dimensiunea fiscala nu vede cheia "
            f"'inactiv'/'anaf_inactive'"
        )

    def test_neplatitor_tva_e_penalizat(self):
        neplatitor_co = {**_healthy_company(), "platitor_tva": False}
        platitor_co = _healthy_company()
        score_neplatitor = _calculate_compare_score(neplatitor_co)
        score_platitor = _calculate_compare_score(platitor_co)
        assert score_neplatitor < score_platitor, (
            f"firma neplatitoare TVA ({score_neplatitor}) nu e penalizata fata de "
            f"varianta platitoare ({score_platitor}) — dimensiunea fiscala nu vede "
            f"cheia 'platitor_tva'"
        )

    def test_control_firma_activa_platitoare_raw_score_neschimbat(self):
        """CONTROL: firma activa + platitoare TVA (nimic de penalizat) trebuie sa
        primeasca acelasi scor RAW (nepnalizat) pe dimensiunea fiscala indiferent daca
        'inactiv'/'platitor_tva' sunt rutate in pozitiile noi corecte sau in pozitiile
        vechi gresite — dovedeste ca fix-ul nu inventeaza o penalizare fantoma pt
        firme curate. Scorul TOTAL ponderat difera totusi intre cele doua rutari
        (vezi docstring clasa) — asta e o consecinta corecta a confidence-ului, nu o
        penalizare, deci NU e ce verifica acest control."""
        from backend.agents.verification.scoring import calculate_risk_score

        company = _healthy_company()

        def _field(val):
            return {"value": val} if val is not None else {}

        base_financial = {
            "cifra_afaceri": _field(company["cifra_afaceri"]),
            "profit_net": _field(company["profit_net"]),
            "profit_brut": _field(company["profit_brut"]),
            "capitaluri_proprii": _field(company["capitaluri"]),
            "numar_angajati": _field(company["angajati"]),
        }
        base_company_info = {
            "data_inregistrare": {"value": company["data_inregistrare"]},
            "stare_inregistrare": {"value": company["stare"]},
        }

        verified_new_keys = {
            "financial": {**base_financial, "platitor_tva": {"value": company["platitor_tva"]}},
            "risk": {"anaf_inactive": {"value": company["inactiv"]}},
            "company": base_company_info,
        }
        verified_old_keys = {
            "financial": dict(base_financial),
            "risk": {
                "inactiv": {"value": company["inactiv"]},
                "platitor_tva": {"value": company["platitor_tva"]},
            },
            "company": base_company_info,
        }

        result_new = calculate_risk_score(verified_new_keys)
        result_old = calculate_risk_score(verified_old_keys)

        # Invariantele pe care ACEST fix le garanteaza (nu constante interne din
        # scoring.py, editat in paralel de alt agent — cuplarea la valori exacte
        # (90/0.3/1.0) ar rupe testul la orice tuning acolo, fara legatura cu
        # compare.py):
        raw_new = result_new["dimensions"]["fiscal"]["raw_score"]
        raw_old = result_old["dimensions"]["fiscal"]["raw_score"]
        assert raw_new == raw_old, (
            f"scorul RAW fiscal difera intre rutari ({raw_old} -> {raw_new}) — ar "
            f"insemna ca fix-ul a inventat o penalizare/bonus pt o firma curata, nu "
            f"doar a corectat unde se citeste cheia"
        )

        # Confirma CAUZA reala a miscarii scorului total: confidence-ul fiscal
        # creste strict cand cheia e prezenta (indiferent de valoarea ei) fata de
        # cand lipsea complet — nu o penalizare noua.
        conf_new = result_new["confidence"]["fiscal"]
        conf_old = result_old["confidence"]["fiscal"]
        assert conf_new > conf_old, (
            f"confidence fiscal nu creste ({conf_old} -> {conf_new}) desi cheia "
            f"'anaf_inactive' e acum prezenta — fix-ul nu isi atinge scopul"
        )

        actual = _calculate_compare_score(company)
        assert actual == result_new["numeric_score"], (
            "codul fixat (_calculate_compare_score) nu produce scorul asteptat pt "
            "firma curata"
        )


class TestCompareScoreFirmaNegasitaAnaf:
    """EXTINDERE 2026-07-16 (cerere Opus, dupa verificare la sursa): fix-ul initial din
    TestCompareScoreFiscalContract folosea `{"value": company.get(cheie, False)}}` —
    corect pt firma GASITA in ANAF, dar pt o firma NEGASITA (compare_companies.py:68-76,
    ramura `else`: seteaza DOAR `cui`+`denumire`, deloc `platitor_tva`/`inactiv`), acel
    default `False` afirma cu confidence 1.0 ceva ce sistemul nu stie deloc — o
    MINCIUNA NOUA de exact clasa documentata in CLAUDE.md (".get(cheie, default)
    MASCHEAZA absenta — nu poti distinge API-ul n-a trimis campul de entitatea n-are
    date"). Fix real: `_field(company.get(cheie))` fara default -> `None` -> `{}` ->
    fara penalizare + confidence 0.3 (onest), pastrand comportamentul EXACT neschimbat
    pt firma gasita (True/False sunt "not None", deci `_field` le trece neschimbate).
    """

    @staticmethod
    def _company_negasita_anaf() -> dict:
        """Forma REALA produsa de ramura `else` din compare_companies (linia 76):
        NU seteaza 'platitor_tva'/'inactiv'/'stare'/'data_inregistrare' — doar cui+
        denumire. Bilant-ul e independent de gasirea in ANAF, deci pastram si datele
        financiare (posibile chiar si cand firma nu e gasita la ANAF TVA)."""
        return {
            "cui": "12345678",
            "denumire": "CUI 12345678 - negasit ANAF",
            "cifra_afaceri": 15_000_000,
            "profit_net": 1_800_000,
            "profit_brut": 2_000_000,
            "capitaluri": 6_000_000,
            "angajati": 45,
        }

    def test_firma_negasita_nu_e_tratata_identic_cu_confirmat_neplatitoare(self):
        """Non-vacuitate: pe versiunea BUGGY (`{"value": company.get(cheie, False)}}`,
        inainte de aceasta extindere), o firma NEGASITA (fara cheile 'platitor_tva'/
        'inactiv') primea EXACT ACELASI tratament ca o firma GASITA si CONFIRMATA
        neplatitoare+activa (platitor_tva=False, inactiv=False explicit) — pentru ca
        `.get(cheie, False)` nu poate distinge "lipsa" de "False real". Dupa fix
        (`_field` fara default), cele doua trebuie sa PRODUCA SCORURI DIFERITE:
        firma negasita nu primeste penalizarea -10 'Neplatitor TVA' (nu stim asta),
        dar nici confidence-ul complet al unei firme verificate.

        Compar exact aceleasi campuri financiare/varsta intre cele doua fixture-uri
        (doar prezenta/absenta 'platitor_tva'/'inactiv' difera) ca sa izolez strict
        efectul acestei extinderi, fara sa amestec diferente de alte dimensiuni."""
        negasita = self._company_negasita_anaf()
        gasita_confirmat_neplatitoare = {
            **self._company_negasita_anaf(),
            "platitor_tva": False,
            "inactiv": False,
        }

        score_negasit = _calculate_compare_score(negasita)
        score_gasit_confirmat = _calculate_compare_score(gasita_confirmat_neplatitoare)

        assert score_negasit != score_gasit_confirmat, (
            f"firma negasita ({score_negasit}) primeste EXACT acelasi scor ca o firma "
            f"GASITA si CONFIRMATA neplatitoare TVA ({score_gasit_confirmat}) — codul "
            f"trateaza 'nu stim' identic cu 'confirmat neplatitor', minciuna pe care "
            f"aceasta extindere trebuia sa o elimine"
        )

    def test_firma_negasita_are_confidence_fiscal_scazuta_nu_maxima(self):
        """Documenteaza MECANISMUL din spatele testului anterior (nu e o proba de
        non-vacuitate separata — acest test isi construieste propriul `verified` cu
        aceeasi logica `_field` corecta, deci trece indiferent de starea reala a
        lui compare.py; non-vacuitatea reala pt aceasta extindere e demonstrata de
        `test_firma_negasita_nu_e_tratata_identic_cu_confirmat_neplatitoare` de mai
        sus, care CHIAR apeleaza `_calculate_compare_score` si PICA pe codul vechi).

        Cu constructia corecta (`_field` fara default), o firma negasita la ANAF
        trebuie sa aiba confidence fiscal SCAZUTA (cheia 'anaf_inactive' lipseste
        real -> {} -> 0.3), nu 1.0 — spre deosebire de varianta buggy
        (`{"value": company.get(cheie, False)}}`), unde cheia era mereu prezenta
        (chiar cu valoarea implicita gresita False), deci confidence ar fi fost
        artificial 1.0 pt o firma pe care sistemul n-a verificat-o deloc."""
        from backend.agents.verification.scoring import calculate_risk_score

        company = self._company_negasita_anaf()

        def _field(val):
            return {"value": val} if val is not None else {}

        verified = {
            "financial": {
                "cifra_afaceri": _field(company.get("cifra_afaceri")),
                "profit_net": _field(company.get("profit_net")),
                "profit_brut": _field(company.get("profit_brut")),
                "capitaluri_proprii": _field(company.get("capitaluri")),
                "numar_angajati": _field(company.get("angajati")),
                "platitor_tva": _field(company.get("platitor_tva")),
            },
            "risk": {"anaf_inactive": _field(company.get("inactiv"))},
            "company": {
                "data_inregistrare": _field(company.get("data_inregistrare")),
                "stare_inregistrare": _field(company.get("stare")),
            },
        }
        result = calculate_risk_score(verified)
        conf_fiscal = result["confidence"]["fiscal"]

        assert conf_fiscal < 0.5, (
            f"confidence fiscal ({conf_fiscal}) e prea mare pt o firma NEGASITA la "
            f"ANAF — sistemul nu ar trebui sa afirme cu incredere mare ceva ce nu "
            f"stie despre statusul ei TVA/activitate"
        )
