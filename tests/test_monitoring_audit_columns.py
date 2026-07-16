"""
Regression tests for the "monitoring_audit column mismatch" bug class — found live
2026-07-16 across THREE call sites (companies.py timeline, monitoring.py /history,
monitoring.py /health).

monitoring_audit's REAL schema (migrations/002_phase8.sql) is:
    id, alert_id, company_cui, company_name, change_type, old_value, new_value,
    severity, triggered_at
It has NEVER had `company_id`, `message`, or `created_at` — all three call sites
read at least one of those, so the query raised "no such column", swallowed by a
bare `except ... events/history=[]`, so every one of these endpoints was silently
empty for every company, always.

Uses run_migrations() against a real temp DB (same pattern as test_companies_schema.py)
— NOT a fixture-built table with the buggy column names, which would just re-encode
the same wrong assumption as the code (this exact failure mode happened 3x in this
project on 2026-07-15/16, per CLAUDE.md).
"""
import aiosqlite
import pytest

import backend.routers.companies as companies_module
import backend.routers.monitoring as monitoring_module
from backend.database import Database


async def _real_schema_db(tmp_path):
    test_db = Database(str(tmp_path / "ris_test.db"))
    test_db._db = await aiosqlite.connect(test_db.db_path)
    test_db._db.row_factory = aiosqlite.Row
    await test_db.run_migrations()
    return test_db


@pytest.mark.asyncio
async def test_company_timeline_shows_monitoring_alert_by_cui(tmp_path, monkeypatch):
    test_db = await _real_schema_db(tmp_path)
    try:
        await test_db.execute(
            "INSERT INTO companies (id, cui, name) VALUES ('c1', '123456', 'Test SRL')"
        )
        await test_db.execute(
            "INSERT INTO monitoring_audit "
            "(company_cui, company_name, change_type, old_value, new_value, severity, triggered_at) "
            "VALUES ('123456', 'Test SRL', 'ca_scazuta', '1000000', '500000', 'RED', '2026-07-16 09:00:00')"
        )

        monkeypatch.setattr(companies_module, "db", test_db)
        result = await companies_module.company_timeline("c1")
        alert_events = [e for e in result["events"] if e["type"] == "alert"]
        assert len(alert_events) == 1, result["events"]
        assert "ca_scazuta" in alert_events[0]["detail"]
        assert "1000000" in alert_events[0]["detail"]
        assert "500000" in alert_events[0]["detail"]
        assert alert_events[0]["date"] == "2026-07-16 09:00:00"
    finally:
        await test_db._db.close()


@pytest.mark.asyncio
async def test_monitoring_history_returns_real_rows(tmp_path, monkeypatch):
    test_db = await _real_schema_db(tmp_path)
    try:
        await test_db.execute(
            "INSERT INTO companies (id, cui, name) VALUES ('c1', '123456', 'Test SRL')"
        )
        await test_db.execute(
            "INSERT INTO monitoring_audit "
            "(company_cui, company_name, change_type, old_value, new_value, severity, triggered_at) "
            "VALUES ('123456', 'Test SRL', 'ca_scazuta', '1000000', '500000', 'RED', '2026-07-16 09:00:00')"
        )

        monkeypatch.setattr(monitoring_module, "db", test_db)
        result = await monitoring_module.get_monitoring_history(limit=20)
        assert len(result["history"]) == 1, result
        assert result["history"][0]["company_name"] == "Test SRL"
    finally:
        await test_db._db.close()


@pytest.mark.asyncio
async def test_monitoring_health_counts_red_alerts_24h(tmp_path, monkeypatch):
    test_db = await _real_schema_db(tmp_path)
    try:
        await test_db.execute(
            "INSERT INTO companies (id, cui, name) VALUES ('c1', '123456', 'Test SRL')"
        )
        await test_db.execute(
            "INSERT INTO monitoring_audit "
            "(company_cui, company_name, change_type, old_value, new_value, severity, triggered_at) "
            "VALUES ('123456', 'Test SRL', 'ca_scazuta', '1000000', '500000', 'RED', datetime('now'))"
        )

        monkeypatch.setattr(monitoring_module, "db", test_db)
        result = await monitoring_module.monitoring_health()
        assert result["red_alerts_24h"] == 1, result
    finally:
        await test_db._db.close()
