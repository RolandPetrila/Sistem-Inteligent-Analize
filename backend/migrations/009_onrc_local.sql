-- Migration 009: ONRC Dataset Local (D1)
-- Tabel pentru dataset ONRC din data.gov.ro (CC BY 4.0), actualizat lunar.
-- Eliminä dependenta de limita 100 req/lunä openapi.ro pentru câmpurile de bazä.

CREATE TABLE IF NOT EXISTS onrc_companies (
    cui INTEGER PRIMARY KEY,
    denumire TEXT NOT NULL,
    caen TEXT,
    judet TEXT,
    localitate TEXT,
    data_inregistrare TEXT,
    status TEXT DEFAULT 'activ',   -- activ / radiat
    forma_juridica TEXT,
    cod_postal TEXT,
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_onrc_cui ON onrc_companies(cui);
CREATE INDEX IF NOT EXISTS idx_onrc_denumire ON onrc_companies(denumire COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_onrc_caen ON onrc_companies(caen);
CREATE INDEX IF NOT EXISTS idx_onrc_judet ON onrc_companies(judet);
