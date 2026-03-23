"""F16: Tests for orchestrator — pipeline flow, deduplication, checkpoints."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from backend.agents.orchestrator import (
    deduplicate_job,
    register_in_flight,
    complete_in_flight,
    _in_flight,
    _in_flight_results,
    run_official,
    run_verification,
    run_synthesis,
)


@pytest.fixture(autouse=True)
def cleanup_in_flight():
    """Clean up in-flight tracking between tests."""
    _in_flight.clear()
    _in_flight_results.clear()
    yield
    _in_flight.clear()
    _in_flight_results.clear()


class TestDeduplication:
    @pytest.mark.asyncio
    async def test_no_duplicate_returns_none(self):
        result = await deduplicate_job("12345")
        assert result is None

    @pytest.mark.asyncio
    async def test_register_and_complete(self):
        register_in_flight("99999")
        assert "99999" in _in_flight
        complete_in_flight("99999", {"status": "done"})
        assert _in_flight_results["99999"]["status"] == "done"

    @pytest.mark.asyncio
    async def test_dedup_waits_for_result(self):
        register_in_flight("11111")

        async def complete_later():
            await asyncio.sleep(0.05)
            complete_in_flight("11111", {"data": "reused"})

        asyncio.create_task(complete_later())
        result = await deduplicate_job("11111")
        assert result is not None
        assert result["data"] == "reused"


class TestRunOfficialErrorBoundary:
    @pytest.mark.asyncio
    async def test_error_boundary_returns_fallback(self):
        state = {"job_id": "test-job", "cui": "1234", "analysis_type": "FULL_COMPANY_PROFILE"}
        with patch("backend.agents.orchestrator.official_agent") as mock_agent:
            mock_agent.run = AsyncMock(side_effect=RuntimeError("Agent 1 crashed"))
            with patch("backend.agents.orchestrator._save_checkpoint", new_callable=AsyncMock):
                result = await run_official(state)
        assert "official_data" in result
        assert "error" in result["official_data"]
        assert "errors" in result


class TestRunVerificationErrorBoundary:
    @pytest.mark.asyncio
    async def test_error_boundary_returns_default_score(self):
        state = {"job_id": "test-job", "cui": "1234"}
        with patch("backend.agents.orchestrator.verification_agent") as mock_agent:
            mock_agent.run = AsyncMock(side_effect=RuntimeError("Agent 4 crashed"))
            with patch("backend.agents.orchestrator._save_checkpoint", new_callable=AsyncMock):
                result = await run_verification(state)
        vd = result["verified_data"]
        assert vd["risk_score"]["score"] == 50
        assert vd["risk_score"]["color"] == "GALBEN"


class TestRunSynthesisErrorBoundary:
    @pytest.mark.asyncio
    async def test_error_boundary_returns_fallback_sections(self):
        state = {
            "job_id": "test-job",
            "cui": "1234",
            "verified_data": {
                "risk_score": {"score": 70, "numeric_score": 70},
                "completeness": {"score": 80},
            },
        }
        with patch("backend.agents.orchestrator.synthesis_agent") as mock_agent:
            mock_agent.run = AsyncMock(side_effect=RuntimeError("Agent 5 crashed"))
            with patch("backend.agents.orchestrator._save_checkpoint", new_callable=AsyncMock):
                result = await run_synthesis(state)
        assert "report_sections" in result
        assert "errors" in result
