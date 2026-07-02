import sqlite3

from src.storage.sqlite import connect_db, init_schema


EXPECTED_TABLES = {
    "files",
    "file_summaries",
    "symbols",
    "doc_summaries",
    "research_notes",
    "index_runs",
    "consistency_flags",
}


def test_init_schema_creates_project_index_tables(tmp_path):
    db_path = tmp_path / "nested" / "project_index.sqlite"

    with connect_db(db_path) as conn:
        init_schema(conn)
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()

    table_names = {row[0] for row in rows}
    assert EXPECTED_TABLES.issubset(table_names)


def test_connection_uses_row_factory(tmp_path):
    db_path = tmp_path / "project_index.sqlite"

    with connect_db(db_path) as conn:
        init_schema(conn)
        conn.execute(
            "INSERT INTO files(path, abs_path, file_type, language, size_bytes, mtime, content_hash, indexed_at, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)",
            ("src/a.cpp", "/tmp/src/a.cpp", "source", "cpp", 10, 1.0, "hash", "active"),
        )
        row = conn.execute("SELECT path FROM files WHERE path = ?", ("src/a.cpp",)).fetchone()

    assert isinstance(row, sqlite3.Row)
    assert row["path"] == "src/a.cpp"
