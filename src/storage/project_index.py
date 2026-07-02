from pathlib import Path
from typing import Iterable

from src.indexer.models import (
    ConsistencyFlag,
    FileSummary,
    ProjectFile,
    ResearchNote,
    SymbolInfo,
)
from src.storage.sqlite import connect_db, init_schema


class ProjectIndexRepository:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path).expanduser()

    def init(self) -> None:
        with connect_db(self.db_path) as conn:
            init_schema(conn)

    def start_run(self, project_root: str) -> int:
        with connect_db(self.db_path) as conn:
            init_schema(conn)
            cur = conn.execute(
                "INSERT INTO index_runs(project_root, started_at, status) VALUES (?, datetime('now'), ?)",
                (project_root, "running"),
            )
            conn.commit()
            return int(cur.lastrowid)

    def finish_run(
        self,
        run_id: int,
        status: str,
        scanned_files: int,
        changed_files: int,
        summarized_files: int,
        error: str | None = None,
    ) -> None:
        with connect_db(self.db_path) as conn:
            conn.execute(
                """
                UPDATE index_runs
                SET finished_at = datetime('now'),
                    scanned_files = ?,
                    changed_files = ?,
                    summarized_files = ?,
                    status = ?,
                    error = ?
                WHERE id = ?
                """,
                (scanned_files, changed_files, summarized_files, status, error, run_id),
            )
            conn.commit()

    def upsert_file(self, file: ProjectFile) -> None:
        with connect_db(self.db_path) as conn:
            init_schema(conn)
            conn.execute(
                """
                INSERT INTO files(path, abs_path, file_type, language, size_bytes, mtime, content_hash, indexed_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
                ON CONFLICT(path) DO UPDATE SET
                    abs_path = excluded.abs_path,
                    file_type = excluded.file_type,
                    language = excluded.language,
                    size_bytes = excluded.size_bytes,
                    mtime = excluded.mtime,
                    content_hash = excluded.content_hash,
                    indexed_at = excluded.indexed_at,
                    status = excluded.status
                """,
                (file.path, file.abs_path, file.file_type, file.language, file.size_bytes, file.mtime, file.content_hash, file.status),
            )
            conn.commit()

    def get_file(self, path: str):
        with connect_db(self.db_path) as conn:
            init_schema(conn)
            return conn.execute("SELECT * FROM files WHERE path = ?", (path,)).fetchone()

    def mark_deleted_missing_paths(self, active_paths: Iterable[str]) -> None:
        active = set(active_paths)
        with connect_db(self.db_path) as conn:
            init_schema(conn)
            rows = conn.execute("SELECT path FROM files WHERE status = 'active'").fetchall()
            for row in rows:
                if row["path"] not in active:
                    conn.execute("UPDATE files SET status = 'deleted' WHERE path = ?", (row["path"],))
            conn.commit()

    def upsert_summary(self, summary: FileSummary) -> None:
        with connect_db(self.db_path) as conn:
            init_schema(conn)
            conn.execute(
                """
                INSERT INTO file_summaries(
                    path, summary, responsibilities, key_points, dependencies, risks,
                    evidence, inconsistencies, confidence, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(path) DO UPDATE SET
                    summary = excluded.summary,
                    responsibilities = excluded.responsibilities,
                    key_points = excluded.key_points,
                    dependencies = excluded.dependencies,
                    risks = excluded.risks,
                    evidence = excluded.evidence,
                    inconsistencies = excluded.inconsistencies,
                    confidence = excluded.confidence,
                    updated_at = excluded.updated_at
                """,
                (summary.path, summary.summary, summary.responsibilities, summary.key_points, summary.dependencies, summary.risks, summary.evidence, summary.inconsistencies, summary.confidence),
            )
            conn.commit()

    def replace_symbols(self, path: str, symbols: list[SymbolInfo]) -> None:
        with connect_db(self.db_path) as conn:
            init_schema(conn)
            conn.execute("DELETE FROM symbols WHERE path = ?", (path,))
            conn.executemany(
                """
                INSERT INTO symbols(
                    path, symbol_type, name, signature, line_start, line_end,
                    summary, observed_behavior, side_effects, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [(s.path, s.symbol_type, s.name, s.signature, s.line_start, s.line_end, s.summary, s.observed_behavior, s.side_effects, s.confidence) for s in symbols],
            )
            conn.commit()

    def replace_consistency_flags(self, path: str, flags: list[ConsistencyFlag]) -> None:
        with connect_db(self.db_path) as conn:
            init_schema(conn)
            conn.execute("DELETE FROM consistency_flags WHERE path = ?", (path,))
            conn.executemany(
                """
                INSERT INTO consistency_flags(
                    path, line_start, line_end, flag_type, subject, claimed_behavior,
                    observed_behavior, evidence, severity, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                [(f.path, f.line_start, f.line_end, f.flag_type, f.subject, f.claimed_behavior, f.observed_behavior, f.evidence, f.severity, f.status) for f in flags],
            )
            conn.commit()

    def insert_research_note(self, note: ResearchNote) -> int:
        with connect_db(self.db_path) as conn:
            init_schema(conn)
            cur = conn.execute(
                """
                INSERT INTO research_notes(
                    thread_id, request_type, question, answer_summary,
                    related_paths, open_questions, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (note.thread_id, note.request_type, note.question, note.answer_summary, note.related_paths, note.open_questions),
            )
            conn.commit()
            return int(cur.lastrowid)
