"""F16: Tests for orchestrator — pipeline flow, deduplication, checkpoints."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from backend.agents.orchestrator import (
    CuiInvalidError,
    _in_flight,
    _in_flight_results,
    build_analysis_graph,
    complete_in_flight,
    deduplicate_job,
    register_in_flight,
    run_market,
    run_official,
    run_synthesis,
    run_verification,
    run_web,
)


class TestCuiInvalidEarlyReturn:
    """BUG 1 fix: official_data['early_return'] must stop the pipeline (CuiInvalidError)."""

    @pytest.mark.asyncio
    async def test_run_official_raises_when_early_return_flagged(self):
        state = {
            "job_id": "test-job-badcui",
            "input_params": {"cui": "1234567890"},
            "analysis_type": "FULL_COMPANY_PROFILE",
        }
        early_return_result = {
            "official_data": {
                "early_return": True,
                "early_return_reason": "CUI 1234567890 nu trece validarea MOD 11: cifra de control gresita",
            },
            "sources": [],
            "errors": [{"agent": "official", "error": "CUI invalid", "recoverable": False}],
        }
        with patch("backend.agents.orchestrator.official_agent") as mock_agent:
            mock_agent.run = AsyncMock(return_value=early_return_result)
            with patch("backend.agents.orchestrator._save_checkpoint", new_callable=AsyncMock):
                with pytest.raises(CuiInvalidError) as excinfo:
                    await run_official(state)
        assert "MOD 11" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_run_official_valid_cui_unaffected(self):
        """CUI valid (fara early_return) -> run_official returneaza normal, fara exceptie."""
        state = {"job_id": "test-job-ok", "input_params": {"cui": "26313362"}}
        ok_result = {
            "official_data": {"cui": "26313362", "company_name": "Firma Test SRL"},
            "sources": [{"source_name": "ANAF", "data_found": True}],
            "errors": [],
        }
        with patch("backend.agents.orchestrator.official_agent") as mock_agent:
            mock_agent.run = AsyncMock(return_value=ok_result)
            with patch("backend.agents.orchestrator._save_checkpoint", new_callable=AsyncMock):
                result = await run_official(state)
        assert result["official_data"]["cui"] == "26313362"
        assert "early_return" not in result["official_data"]


class TestEarlyReturnStopsDownstreamAgents:
    """BUG 1 acceptance: web/market/verification/synthesis must NOT run for an invalid CUI
    — this is the actual quota-saving guarantee, proven at the full-graph level."""

    @pytest.mark.asyncio
    async def test_full_graph_stops_before_web_market_verification_synthesis(self):
        early_return_result = {
            "official_data": {
                "early_return": True,
                "early_return_reason": "CUI 000 nu trece validarea MOD 11: prea scurt",
            },
            "sources": [],
            "errors": [{"agent": "official", "error": "CUI invalid", "recoverable": False}],
        }
        initial_state = {
            "job_id": "test-job-graph",
            "analysis_type": "FULL_COMPANY_PROFILE",
            "report_level": 2,
            "input_params": {"cui": "000"},
            "agents_needed": ["official", "web", "market"],
            "errors": [],
            "sources": [],
            "progress": 0.0,
            "current_step": "Start",
            "_agent_metrics": {},
        }
        with (
            patch("backend.agents.orchestrator.official_agent") as mock_official,
            patch("backend.agents.tools.tavily_client.search", new_callable=AsyncMock) as mock_tavily,
            patch("backend.agents.tools.seap_client.get_contracts_won", new_callable=AsyncMock) as mock_seap,
            patch("backend.agents.orchestrator.verification_agent") as mock_verification,
            patch("backend.agents.orchestrator.synthesis_agent") as mock_synthesis,
            patch("backend.agents.orchestrator._save_checkpoint", new_callable=AsyncMock),
        ):
            mock_official.run = AsyncMock(return_value=early_return_result)
            mock_verification.run = AsyncMock()
            mock_synthesis.run = AsyncMock()

            graph = build_analysis_graph()
            with pytest.raises(CuiInvalidError):
                await graph.ainvoke(initial_state)

        mock_tavily.assert_not_called()
        mock_seap.assert_not_called()
        mock_verification.run.assert_not_called()
        mock_synthesis.run.assert_not_called()


class TestAgentCompleteStatusOnError:
    """BUG 3 fix: web/market must emit agent_complete(status='error') when they fail,
    matching the contract already used by official/verification/synthesis (2026-07-13)."""

    @pytest.mark.asyncio
    async def test_run_web_emits_agent_complete_error_on_failure(self):
        ws_manager = AsyncMock()
        state = {
            "job_id": "test-job-web-err",
            "_ws_manager": ws_manager,
            "input_params": {"cui": "26313362"},
            "official_data": {"company_name": "Firma Test SRL"},
        }
        with (
            patch("backend.agents.tools.tavily_client.search", new_callable=AsyncMock) as mock_search,
            patch("backend.agents.orchestrator._save_checkpoint", new_callable=AsyncMock),
        ):
            mock_search.side_effect = RuntimeError("Tavily boom")
            result = await run_web(state)

        assert result["web_data"] == {}
        complete_calls = [
            c for c in ws_manager.broadcast.call_args_list
            if c.args[1].get("type") == "agent_complete"
        ]
        assert complete_calls, "agent_complete nu a fost emis deloc pe eroare"
        assert complete_calls[-1].args[1]["status"] == "error"
        assert complete_calls[-1].args[1]["agent"] == "web"

    @pytest.mark.asyncio
    async def test_run_market_emits_agent_complete_error_on_failure(self):
        ws_manager = AsyncMock()
        state = {
            "job_id": "test-job-market-err",
            "_ws_manager": ws_manager,
            "input_params": {"cui": "26313362"},
        }
        with (
            patch("backend.agents.tools.seap_client.get_contracts_won", new_callable=AsyncMock) as mock_seap,
            patch("backend.agents.orchestrator._save_checkpoint", new_callable=AsyncMock),
        ):
            mock_seap.side_effect = RuntimeError("SEAP boom")
            result = await run_market(state)

        assert result["market_data"] == {}
        complete_calls = [
            c for c in ws_manager.broadcast.call_args_list
            if c.args[1].get("type") == "agent_complete"
        ]
        assert complete_calls, "agent_complete nu a fost emis deloc pe eroare"
        assert complete_calls[-1].args[1]["status"] == "error"
        assert complete_calls[-1].args[1]["agent"] == "market"


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
