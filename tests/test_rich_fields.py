"""DRY #3 (2026-07-14): tests for build_rich_fields_model, the shared normalization
consumed by html_generator / pdf_generator / docx_generator. Locks the normalized
field preference (label-over-type, snippet-over-detail) -- the exact fix from
2026-06-27, previously triplicated independently in 3 files, now normalized once."""

from backend.reports.rich_fields import build_rich_fields_model


class TestHistoricalFlagsNormalization:
    def test_prefers_label_over_type_and_title_and_category(self):
        data = {"historical_flags": [{
            "type": "cesiune_parti_sociale",
            "title": "should not win",
            "category": "should not win",
            "label": "Cesiune parti sociale detectata",
            "severity": "HIGH",
            "snippet": "cesiune 60% parti sociale",
        }]}
        flx = build_rich_fields_model(data)["garantii"]["historical_flags"][0]
        assert flx["label"] == "Cesiune parti sociale detectata"
        assert flx["is_dict"] is True

    def test_prefers_snippet_over_detail_description_text(self):
        data = {"historical_flags": [{
            "type": "x",
            "snippet": "snippet wins",
            "detail": "should not win",
            "description": "should not win",
            "text": "should not win",
        }]}
        flx = build_rich_fields_model(data)["garantii"]["historical_flags"][0]
        assert flx["detail"] == "snippet wins"

    def test_label_falls_back_to_category_then_semnal(self):
        flx1 = build_rich_fields_model({"historical_flags": [{"category": "categ value"}]})["garantii"]["historical_flags"][0]
        assert flx1["label"] == "categ value"

        flx2 = build_rich_fields_model({"historical_flags": [{}]})["garantii"]["historical_flags"][0]
        assert flx2["label"] == "Semnal"

    def test_detail_falls_back_to_text_then_empty(self):
        flx1 = build_rich_fields_model({"historical_flags": [{"text": "text value"}]})["garantii"]["historical_flags"][0]
        assert flx1["detail"] == "text value"

        flx2 = build_rich_fields_model({"historical_flags": [{}]})["garantii"]["historical_flags"][0]
        assert flx2["detail"] == ""

    def test_real_osint_shape_type_label_severity_snippet(self):
        """Exact shape emitted by osint_client.search_monitorul_oficial:
        {type(slug), label(human), severity, snippet} -- no detail/description/text/category."""
        data = {"historical_flags": [{
            "type": "cesiune_parti_sociale",
            "label": "Cesiune parti sociale detectata",
            "severity": "HIGH",
            "snippet": "cesiune 60% parti sociale catre o terta persoana",
        }]}
        flx = build_rich_fields_model(data)["garantii"]["historical_flags"][0]
        assert flx["label"] == "Cesiune parti sociale detectata"
        assert flx["detail"] == "cesiune 60% parti sociale catre o terta persoana"
        assert flx["severity"] == "HIGH"

    def test_non_dict_item_preserved_as_is(self):
        flx = build_rich_fields_model({"historical_flags": ["raw string signal"]})["garantii"]["historical_flags"][0]
        assert flx["is_dict"] is False
        assert flx["detail"] == "raw string signal"


class TestAegrmGuaranteesNormalization:
    """Bug real: aegrm_client.check_aegrm_guarantees() pune lista itemizata
    sub cheia "details" -- NICIODATA "guarantees"/"results", care e ce
    citeau (direct, fara trecere prin model) html/pdf/docx_generator. Lista
    detaliata era mereu goala in toate 3 formatele. Date sintetice (structura
    reala a payload-ului AEGRM, valori inventate -- repo public)."""

    def _aegrm_field(self, details):
        return {
            "risk": {
                "aegrm_guarantees": {
                    "value": {
                        "has_data": True,
                        "has_guarantees": True,
                        "count": len(details),
                        "details": details,
                        "source": "AEGRM",
                    }
                }
            }
        }

    def test_details_key_normalizata_in_guarantees(self):
        details = [{
            "nr_inregistrare": "2024-000123",
            "data": "2024-03-11",
            "creditor": "BANCA EXEMPLU SA",
            "tip_bun": "Echipamente industriale",
            "status": "ACTIV",
        }]
        model = build_rich_fields_model(self._aegrm_field(details))
        guarantees = model["garantii"]["guarantees"]
        assert len(guarantees) == 1
        assert guarantees[0]["creditor"] == "BANCA EXEMPLU SA"
        assert guarantees[0]["tip_bun"] == "Echipamente industriale"
        assert guarantees[0]["status"] == "ACTIV"
        assert guarantees[0]["data"] == "2024-03-11"

    def test_guarantees_results_keys_ignorate_deliberat(self):
        """Cheile vechi cautate de bug ("guarantees"/"results") nu exista
        NICIODATA pe raspunsul real -- modelul trebuie sa produca lista din
        "details", nu sa ramana gol pentru ca acele chei lipsesc."""
        aegrm_data = self._aegrm_field([{"creditor": "X", "tip_bun": "Y", "status": "Z", "data": "2025-01-01"}])
        # confirma ca payload-ul real NU are "guarantees"/"results"
        raw = aegrm_data["risk"]["aegrm_guarantees"]["value"]
        assert "guarantees" not in raw
        assert "results" not in raw

        model = build_rich_fields_model(aegrm_data)
        assert len(model["garantii"]["guarantees"]) == 1

    def test_fara_details_lista_goala(self):
        model = build_rich_fields_model(self._aegrm_field([]))
        assert model["garantii"]["guarantees"] == []

    def test_no_aegrm_data_guarantees_lista_goala(self):
        model = build_rich_fields_model({})
        assert model["garantii"]["guarantees"] == []


class TestGateBooleans:
    def test_empty_verified_data_all_hidden(self):
        model = build_rich_fields_model({})
        for key in model:
            assert model[key]["shown"] is False

    def test_aegrm_only_shows_garantii_without_historical(self):
        data = {"risk": {"aegrm_guarantees": {"value": {"has_data": True, "count": 1}}}}
        model = build_rich_fields_model(data)
        assert model["garantii"]["shown"] is True
        assert model["garantii"]["aegrm_ok"] is True
        assert model["garantii"]["hist_ok"] is False

    def test_seap_unwraps_make_field_value(self):
        data = {"market": {"seap": {"value": {"contracts_verified": True, "total_contracts": 3}}}}
        model = build_rich_fields_model(data)
        assert model["seap"]["shown"] is True
        assert model["seap"]["data"]["total_contracts"] == 3

    def test_actionariat_shown_from_relations_flags_alone(self):
        data = {"relations": {"flags": [{"type": "ONE_PERSON", "detail": "x", "severity": "INFO"}]}}
        model = build_rich_fields_model(data)
        assert model["actionariat"]["shown"] is True
        assert model["actionariat"]["act_ok"] is False

    def test_credit_exposure_hidden_when_absent(self):
        model = build_rich_fields_model({})
        assert model["credit_exposure"]["shown"] is False

    def test_credit_exposure_shown_when_computed(self):
        data = {"credit_exposure": {"expunere_ron": 5000, "metode_folosite": 1, "formula": "x", "kill_switch": False, "disclaimer": "y"}}
        model = build_rich_fields_model(data)
        assert model["credit_exposure"]["shown"] is True
        assert model["credit_exposure"]["data"]["expunere_ron"] == 5000


class TestWebIntelligenceNormalization:
    """verified["web_intelligence"] (agent_verification.py:274-275, propagated
    verbatim from official["web_intelligence"]) is Brave Search + Jina enrichment
    run on EVERY analysis (real quota spent), but was rendered NOWHERE (grep in
    backend/reports/ = 0 hits) before this fix. Shape confirmed in
    data/ris.db reports.full_data: {"categories": {cat: [{"title","url","sentiment"}]}}
    -- plain dict, NOT wrapped in {"value": ...}. Real data observed 2 identical
    entries (same title+url) in one category -- must dedup."""

    def test_dedup_by_url(self):
        data = {"web_intelligence": {"categories": {"stiri": [
            {"title": "Stire A", "url": "http://example.ro/a", "sentiment": "neutral"},
            {"title": "Stire A", "url": "http://example.ro/a", "sentiment": "neutral"},
        ]}}}
        model = build_rich_fields_model(data)
        assert model["web_intelligence"]["shown"] is True
        cats = model["web_intelligence"]["categories"]
        assert len(cats) == 1
        assert len(cats[0]["items"]) == 1

    def test_dedup_falls_back_to_title_when_url_missing(self):
        data = {"web_intelligence": {"categories": {"stiri": [
            {"title": "Aceeasi stire", "url": "", "sentiment": "neutral"},
            {"title": "Aceeasi stire", "url": "", "sentiment": "neutral"},
        ]}}}
        model = build_rich_fields_model(data)
        assert len(model["web_intelligence"]["categories"][0]["items"]) == 1

    def test_empty_categories_omitted(self):
        data = {"web_intelligence": {"categories": {
            "stiri": [], "recenzii": [], "oficial": [], "juridic": [],
            "financiar": [{"title": "X", "url": "http://x.ro", "sentiment": "positive"}],
        }}}
        model = build_rich_fields_model(data)
        cats = model["web_intelligence"]["categories"]
        assert len(cats) == 1
        assert cats[0]["key"] == "financiar"

    def test_all_categories_empty_hides_section(self):
        data = {"web_intelligence": {"categories": {"stiri": [], "recenzii": []}}}
        model = build_rich_fields_model(data)
        assert model["web_intelligence"]["shown"] is False
        assert model["web_intelligence"]["categories"] == []

    def test_absent_hides_section(self):
        model = build_rich_fields_model({})
        assert model["web_intelligence"]["shown"] is False

    def test_known_category_labels_mapped_to_romanian(self):
        data = {"web_intelligence": {"categories": {
            "stiri": [{"title": "X", "url": "http://x.ro", "sentiment": "neutral"}],
            "recenzii": [{"title": "Y", "url": "http://y.ro", "sentiment": "positive"}],
            "oficial": [{"title": "Z", "url": "http://z.ro", "sentiment": "neutral"}],
            "juridic": [{"title": "W", "url": "http://w.ro", "sentiment": "negative"}],
            "financiar": [{"title": "V", "url": "http://v.ro", "sentiment": "positive"}],
        }}}
        model = build_rich_fields_model(data)
        labels = {c["key"]: c["label"] for c in model["web_intelligence"]["categories"]}
        assert labels == {
            "stiri": "Stiri", "recenzii": "Recenzii", "oficial": "Surse Oficiale",
            "juridic": "Juridic", "financiar": "Financiar",
        }

    def test_sentiment_lowercased_and_defaults_to_neutral(self):
        data = {"web_intelligence": {"categories": {"stiri": [
            {"title": "X", "url": "http://x.ro", "sentiment": "POSITIVE"},
            {"title": "Y", "url": "http://y.ro"},
        ]}}}
        model = build_rich_fields_model(data)
        items = model["web_intelligence"]["categories"][0]["items"]
        assert items[0]["sentiment"] == "positive"
        assert items[1]["sentiment"] == "neutral"

    def test_non_dict_items_skipped(self):
        data = {"web_intelligence": {"categories": {"stiri": ["raw string", None,
            {"title": "Valid", "url": "http://ok.ro", "sentiment": "neutral"}]}}}
        model = build_rich_fields_model(data)
        items = model["web_intelligence"]["categories"][0]["items"]
        assert len(items) == 1
        assert items[0]["title"] == "Valid"


class TestTavilyQuotaExhausted:
    """A6 (2026-07-16): official_data["tavily_quota_exhausted"] (agent_official.py,
    _check_tavily_quota) gateaza cautarea legala (litigii) SI semnalele OSINT
    istorice -- pana la acest fix, NIMIC nu citea flagul, deci un raport generat
    cu cota epuizata arata IDENTIC cu o firma curata (absenta dovezii randata ca
    dovada a absentei). Propagat in agent_verification.py, randat onest aici."""

    def test_shown_and_message_when_flag_true(self):
        data = {"tavily_quota_exhausted": {"value": True, "usage": 823}}
        model = build_rich_fields_model(data)
        assert model["tavily_quota_exhausted"]["shown"] is True
        msg = model["tavily_quota_exhausted"]["message"]
        assert "NU a fost efectuata" in msg
        assert "823/1000 interogari" in msg

    def test_hidden_when_absent(self):
        model = build_rich_fields_model({})
        assert model["tavily_quota_exhausted"]["shown"] is False
        assert model["tavily_quota_exhausted"]["message"] == ""

    def test_hidden_when_value_false(self):
        data = {"tavily_quota_exhausted": {"value": False}}
        model = build_rich_fields_model(data)
        assert model["tavily_quota_exhausted"]["shown"] is False

    def test_message_without_usage_says_unknown(self):
        data = {"tavily_quota_exhausted": {"value": True, "usage": None}}
        model = build_rich_fields_model(data)
        assert "uzaj necunoscut" in model["tavily_quota_exhausted"]["message"]


class TestPredictiveDivergence:
    """A4 (2026-07-16): compara FAPTIC scorul 6D (verified['risk_score']) cu
    semnalul fiecarui model predictiv DISPONIBIL. Randeaza doar FAPTUL
    dezacordului, niciodata un verdict nou -- scoring.py ramane neatins.
    Caz real verificat in data/ris.db (TAROM, CUI 477647): scor 74.5/Verde,
    Zmijewski -0.85 = fara semnal de distres -- NU diverge (ambele "ok")."""

    def _pred(self, **overrides):
        base = {
            "altman_z": {"z_score": None, "zone": "INDISPONIBIL"},
            "piotroski_f": {"f_score": 4, "max_possible": 5, "grade": "STRONG"},
            "beneish_m": {"m_score": None, "risk": "INDISPONIBIL", "available": False},
            "zmijewski_x": {"x_score": -0.85, "distress": False, "available": True},
            "distress_signals": 0,
            "summary": "Indicatori financiari in zona normala",
        }
        base.update(overrides)
        return base

    def test_real_tarom_case_no_divergence(self):
        """Scor 74.5/Verde, Zmijewski fara distres -- ambele "healthy", NU diverge."""
        data = {"risk_score": {"score": "Verde", "numeric_score": 74.5}, "predictive_scores": self._pred()}
        model = build_rich_fields_model(data)
        assert model["predictive_scores"]["divergences"] == []

    def test_verde_vs_zmijewski_distress_diverges(self):
        """Fixture SINTETIC (nu real): scor 6D Verde dar Zmijewski semnaleaza distres."""
        pred = self._pred(zmijewski_x={"x_score": 2.4, "distress": True, "available": True})
        data = {"risk_score": {"score": "Verde", "numeric_score": 78.0}, "predictive_scores": pred}
        model = build_rich_fields_model(data)
        divergences = model["predictive_scores"]["divergences"]
        assert len(divergences) == 1
        assert divergences[0]["model"] == "Zmijewski X"
        text = divergences[0]["text"]
        assert "Scor 6D: Verde (78.0)" in text
        assert "semnal de distres" in text
        assert "Cele doua metode nu concorda" in text
        # NU un verdict nou -- scorul 6D original ramane neschimbat in output.
        assert data["risk_score"]["score"] == "Verde"

    def test_verde_vs_piotroski_weak_diverges(self):
        pred = self._pred(piotroski_f={"f_score": 1, "max_possible": 5, "grade": "WEAK"})
        data = {"risk_score": {"score": "Verde", "numeric_score": 74.5}, "predictive_scores": pred}
        model = build_rich_fields_model(data)
        divergences = model["predictive_scores"]["divergences"]
        assert any(d["model"] == "Piotroski F" for d in divergences)

    def test_indisponibil_altman_never_diverges(self):
        """Altman INDISPONIBIL (zone-ul real cel mai frecvent, confirmat in DB) nu
        poate diverge -- exclus din comparatie, nu tratat ca 'de acord'."""
        data = {"risk_score": {"score": "Verde", "numeric_score": 74.5}, "predictive_scores": self._pred()}
        model = build_rich_fields_model(data)
        assert all(d["model"] != "Altman Z''" for d in model["predictive_scores"]["divergences"])

    def test_galben_bucket_never_compared(self):
        """Zona ambigua (Galben) nu se compara cu niciun model -- ar fi zgomot."""
        pred = self._pred(zmijewski_x={"x_score": 2.4, "distress": True, "available": True})
        data = {"risk_score": {"score": "Galben", "numeric_score": 55.0}, "predictive_scores": pred}
        model = build_rich_fields_model(data)
        assert model["predictive_scores"]["divergences"] == []

    def test_no_predictive_scores_no_divergence(self):
        data = {"risk_score": {"score": "Rosu", "numeric_score": 20.0}}
        model = build_rich_fields_model(data)
        assert model["predictive_scores"]["divergences"] == []

    def test_missing_risk_score_no_divergence(self):
        data = {"predictive_scores": self._pred(zmijewski_x={"x_score": 2.4, "distress": True, "available": True})}
        model = build_rich_fields_model(data)
        assert model["predictive_scores"]["divergences"] == []

    def test_beneish_ok_agrees_with_verde_no_divergence(self):
        pred = self._pred(beneish_m={"m_score": -3.0, "risk": "OK", "available": True})
        data = {"risk_score": {"score": "Verde", "numeric_score": 80.0}, "predictive_scores": pred}
        model = build_rich_fields_model(data)
        assert all(d["model"] != "Beneish M" for d in model["predictive_scores"]["divergences"])

    def test_beneish_manipulator_diverges_from_verde(self):
        pred = self._pred(beneish_m={"m_score": -1.0, "risk": "MANIPULATOR_PROBABIL", "available": True})
        data = {"risk_score": {"score": "Verde", "numeric_score": 80.0}, "predictive_scores": pred}
        model = build_rich_fields_model(data)
        divergences = model["predictive_scores"]["divergences"]
        assert any(d["model"] == "Beneish M" for d in divergences)


class TestMapsRatingKeyTakeawaysSectorPosition:
    """2026-07-16 ("RIS colecteaza > afiseaza", etajul 3): 3 campuri calculate corect
    dar randate in 0/8 formate inainte de acest fix (grep in backend/reports/ = 0
    potriviri pt fiecare). Fixture-urile de mai jos folosesc formele REALE gasite in
    data/ris.db (job 85ec7fff, TAROM CUI 477647) -- valorile sunt cele reale (repo
    public)."""

    def test_maps_rating_shown_when_found(self):
        data = {"maps_rating": {
            "found": True, "name": "TAROM", "rating": 3.3, "reviews_count": 767,
            "place_id": "ChIJP-J_np8cskAR6IF5_IXDPgU",
            "address": "Calea Bucurestilor 224F, 075100 Otopeni", "source": "google_maps",
        }}
        model = build_rich_fields_model(data)
        assert model["maps_rating"]["shown"] is True
        assert model["maps_rating"]["data"]["rating"] == 3.3

    def test_maps_rating_hidden_when_not_found(self):
        """Real shape observed in data/ris.db: {"found": False, "error": "no_results",
        "source": "google_maps"} -- must be treated as legitimate absence, not shown
        as "0 stele"."""
        data = {"maps_rating": {"found": False, "error": "no_results", "source": "google_maps"}}
        model = build_rich_fields_model(data)
        assert model["maps_rating"]["shown"] is False

    def test_maps_rating_hidden_when_absent(self):
        model = build_rich_fields_model({})
        assert model["maps_rating"]["shown"] is False

    def test_key_takeaways_normalized_from_real_tarom_string(self):
        """Real shape observed in data/ris.db: a single string, bullets separated by
        "\\n", each prefixed "• "."""
        kt = (
            "• Cu o cifra de afaceri de 1,226,498,739 RON, TAROM prezinta o baza "
            "financiara solida pentru parteneriat.\n"
            "• Capitalurile proprii negative de -105,192,156 RON indica un risc de "
            "insolventa tehnica ce necesita monitorizare.\n"
            "• Avand 709 dosare judecatoresti, decidentii ar trebui sa evalueze "
            "suplimentar riscurile juridice asociate parteneriatului cu TAROM."
        )
        model = build_rich_fields_model({"key_takeaways": kt})
        assert model["key_takeaways"]["shown"] is True
        items = model["key_takeaways"]["items"]
        assert len(items) == 3
        assert items[0].startswith("Cu o cifra de afaceri")
        assert "•" not in items[0]

    def test_key_takeaways_none_hides_section(self):
        """Real shape observed: 11/78 reports have key_takeaways=None."""
        model = build_rich_fields_model({"key_takeaways": None})
        assert model["key_takeaways"]["shown"] is False
        assert model["key_takeaways"]["items"] == []

    def test_key_takeaways_absent_hides_section(self):
        model = build_rich_fields_model({})
        assert model["key_takeaways"]["shown"] is False

    def test_sector_position_shown_with_real_bucket_shape(self):
        """Real shape observed in data/ris.db (28/78 reports): dict keyed by metric
        name, each a CATEGORICAL bucket ("P90+".."sub P25"), NOT a numeric percentile."""
        data = {"risk_score": {"sector_position": {
            "Cifra de afaceri": {"ratio_vs_avg": 0.37, "estimated_percentile": "sub P25"},
            "Numar angajati": {"ratio_vs_avg": 0.12, "estimated_percentile": "sub P25"},
        }}}
        model = build_rich_fields_model(data)
        assert model["sector_position"]["shown"] is True
        assert model["sector_position"]["data"]["Cifra de afaceri"]["estimated_percentile"] == "sub P25"

    def test_sector_position_hidden_when_empty_dict(self):
        """Real shape: benchmark unavailable -> risk_score["sector_position"] == {}
        (confirmed in job 85ec7fff itself, benchmark.available=False)."""
        data = {"risk_score": {"sector_position": {}}}
        model = build_rich_fields_model(data)
        assert model["sector_position"]["shown"] is False

    def test_sector_position_hidden_when_absent(self):
        model = build_rich_fields_model({})
        assert model["sector_position"]["shown"] is False


class TestRnpmManualGuarantees:
    """CERINTA #4 (2026-07-26): AEGRM auto-fetch e structural mort -> partea de garantii
    reale mobiliare lipsea tacit din orice raport. Modelul expune NECONDITIONAT
    garantii.rnpm_url + rnpm_manual (portalul RNPM viu la co.rnpm.ro, verificat manual)
    -- indiferent de datele firmei, pentru ca auto-verificarea e indisponibila structural.
    Non-vacuitate: pe HEAD dict-ul garantii nu avea aceste chei -> KeyError la acces."""

    def test_rnpm_fields_present_on_empty_verified(self):
        g = build_rich_fields_model({})["garantii"]
        assert g["rnpm_url"] == "https://co.rnpm.ro"
        assert "co.rnpm.ro" in g["rnpm_url"]
        assert "verificare automata indisponibila" in g["rnpm_manual"]

    def test_rnpm_fields_present_even_when_aegrm_and_hist_populated(self):
        # santinela: pe calea populata (aegrm has_data + historical_flags) cheile
        # RNPM raman prezente alaturi de datele reale.
        data = {
            "risk": {"aegrm_guarantees": {"value": {"has_data": True, "count": 2}}},
            "historical_flags": [{"type": "radiere", "snippet": "x"}],
        }
        g = build_rich_fields_model(data)["garantii"]
        assert g["shown"] is True
        assert g["aegrm_ok"] is True
        assert g["rnpm_url"] == "https://co.rnpm.ro"

    def test_rnpm_manual_is_ascii_safe_for_pdf_latin1(self):
        # Mesajul trebuie sa treaca nealterat pe calea PDF latin-1 (fara diacritice
        # ne-latin1 ca s/t cu virgula, care ar deveni "?").
        msg = build_rich_fields_model({})["garantii"]["rnpm_manual"]
        msg.encode("latin-1")  # nu arunca => sigur pe calea _sanitize
        assert "0 garantii" not in msg.lower()
        assert "curat" not in msg.lower()
