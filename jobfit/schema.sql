CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    cv_filename TEXT,
    cv_pdf BLOB,
    cv_text TEXT,
    preferences TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    error_message TEXT,
    report_markdown TEXT,
    model_name TEXT,
    log_text TEXT
);

CREATE TABLE IF NOT EXISTS job_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(id),
    rank INTEGER,
    title TEXT,
    company TEXT,
    url TEXT,
    fit_score INTEGER,
    apply_decision TEXT,
    rationale TEXT,
    is_rejected INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_job_entries_run_id ON job_entries(run_id);
