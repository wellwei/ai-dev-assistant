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

from src.indexer.models import (
    ConsistencyFlag,
    FileSummary,
    ProjectFile,
    ResearchNote,
    SymbolInfo,
)
from src.storage.project_index import ProjectIndexRepository


def test_repository_upserts_file_summary_symbols_flags_and_notes(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()

    run_id = repo.start_run("/tmp/project")
    assert isinstance(run_id, int)

    project_file = ProjectFile(
        path="src/a.cpp",
        abs_path="/tmp/project/src/a.cpp",
        file_type="source",
        language="cpp",
        size_bytes=100,
        mtime=12.5,
        content_hash="abc",
        status="active",
    )
    repo.upsert_file(project_file)

    summary = FileSummary(
        path="src/a.cpp",
        summary="Implements route state changes.",
        responsibilities="Route state management",
        key_points="mutates route context",
        dependencies="map_data",
        risks="naming may hide side effects",
        evidence="calls mutable_route_ctx",
        inconsistencies="query-like name mutates state",
        confidence="medium",
    )
    repo.upsert_summary(summary)

    symbols = [
        SymbolInfo(
            path="src/a.cpp",
            symbol_type="function",
            name="query_route",
            signature="int query_route(Context* ctx)",
            line_start=10,
            line_end=20,
            summary="Queries and mutates route state.",
            observed_behavior="updates ctx route fields",
            side_effects="state_write",
            confidence="medium",
        )
    ]
    repo.replace_symbols("src/a.cpp", symbols)

    flags = [
        ConsistencyFlag(
            path="src/a.cpp",
            line_start=10,
            line_end=20,
            flag_type="side_effect_hidden",
            subject="query_route",
            claimed_behavior="query route",
            observed_behavior="updates ctx route fields",
            evidence="signature and body contain mutable_route_ctx",
            severity="warning",
            status="open",
        )
    ]
    repo.replace_consistency_flags("src/a.cpp", flags)

    note_id = repo.insert_research_note(
        ResearchNote(
            thread_id="thread-1",
            request_type="project_qa",
            question="route在哪",
            answer_summary="src/a.cpp has route logic",
            related_paths='["src/a.cpp"]',
            open_questions="[]",
        )
    )
    repo.finish_run(run_id, "success", 1, 1, 1)

    with connect_db(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM files").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM file_summaries").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM symbols").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM consistency_flags").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM research_notes").fetchone()[0] == 1
        assert conn.execute("SELECT status FROM index_runs WHERE id = ?", (run_id,)).fetchone()[0] == "success"
        assert note_id == 1
