-- Phase 10 Schema: Cache versioning + Scheduler checkpoints + Job checkpoints

-- Scheduler state persistence (M9.3)
CREATE TABLE IF NOT EXISTS scheduler_state (
    key TEXT PRIMARY KEY,
    last_run DATETIME,
    run_count INTEGER DEFAULT 0,
    last_status TEXT
);

-- 10F M5.4: Job checkpoints for crash recovery
CREATE TABLE IF NOT EXISTS job_checkpoints (
    job_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    state_data TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (job_id, agent_name)
);
