import sqlite3


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    if column not in _columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def apply_migrations(conn: sqlite3.Connection) -> None:
    _add_column_if_missing(conn, "index_runs", "indexer_version", "TEXT NOT NULL DEFAULT 'unknown'")

    _add_column_if_missing(conn, "file_summaries", "content_hash", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "file_summaries", "index_run_id", "INTEGER")
    _add_column_if_missing(conn, "file_summaries", "indexer_version", "TEXT NOT NULL DEFAULT 'unknown'")
    _add_column_if_missing(conn, "file_summaries", "evidence_spans", "TEXT NOT NULL DEFAULT '[]'")
    _add_column_if_missing(conn, "file_summaries", "confidence_score", "REAL NOT NULL DEFAULT 0.0")
    _add_column_if_missing(conn, "file_summaries", "confidence_reasons", "TEXT NOT NULL DEFAULT '[]'")

    _add_column_if_missing(conn, "symbols", "content_hash", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "symbols", "index_run_id", "INTEGER")
    _add_column_if_missing(conn, "symbols", "indexer_version", "TEXT NOT NULL DEFAULT 'unknown'")
    _add_column_if_missing(conn, "symbols", "body_hash", "TEXT")
    _add_column_if_missing(conn, "symbols", "evidence_preview", "TEXT")

    _add_column_if_missing(conn, "consistency_flags", "content_hash", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "consistency_flags", "index_run_id", "INTEGER")
    _add_column_if_missing(conn, "consistency_flags", "indexer_version", "TEXT NOT NULL DEFAULT 'unknown'")

    _add_column_if_missing(conn, "research_notes", "project_root", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "research_notes", "source_note_ids", "TEXT NOT NULL DEFAULT '[]'")
    _add_column_if_missing(conn, "research_notes", "internal_memory_summary", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "research_notes", "user_answer_summary", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_missing(conn, "research_notes", "confidence", "TEXT NOT NULL DEFAULT 'low'")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_file_summaries_provenance ON file_summaries(path, content_hash, indexer_version)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_symbols_provenance ON symbols(path, content_hash, indexer_version)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_consistency_flags_provenance ON consistency_flags(path, content_hash, indexer_version)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_research_notes_project_root ON research_notes(project_root)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_research_notes_created_at ON research_notes(created_at)")
    conn.execute(
        """
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
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_improvement_proposals_status ON improvement_proposals(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_improvement_proposals_type ON improvement_proposals(proposal_type)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_root TEXT NOT NULL DEFAULT '',
            memory_type TEXT NOT NULL,
            subject TEXT NOT NULL,
            summary TEXT NOT NULL,
            evidence_refs TEXT NOT NULL DEFAULT '[]',
            related_paths TEXT NOT NULL DEFAULT '[]',
            source_note_ids TEXT NOT NULL DEFAULT '[]',
            confidence TEXT NOT NULL DEFAULT 'low',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            flow_version TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_memories_project_root ON project_memories(project_root)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_memories_type ON project_memories(memory_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_memories_status ON project_memories(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_memories_updated_at ON project_memories(updated_at)")
    conn.execute(
        """
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
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_source ON embeddings(source_type, source_id, embedding_model)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_path ON embeddings(source_path)")
