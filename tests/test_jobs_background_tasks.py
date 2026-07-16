"""BUG 2 fix (2026-07-16): asyncio.create_task() without a retained reference is only
weakly held by the event loop — per the asyncio docs ("Important: Save a reference"),
such a task can be garbage-collected mid-flight, silently dropping the work. `start_job`
(backend/routers/jobs.py) used to fire the whole analysis pipeline this way. This module
proves the retention mechanism (`_track_background_task` + `_background_tasks` set)
actually keeps a strong reference while the task is pending and releases it on completion.

Import-cache isolation note (found empirically while writing this test — NOT part of the
BUG 2 fix itself, but load-bearing for test suite health): `backend/routers/jobs.py` does
`from backend.database import db` at module scope, binding a permanent reference to
whatever `backend.database.db` is AT IMPORT TIME. `tests/test_routers.py::client` fixture
patches `backend.database.db` to a mock and THEN does the first `from backend.main import
app` of the whole session, relying on `backend.routers.jobs` not being cached yet so its
`db` binds to the mock. A plain `from backend.routers.jobs import ...` here (any test file
collected before test_routers.py has the same effect — this one just happened to be first)
would cache the module with the REAL, disconnected-in-tests db bound forever, breaking
TestJobsEndpoints in test_routers.py with 'RuntimeError: Database not connected' for the
rest of the pytest session. Fix: load backend/routers/jobs.py under a throwaway module
name via importlib instead of a normal `import` — this runs the module's top-level code
(so `_background_tasks`/`_track_background_task` exist and work identically) WITHOUT ever
touching `sys.modules["backend.routers.jobs"]`, so the canonical cache entry test_routers.py
depends on stays untouched by this file.
"""
import asyncio
import importlib.util
import pathlib

import pytest


def _load_jobs_shadow_module():
    """Exec backend/routers/jobs.py under a private module name (see docstring above)."""
    jobs_path = pathlib.Path(__file__).resolve().parents[1] / "backend" / "routers" / "jobs.py"
    spec = importlib.util.spec_from_file_location("_ris_test_jobs_shadow", jobs_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def jobs_module():
    """Fresh shadow-loaded copy per test — avoids state leaking between tests too."""
    return _load_jobs_shadow_module()


class TestBackgroundTaskRetention:
    @pytest.mark.asyncio
    async def test_tracked_task_is_retained_while_pending(self, jobs_module):
        """The whole point of the fix: our own strong reference lives in
        _background_tasks while the task hasn't finished yet — this is what
        prevents the GC-collection race the asyncio docs warn about, independent
        of whatever weak bookkeeping asyncio itself does internally."""
        release = asyncio.Event()

        async def _work():
            await release.wait()

        task = jobs_module._track_background_task(_work())
        try:
            assert task in jobs_module._background_tasks
        finally:
            release.set()
            await task

    @pytest.mark.asyncio
    async def test_tracked_task_is_discarded_on_completion(self, jobs_module):
        """add_done_callback(discard) must fire — otherwise _background_tasks grows
        unbounded forever (a slow memory leak in the fix itself)."""
        async def _work():
            return "done"

        task = jobs_module._track_background_task(_work())
        await task
        assert task not in jobs_module._background_tasks

    @pytest.mark.asyncio
    async def test_tracked_task_still_completes_when_local_reference_is_dropped(self, jobs_module):
        """Simulates exactly the start_job pattern: the caller doesn't keep the
        asyncio.create_task() return value around (it's fire-and-forget). Without
        the module-level set, nothing else references the Task object. Proves the
        work still runs to completion."""
        result = {"ran": False}

        async def _work():
            await asyncio.sleep(0)
            result["ran"] = True

        jobs_module._track_background_task(_work())  # fire-and-forget, exactly like start_job

        # Give the event loop a few iterations to run the tracked task to completion.
        for _ in range(5):
            await asyncio.sleep(0)

        assert result["ran"] is True
        assert len(jobs_module._background_tasks) == 0  # discarded after completion
