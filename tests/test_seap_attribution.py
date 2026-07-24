"""
Regresie pentru cel mai grav finding din auditul 2026-07-24: SEAP prezenta
contractele ALTOR firme ca fiind ale firmei analizate, in FIECARE raport.

Cauza: `spiCuiSupplier` era o cheie NECUNOSCUTA pentru SICAP, iar SICAP ignora
TACIT cheile necunoscute (nu returneaza eroare). Raspunsul era lista nefiltrata
la nivel national — verificat live: acelasi set de id-uri pentru CUI-uri diferite
SI pentru niciun filtru, pe ambele endpoint-uri.

Filtrarea reala se face pe id-ul INTERN de furnizor, rezolvat din CUI, si fiecare
endpoint are ALT NUME de parametru (fara simetrie):
    GetCANoticeList          -> winnerId    (plafon `total` 3000)
    GetDirectAcquisitionList -> supplierId  (plafon `total` 2000)

Valorile din fixture-uri sunt cele MASURATE live pe raspunsul real (2026-07-24),
nu inventate — exact ca sa nu se repete tiparul "fixture-ul codifica aceeasi
presupunere gresita ca si codul".
"""
from unittest.mock import AsyncMock, patch

import pytest

from backend.agents.tools import seap_client
from backend.agents.tools.seap_client import (
    _cui_from_supplier_field,
    _parse_ca_notice,
    _parse_direct_acquisition,
    seap_status,
)

# --- forme REALE, copiate din raspunsul masurat ---------------------------------

REAL_DA_ITEM = {
    "caDecisionDeadline": "2026-07-15T17:00:00+03:00",
    "closingValue": 228056.59,
    "contractingAuthority": "4406134 Comuna Rasinari",
    "cpvCode": "45233142-6 - Lucrari de reparare a drumurilor (Rev.2)",
    "directAcquisitionId": 122593630,
    "directAcquisitionName": "Reparatii capitale str.Giurculetului",
    "estimatedValueRon": 228056.59,
    "finalizationDate": "2026-07-10T10:36:28+03:00",
    "publicationDate": "2026-07-09T20:55:26+03:00",
    "supplier": "RO 6891914 STRABAG",
    "sysDirectAcquisitionState": {"id": 7, "text": "Oferta acceptata"},
    "uniqueIdentificationCode": "DA40798347",
}

REAL_CA_ITEM = {
    "caNoticeId": 100644260,
    "contractTitle": "Acord-cadru pentru lucrari de intretinere",
    "contractingAuthorityNameAndFN": "16054368 - COMPANIA NATIONALA",
    "cpvCodeAndName": "45233139-3 - Lucrari de intretinere a drumurilor (Rev.2)",
    "currencyCode": "RON",
    "noticeNo": "CAN1171835",
    "noticeStateDate": "2026-07-23T10:50:18+03:00",
    "ronContractValue": 0.0,  # real pe acordurile-cadru
    "sysNoticeState": {"id": 2, "text": "Publicat"},
    "sysNoticeTypeId": 3,
}


class TestParsareCampuriReale:
    """Campurile citite trebuie sa EXISTE in raspuns. Camp gol pe date reale =
    mapare gresita, nu date lipsa."""

    def test_achizitie_directa_toate_campurile_populate(self):
        p = _parse_direct_acquisition(REAL_DA_ITEM)
        goale = [k for k in ("title", "authority", "date", "state", "cpv") if not p[k]]
        assert not goale, f"campuri goale pe un item REAL: {goale} — mapare gresita"
        assert p["value"] == 228056.59
        assert p["authority"] == "4406134 Comuna Rasinari"
        assert p["state"] == "Oferta acceptata"
        assert p["state_id"] == 7
        assert p["won"] is True

    def test_campurile_moarte_din_parserul_vechi(self):
        """`contractingAuthorityName` si `sysDirectAcqStateName` NU exista in
        raspunsul real — parserul vechi le citea, deci erau goale dintotdeauna."""
        assert "contractingAuthorityName" not in REAL_DA_ITEM
        assert "sysDirectAcqStateName" not in REAL_DA_ITEM
        p = _parse_direct_acquisition(REAL_DA_ITEM)
        assert p["authority"] and p["state"], "parserul nou trebuie sa le citeasca corect"

    def test_atribuire_clasica_campuri_reale(self):
        p = _parse_ca_notice(REAL_CA_ITEM)
        assert p["authority"] == "16054368 - COMPANIA NATIONALA"
        assert p["date"] == "2026-07-23T10:50:18+03:00"
        assert p["currency"] == "RON"

    def test_acord_cadru_nu_raporteaza_valoarea_zero(self):
        """`ronContractValue` e 0.0 real pe acorduri-cadru — zero ar dezumfla totalul."""
        p = _parse_ca_notice(REAL_CA_ITEM)
        assert p["value"] is None
        assert p["value_unknown"] is True


class TestExtragereCuiFurnizor:
    """Formatul difera intre endpoint-uri — `supplier` are prefix RO, textul de
    la searchSuppliers nu."""

    @pytest.mark.parametrize("raw,expected", [
        ("RO 6891914 STRABAG", "6891914"),
        ("RO6891914 STRABAG", "6891914"),
        ("6891914 STRABAG", "6891914"),
        ("1589886 Societatea de Transport", "1589886"),
        ("STRABAG fara cui", ""),
        ("", ""),
        (None, ""),
    ])
    def test_cui_din_camp_supplier(self, raw, expected):
        assert _cui_from_supplier_field(raw) == expected


class TestStareaAchizitiei:
    """Doar `id == 7` inseamna contract castigat. Orice alt id — inclusiv unul
    NECUNOSCUT — inseamna nefinalizat."""

    @pytest.mark.parametrize("state_id,won", [
        (7, True),
        (6, False),   # Oferta refuzata
        (3, False),   # Conditii refuzate
        (4, False),   # Conditii neacceptate la termen (lipsea din esantionul de 100)
        (8, False),   # Oferta neacceptata in termen
        (99, False),  # stare VIITOARE, necunoscuta -> nu trece ca "castigat"
        (None, False),
    ])
    def test_doar_oferta_acceptata_conteaza(self, state_id, won):
        item = {**REAL_DA_ITEM,
                "sysDirectAcquisitionState": ({"id": state_id, "text": "x"} if state_id else None)}
        assert _parse_direct_acquisition(item)["won"] is won


class TestSeapStatus:
    """Verdictul unic pe care il citesc toti consumatorii."""

    @pytest.mark.parametrize("payload,expected", [
        ({"contracts_verified": True, "total_contracts": 5}, "verified_with_contracts"),
        ({"contracts_verified": True, "total_contracts": 0}, "verified_empty"),
        ({"contracts_verified": False, "total_contracts": 0}, "unverified"),
        ({}, "unverified"),
        (None, "unverified"),
        # forma WRAPPED (_make_field) — consumatorii nu trebuie sa re-implementeze unwrap
        ({"value": {"contracts_verified": True, "total_contracts": 3}}, "verified_with_contracts"),
    ])
    def test_verdict(self, payload, expected):
        assert seap_status(payload) == expected

    def test_zero_verificat_difera_de_zero_neverificat(self):
        """Intreg scopul flagului: pana acum ambele arata ca 0."""
        assert seap_status({"contracts_verified": True, "total_contracts": 0}) != \
               seap_status({"contracts_verified": False, "total_contracts": 0})


class TestGardaDeRezolutie:
    """0 sau >=2 potriviri exacte -> STOP. Al doilea apel NU trebuie sa plece:
    fara parametrul de furnizor, raspunsul e lista nefiltrata (plafonul)."""

    @pytest.mark.asyncio
    async def test_furnizor_negasit_opreste_inainte_de_al_doilea_apel(self):
        with patch.object(seap_client, "resolve_supplier_id",
                          AsyncMock(return_value={"resolved": False, "supplier_id": None,
                                                  "reason": "CUI negasit"})), \
             patch.object(seap_client, "get_client") as mock_client, \
             patch("backend.services.cache_service.get", AsyncMock(return_value=None)), \
             patch("backend.services.cache_service.set", AsyncMock()):

            r = await seap_client.get_contracts_won("43978110")

            assert r["contracts_verified"] is False
            assert r["contracts"] == [] and r["direct_acquisitions"] == []
            assert r["total_contracts"] == 0
            mock_client.assert_not_called(), "s-a facut un request DUPA esecul rezolutiei"

    @pytest.mark.asyncio
    async def test_ambiguitatea_nu_se_rezolva_prin_ghicire(self):
        """Doi furnizori cu acelasi CUI -> nerezolvat, nu 'il iau pe primul'."""
        resp = type("R", (), {"status_code": 200,
                              "json": lambda self: [{"id": 1, "text": "6891914 A"},
                                                    {"id": 2, "text": "6891914 B"}]})()
        with patch.object(seap_client, "with_retry", AsyncMock(return_value=resp)), \
             patch("backend.services.cache_service.get", AsyncMock(return_value=None)), \
             patch("backend.services.cache_service.set", AsyncMock()):
            out = await seap_client.resolve_supplier_id("6891914")
        assert out["resolved"] is False
        assert "ambiguu" in out["reason"]

    @pytest.mark.asyncio
    async def test_potrivire_exacta_nu_prefix(self):
        """CUI de 7 cifre confundabil cu prefixul unuia de 8 — de aceea egalitate,
        nu startswith."""
        resp = type("R", (), {"status_code": 200,
                              "json": lambda self: [{"id": 9, "text": "80001380 ALTA FIRMA"}]})()
        with patch.object(seap_client, "with_retry", AsyncMock(return_value=resp)), \
             patch("backend.services.cache_service.get", AsyncMock(return_value=None)), \
             patch("backend.services.cache_service.set", AsyncMock()):
            out = await seap_client.resolve_supplier_id("8000138")
        assert out["resolved"] is False


class TestDefensivaLaParsare:
    """Sursa esuata si firma fara contracte NU mai arata la fel. SICAP nu expune
    niciun header de rate-limit, deci o blocare poate arata ca 200 cu lista goala."""

    def test_status_non_200_arunca(self):
        resp = type("R", (), {"status_code": 503, "text": "unavailable"})()
        with pytest.raises(seap_client.SeapSourceError, match="503"):
            seap_client._json_or_raise(resp, "test")

    def test_corp_non_json_arunca(self):
        def _boom(self):
            raise ValueError("nu e json")
        resp = type("R", (), {"status_code": 200, "json": _boom})()
        with pytest.raises(seap_client.SeapSourceError, match="non-JSON"):
            seap_client._json_or_raise(resp, "test")

    def test_forma_neasteptata_arunca(self):
        """200 cu JSON valid dar fara `items` — nu e zero, e sursa schimbata."""
        resp = type("R", (), {"status_code": 200, "json": lambda self: {"altceva": 1}})()
        with pytest.raises(seap_client.SeapSourceError, match="forma neasteptata"):
            seap_client._json_or_raise(resp, "test")


class TestConsumatoriiRespectaFlagul:
    """Fiecare consumator trebuie sa trateze 'neverificat' ca necunoscut, nu ca zero."""

    def test_completitudinea_nu_numara_sursa_neverificata(self):
        from backend.agents.verification.completeness import check_completeness
        base = {"company": {}, "financial": {}, "risk": {}}

        neverificat = check_completeness(
            base, {}, {"seap": {"contracts_verified": False, "total_contracts": 0}})
        verificat_gol = check_completeness(
            base, {}, {"seap": {"contracts_verified": True, "total_contracts": 0}})

        assert verificat_gol["score"] > neverificat["score"], (
            "'verificat, firma n-are contracte' e un raspuns si trebuie sa treaca "
            "verificarea; 'n-am putut verifica' nu"
        )

    def test_randarea_nu_afiseaza_sectiunea_pe_date_neverificate(self):
        from backend.reports.rich_fields import build_rich_fields_model
        m = build_rich_fields_model(
            {"market": {"seap": {"value": {"contracts_verified": False, "total_contracts": 20,
                                           "contracts": [{"title": "al altei firme"}]}}}})
        assert m["seap"]["shown"] is False, (
            "sectiunea SICAP s-a randat pe date neatribuite firmei"
        )

    def test_scoringul_nu_da_bonus_pe_date_neverificate(self):
        from backend.agents.verification.scoring import _score_piata
        dim, _, _ = _score_piata(
            {"seap": {"value": {"contracts_verified": False, "total_contracts": 20}}}, {})
        motive = " ".join(r["text"] for r in dim["reasons"])
        assert "Contracte SEAP" not in motive, (
            "bonusul de piata s-a acordat pe contracte neatribuite firmei"
        )
