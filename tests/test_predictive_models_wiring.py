"""
Teste de cablare NON-VACUE pentru modelele predictive de faliment.

De ce exista acest fisier separat de `test_predictive_models.py`:
cele 29 de teste existente paseaza dict-uri de bilant SINTETICE direct in
`calculate_altman_z_ems`/`calculate_piotroski_f`/etc — trec verzi indiferent
daca `verified["financial"]["active_totale"]` e vreodata populat in productie.
Ele NU testeaza granita `official_data -> verified["financial"] ->
calculate_all_predictive_scores`, unde a fost gasit bug-ul (fix 2026-07-15):
`active_totale`/`datorii_totale` erau deja parsate din ANAF Bilant dar nu
ajungeau niciodata in `verified["financial"]`, iar bilantul anului anterior
nu era cablat deloc pentru Piotroski F4-F9 / Beneish M.

Acest fisier porneste de la un `official["financial_official"]["data"]`
FICTIV dar cu forma IDENTICA celei reale (verificata live pe 2 CUI-uri reale
2026-07-15 — identitatea de bilant activ_imobilizate+active_circulante+
cheltuieli_avans = capitaluri+datorii+provizioane+venituri_avans se respecta),
si trece prin calea REALA de productie: `VerificationAgent._verify_financial`
+ `calculate_all_predictive_scores`, nu o reimplementare izolata.

Date 100% fictive — repo public, nu se folosesc cifre de firme reale.
"""
from backend.agents.agent_verification import VerificationAgent
from backend.agents.verification.credit_exposure import commercial_exposure_ron
from backend.agents.verification.predictive_models import calculate_all_predictive_scores

# Bilant fictiv pe 2 ani consecutivi, forma identica cu raspunsul ANAF Bilant
# parsat de anaf_bilant_client.get_bilant (inclusiv active_totale, calculat
# acolo ca active_imobilizate + active_circulante + cheltuieli_avans).
FICTIONAL_OFFICIAL = {
    "anaf": {"found": True, "platitor_tva": True, "inactiv": False, "split_tva": False},
    "financial_official": {
        "cui": "99999999",
        "years_found": [2024, 2023],
        "data": {
            2024: {
                "cui": "99999999", "year": 2024, "found": True,
                "denumire": "FIRMA FICTIVA SRL", "caen_code": "4711",
                "active_imobilizate": 500_000, "active_circulante": 300_000,
                "stocuri": 100_000, "creante": 150_000, "casa_conturi_banci": 50_000,
                "cheltuieli_avans": 10_000, "datorii_totale": 250_000,
                "venituri_avans": 1_000, "provizioane": 5_000,
                "capitaluri_proprii": 554_000, "capital_social": 10_000,
                "cifra_afaceri_neta": 2_000_000, "profit_brut": 150_000,
                "profit_net": 120_000, "numar_mediu_salariati": 25,
                "active_totale": 810_000,  # = 500_000 + 300_000 + 10_000
            },
            2023: {
                "cui": "99999999", "year": 2023, "found": True,
                "denumire": "FIRMA FICTIVA SRL", "caen_code": "4711",
                "active_imobilizate": 400_000, "active_circulante": 250_000,
                "stocuri": 80_000, "creante": 120_000, "casa_conturi_banci": 50_000,
                "cheltuieli_avans": 5_000, "datorii_totale": 200_000,
                "venituri_avans": 0, "provizioane": 0,
                "capitaluri_proprii": 455_000, "capital_social": 10_000,
                "cifra_afaceri_neta": 1_600_000, "profit_brut": 110_000,
                "profit_net": 90_000, "numar_mediu_salariati": 20,
                "active_totale": 655_000,  # = 400_000 + 250_000 + 5_000
            },
        },
        "trend": {},
        "errors": [],
        "source": "ANAF Bilant",
    },
}


class TestVerifiedFinancialWiring:
    """Granita official_data -> verified['financial'] (agent_verification._verify_financial,
    metoda REALA, nu o reimplementare)."""

    def test_active_totale_propagat(self):
        agent = VerificationAgent()
        financial = agent._verify_financial(FICTIONAL_OFFICIAL)
        assert "active_totale" in financial, (
            "active_totale nu a fost propagat in verified['financial'] — "
            "regresie la bug-ul din 2026-07-15"
        )
        assert financial["active_totale"]["value"] == 810_000

    def test_datorii_totale_propagat(self):
        agent = VerificationAgent()
        financial = agent._verify_financial(FICTIONAL_OFFICIAL)
        assert "datorii_totale" in financial
        assert financial["datorii_totale"]["value"] == 250_000

    def test_absent_cand_nu_exista_date_bilant(self):
        """Fara financial_official.data -> campurile raman ABSENTE (nu 0/None
        fals-linistitor) — regula explicita din brief: un camp lipsa e mai
        sigur decat unul calculat gresit."""
        agent = VerificationAgent()
        financial = agent._verify_financial({"anaf": {"found": True}})
        assert "active_totale" not in financial
        assert "datorii_totale" not in financial


class TestPredictiveScoresWiring:
    """Granita verified['financial'] + official_data -> calculate_all_predictive_scores
    (functia REALA, apelata exact cum e apelata in productie de agent_verification.py)."""

    def _verified(self):
        agent = VerificationAgent()
        return {"financial": agent._verify_financial(FICTIONAL_OFFICIAL)}

    def test_altman_indisponibil_cu_motivul_REAL(self):
        """Altman NU e calculabil din ANAF Bilant: are nevoie de capital circulant
        net, deci de split-ul datorii curente/necurente, pe care ANAF nu-l expune
        (verificat la sursa 2026-07-15 pe 4 firma-ani). Contractul cerut aici:
        ramane INDISPONIBIL, dar cu motivul REAL — NU cel generic despre active
        totale (care ACUM exista), si mai ales NU un z_score cu X1 zeroit tacit,
        care ar fi fals cu aparenta de autoritate."""
        result = calculate_all_predictive_scores(self._verified(), FICTIONAL_OFFICIAL)
        altman = result["altman_z"]
        assert altman["zone"] == "INDISPONIBIL"
        assert altman["z_score"] is None, (
            "Altman a intors un z_score desi capitalul circulant net nu e "
            "calculabil — X1 (coeficient 6.56) ar fi zeroit tacit"
        )
        assert "datorii curente" in altman["reason"].lower()
        assert "active totale indisponibile" not in altman["reason"].lower()

    def test_altman_calculabil_cand_exista_split_datorii(self):
        """Contra-proba: daca o sursa viitoare aduce active_curente+datorii_curente,
        Altman devine calculabil — gate-ul e pe DATE lipsa, nu dezactivat permanent."""
        from backend.agents.verification.predictive_models import calculate_altman_z_ems
        bilant = {
            "active_totale": 810_000, "total_datorii": 250_000,
            "capitaluri_proprii": 554_000, "profit_net": 120_000,
            "profit_brut": 150_000, "cifra_afaceri": 2_000_000,
            "active_curente": 300_000, "datorii_curente": 180_000,
        }
        altman = calculate_altman_z_ems(bilant)
        assert altman["zone"] in ("SAFE", "GREY", "DISTRESS")
        assert altman["z_score"] is not None

    def test_zmijewski_disponibil(self):
        """Zmijewski RAMANE disponibil fara split-ul de datorii: singurul termen
        afectat (AC/DC) are coeficientul 0.004, cu 3 ordine de marime sub ceilalti
        doi — nu poate rasturna verdictul. Dar omisiunea e declarata explicit."""
        result = calculate_all_predictive_scores(self._verified(), FICTIONAL_OFFICIAL)
        zmijewski = result["zmijewski_x"]
        assert zmijewski["available"] is True
        assert zmijewski["x_score"] is not None
        assert zmijewski["confidence"] < 1
        assert "lichiditate" in zmijewski["disclaimer"].lower()

    def test_zmijewski_discrimineaza_distres_real(self):
        """Un detector care nu se declanseaza niciodata e inutil — verificam ca
        Zmijewski chiar separa o firma sanatoasa de una in distres real."""
        from backend.agents.verification.predictive_models import calculate_zmijewski_x
        sanatoasa = calculate_zmijewski_x(
            {"active_totale": 6_000_000, "total_datorii": 1_740_000, "profit_net": 724_000}
        )
        distress = calculate_zmijewski_x(
            {"active_totale": 1_900_000, "total_datorii": 2_000_000, "profit_net": -300_000}
        )
        assert sanatoasa["distress"] is False
        assert distress["distress"] is True

    def test_piotroski_nu_acorda_puncte_pt_criterii_nemasurabile(self):
        """F5 (lichiditate curenta) si F7 (marja bruta) nu sunt masurabile din
        ANAF Bilant. Inainte de fix acordau punctul MEREU (0/1 >= 0/1 si
        1.0 >= 1.0) — puncte gratuite intr-un detector de faliment = fals confort.
        Acum trebuie sa fie None, nu 1."""
        result = calculate_all_predictive_scores(self._verified(), FICTIONAL_OFFICIAL)
        criteria = result["piotroski_f"]["criteria"]
        assert criteria[4] is None, "F5 (lichiditate) a acordat punct fara sa masoare nimic"
        assert criteria[6] is None, "F7 (marja bruta) a acordat punct fara sa masoare nimic"

    def test_piotroski_foloseste_anul_anterior(self):
        result = calculate_all_predictive_scores(self._verified(), FICTIONAL_OFFICIAL)
        piotroski = result["piotroski_f"]
        assert piotroski["has_prior_year"] is True, (
            "Piotroski nu a primit bilant_t1 — regresie la bug-ul din 2026-07-15 "
            "(Beneish/Piotroski apelate cu un singur argument)"
        )
        # 7, nu 9: F5+F7 raman nemasurabile din ANAF (vezi testul dedicat).
        # Inainte de fix: 3 (fara an anterior deloc).
        assert piotroski["max_possible"] == 7, (
            f"Asteptat 7 criterii calculabile din ANAF cu 2 ani de date, primit {piotroski['max_possible']}"
        )
        assert piotroski["grade"] != "INSUFICIENT"

    def test_beneish_disponibil_cu_doi_ani(self):
        result = calculate_all_predictive_scores(self._verified(), FICTIONAL_OFFICIAL)
        beneish = result["beneish_m"]
        assert beneish["available"] is True, (
            "Beneish tot INDISPONIBIL — bilant_t1 nu a fost cablat"
        )
        assert beneish["m_score"] is not None

    def test_beneish_nu_explodeaza_fara_active_totale(self):
        """REGRESIE (gasit LIVE 2026-07-15, CUI 6719278): cu `active_totale` lipsa,
        Beneish facea TA = `... or 1` -> TATA = (profit-cfo)/1 = 1.2e7, coeficient
        7.770 -> M-score 97.001.528 -> "MANIPULATOR_PROBABIL" pe un retailer sanatos.
        O acuzatie FALSA de manipulare contabila, cu aparenta de autoritate — exact
        modul de esec pe care fix-ul asta trebuia sa-l elimine, nu sa-l creeze.
        Mod inaccesibil inainte (Beneish era mereu INDISPONIBIL fara an anterior),
        deschis chiar de cablarea lui bilant_t1."""
        from backend.agents.verification.predictive_models import calculate_beneish_m
        an_t = {"cifra_afaceri": 12_256_333_315, "profit_net": 124_841_094, "creante": 149_279_737}
        an_t1 = {"cifra_afaceri": 10_584_116_263, "profit_net": 116_976_590, "creante": 114_955_229}
        result = calculate_beneish_m(an_t, an_t1)
        assert result["available"] is False
        assert result["m_score"] is None
        assert result["risk"] == "INDISPONIBIL"
        assert "active totale" in result["reason"].lower()

    def test_beneish_plauzibil_cu_active_totale(self):
        """Contra-proba: cu active totale reale, M-score sta in intervalul
        rezonabil al modelului (uzual -4..0 pt firme normale), nu 1e8."""
        from backend.agents.verification.predictive_models import calculate_beneish_m
        an_t = {
            "cifra_afaceri": 11_950_149, "profit_net": 724_147, "creante": 2_049_027,
            "active_totale": 6_005_910, "active_imobilizate": 2_920_496,
        }
        an_t1 = {
            "cifra_afaceri": 8_935_629, "profit_net": 320_280, "creante": 1_837_812,
            "active_totale": 5_946_469, "active_imobilizate": 2_883_779,
        }
        result = calculate_beneish_m(an_t, an_t1)
        assert result["available"] is True
        assert -8 < result["m_score"] < 2, f"M-score implauzibil: {result['m_score']}"

    def test_summary_nu_mai_linisteste_fals_cand_nimic_calculat(self):
        """Cazul cel mai periculos: 0 modele calculate NU mai produce
        'Indicatori financiari in zona normala' (mesaj fals-linistitor)."""
        result = calculate_all_predictive_scores({"financial": {}}, None)
        assert result["models_available"] == 0
        assert result["summary"] != "Indicatori financiari in zona normala"
        assert "nu a putut fi calculat" in result["summary"].lower() or "nu a fost evaluat" in result["summary"].lower()

    def test_summary_mentioneaza_cate_modele_partial(self):
        """Cand doar UNELE modele ruleaza (Altman+Zmijewski au active_totale
        dar Piotroski/Beneish nu au bilant_t1 -> raman INSUFICIENT/INDISPONIBIL),
        summary spune explicit cate din cele 4 s-au calculat."""
        verified = {
            "financial": {
                "cifra_afaceri": {"value": 1_000_000},
                "profit_net": {"value": 50_000},
                "capitaluri_proprii": {"value": 400_000},
                "active_totale": {"value": 800_000},
            }
        }
        result = calculate_all_predictive_scores(verified, None)
        assert 0 < result["models_available"] < result["models_total"]
        assert str(result["models_available"]) in result["summary"]
        assert str(result["models_total"]) in result["summary"]


class TestCreditExposureKillSwitch:
    """Cascada P1-4: kill-switch-ul de expunere comerciala se baza EXCLUSIV pe
    `altman.zone == "DISTRESS"`, iar Altman e structural necalculabil din ANAF
    (lipsa split datorii curente) -> kill-switch-ul nu se putea declansa NICIODATA,
    deci RIS putea recomanda expunere in RON pentru o firma in dificultate reala.
    Cuplat acum SI la Zmijewski, care e calculabil din ANAF."""

    def _verified_with(self, predictive: dict, color: str = "Verde") -> dict:
        return {
            "financial": {
                "cifra_afaceri": {"value": 12_000_000},
                "profit_net": {"value": 700_000},
                "capitaluri_proprii": {"value": 4_000_000},
            },
            "risk": {},
            "risk_score": {"score": color},
            "predictive_scores": predictive,
        }

    def test_kill_switch_se_declanseaza_pe_zmijewski_distress(self):
        verified = self._verified_with(
            {
                "altman_z": {"zone": "INDISPONIBIL", "z_score": None},
                "zmijewski_x": {"available": True, "distress": True, "x_score": 2.35},
            }
        )
        result = commercial_exposure_ron(verified)
        assert result["kill_switch"] is True
        assert result["expunere_ron"] == 0
        assert "Zmijewski" in result["formula"]

    def test_fara_kill_switch_pe_firma_sanatoasa(self):
        verified = self._verified_with(
            {
                "altman_z": {"zone": "INDISPONIBIL", "z_score": None},
                "zmijewski_x": {"available": True, "distress": False, "x_score": -3.24},
            }
        )
        result = commercial_exposure_ron(verified)
        assert result["kill_switch"] is False
        assert result["expunere_ron"] > 0

    def test_zmijewski_indisponibil_nu_declanseaza_kill_switch(self):
        """`distress: None` + `available: False` nu trebuie citit ca distres."""
        verified = self._verified_with(
            {
                "altman_z": {"zone": "INDISPONIBIL", "z_score": None},
                "zmijewski_x": {"available": False, "distress": None, "x_score": None},
            }
        )
        result = commercial_exposure_ron(verified)
        assert result["kill_switch"] is False

    def test_altman_distress_ramane_cablat(self):
        """Altman ramane un declansator valid pt cand o sursa viitoare aduce
        split-ul de datorii — nu l-am inlocuit, l-am completat."""
        verified = self._verified_with(
            {
                "altman_z": {"zone": "DISTRESS", "z_score": 0.4},
                "zmijewski_x": {"available": True, "distress": False, "x_score": -3.0},
            }
        )
        result = commercial_exposure_ron(verified)
        assert result["kill_switch"] is True
        assert "Altman DISTRESS" in result["formula"]
