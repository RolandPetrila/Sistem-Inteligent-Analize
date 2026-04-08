from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite
from loguru import logger

from backend.config import settings

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA synchronous=NORMAL")
        await self._db.execute("PRAGMA busy_timeout=5000")
        await self._db.execute("PRAGMA foreign_keys=ON")
        await self._db.execute("PRAGMA cache_size=-64000")
        await self._db.execute("PRAGMA mmap_size=268435456")
        await self._db.execute("PRAGMA temp_store=MEMORY")
        self._db.row_factory = aiosqlite.Row
        # H3: Indexuri lipsă identificate în audit R16
        await self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_score_history_recorded ON score_history(recorded_at)"
        )
        await self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_reports_job_id ON reports(job_id)"
        )
        # Dynamic percentile scoring: stocheaza CA real per firma pentru percentile CAEN
        try:
            await self._db.execute(
                "ALTER TABLE companies ADD COLUMN latest_ca INTEGER DEFAULT NULL"
            )
            await self._db.execute(
                "CREATE INDEX IF NOT EXISTS idx_companies_caen_ca ON companies(caen_code, latest_ca)"
            )
        except Exception:
            pass  # Column/index already exists
        await self._db.commit()
        logger.info(f"Database connected: {self.db_path}")

    async def close(self):
        if self._db:
            await self._db.execute("PRAGMA optimize")
            await self._db.close()
            logger.info("Database closed")

    @property
    def db(self) -> aiosqlite.Connection:
        if not self._db:
            raise RuntimeError("Database not connected")
        return self._db

    async def execute(self, sql: str, params: tuple = ()) -> aiosqlite.Cursor:
        cursor = await self.db.execute(sql, params)
        await self.db.commit()
        return cursor

    @asynccontextmanager
    async def transaction(self):
        """Context manager for atomic multi-step DB operations."""
        try:
            yield self
            await self.db.commit()
        except Exception as e:
            logger.error(f"[db] Transaction rollback: {e}", exc_info=True)
            await self.db.rollback()
            raise

    async def fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        cursor = await self.db.execute(sql, params)
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def get_next_report_number(self) -> str:
        """A1: Genereaza numarul urmator in format RIS-YYYY-XXXX."""
        from datetime import UTC, datetime
        year = datetime.now(UTC).year
        await self.execute(
            "INSERT INTO report_sequences (year, last_seq) VALUES (?, 1) "
            "ON CONFLICT(year) DO UPDATE SET last_seq = last_seq + 1",
            (year,),
        )
        row = await self.fetch_one(
            "SELECT last_seq FROM report_sequences WHERE year = ?", (year,)
        )
        seq = row["last_seq"] if row else 1
        return f"RIS-{year}-{seq:04d}"

    async def fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        cursor = await self.db.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def run_migrations(self):
        migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        for mf in migration_files:
            logger.info(f"Running migration: {mf.name}")
            sql = mf.read_text(encoding="utf-8")
            await self.db.executescript(sql)
        # 10A M10.2: Add schema_version column to cache (safe — ignores if exists)
        try:
            await self.db.execute("ALTER TABLE data_cache ADD COLUMN schema_version INTEGER DEFAULT 1")
            await self.db.commit()
            logger.info("Migration: added schema_version to data_cache")
        except Exception as e:
            logger.debug(f"Migration column check (expected if exists): {e}")
        # Add is_favorite column to companies (safe — ignores if exists)
        try:
            await self.db.execute("ALTER TABLE companies ADD COLUMN is_favorite INTEGER DEFAULT 0")
            await self.db.commit()
            logger.info("Migration: added is_favorite to companies")
        except Exception as e:
            logger.debug(f"Migration column check (expected if exists): {e}")
        # FIX #17: Extinde report_deltas cu coloanele pentru delta endpoint
        for col_sql, col_name in [
            ("ALTER TABLE report_deltas ADD COLUMN report_id TEXT", "report_id"),
            ("ALTER TABLE report_deltas ADD COLUMN previous_report_id TEXT", "previous_report_id"),
            ("ALTER TABLE report_deltas ADD COLUMN company_id INTEGER", "company_id"),
            ("ALTER TABLE report_deltas ADD COLUMN previous_score INTEGER", "previous_score"),
            ("ALTER TABLE report_deltas ADD COLUMN current_score INTEGER", "current_score"),
            ("ALTER TABLE report_deltas ADD COLUMN changes_json TEXT", "changes_json"),
        ]:
            try:
                await self.db.execute(col_sql)
                await self.db.commit()
                logger.info(f"Migration: added {col_name} to report_deltas")
            except Exception as e:
                logger.debug(f"Migration column check report_deltas.{col_name} (expected if exists): {e}")
        # FIX #17: Index pe report_deltas.report_id
        try:
            await self.db.execute(
                "CREATE INDEX IF NOT EXISTS idx_report_deltas_report ON report_deltas(report_id)"
            )
            await self.db.commit()
        except Exception as e:
            logger.debug(f"Migration index report_deltas: {e}")
        # F3-3: Auto-reanalyze columns pe companies (safe ALTER TABLE)
        for col_sql, col_name in [
            ("ALTER TABLE companies ADD COLUMN auto_reanalyze_days INTEGER DEFAULT NULL", "auto_reanalyze_days"),
            ("ALTER TABLE companies ADD COLUMN next_reanalyze_at TEXT DEFAULT NULL", "next_reanalyze_at"),
            ("ALTER TABLE companies ADD COLUMN reanalyze_level INTEGER DEFAULT 2", "reanalyze_level"),
        ]:
            try:
                await self.db.execute(col_sql)
                await self.db.commit()
                logger.info(f"Migration: added {col_name} to companies")
            except Exception as e:
                logger.debug(f"Migration column check companies.{col_name} (expected if exists): {e}")
        # A1: Număr Raport Unic (RIS-YYYY-XXXX)
        try:
            await self.db.execute("ALTER TABLE reports ADD COLUMN report_number TEXT DEFAULT NULL")
            await self.db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_reports_number ON reports(report_number)")
            await self.db.commit()
            logger.info("Migration: added report_number to reports")
        except Exception as e:
            logger.debug(f"Migration column check reports.report_number (expected if exists): {e}")
        try:
            await self.db.execute(
                "CREATE TABLE IF NOT EXISTS report_sequences ("
                "year INTEGER PRIMARY KEY, last_seq INTEGER DEFAULT 0)"
            )
            await self.db.commit()
            logger.info("Migration: created report_sequences table")
        except Exception as e:
            logger.debug(f"Migration report_sequences (expected if exists): {e}")
        # B5: Share link pentru rapoarte HTML
        for col_sql, col_name in [
            ("ALTER TABLE reports ADD COLUMN share_token TEXT DEFAULT NULL", "share_token"),
            ("ALTER TABLE reports ADD COLUMN share_expires_at TEXT DEFAULT NULL", "share_expires_at"),
        ]:
            try:
                await self.db.execute(col_sql)
                await self.db.commit()
                logger.info(f"Migration: added {col_name} to reports")
            except Exception as e:
                logger.debug(f"Migration column check reports.{col_name} (expected if exists): {e}")
        try:
            await self.db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_reports_share_token ON reports(share_token)"
            )
            await self.db.commit()
        except Exception as e:
            logger.debug(f"Migration index reports.share_token (expected if exists): {e}")
        logger.info(f"Migrations complete ({len(migration_files)} files)")


db = Database(settings.database_path)
