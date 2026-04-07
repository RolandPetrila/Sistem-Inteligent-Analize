-- Migration 008: Company network & administrators tracking
-- Phase R6 F1-2: SQL table for openapi.ro company administrators/associates

CREATE TABLE IF NOT EXISTS company_administrators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cui TEXT NOT NULL,
    company_name TEXT,
    person_name TEXT NOT NULL,
    role TEXT,
    ownership_pct REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_admin_person ON company_administrators(person_name);
CREATE INDEX IF NOT EXISTS idx_admin_cui ON company_administrators(cui);
CREATE UNIQUE INDEX IF NOT EXISTS idx_admin_unique ON company_administrators(cui, person_name, role);

-- Alert suppression for monitoring (F4-4)
ALTER TABLE monitoring_alerts ADD COLUMN suppressed_until TIMESTAMP DEFAULT NULL;
ALTER TABLE monitoring_alerts ADD COLUMN suppress_reason TEXT DEFAULT NULL;
