"""
F8-1: Teste pentru network_client — retea firme prin asociati comuni.
Testeaza store_administrators, get_company_network (fara DB real via mock).
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestStoreAdministrators:
    @pytest.mark.asyncio
    async def test_cui_gol_nu_face_nimic(self):
        # Nu trebuie sa crape cu CUI gol si nu apeleaza DB
        with patch("backend.agents.tools.network_client.db") as mock_db:
            mock_db.execute = AsyncMock()
            from backend.agents.tools.network_client import store_administrators
            await store_administrators("", "Test SRL", [{"name": "Ion", "role": "admin"}])
            mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_lista_goala_nu_face_nimic(self):
        with patch("backend.agents.tools.network_client.db") as mock_db:
            mock_db.execute = AsyncMock()
            from backend.agents.tools.network_client import store_administrators
            await store_administrators("12345678", "Test SRL", [])
            mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_persoane_valide_se_insereaza(self):
        with patch("backend.agents.tools.network_client.db") as mock_db:
            mock_db.execute = AsyncMock()
            from backend.agents.tools.network_client import store_administrators
            persons = [
                {"name": "Ion Popescu", "role": "administrator", "ownership_pct": None},
                {"name": "Maria Ionescu", "role": "asociat", "ownership_pct": 50.0},
            ]
            await store_administrators("12345678", "Test SRL", persons)
            assert mock_db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_persoana_fara_nume_ignorata(self):
        with patch("backend.agents.tools.network_client.db") as mock_db:
            mock_db.execute = AsyncMock()
            from backend.agents.tools.network_client import store_administrators
            persons = [
                {"name": "", "role": "administrator"},
                {"name": "   ", "role": "administrator"},
                {"name": "Ion Popescu", "role": "asociat"},
            ]
            await store_administrators("12345678", "Test SRL", persons)
            # Doar Ion Popescu e valid (nume gol sau spatii sunt ignorate)
            assert mock_db.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_persoana_fara_camp_name_ignorata(self):
        with patch("backend.agents.tools.network_client.db") as mock_db:
            mock_db.execute = AsyncMock()
            from backend.agents.tools.network_client import store_administrators
            persons = [
                {"role": "administrator"},  # fara key "name"
                {"name": "Valida Test", "role": "asociat"},
            ]
            await store_administrators("12345678", "Test SRL", persons)
            assert mock_db.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_eroare_db_nu_propage(self):
        with patch("backend.agents.tools.network_client.db") as mock_db:
            mock_db.execute = AsyncMock(side_effect=Exception("DB error"))
            from backend.agents.tools.network_client import store_administrators
            # Nu trebuie sa propage exceptia — e prinsa intern
            await store_administrators("12345678", "Test SRL", [{"name": "Ion", "role": "admin"}])

    @pytest.mark.asyncio
    async def test_ownership_none_acceptat(self):
        with patch("backend.agents.tools.network_client.db") as mock_db:
            mock_db.execute = AsyncMock()
            from backend.agents.tools.network_client import store_administrators
            await store_administrators("99999999", "Firma SRL", [
                {"name": "Ana Maria", "role": "asociat", "ownership_pct": None}
            ])
            mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_ownership_procent_acceptat(self):
        with patch("backend.agents.tools.network_client.db") as mock_db:
            mock_db.execute = AsyncMock()
            from backend.agents.tools.network_client import store_administrators
            await store_administrators("88888888", "Firma SRL", [
                {"name": "Bogdan Test", "role": "asociat", "ownership_pct": 75.5}
            ])
            # Verifica ca ownership_pct a fost transmis ca parametru
            call_args = mock_db.execute.call_args[0][1]
            assert 75.5 in call_args

    @pytest.mark.asyncio
    async def test_rol_default_administrator(self):
        with patch("backend.agents.tools.network_client.db") as mock_db:
            mock_db.execute = AsyncMock()
            from backend.agents.tools.network_client import store_administrators
            await store_administrators("77777777", "Firma SRL", [
                {"name": "Test User"}  # fara role
            ])
            # Trebuie sa foloseasca "administrator" ca default
            call_args = mock_db.execute.call_args[0][1]
            assert "administrator" in call_args


class TestGetCompanyNetwork:
    @pytest.mark.asyncio
    async def test_cui_gol_returneaza_has_data_false(self):
        from backend.agents.tools.network_client import get_company_network
        result = await get_company_network("")
        assert result["has_data"] is False
        assert result["persons"] == []
        assert result["related_companies"] == []
        assert result["risk_flags"] == []

    @pytest.mark.asyncio
    async def test_fara_date_in_db_returneaza_has_data_false(self):
        with patch("backend.agents.tools.network_client.db") as mock_db:
            mock_db.fetch_all = AsyncMock(return_value=[])
            from backend.agents.tools.network_client import get_company_network
            result = await get_company_network("12345678")
            assert result["has_data"] is False
            assert result["persons"] == []

    @pytest.mark.asyncio
    async def test_fara_date_include_nota(self):
        with patch("backend.agents.tools.network_client.db") as mock_db:
            mock_db.fetch_all = AsyncMock(return_value=[])
            from backend.agents.tools.network_client import get_company_network
            result = await get_company_network("12345678")
            assert "note" in result

    @pytest.mark.asyncio
    async def test_cu_date_returneaza_has_data_true(self):
        # Simuleaza un admin gasit
        mock_person = MagicMock()
        mock_person.__getitem__ = lambda self, key: {
            "person_name": "Ion Popescu",
            "role": "administrator",
            "ownership_pct": None,
        }[key]

        # Simuleaza nicio firma conexa (persoanele nu apar in alte firme)
        with patch("backend.agents.tools.network_client.db") as mock_db:
            # Prima apelare: persons (row-uri cu person_name, role, ownership_pct)
            # A doua apelare: related companies (goala)
            row1 = {"person_name": "Ion Popescu", "role": "administrator", "ownership_pct": None}
            mock_db.fetch_all = AsyncMock(side_effect=[[row1], []])
            from backend.agents.tools.network_client import get_company_network
            result = await get_company_network("12345678")
            assert result["has_data"] is True
            assert len(result["persons"]) == 1
            assert result["persons"][0]["name"] == "Ion Popescu"

    @pytest.mark.asyncio
    async def test_cu_date_structura_completa(self):
        row_person = {"person_name": "Maria Test", "role": "asociat", "ownership_pct": 50.0}
        with patch("backend.agents.tools.network_client.db") as mock_db:
            mock_db.fetch_all = AsyncMock(side_effect=[[row_person], []])
            from backend.agents.tools.network_client import get_company_network
            result = await get_company_network("12345678")
            # Verifica structura de returnare completa
            assert "has_data" in result
            assert "persons" in result
            assert "related_companies" in result
            assert "risk_flags" in result
            assert "total_connected" in result
            assert "stats" in result

    @pytest.mark.asyncio
    async def test_firma_inactiva_genereaza_risk_flag(self):
        row_person = {"person_name": "Ion Popescu", "role": "administrator", "ownership_pct": None}
        row_related = {
            "cui": "87654321",
            "company_name": "Firma Inactiva SRL",
            "person_name": "Ion Popescu",
            "role": "asociat",
            "last_analyzed_at": "2026-01-01",
            "is_active": 0,
        }
        with patch("backend.agents.tools.network_client.db") as mock_db:
            mock_db.fetch_all = AsyncMock(side_effect=[[row_person], [row_related]])
            from backend.agents.tools.network_client import get_company_network
            result = await get_company_network("12345678")
            assert len(result["risk_flags"]) > 0
            flag_types = [f["type"] for f in result["risk_flags"]]
            assert "ASOCIAT_FIRMA_INACTIVA" in flag_types

    @pytest.mark.asyncio
    async def test_firma_inactiva_o_singura_e_yellow(self):
        row_person = {"person_name": "Ion Popescu", "role": "administrator", "ownership_pct": None}
        row_related = {
            "cui": "87654321",
            "company_name": "Firma Inactiva SRL",
            "person_name": "Ion Popescu",
            "role": "asociat",
            "last_analyzed_at": "2026-01-01",
            "is_active": 0,
        }
        with patch("backend.agents.tools.network_client.db") as mock_db:
            mock_db.fetch_all = AsyncMock(side_effect=[[row_person], [row_related]])
            from backend.agents.tools.network_client import get_company_network
            result = await get_company_network("12345678")
            inactive_flag = next(f for f in result["risk_flags"] if f["type"] == "ASOCIAT_FIRMA_INACTIVA")
            assert inactive_flag["severity"] == "YELLOW"

    @pytest.mark.asyncio
    async def test_doua_firme_inactive_severity_red(self):
        row_person = {"person_name": "Ion Popescu", "role": "administrator", "ownership_pct": None}
        rows_related = [
            {
                "cui": "11111111",
                "company_name": "Firma Inactiva 1 SRL",
                "person_name": "Ion Popescu",
                "role": "asociat",
                "last_analyzed_at": "2026-01-01",
                "is_active": 0,
            },
            {
                "cui": "22222222",
                "company_name": "Firma Inactiva 2 SRL",
                "person_name": "Ion Popescu",
                "role": "asociat",
                "last_analyzed_at": "2026-01-01",
                "is_active": 0,
            },
        ]
        with patch("backend.agents.tools.network_client.db") as mock_db:
            mock_db.fetch_all = AsyncMock(side_effect=[[row_person], rows_related])
            from backend.agents.tools.network_client import get_company_network
            result = await get_company_network("12345678")
            inactive_flag = next(f for f in result["risk_flags"] if f["type"] == "ASOCIAT_FIRMA_INACTIVA")
            assert inactive_flag["severity"] == "RED"

    @pytest.mark.asyncio
    async def test_retea_extinsa_genereaza_flag(self):
        row_person = {"person_name": "Ion Popescu", "role": "administrator", "ownership_pct": None}
        # 11 firme conexe
        rows_related = [
            {
                "cui": f"1000000{i}",
                "company_name": f"Firma {i} SRL",
                "person_name": "Ion Popescu",
                "role": "asociat",
                "last_analyzed_at": "2026-01-01",
                "is_active": 1,
            }
            for i in range(11)
        ]
        with patch("backend.agents.tools.network_client.db") as mock_db:
            mock_db.fetch_all = AsyncMock(side_effect=[[row_person], rows_related])
            from backend.agents.tools.network_client import get_company_network
            result = await get_company_network("12345678")
            flag_types = [f["type"] for f in result["risk_flags"]]
            assert "RETEA_EXTINSA" in flag_types

    @pytest.mark.asyncio
    async def test_stats_corecte(self):
        row_person = {"person_name": "Ion Popescu", "role": "administrator", "ownership_pct": None}
        rows_related = [
            {
                "cui": "11111111",
                "company_name": "Firma Activa SRL",
                "person_name": "Ion Popescu",
                "role": "asociat",
                "last_analyzed_at": "2026-01-01",
                "is_active": 1,
            },
            {
                "cui": "22222222",
                "company_name": "Firma Inactiva SRL",
                "person_name": "Ion Popescu",
                "role": "asociat",
                "last_analyzed_at": "2026-01-01",
                "is_active": 0,
            },
            {
                "cui": "33333333",
                "company_name": "Firma Necunoscuta SRL",
                "person_name": "Ion Popescu",
                "role": "asociat",
                "last_analyzed_at": None,
                "is_active": None,
            },
        ]
        with patch("backend.agents.tools.network_client.db") as mock_db:
            mock_db.fetch_all = AsyncMock(side_effect=[[row_person], rows_related])
            from backend.agents.tools.network_client import get_company_network
            result = await get_company_network("12345678")
            stats = result["stats"]
            assert stats["inactive"] == 1
            assert stats["unknown_status"] == 1
            assert stats["active"] == 1

    @pytest.mark.asyncio
    async def test_firma_exclusa_din_propria_retea(self):
        # Firma X nu trebuie sa apara in propria retea
        row_person = {"person_name": "Ion Popescu", "role": "administrator", "ownership_pct": None}
        # SQL-ul are AND ca.cui != ? deci firma sursa e exclusa — simulam ca DB returneaza corect
        with patch("backend.agents.tools.network_client.db") as mock_db:
            mock_db.fetch_all = AsyncMock(side_effect=[[row_person], []])
            from backend.agents.tools.network_client import get_company_network
            result = await get_company_network("12345678")
            # Niciuna din firmele conexe nu are CUI-ul firmei cautate
            cuis = [c["cui"] for c in result.get("related_companies", [])]
            assert "12345678" not in cuis
