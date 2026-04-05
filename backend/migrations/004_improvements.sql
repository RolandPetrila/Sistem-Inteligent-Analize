-- Phase improvements: notifications, favorites, provider_health
CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    type TEXT NOT NULL DEFAULT 'info',
    title TEXT NOT NULL,
    message TEXT,
    link TEXT,
    severity TEXT DEFAULT 'info',
    read_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_notif_unread ON notifications(read_at) WHERE read_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_notif_created ON notifications(created_at);

-- Favorites column on companies
-- Note: ALTER TABLE ADD COLUMN is safe in SQLite (ignores if exists via try/catch in Python)

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_score_history_company
    ON score_history(company_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_jobs_type_status
    ON jobs(type, status);

CREATE INDEX IF NOT EXISTS idx_jobs_created_at
    ON jobs(created_at DESC);
