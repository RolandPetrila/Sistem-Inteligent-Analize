"""Teste pentru backend/ws.py — ConnectionManager."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.ws import ConnectionManager


@pytest.mark.asyncio
async def test_connect_new_job():
    manager = ConnectionManager()
    ws = AsyncMock()
    await manager.connect("job1", ws)
    assert "job1" in manager.active
    assert ws in manager.active["job1"]


@pytest.mark.asyncio
async def test_disconnect_removes_ws():
    manager = ConnectionManager()
    ws = AsyncMock()
    await manager.connect("job1", ws)
    manager.disconnect("job1", ws)
    assert "job1" not in manager.active


@pytest.mark.asyncio
async def test_disconnect_nonexistent_ws():
    manager = ConnectionManager()
    ws = AsyncMock()
    # Nu trebuie sa dea exceptie
    manager.disconnect("nonexistent", ws)


@pytest.mark.asyncio
async def test_broadcast_sends_message():
    manager = ConnectionManager()
    ws = AsyncMock()
    await manager.connect("job1", ws)
    await manager.broadcast("job1", {"status": "running", "progress": 50})
    ws.send_text.assert_called_once()
    call_arg = ws.send_text.call_args[0][0]
    assert "running" in call_arg


@pytest.mark.asyncio
async def test_broadcast_removes_dead_connections():
    manager = ConnectionManager()
    ws = AsyncMock()
    ws.send_text.side_effect = Exception("Connection closed")
    await manager.connect("job1", ws)
    await manager.broadcast("job1", {"status": "done"})
    # Dupa broadcast esuat, conexiunea trebuie eliminata
    assert ws not in manager.active.get("job1", [])


@pytest.mark.asyncio
async def test_broadcast_empty_job():
    manager = ConnectionManager()
    # Nu trebuie sa dea exceptie pentru job inexistent
    await manager.broadcast("nonexistent", {"status": "ok"})
