"""
Test dedicat pentru fix-ul `_fetch_google_maps` (2026-07-15): adresa reala trebuie
trimisa la Google Maps in loc de string gol.

De ce NU prin testul de caracterizare existent: acolo `maps_client.get_maps_rating`
e mockuit cu `AsyncMock(return_value=...)` -- ignora argumentele cu care e apelat,
deci nu ar fi prins niciodata regresia (bug-ul vechi trecea golden-ul la fel de bine
ca fix-ul nou). Acest test verifica explicit ARGUMENTUL `address` cu care e apelat
`get_maps_rating`, nu doar valoarea de retur.

Fixture-uri 100% sintetice (repo PUBLIC) -- niciun date reale de firma.
"""
from unittest.mock import AsyncMock, patch

import pytest

from backend.agents.agent_official import OfficialAgent
from backend.agents.tools import maps_client
from backend.config import settings


@pytest.mark.asyncio
async def test_fetch_google_maps_uses_real_anaf_address():
    """Cand official_data["anaf"]["adresa"] e populat, get_maps_rating primeste acea
    adresa (nu string gol)."""
    agent = OfficialAgent()
    official_data = {
        "anaf": {"adresa": "Str. Exemplu nr. 1, Arad", "denumire": "TEST SRL"},
    }
    sources: list = []
    mock_get_rating = AsyncMock(return_value={"found": False})

    with patch.object(maps_client, "get_maps_rating", new=mock_get_rating), \
         patch.object(settings, "google_cloud_api_key", "fake-key-for-test"):
        await agent._fetch_google_maps(official_data, sources, "TEST SRL")

    mock_get_rating.assert_awaited_once_with("TEST SRL", "Str. Exemplu nr. 1, Arad")


@pytest.mark.asyncio
async def test_fetch_google_maps_falls_back_to_onrc_structured_address():
    """Cand ANAF nu are adresa (ex. sursa a picat) dar openapi.ro (onrc_structured) are,
    fallback-ul e folosit."""
    agent = OfficialAgent()
    official_data = {
        "onrc_structured": {"adresa": "Str. Fallback nr. 2, Cluj", "judet": "Cluj"},
    }
    sources: list = []
    mock_get_rating = AsyncMock(return_value={"found": False})

    with patch.object(maps_client, "get_maps_rating", new=mock_get_rating), \
         patch.object(settings, "google_cloud_api_key", "fake-key-for-test"):
        await agent._fetch_google_maps(official_data, sources, "TEST SRL")

    mock_get_rating.assert_awaited_once_with("TEST SRL", "Str. Fallback nr. 2, Cluj")


@pytest.mark.asyncio
async def test_fetch_google_maps_prefers_anaf_over_onrc_structured():
    """Cand AMBELE surse au adresa, ANAF (sursa oficiala primara) are prioritate."""
    agent = OfficialAgent()
    official_data = {
        "anaf": {"adresa": "Adresa ANAF"},
        "onrc_structured": {"adresa": "Adresa openapi.ro"},
    }
    sources: list = []
    mock_get_rating = AsyncMock(return_value={"found": False})

    with patch.object(maps_client, "get_maps_rating", new=mock_get_rating), \
         patch.object(settings, "google_cloud_api_key", "fake-key-for-test"):
        await agent._fetch_google_maps(official_data, sources, "TEST SRL")

    mock_get_rating.assert_awaited_once_with("TEST SRL", "Adresa ANAF")


@pytest.mark.asyncio
async def test_fetch_google_maps_empty_address_when_no_source_available():
    """Comportament sigur nemodificat: fara ANAF/openapi.ro cu adresa, se trimite ""
    (identic cu comportamentul dinaintea fix-ului), NU o exceptie."""
    agent = OfficialAgent()
    official_data: dict = {}
    sources: list = []
    mock_get_rating = AsyncMock(return_value={"found": False})

    with patch.object(maps_client, "get_maps_rating", new=mock_get_rating), \
         patch.object(settings, "google_cloud_api_key", "fake-key-for-test"):
        await agent._fetch_google_maps(official_data, sources, "TEST SRL")

    mock_get_rating.assert_awaited_once_with("TEST SRL", "")
