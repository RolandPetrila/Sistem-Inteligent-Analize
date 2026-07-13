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
        data = {"market": {"seap": {"value": {"total_contracts": 3}}}}
        model = build_rich_fields_model(data)
        assert model["seap"]["shown"] is True
        assert model["seap"]["data"]["total_contracts"] == 3

    def test_actionariat_shown_from_relations_flags_alone(self):
        data = {"relations": {"flags": [{"type": "ONE_PERSON", "detail": "x", "severity": "INFO"}]}}
        model = build_rich_fields_model(data)
        assert model["actionariat"]["shown"] is True
        assert model["actionariat"]["act_ok"] is False
