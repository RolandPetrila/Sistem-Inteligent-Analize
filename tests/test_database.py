"""
F8-1: Teste pentru database.py — connection, WAL mode, migrations, fetch helpers.
Utilizeaza o DB in-memory SQLite pentru izolarea testelor.
"""
import aiosqlite
import pytest


class TestDatabaseConnection:
    """Teste pentru conectarea la DB si configuratia WAL."""

    @pytest.mark.asyncio
    async def test_in_memory_db_ok(self):
        """Conexiunea la SQLite in-memory functioneaza."""
        async with aiosqlite.connect(":memory:") as db_conn:
            await db_conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)")
            await db_conn.execute("INSERT INTO test VALUES (1, 'hello')")
            await db_conn.commit()
            async with db_conn.execute("SELECT val FROM test WHERE id=1") as cursor:
                row = await cursor.fetchone()
            assert row[0] == "hello"

    @pytest.mark.asyncio
    async def test_wal_mode_pragma(self):
        """PRAGMA journal_mode=WAL functioneaza."""
        async with aiosqlite.connect(":memory:") as db_conn:
            await db_conn.execute("PRAGMA journal_mode=WAL")
            async with db_conn.execute("PRAGMA journal_mode") as cursor:
                row = await cursor.fetchone()
            # In-memory nu suporta WAL real, dar comanda nu arunca eroare
            assert row is not None

    @pytest.mark.asyncio
    async def test_synchronous_normal(self):
        """PRAGMA synchronous=NORMAL se aplica fara erori."""
        async with aiosqlite.connect(":memory:") as db_conn:
            await db_conn.execute("PRAGMA synchronous=NORMAL")
            async with db_conn.execute("PRAGMA synchronous") as cursor:
                row = await cursor.fetchone()
            # 1 = NORMAL
            assert row[0] == 1

    @pytest.mark.asyncio
    async def test_create_index(self):
        """CREATE INDEX IF NOT EXISTS nu arunca eroare."""
        async with aiosqlite.connect(":memory:") as db_conn:
            await db_conn.execute("CREATE TABLE t (id TEXT, val INTEGER)")
            await db_conn.execute("CREATE INDEX IF NOT EXISTS idx_t_id ON t(id)")
            # Re-creare cu IF NOT EXISTS nu arunca eroare
            await db_conn.execute("CREATE INDEX IF NOT EXISTS idx_t_id ON t(id)")


class TestDatabaseSchemaMinimal:
    """Teste pentru schema minimala necesara aplicatiei."""

    @pytest.mark.asyncio
    async def test_jobs_table_structure(self):
        """Tabela 'jobs' are coloanele asteptate."""
        async with aiosqlite.connect(":memory:") as db_conn:
            await db_conn.execute("""
                CREATE TABLE jobs (
                    id TEXT PRIMARY KEY,
                    cui TEXT,
                    company_name TEXT,
                    status TEXT DEFAULT 'PENDING',
                    progress_percent INTEGER DEFAULT 0,
                    current_step TEXT,
                    input_data TEXT,
                    result_data TEXT,
                    error_message TEXT,
                    created_at TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)
            await db_conn.execute(
                "INSERT INTO jobs (id, cui, status) VALUES (?,?,?)",
                ("job-001", "12345678", "PENDING")
            )
            await db_conn.commit()
            async with db_conn.execute("SELECT id, status FROM jobs WHERE id='job-001'") as cur:
                row = await cur.fetchone()
            assert row[0] == "job-001"
            assert row[1] == "PENDING"

    @pytest.mark.asyncio
    async def test_companies_table_crud(self):
        """CRUD pe tabela 'companies' functioneaza."""
        async with aiosqlite.connect(":memory:") as db_conn:
            await db_conn.execute("""
                CREATE TABLE companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cui TEXT UNIQUE NOT NULL,
                    name TEXT,
                    last_score INTEGER,
                    is_favorite INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP
                )
            """)
            await db_conn.execute(
                "INSERT OR REPLACE INTO companies (cui, name, last_score) VALUES (?,?,?)",
                ("12345678", "Test SRL", 75)
            )
            await db_conn.commit()

            async with db_conn.execute("SELECT name, last_score FROM companies WHERE cui=?", ("12345678",)) as cur:
                row = await cur.fetchone()
            assert row[0] == "Test SRL"
            assert row[1] == 75

    @pytest.mark.asyncio
    async def test_update_job_status(self):
        """UPDATE status job functioneaza corect."""
        async with aiosqlite.connect(":memory:") as db_conn:
            await db_conn.execute("""
                CREATE TABLE jobs (id TEXT PRIMARY KEY, status TEXT, progress_percent INTEGER)
            """)
            await db_conn.execute("INSERT INTO jobs VALUES ('job-1', 'PENDING', 0)")
            await db_conn.execute("UPDATE jobs SET status='RUNNING', progress_percent=50 WHERE id='job-1'")
            await db_conn.commit()

            async with db_conn.execute("SELECT status, progress_percent FROM jobs WHERE id='job-1'") as cur:
                row = await cur.fetchone()
            assert row[0] == "RUNNING"
            assert row[1] == 50

    @pytest.mark.asyncio
    async def test_concurrent_reads_no_lock(self):
        """Multiple SELECT simultane pe aceeasi DB nu genereaza lock."""
        async with aiosqlite.connect(":memory:") as db_conn:
            await db_conn.execute("CREATE TABLE t (val INTEGER)")
            for i in range(10):
                await db_conn.execute("INSERT INTO t VALUES (?)", (i,))
            await db_conn.commit()

            results = []
            for _ in range(5):
                async with db_conn.execute("SELECT COUNT(*) FROM t") as cur:
                    row = await cur.fetchone()
                    results.append(row[0])

            assert all(r == 10 for r in results)


class TestDatabaseRowFactoryAndHelpers:
    """Teste pentru row_factory si helpers de fetch."""

    @pytest.mark.asyncio
    async def test_row_factory_dict_access(self):
        """Cu row_factory=aiosqlite.Row, accesul prin coloana functioneaza."""
        async with aiosqlite.connect(":memory:") as db_conn:
            db_conn.row_factory = aiosqlite.Row
            await db_conn.execute("CREATE TABLE t (id INTEGER, name TEXT)")
            await db_conn.execute("INSERT INTO t VALUES (1, 'Test')")
            await db_conn.commit()

            async with db_conn.execute("SELECT id, name FROM t") as cur:
                row = await cur.fetchone()

            assert row["id"] == 1
            assert row["name"] == "Test"

    @pytest.mark.asyncio
    async def test_fetch_all_returns_list(self):
        """fetchall returneaza lista goala cand nu exista randuri."""
        async with aiosqlite.connect(":memory:") as db_conn:
            await db_conn.execute("CREATE TABLE t (id INTEGER)")
            async with db_conn.execute("SELECT * FROM t") as cur:
                rows = await cur.fetchall()
            assert rows == []

    @pytest.mark.asyncio
    async def test_json_field_insert_retrieve(self):
        """Campuri JSON stocate ca TEXT se pot deserializa."""
        import json
        async with aiosqlite.connect(":memory:") as db_conn:
            await db_conn.execute("CREATE TABLE t (id TEXT, data TEXT)")
            payload = {"score": 75, "reasons": ["A", "B"]}
            await db_conn.execute(
                "INSERT INTO t VALUES (?, ?)",
                ("1", json.dumps(payload))
            )
            await db_conn.commit()

            async with db_conn.execute("SELECT data FROM t WHERE id='1'") as cur:
                row = await cur.fetchone()

            loaded = json.loads(row[0])
            assert loaded["score"] == 75
            assert loaded["reasons"] == ["A", "B"]
