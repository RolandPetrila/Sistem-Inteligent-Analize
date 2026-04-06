-- Tags per companie
CREATE TABLE IF NOT EXISTS company_tags (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    tag TEXT NOT NULL CHECK(length(tag) <= 30),
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(company_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_company_tags_company ON company_tags(company_id);

-- Note per companie (una singura per companie)
CREATE TABLE IF NOT EXISTS company_notes (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    company_id TEXT NOT NULL UNIQUE REFERENCES companies(id) ON DELETE CASCADE,
    note TEXT NOT NULL CHECK(length(note) <= 2000),
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Compare templates
CREATE TABLE IF NOT EXISTS compare_templates (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    name TEXT NOT NULL CHECK(length(name) <= 50),
    cuis TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
