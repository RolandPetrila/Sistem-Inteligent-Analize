"""
D1: Import ONRC dataset din data.gov.ro in SQLite local.
Dataset oficial (CC BY 4.0), actualizat lunar pe data.gov.ro.

Utilizare:
    python tools/import_onrc.py --active firme_active.csv
    python tools/import_onrc.py --radiate firme_radiate.csv
    python tools/import_onrc.py --url https://data.gov.ro/dataset/...

CSV-urile ONRC au header-uri variate. Scriptul detecteaza automat coloanele relevante.
"""

import argparse
import csv
import sqlite3
import sys
import time
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "ris.db"

# Mapare coloane ONRC CSV -> coloane DB (case-insensitive, partial match)
COLUMN_MAP = {
    "cui": ["cui", "cod_fiscal", "cod fiscal", "cif"],
    "denumire": ["denumire", "firma", "nume", "company_name", "den"],
    "caen": ["caen", "cod_caen", "cod caen", "caen_cod"],
    "judet": ["judet", "jud", "county"],
    "localitate": ["localitate", "oras", "loc", "city"],
    "data_inregistrare": ["data_inregistrare", "data inregistrare", "data_inreg", "date_registered"],
    "forma_juridica": ["forma_juridica", "forma juridica", "tip"],
    "cod_postal": ["cod_postal", "cod postal", "zip"],
}

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS onrc_companies (
    cui INTEGER PRIMARY KEY,
    denumire TEXT NOT NULL,
    caen TEXT,
    judet TEXT,
    localitate TEXT,
    data_inregistrare TEXT,
    status TEXT DEFAULT 'activ',
    forma_juridica TEXT,
    cod_postal TEXT,
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_onrc_cui ON onrc_companies(cui);
CREATE INDEX IF NOT EXISTS idx_onrc_denumire ON onrc_companies(denumire COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_onrc_caen ON onrc_companies(caen);
CREATE INDEX IF NOT EXISTS idx_onrc_judet ON onrc_companies(judet);
"""

BATCH_SIZE = 5000


def detect_columns(headers: list[str]) -> dict[str, int]:
    """Detecteaza automat coloanele relevante din header CSV."""
    mapping = {}
    lower_headers = [h.strip().lower() for h in headers]

    for db_col, variants in COLUMN_MAP.items():
        for variant in variants:
            for i, header in enumerate(lower_headers):
                if variant == header or variant in header:
                    mapping[db_col] = i
                    break
            if db_col in mapping:
                break

    return mapping


def import_csv(csv_path: str, db_path: str, status: str = "activ", encoding: str = "utf-8"):
    """Import CSV ONRC in SQLite cu batch inserts."""
    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"EROARE: Fisierul {csv_path} nu exista.")
        sys.exit(1)

    file_size_mb = csv_file.stat().st_size / (1024 * 1024)
    print(f"Import {csv_file.name} ({file_size_mb:.1f} MB) cu status='{status}'...")

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
    conn.executescript(CREATE_TABLE_SQL)

    inserted = 0
    skipped = 0
    start_time = time.time()

    # Detecteaza encoding si delimiter
    with open(csv_path, encoding=encoding, errors="replace") as f:
        # Citeste primele linii pentru a detecta delimitatorul
        sample = f.read(4096)
        f.seek(0)

        # Detecteaza delimiter (virgula sau punct-virgula)
        delimiter = ";" if sample.count(";") > sample.count(",") else ","

        reader = csv.reader(f, delimiter=delimiter)
        headers = next(reader)
        col_map = detect_columns(headers)

        if "cui" not in col_map or "denumire" not in col_map:
            print(f"EROARE: Nu pot detecta coloanele CUI si DENUMIRE din header: {headers[:10]}")
            print(f"Coloane detectate: {col_map}")
            conn.close()
            sys.exit(1)

        print(f"Coloane detectate: {col_map}")
        print(f"Delimiter: '{delimiter}'")

        batch = []
        for row_num, row in enumerate(reader, start=2):
            try:
                cui_val = row[col_map["cui"]].strip()
                # Extrage doar cifrele din CUI (poate avea 'RO' prefix)
                cui_digits = "".join(c for c in cui_val if c.isdigit())
                if not cui_digits:
                    skipped += 1
                    continue

                cui_int = int(cui_digits)
                denumire = row[col_map["denumire"]].strip() if "denumire" in col_map else ""
                if not denumire:
                    skipped += 1
                    continue

                caen = row[col_map["caen"]].strip() if "caen" in col_map and col_map["caen"] < len(row) else None
                judet = row[col_map["judet"]].strip() if "judet" in col_map and col_map["judet"] < len(row) else None
                localitate = row[col_map["localitate"]].strip() if "localitate" in col_map and col_map["localitate"] < len(row) else None
                data_inreg = row[col_map["data_inregistrare"]].strip() if "data_inregistrare" in col_map and col_map["data_inregistrare"] < len(row) else None
                forma = row[col_map["forma_juridica"]].strip() if "forma_juridica" in col_map and col_map["forma_juridica"] < len(row) else None
                cod_postal = row[col_map["cod_postal"]].strip() if "cod_postal" in col_map and col_map["cod_postal"] < len(row) else None

                batch.append((cui_int, denumire, caen, judet, localitate, data_inreg, status, forma, cod_postal))

                if len(batch) >= BATCH_SIZE:
                    conn.executemany(
                        """INSERT OR REPLACE INTO onrc_companies
                           (cui, denumire, caen, judet, localitate, data_inregistrare, status, forma_juridica, cod_postal)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        batch,
                    )
                    conn.commit()
                    inserted += len(batch)
                    elapsed = time.time() - start_time
                    rate = inserted / elapsed if elapsed > 0 else 0
                    print(f"  {inserted:>9,} importate ({rate:,.0f}/sec)...", end="\r")
                    batch = []

            except (IndexError, ValueError) as e:
                skipped += 1
                if skipped <= 5:
                    print(f"  Skip row {row_num}: {e}")
                continue

        # Insert remaining batch
        if batch:
            conn.executemany(
                """INSERT OR REPLACE INTO onrc_companies
                   (cui, denumire, caen, judet, localitate, data_inregistrare, status, forma_juridica, cod_postal)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                batch,
            )
            conn.commit()
            inserted += len(batch)

    elapsed = time.time() - start_time
    conn.close()

    print(f"\nDone! {inserted:,} firme importate, {skipped:,} skipped in {elapsed:.1f}s")
    print(f"Database: {db_path}")


def main():
    parser = argparse.ArgumentParser(description="Import ONRC dataset din data.gov.ro in RIS SQLite")
    parser.add_argument("csv_file", help="Cale catre fisierul CSV ONRC")
    parser.add_argument("--status", default="activ", choices=["activ", "radiat"],
                        help="Status firme: activ (default) sau radiat")
    parser.add_argument("--db", default=str(DB_PATH), help=f"Cale DB (default: {DB_PATH})")
    parser.add_argument("--encoding", default="utf-8", help="Encoding CSV (default: utf-8)")

    args = parser.parse_args()
    import_csv(args.csv_file, args.db, status=args.status, encoding=args.encoding)


if __name__ == "__main__":
    main()
