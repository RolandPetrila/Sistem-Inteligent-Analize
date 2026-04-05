-- Migration 006: Composite indexes pentru performanta query-urilor
-- F5.5: Timeline + score history + monitoring queries 2-5x mai rapide

CREATE INDEX IF NOT EXISTS idx_score_company_date
ON score_history(company_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_reports_company_created
ON reports(company_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_monitoring_company_created
ON monitoring_audit(company_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_jobs_type_status
ON jobs(type, status);

CREATE INDEX IF NOT EXISTS idx_jobs_created_at
ON jobs(created_at DESC);
