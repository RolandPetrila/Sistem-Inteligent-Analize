"""BUG 2 fix (2026-07-16): asyncio.create_task() without a retained reference is only
weakly held by the event loop — per the asyncio docs ("Important: Save a reference"),
such a task can be garbage-collected mid-flight, silently dropping the work. Both
create_batch and resume_batch (backend/routers/batch.py) used to fire `_run_batch(...)`
this way. This module proves the retention mechanism (`_track_background_task` +
`_background_tasks` set) actually keeps a strong reference while the task is pending
and releases it on completion. Mirrors tests/test_jobs_background_tasks.py.

Import-cache isolation note: same rationale as tests/test_jobs_background_tasks.py —
`backend/routers/batch.py` also does `from backend.database import db` at module scope,
so a plain `import` here would cache it unpatched for the rest of the pytest session and
break test_routers.py's DB-mocked fixture (see that module's docstring for the full
mechanism). Loading via importlib under a throwaway module name avoids touching
`sys.modules["backend.routers.batch"]` entirely.
"""
import asyncio
import importlib.util
import pathlib

import pytest


def _load_batch_shadow_module():
    """Exec backend/routers/batch.py under a private module name (see docstring above)."""
    batch_path = pathlib.Path(__file__).resolve().parents[1] / "backend" / "routers" / "batch.py"
    spec = importlib.util.spec_from_file_location("_ris_test_batch_shadow", batch_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def batch_module():
    """Fresh shadow-loaded copy per test — avoids state leaking between tests too."""
    return _load_batch_shadow_module()


class TestBatchBackgroundTaskRetention:
    @pytest.mark.asyncio
    async def test_tracked_task_is_retained_while_pending(self, batch_module):
        release = asyncio.Event()

        async def _work():
            await release.wait()

        task = batch_module._track_background_task(_work())
        try:
            assert task in batch_module._background_tasks
        finally:
            release.set()
            await task

    @pytest.mark.asyncio
    async def test_tracked_task_is_discarded_on_completion(self, batch_module):
        async def _work():
            return "done"

        task = batch_module._track_background_task(_work())
        await task
        assert task not in batch_module._background_tasks

    @pytest.mark.asyncio
    async def test_tracked_task_still_completes_when_local_reference_is_dropped(self, batch_module):
        """Simulates the create_batch/resume_batch pattern: fire-and-forget, no local
        var kept for the asyncio.create_task() return value."""
        result = {"ran": False}

        async def _work():
            await asyncio.sleep(0)
            result["ran"] = True

        batch_module._track_background_task(_work())

        for _ in range(5):
            await asyncio.sleep(0)

        assert result["ran"] is True
        assert len(batch_module._background_tasks) == 0
