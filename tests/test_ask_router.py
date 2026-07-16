"""
Regression tests for backend/routers/ask.py — NLQ intents "statistici" si "ultimele".

Bug class identic cu test_companies_schema.py: cod care citeste o valoare/coloana
pe care nimic nu o scrie, tacut (fara crash, doar rezultat gresit).

- "statistici": filtra jobs.status = 'COMPLETED', dar enum-ul canonic (backend.models.
  JobStatus) NU are niciodata valoarea asta — statusul real de job finalizat e 'DONE'.
  Rularea reala pe DB arata DONE=79/FAILED=11/PAUSED=1/PENDING=1, COMPLETED=0 mereu.
- "ultimele": JOIN companies c ON c.cui = j.input_data — input_data e un blob JSON
  ('{"cui": "43978110", ...}'), nu un CUI, deci JOIN-ul nu se potriveste NICIODATA.

Foloseste run_migrations() real (nu o schema inventata in test) — acelasi pattern ca
test_companies_schema.py — ca sa nu repete greseala descrisa in ISSUES: un fixture care
isi construieste propriul dict/schema cu aceeasi presupunere gresita ca si codul.
"""
import aiosqlite
import pytest

import backend.routers.ask as ask_module
from backend.database import Database


async def _real_schema_db(tmp_path):
    test_db = Database(str(tmp_path / "ris_test.db"))
    test_db._db = await aiosqlite.connect(test_db.db_path)
    test_db._db.row_factory = aiosqlite.Row
    await test_db.run_migrations()
    return test_db


@pytest.mark.asyncio
async def test_statistici_counts_done_jobs_not_completed(tmp_path, monkeypatch):
    test_db = await _real_schema_db(tmp_path)
    try:
        await test_db.execute(
            "INSERT INTO jobs (id, type, status) VALUES ('j1', 'FULL_COMPANY_PROFILE', 'DONE')"
        )
        await test_db.execute(
            "INSERT INTO jobs (id, type, status) VALUES ('j2', 'FULL_COMPANY_PROFILE', 'DONE')"
        )
        await test_db.execute(
            "INSERT INTO jobs (id, type, status) VALUES ('j3', 'FULL_COMPANY_PROFILE', 'FAILED')"
        )

        monkeypatch.setattr(ask_module, "db", test_db)
        resp = await ask_module.ask_ris(
            ask_module.AskRequest(question="Cate analize am facut?"), _=None
        )
        assert "Analize completate: 2" in resp.answer, resp.answer
    finally:
        await test_db._db.close()


@pytest.mark.asyncio
async def test_ultimele_resolves_company_via_reports_join(tmp_path, monkeypatch):
    test_db = await _real_schema_db(tmp_path)
    try:
        await test_db.execute(
            "INSERT INTO companies (id, cui, name) VALUES ('c1', '123456', 'Test SRL')"
        )
        await test_db.execute(
            "INSERT INTO jobs (id, type, status, input_data, created_at) "
            "VALUES ('j1', 'FULL_COMPANY_PROFILE', 'DONE', '{\"cui\": \"123456\"}', '2026-07-16 10:00:00')"
        )
        # reports.company_id e FK-ul real populat de job_service._save_job_results
        # dupa o analiza reusita — simulam exact acea legatura.
        await test_db.execute(
            "INSERT INTO reports (id, job_id, company_id, report_type, created_at) "
            "VALUES ('r1', 'j1', 'c1', 'FULL_COMPANY_PROFILE', '2026-07-16 10:05:00')"
        )

        monkeypatch.setattr(ask_module, "db", test_db)
        resp = await ask_module.ask_ris(
            ask_module.AskRequest(question="Ce am analizat ultima oara?"), _=None
        )
        assert "Test SRL" in resp.answer, resp.answer
        assert "N/A" not in resp.answer, resp.answer
    finally:
        await test_db._db.close()
