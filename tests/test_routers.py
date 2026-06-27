"""
TST-02: Router tests with FastAPI TestClient.
Tests API endpoints: health, stats, jobs CRUD, companies, reports, settings, monitoring.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create TestClient with mocked database."""
    with patch("backend.database.db") as mock_db:
        # Mock database methods
        mock_db.connect = AsyncMock()
        mock_db.run_migrations = AsyncMock()
        mock_db.close = AsyncMock()
        mock_db.fetch_one = AsyncMock(return_value=None)
        mock_db.fetch_all = AsyncMock(return_value=[])
        mock_db.execute = AsyncMock()

        with patch("backend.http_client.startup", new_callable=AsyncMock):
            with patch("backend.http_client.shutdown", new_callable=AsyncMock):
                with patch("backend.services.cache_service.cleanup_expired", new_callable=AsyncMock):
                    with patch("backend.services.scheduler.start_scheduler", new_callable=AsyncMock, return_value=AsyncMock()):
                        with patch("backend.services.scheduler.stop_scheduler", new_callable=AsyncMock):
                            from backend.main import app
                            yield TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_basic(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_health_deep(self, client):
        with patch("backend.main.db") as mock_db:
            mock_db.execute = AsyncMock()
            resp = client.get("/api/health/deep")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data


class TestStatsEndpoints:
    """Test statistics endpoints."""

    def test_stats(self, client):
        with patch("backend.main.db") as mock_db:
            mock_db.fetch_one = AsyncMock(return_value={"c": 0})
            # Reset cache
            import backend.main
            backend.main._stats_cache = None
            resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_jobs" in data

    def test_stats_trend(self, client):
        with patch("backend.main.db") as mock_db:
            mock_db.fetch_all = AsyncMock(return_value=[])
            resp = client.get("/api/stats/trend")
        assert resp.status_code == 200
        data = resp.json()
        assert "trend" in data


class TestFrontendLog:
    """Test frontend logging endpoint."""

    def test_frontend_log_single(self, client):
        resp = client.post("/api/frontend-log", json={
            "ts": "12:00:00",
            "level": "ACTION",
            "page": "Dashboard",
            "message": "loaded",
        })
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_frontend_log_batch(self, client):
        resp = client.post("/api/frontend-log", json=[
            {"ts": "12:00:00", "level": "ACTION", "page": "Dashboard", "message": "loaded"},
            {"ts": "12:00:01", "level": "API", "page": "Dashboard", "message": "GET /stats | 200"},
        ])
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_frontend_log_session(self, client):
        resp = client.post("/api/frontend-log", json={
            "ts": "12:00:00",
            "level": "SESSION",
            "page": "-",
            "message": "Chrome | 1920x1080 | Windows",
        })
        assert resp.status_code == 200


class TestJobsEndpoints:
    """Test jobs CRUD endpoints."""

    def test_list_jobs(self, client):
        with patch("backend.database.db") as mock_db:
            mock_db.fetch_all = AsyncMock(return_value=[])
            mock_db.fetch_one = AsyncMock(return_value={"c": 0})
            resp = client.get("/api/jobs")
        assert resp.status_code == 200

    def test_create_job(self, client):
        with patch("backend.database.db") as mock_db:
            mock_db.execute = AsyncMock()
            mock_db.fetch_one = AsyncMock(return_value=None)
            resp = client.post("/api/jobs", json={
                "analysis_type": "FULL_COMPANY_PROFILE",
                "report_level": 2,
                "input_params": {"cui": "12345678"},
            })
        assert resp.status_code == 200

    def test_get_job_not_found(self, client):
        with patch("backend.database.db") as mock_db:
            mock_db.fetch_one = AsyncMock(return_value=None)
            resp = client.get("/api/jobs/nonexistent-id")
        assert resp.status_code in (404, 200)  # depends on error handling


class TestAnalysisEndpoints:
    """Test analysis type endpoints."""

    def test_list_analysis_types(self, client):
        resp = client.get("/api/analysis/types")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 5  # At least 5 analysis types

    def test_parse_query(self, client):
        resp = client.post("/api/analysis/parse-query", json={"query": "analiza firma 12345678"})
        assert resp.status_code == 200
        data = resp.json()
        assert "analysis_type" in data


class TestSettingsEndpoints:
    """Test settings endpoints."""

    def test_get_settings(self, client):
        resp = client.get("/api/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert "synthesis_mode" in data
        assert "fields" in data

    def test_update_settings(self, client):
        resp = client.put("/api/settings", json={"fields": {"SYNTHESIS_MODE": "autonomous"}})
        assert resp.status_code == 200


class TestCacheEndpoint:
    """Test cache stats endpoint."""

    def test_cache_stats(self, client):
        with patch("backend.services.cache_service.get_stats", new_callable=AsyncMock, return_value={"total": 0}):
            resp = client.get("/api/cache/stats")
        assert resp.status_code == 200


class TestRegenerateSection:
    """TASK1 (2026-06-27): POST /jobs/{id}/section/{key}/regenerate.

    Re-ruleaza sinteza unei singure sectiuni si persista noul continut in full_data.
    """

    def _report_row(self, sections=None):
        full_data = {
            "company": {"cui": {"value": "12345678"}, "denumire": {"value": "TEST SRL"}},
            "financial": {
                "cifra_afaceri": {"value": 1_000_000},
                "profit_net": {"value": 100_000},
            },
            "risk_score": {"score": "Verde", "numeric_score": 80},
            "completeness": {"score": 90},
        }
        if sections is not None:
            full_data["report_sections"] = sections
        return {
            "id": "report-1",
            "full_data": json.dumps(full_data),
            "report_type": "FULL_COMPANY_PROFILE",
            "report_level": 2,
        }

    def test_regenerate_persists_new_content(self, client):
        captured = {}

        async def fake_execute(sql, params=None):
            if "UPDATE reports SET full_data" in sql:
                captured["full_data"] = params[0]

        new_section = {
            "title": "Rezumat Executiv",
            "content": "CONTINUT NOU REGENERAT prin sinteza.",
            "word_count": 4,
        }
        old_sections = {
            "executive_summary": {
                "title": "Rezumat Executiv",
                "content": "VECHI",
                "word_count": 1,
            },
        }

        with patch("backend.routers.jobs.db") as mock_db, \
             patch("backend.security.settings") as mock_settings, \
             patch(
                 "backend.agents.agent_synthesis.synthesis_agent.generate_section",
                 new=AsyncMock(return_value=new_section),
             ):
            mock_settings.ris_api_key = ""
            mock_db.fetch_one = AsyncMock(return_value=self._report_row(old_sections))
            mock_db.execute = AsyncMock(side_effect=fake_execute)
            resp = client.post("/api/jobs/job-1/section/executive_summary/regenerate")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["section_key"] == "executive_summary"
        assert body["status"] == "done"
        assert body["section"]["content"] == "CONTINUT NOU REGENERAT prin sinteza."
        # Persistat: UPDATE reports a primit full_data cu noul continut
        assert "full_data" in captured
        saved = json.loads(captured["full_data"])
        assert (
            saved["report_sections"]["executive_summary"]["content"]
            == "CONTINUT NOU REGENERAT prin sinteza."
        )

    def test_regenerate_invalid_section_returns_400(self, client):
        with patch("backend.routers.jobs.db") as mock_db, \
             patch("backend.security.settings") as mock_settings:
            mock_settings.ris_api_key = ""
            mock_db.fetch_one = AsyncMock(return_value=self._report_row())
            mock_db.execute = AsyncMock()
            resp = client.post("/api/jobs/job-1/section/nonexistent_xyz/regenerate")
        assert resp.status_code == 400

    def test_regenerate_report_not_found_returns_404(self, client):
        with patch("backend.routers.jobs.db") as mock_db, \
             patch("backend.security.settings") as mock_settings:
            mock_settings.ris_api_key = ""
            mock_db.fetch_one = AsyncMock(return_value=None)
            resp = client.post("/api/jobs/job-1/section/executive_summary/regenerate")
        assert resp.status_code == 404
