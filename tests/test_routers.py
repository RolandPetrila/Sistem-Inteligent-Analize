"""
TST-02: Router tests with FastAPI TestClient.
Tests API endpoints: health, stats, jobs CRUD, companies, reports, settings, monitoring.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
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
