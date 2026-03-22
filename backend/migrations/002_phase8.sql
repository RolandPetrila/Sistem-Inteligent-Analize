-- Phase 8 Schema Extensions
-- Monitoring Audit Log (M9)
CREATE TABLE IF NOT EXISTS monitoring_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT REFERENCES monitoring_alerts(id),
    company_cui TEXT,
    company_name TEXT,
    change_type TEXT,
    old_value TEXT,
    new_value TEXT,
    severity TEXT DEFAULT 'INFO',
    triggered_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_audit_alert ON monitoring_audit(alert_id);
CREATE INDEX IF NOT EXISTS idx_audit_triggered ON monitoring_audit(triggered_at DESC);

-- Score History for Delta Scoring (M3)
CREATE TABLE IF NOT EXISTS score_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT REFERENCES companies(id),
    cui TEXT,
    numeric_score REAL,
    dimensions TEXT,
    factors TEXT,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_score_company ON score_history(company_id);
CREATE INDEX IF NOT EXISTS idx_score_cui ON score_history(cui);

-- Compare History (M7)
CREATE TABLE IF NOT EXISTS compare_history (
    id TEXT PRIMARY KEY,
    cui_list TEXT,
    result_data TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
