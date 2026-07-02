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
    content_hash TEXT NOT NULL DEFAULT '',
    index_run_id INTEGER,
    indexer_version TEXT NOT NULL DEFAULT 'unknown',
    evidence_spans TEXT NOT NULL DEFAULT '[]',
    confidence_score REAL NOT NULL DEFAULT 0.0,
    confidence_reasons TEXT NOT NULL DEFAULT '[]',
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
    content_hash TEXT NOT NULL DEFAULT '',
    index_run_id INTEGER,
    indexer_version TEXT NOT NULL DEFAULT 'unknown',
    body_hash TEXT,
    evidence_preview TEXT,
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
    created_at TEXT NOT NULL,
    project_root TEXT NOT NULL DEFAULT '',
    source_note_ids TEXT NOT NULL DEFAULT '[]',
    internal_memory_summary TEXT NOT NULL DEFAULT '',
    user_answer_summary TEXT NOT NULL DEFAULT '',
    confidence TEXT NOT NULL DEFAULT 'low'
);

CREATE INDEX IF NOT EXISTS idx_research_notes_thread_id ON research_notes(thread_id);
CREATE INDEX IF NOT EXISTS idx_research_notes_request_type ON research_notes(request_type);

CREATE TABLE IF NOT EXISTS improvement_proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proposal_type TEXT NOT NULL,
    source_note_ids TEXT NOT NULL DEFAULT '[]',
    target_component TEXT NOT NULL,
    proposed_change TEXT NOT NULL,
    rationale TEXT NOT NULL,
    evidence TEXT NOT NULL,
    risk TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    applied_at TEXT,
    flow_version TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_improvement_proposals_status ON improvement_proposals(status);
CREATE INDEX IF NOT EXISTS idx_improvement_proposals_type ON improvement_proposals(proposal_type);

CREATE TABLE IF NOT EXISTS index_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_root TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    scanned_files INTEGER DEFAULT 0,
    changed_files INTEGER DEFAULT 0,
    summarized_files INTEGER DEFAULT 0,
    status TEXT NOT NULL,
    error TEXT,
    indexer_version TEXT NOT NULL DEFAULT 'unknown'
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
    content_hash TEXT NOT NULL DEFAULT '',
    index_run_id INTEGER,
    indexer_version TEXT NOT NULL DEFAULT 'unknown',
    FOREIGN KEY(path) REFERENCES files(path)
);

CREATE TABLE IF NOT EXISTS embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_path TEXT,
    source_hash TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_dim INTEGER NOT NULL,
    embedding_text_hash TEXT NOT NULL,
    vector TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(source_type, source_id, embedding_model)
);

CREATE INDEX IF NOT EXISTS idx_consistency_flags_path ON consistency_flags(path);
CREATE INDEX IF NOT EXISTS idx_consistency_flags_type ON consistency_flags(flag_type);
