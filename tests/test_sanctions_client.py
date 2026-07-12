"""Teste sanctions_client — normalizare, parsere OFAC/EU/UN, screening + anti-fals-pozitiv."""

import pytest

import backend.agents.tools.sanctions_client as sc


@pytest.fixture(autouse=True)
def _reset_index():
    """Reseteaza indexul global intre teste (evita contaminare)."""
    saved = sc._index, sc._records_tok, sc._meta
    yield
    sc._index, sc._records_tok, sc._meta = saved
    sc._index = None


# ---- Normalizare + chei ----
class TestKey:
    def test_strips_diacritics_and_suffix(self):
        # SRL eliminat, diacritice stripate
        assert sc._key("Qoussaï SRL") == sc._key("Qoussai")

    def test_multi_token_order_independent(self):
        assert sc._key("IVAN IVANOV") == sc._key("IVANOV IVAN")

    def test_single_short_token_is_none(self):
        # cuvinte comune scurte -> fara cheie (anti-fals-pozitiv)
        assert sc._key("Global") is None       # 6 litere < 8
        assert sc._key("Company") is None       # suffix eliminat -> gol
        assert sc._key("SA") is None            # suffix juridic
        assert sc._key("de") is None            # stopword

    def test_single_long_token_ok(self):
        assert sc._key("Rosoboronexport") == "ROSOBORONEXPORT"


# ---- Parsere ----
class TestParsers:
    def test_parse_ofac_skips_null_and_maps_type(self):
        csv_text = (
            '36,"AEROCARIBBEAN AIRLINES",-0- ,"CUBA"\n'
            '100,"BADGUY, Ivan","individual","IRAN"\n'
            '999,-0- ,-0- ,-0-\n'
        )
        recs = sc._parse_ofac(csv_text)
        names = {r["name"] for r in recs}
        assert "AEROCARIBBEAN AIRLINES" in names
        assert "BADGUY, Ivan" in names
        assert all(r["source"] == "OFAC" for r in recs)
        # linia cu nume -0- e sarita
        assert len(recs) == 2
        entity = next(r for r in recs if r["name"] == "AEROCARIBBEAN AIRLINES")
        assert entity["type"] == "entity"  # -0- -> default entity

    def test_parse_eu_extracts_all_aliases(self):
        xml = (
            '<export xmlns="http://eu.europa.ec/fpi/fsd/export">'
            "<sanctionEntity>"
            '<subjectType code="person" classificationCode="P"/>'
            '<nameAlias wholeName="Saddam Hussein Al-Tikriti" strong="true"/>'
            '<nameAlias wholeName="Abu Ali"/>'
            "</sanctionEntity></export>"
        )
        recs = sc._parse_eu(xml)
        names = {r["name"] for r in recs}
        assert names == {"Saddam Hussein Al-Tikriti", "Abu Ali"}
        assert all(r["type"] == "person" and r["source"] == "EU" for r in recs)

    def test_parse_un_individuals_and_entities(self):
        xml = (
            "<CONSOLIDATED_LIST><INDIVIDUALS>"
            "<INDIVIDUAL><FIRST_NAME>ERIC</FIRST_NAME><SECOND_NAME>BADEGE</SECOND_NAME>"
            "<INDIVIDUAL_ALIAS><ALIAS_NAME>Eric Badege Jr</ALIAS_NAME></INDIVIDUAL_ALIAS>"
            "</INDIVIDUAL></INDIVIDUALS>"
            "<ENTITIES><ENTITY><FIRST_NAME>ACME TERROR CORP</FIRST_NAME>"
            "<ENTITY_ALIAS><ALIAS_NAME>ATC GROUP</ALIAS_NAME></ENTITY_ALIAS>"
            "</ENTITY></ENTITIES></CONSOLIDATED_LIST>"
        )
        recs = sc._parse_un(xml)
        names = {r["name"] for r in recs}
        assert "ERIC BADEGE" in names
        assert "Eric Badege Jr" in names
        assert "ACME TERROR CORP" in names


# ---- Screening ----
def _inject(records, sources=("OFAC", "EU", "UN")):
    sc._index, sc._records_tok = sc._build_index(records)
    sc._meta = {"sources": list(sources), "total": len(records), "built_at": "2026-07-11T00:00:00Z"}


class TestScreen:
    async def test_hit_across_variants(self):
        _inject([
            {"name": "AL-TIKRITI, Saddam Hussein", "type": "individual", "source": "OFAC"},
            {"name": "Saddam Hussein Al-Tikriti", "type": "person", "source": "EU"},
        ])
        r = await sc.screen(["Saddam Hussein Al-Tikriti"])
        assert r["status"] == "hit"
        assert len(r["hits"]) == 2  # ambele surse, order-independent match
        assert r["lists_checked"] == ["OFAC", "EU", "UN"]

    async def test_clean_ro_company(self):
        _inject([{"name": "Some Sanctioned Person", "type": "individual", "source": "UN"}])
        r = await sc.screen(["BORG DESIGN SRL", "Ion Popescu Administrator"])
        assert r["status"] == "clean"
        assert r["hits"] == []

    async def test_generic_single_token_no_false_positive(self):
        _inject([
            {"name": "Global", "type": "entity", "source": "OFAC"},  # filtrat: cheie None
            {"name": "Some Real Sanctioned Entity", "type": "entity", "source": "OFAC"},  # index ne-gol
        ])
        r = await sc.screen(["Global Company SRL", "Global"])
        # "Global" (6) nu produce cheie -> niciun hit chiar daca exista o intrare "Global"
        assert r["status"] == "clean"

    async def test_unavailable_when_no_data(self):
        sc._index = None
        sc._meta = {"sources": [], "total": 0, "built_at": ""}

        async def _fake_build():
            return {"records": [], "sources": [], "built_at": ""}

        # forteaza calea "fara date" fara retea
        import unittest.mock as m
        with m.patch.object(sc, "_load_cache", return_value=None), \
                m.patch.object(sc, "_build_from_sources", side_effect=_fake_build):
            r = await sc.screen(["Anything"])
        assert r["status"] == "unavailable"

    async def test_reports_completeness_partial(self):
        # Doar OFAC incarcat (EU+UN cazute) -> verdict NEautoritar, semnalat
        _inject([{"name": "Some Real Sanctioned Entity", "type": "entity", "source": "OFAC"}], sources=["OFAC"])
        r = await sc.screen(["Firma Curata SRL"])
        assert r["complete"] is False
        assert set(r["lists_missing"]) == {"EU", "UN"}
        assert r["lists_checked"] == ["OFAC"]

    async def test_reports_completeness_full(self):
        _inject([{"name": "Some Real Sanctioned Entity", "type": "entity", "source": "OFAC"}])
        r = await sc.screen(["Firma Curata SRL"])
        assert r["complete"] is True
        assert r["lists_missing"] == []

    async def test_subset_match_individual(self):
        # Nume administrator 2-token continut intr-un nume formal sanctionat 3-token
        _inject([{"name": "Ali Hassan Mohammed", "type": "individual", "source": "UN"}])
        r = await sc.screen(["Ali Mohammed"])
        assert r["status"] == "hit"
        assert r["hits"][0]["matched_name"] == "Ali Hassan Mohammed"

    async def test_subset_generic_capped(self):
        # Un nume generic care ar fi subset in prea multe intrari -> peste cap -> ignorat
        recs = [{"name": f"Ion Popescu Variant{i} Extra", "type": "individual", "source": "UN"}
                for i in range(15)]
        _inject(recs)
        r = await sc.screen(["Ion Popescu"])
        assert r["status"] == "clean"
