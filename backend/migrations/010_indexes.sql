-- FORTIFY F11/F12: indexes for full-scan hotspots
-- F11: risk-movers filters score_history.recorded_at globally (-30d); only composite (company_id, recorded_at) existed
CREATE INDEX IF NOT EXISTS idx_score_recorded ON score_history(recorded_at DESC);
-- F12: public share-link lookup WHERE share_token=? had no index (unauth full-scan of reports)
CREATE INDEX IF NOT EXISTS idx_reports_share_token ON reports(share_token) WHERE share_token IS NOT NULL;
