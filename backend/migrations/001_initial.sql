-- RIS Initial Schema
-- Jobs
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    input_data TEXT,
    report_level INTEGER DEFAULT 2,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME,
    error_message TEXT,
    progress_percent INTEGER DEFAULT 0,
    current_step TEXT,
    checkpoint_data TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC);

-- Companies
CREATE TABLE IF NOT EXISTS companies (
    id TEXT PRIMARY KEY,
    cui TEXT UNIQUE,
    name TEXT NOT NULL,
    caen_code TEXT,
    caen_description TEXT,
    county TEXT,
    city TEXT,
    first_analyzed_at DATETIME,
    last_analyzed_at DATETIME,
    analysis_count INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_companies_cui ON companies(cui);
CREATE INDEX IF NOT EXISTS idx_companies_caen ON companies(caen_code);
CREATE INDEX IF NOT EXISTS idx_companies_county ON companies(county);

-- Reports
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    job_id TEXT REFERENCES jobs(id),
    company_id TEXT REFERENCES companies(id),
    report_type TEXT,
    report_level INTEGER,
    title TEXT,
    summary TEXT,
    full_data TEXT,
    risk_score TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    pdf_path TEXT,
    docx_path TEXT,
    excel_path TEXT,
    html_path TEXT,
    pptx_path TEXT
);
CREATE INDEX IF NOT EXISTS idx_reports_company ON reports(company_id);
CREATE INDEX IF NOT EXISTS idx_reports_type ON reports(report_type);
CREATE INDEX IF NOT EXISTS idx_reports_created ON reports(created_at DESC);

-- Report Sources
CREATE TABLE IF NOT EXISTS report_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT REFERENCES reports(id),
    source_name TEXT,
    source_url TEXT,
    accessed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT,
    data_found BOOLEAN,
    response_time_ms INTEGER
);
CREATE INDEX IF NOT EXISTS idx_sources_report ON report_sources(report_id);

-- Markets
CREATE TABLE IF NOT EXISTS markets (
    id TEXT PRIMARY KEY,
    caen_code TEXT,
    description TEXT,
    county TEXT,
    last_analyzed_at DATETIME,
    competitor_count INTEGER,
    analysis_count INTEGER DEFAULT 0
);

-- Monitoring Alerts (Faza 5)
CREATE TABLE IF NOT EXISTS monitoring_alerts (
    id TEXT PRIMARY KEY,
    company_id TEXT REFERENCES companies(id),
    alert_type TEXT,
    is_active BOOLEAN DEFAULT 1,
    check_frequency TEXT,
    last_checked_at DATETIME,
    telegram_notify BOOLEAN DEFAULT 1
);

-- Report Deltas
CREATE TABLE IF NOT EXISTS report_deltas (
    id TEXT PRIMARY KEY,
    report_id_new TEXT REFERENCES reports(id),
    report_id_old TEXT REFERENCES reports(id),
    delta_summary TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Data Cache
CREATE TABLE IF NOT EXISTS data_cache (
    cache_key TEXT PRIMARY KEY,
    data TEXT,
    source TEXT,
    cached_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME
);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON data_cache(expires_at);
