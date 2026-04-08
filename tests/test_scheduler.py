"""
Teste pentru scheduler — get_scheduler_status, _get_checkpoint, _save_checkpoint, stop_scheduler, start_scheduler.
Pattern: import inline, mock DB via patch, @pytest.mark.asyncio pentru async.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGetSchedulerStatus:
    @pytest.mark.asyncio
    async def test_status_stopped_cand_task_none(self):
        """Cand _task este None, statusul trebuie sa fie 'stopped'."""
        import backend.services.scheduler as sched_module
        original_task = sched_module._task
        sched_module._task = None
        try:
            from backend.services.scheduler import get_scheduler_status
            result = await get_scheduler_status()
            assert "status" in result
            assert result["status"] == "stopped"
        finally:
            sched_module._task = original_task

    @pytest.mark.asyncio
    async def test_status_returneaza_dict(self):
        """get_scheduler_status trebuie sa returneze intotdeauna un dict."""
        import backend.services.scheduler as sched_module
        original_task = sched_module._task
        sched_module._task = None
        try:
            from backend.services.scheduler import get_scheduler_status
            result = await get_scheduler_status()
            assert isinstance(result, dict)
        finally:
            sched_module._task = original_task

    @pytest.mark.asyncio
    async def test_status_contine_running(self):
        """Rezultatul contine cheia 'running'."""
        import backend.services.scheduler as sched_module
        original_task = sched_module._task
        sched_module._task = None
        try:
            from backend.services.scheduler import get_scheduler_status
            result = await get_scheduler_status()
            assert "running" in result
            assert result["running"] is False
        finally:
            sched_module._task = original_task


class TestGetCheckpoint:
    @pytest.mark.asyncio
    async def test_returneaza_zero_cand_row_none(self):
        """Daca DB returneaza None, _get_checkpoint returneaza 0.0."""
        # scheduler.py importa db local (from backend.database import db)
        # patch-uim backend.database.db care este sursa
        mock_db = AsyncMock()
        mock_db.fetch_one = AsyncMock(return_value=None)

        with patch("backend.database.db", mock_db):
            from backend.services.scheduler import _get_checkpoint
            result = await _get_checkpoint("monitoring")
            assert result == 0.0

    @pytest.mark.asyncio
    async def test_returneaza_float_din_row(self):
        """Daca DB returneaza un row cu last_run valid, returneaza timestamp float."""
        from datetime import UTC, datetime
        iso_now = datetime.now(UTC).isoformat()

        mock_db = AsyncMock()
        mock_db.fetch_one = AsyncMock(return_value={"last_run": iso_now})

        with patch("backend.database.db", mock_db):
            from backend.services.scheduler import _get_checkpoint
            result = await _get_checkpoint("backup")
            assert isinstance(result, float)
            assert result > 0.0


class TestSaveCheckpoint:
    @pytest.mark.asyncio
    async def test_apeleaza_db_execute(self):
        """_save_checkpoint trebuie sa apeleze db.execute cel putin o data."""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()

        with patch("backend.database.db", mock_db):
            from backend.services.scheduler import _save_checkpoint
            await _save_checkpoint("monitoring", "OK")
            mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_nu_arunca_exceptie_la_db_error(self):
        """Daca DB arunca exceptie, _save_checkpoint o ingite (nu propaga)."""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=Exception("DB error"))

        with patch("backend.database.db", mock_db):
            from backend.services.scheduler import _save_checkpoint
            # Nu trebuie sa arunce exceptie
            await _save_checkpoint("backup", "OK")


class TestStopScheduler:
    @pytest.mark.asyncio
    async def test_stop_cu_task_valid_nu_arunca_exceptie(self):
        """stop_scheduler cu un task valid nu trebuie sa arunce exceptie."""
        import asyncio

        # Creeaza un task real care poate fi cancelat
        async def dummy():
            await asyncio.sleep(100)

        task = asyncio.create_task(dummy())

        from backend.services.scheduler import stop_scheduler
        # Nu trebuie sa arunce exceptie
        await stop_scheduler(task)
        assert task.cancelled() or task.done()


class TestStartScheduler:
    @pytest.mark.asyncio
    async def test_start_returneaza_task(self):
        """start_scheduler trebuie sa returneze un asyncio.Task."""
        import asyncio

        fake_task = MagicMock(spec=asyncio.Task)

        with patch("asyncio.create_task", return_value=fake_task):
            from backend.services.scheduler import start_scheduler
            result = await start_scheduler()
            assert result is fake_task
