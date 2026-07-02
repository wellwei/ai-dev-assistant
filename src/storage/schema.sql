PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    abs_path TEXT NOT NULL,
    file_type TEXT NOT NULL,
    language TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    mtime REAL NOT NULL,
    content_hash TEXT NOT NULL,
    indexed_at TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS file_summaries (
    path TEXT PRIMARY KEY,
    summary TEXT NOT NULL,
    responsibilities TEXT,
    key_points TEXT,
    dependencies TEXT,
    risks TEXT,
    evidence TEXT,
    inconsistencies TEXT,
    confidence TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(path) REFERENCES files(path)
);

CREATE TABLE IF NOT EXISTS symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL,
    symbol_type TEXT NOT NULL,
    name TEXT NOT NULL,
    signature TEXT,
    line_start INTEGER,
    line_end INTEGER,
    summary TEXT,
    observed_behavior TEXT,
    side_effects TEXT,
    confidence TEXT,
    FOREIGN KEY(path) REFERENCES files(path)
);

CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
CREATE INDEX IF NOT EXISTS idx_symbols_path ON symbols(path);

CREATE TABLE IF NOT EXISTS doc_summaries (
    path TEXT PRIMARY KEY,
    title TEXT,
    summary TEXT NOT NULL,
    topics TEXT,
    mentioned_files TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(path) REFERENCES files(path)
);

CREATE TABLE IF NOT EXISTS research_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,
    request_type TEXT NOT NULL,
    question TEXT NOT NULL,
    answer_summary TEXT NOT NULL,
    related_paths TEXT,
    open_questions TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_research_notes_thread_id ON research_notes(thread_id);
CREATE INDEX IF NOT EXISTS idx_research_notes_request_type ON research_notes(request_type);

CREATE TABLE IF NOT EXISTS index_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_root TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    scanned_files INTEGER DEFAULT 0,
    changed_files INTEGER DEFAULT 0,
    summarized_files INTEGER DEFAULT 0,
    status TEXT NOT NULL,
    error TEXT
);

CREATE TABLE IF NOT EXISTS consistency_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL,
    line_start INTEGER,
    line_end INTEGER,
    flag_type TEXT NOT NULL,
    subject TEXT NOT NULL,
    claimed_behavior TEXT,
    observed_behavior TEXT NOT NULL,
    evidence TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(path) REFERENCES files(path)
);

CREATE INDEX IF NOT EXISTS idx_consistency_flags_path ON consistency_flags(path);
CREATE INDEX IF NOT EXISTS idx_consistency_flags_type ON consistency_flags(flag_type);
