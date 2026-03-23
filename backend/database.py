import aiosqlite
from pathlib import Path
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
        await self._db.execute("PRAGMA cache_size=-20000")
        await self._db.execute("PRAGMA mmap_size=268435456")
        await self._db.execute("PRAGMA temp_store=MEMORY")
        self._db.row_factory = aiosqlite.Row
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

    async def fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        cursor = await self.db.execute(sql, params)
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

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
        except Exception:
            pass  # Column already exists
        logger.info(f"Migrations complete ({len(migration_files)} files)")


db = Database(settings.database_path)
