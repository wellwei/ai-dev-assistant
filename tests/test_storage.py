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


def test_init_schema_adds_provenance_columns_idempotently(tmp_path):
    db_path = tmp_path / "project_index.sqlite"

    with connect_db(db_path) as conn:
        init_schema(conn)
        init_schema(conn)
        table_columns = {
            table: {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            for table in ["index_runs", "file_summaries", "symbols", "consistency_flags"]
        }

    assert "indexer_version" in table_columns["index_runs"]
    assert {
        "content_hash",
        "index_run_id",
        "indexer_version",
        "evidence_spans",
        "confidence_score",
        "confidence_reasons",
    }.issubset(table_columns["file_summaries"])
    assert {"content_hash", "index_run_id", "indexer_version", "body_hash", "evidence_preview"}.issubset(
        table_columns["symbols"]
    )
    assert {"content_hash", "index_run_id", "indexer_version"}.issubset(table_columns["consistency_flags"])


def test_init_schema_migrates_old_research_notes_before_creating_new_indexes(tmp_path):
    db_path = tmp_path / "project_index.sqlite"

    with connect_db(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE research_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                request_type TEXT NOT NULL,
                question TEXT NOT NULL,
                answer_summary TEXT NOT NULL,
                related_paths TEXT,
                open_questions TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
        init_schema(conn)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(research_notes)").fetchall()}
        index_row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND name = 'idx_research_notes_project_root'"
        ).fetchone()

    assert "project_root" in columns
    assert index_row is not None

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


def test_repository_records_provenance_and_detects_stale_indexer_version(tmp_path):
    from src.indexer.version import CURRENT_INDEXER_VERSION

    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()
    run_id = repo.start_run("/tmp/project")
    project_file = ProjectFile("src/a.cpp", "/tmp/project/src/a.cpp", "source", "cpp", 100, 12.5, "abc")
    summary = FileSummary(
        path="src/a.cpp",
        summary="Implements route state changes.",
        responsibilities="Route state management",
        key_points="mutates route context",
        dependencies="map_data",
        risks="naming may hide side effects",
        evidence="calls mutable_route_ctx",
        inconsistencies="none",
        confidence="medium",
    )
    symbol = SymbolInfo(
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

    repo.upsert_file(project_file)
    repo.upsert_summary(summary, content_hash="abc", run_id=run_id, indexer_version=CURRENT_INDEXER_VERSION)
    repo.replace_symbols("src/a.cpp", [symbol], content_hash="abc", run_id=run_id, indexer_version=CURRENT_INDEXER_VERSION)

    assert repo.needs_reindex(project_file, CURRENT_INDEXER_VERSION) is False
    assert repo.needs_reindex(project_file, "future-version") is True

    with connect_db(db_path) as conn:
        run = conn.execute("SELECT indexer_version FROM index_runs WHERE id = ?", (run_id,)).fetchone()
        summary_row = conn.execute(
            "SELECT content_hash, index_run_id, indexer_version FROM file_summaries WHERE path = ?", ("src/a.cpp",)
        ).fetchone()
        symbol_row = conn.execute(
            "SELECT content_hash, index_run_id, indexer_version FROM symbols WHERE path = ?", ("src/a.cpp",)
        ).fetchone()

    assert run["indexer_version"] == CURRENT_INDEXER_VERSION
    assert dict(summary_row) == {
        "content_hash": "abc",
        "index_run_id": run_id,
        "indexer_version": CURRENT_INDEXER_VERSION,
    }
    assert dict(symbol_row) == {
        "content_hash": "abc",
        "index_run_id": run_id,
        "indexer_version": CURRENT_INDEXER_VERSION,
    }


def test_repository_searches_research_notes_by_project_root_and_summary(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()
    note_id = repo.insert_research_note(
        ResearchNote(
            thread_id="thread-1",
            request_type="requirement_research",
            question="押镖路线风险在哪里？",
            answer_summary="历史结论：route risk is around recalc_route_main_work_handler.",
            related_paths='["src/route.cpp"]',
            open_questions="[]",
            project_root="/tmp/project-a",
            source_note_ids="[]",
            internal_memory_summary="Prior research found route recalculation risk in recalc_route_main_work_handler.",
            user_answer_summary="历史调研认为路线重算风险集中在 src/route.cpp。",
            confidence="medium",
        )
    )
    repo.insert_research_note(
        ResearchNote(
            thread_id="thread-2",
            request_type="requirement_research",
            question="other project route risk",
            answer_summary="other project",
            related_paths='["src/other.cpp"]',
            open_questions="[]",
            project_root="/tmp/project-b",
            source_note_ids="[]",
            internal_memory_summary="Other project route risk.",
            user_answer_summary="其他项目。",
            confidence="medium",
        )
    )

    hits = repo.search_research_notes("押镖 route risk", project_root="/tmp/project-a")

    assert [hit["id"] for hit in hits] == [note_id]
    assert hits[0]["source"] == "research_note"
    assert hits[0]["related_paths"] == ["src/route.cpp"]
