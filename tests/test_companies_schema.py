"""
F26 (fortify): regression guard for the F1 schema-drift class.

backend/routers/companies.py SELECTs/filters/sorts on a fixed set of `companies`
columns. The existing router tests (test_routers.py) MOCK the DB, so a column the
code references but no migration creates still passes the suite while the live
endpoint 500s — exactly what happened with is_active / risk_score / tag / note.

This test runs the REAL run_migrations() on a fresh temp DB and executes every
query shape used by the companies router, so any future phantom column fails CI.
"""
import aiosqlite
import pytest

from backend.database import Database
from backend.routers.companies import VALID_RISK_SCORES, VALID_SORT_COLS

# Mirrors the projection in list_companies / get_company / list_favorites.
_COMPANIES_SELECT = (
    "SELECT id, cui, name, caen_code, county, is_active, is_favorite, "
    "last_analyzed_at, risk_score FROM companies"
)


@pytest.mark.asyncio
async def test_companies_router_queries_resolve_against_real_schema(tmp_path):
    db = Database(str(tmp_path / "ris_test.db"))
    # Open the connection directly (bypass connect()'s index pre-creation) so
    # run_migrations() builds the full schema first.
    db._db = await aiosqlite.connect(db.db_path)
    db._db.row_factory = aiosqlite.Row
    try:
        await db.run_migrations()
        await db.execute(
            "INSERT INTO companies (id, cui, name) VALUES ('t1', '123', 'Test SRL')"
        )

        # list / favorites / detail projections must all resolve
        await db.fetch_all(f"{_COMPANIES_SELECT} WHERE is_favorite = 1 LIMIT 500")
        await db.fetch_all(
            f"{_COMPANIES_SELECT} ORDER BY last_analyzed_at DESC LIMIT 20 OFFSET 0"
        )
        await db.fetch_one(f"{_COMPANIES_SELECT} WHERE id = ?", ("t1",))

        # every VALID_SORT_COLS ORDER BY expression must be a valid sort
        for expr in VALID_SORT_COLS.values():
            await db.fetch_all(f"SELECT id FROM companies ORDER BY {expr} LIMIT 1")

        # the risk_score filter column must exist
        for color in VALID_RISK_SCORES:
            await db.fetch_all(
                "SELECT id FROM companies WHERE risk_score = ?", (color,)
            )
    finally:
        await db._db.close()
