import json
from pathlib import Path
import re
from typing import Iterable

from src.indexer.models import (
    ConsistencyFlag,
    FileSummary,
    ImprovementProposal,
    ProjectFile,
    ResearchNote,
    SymbolInfo,
)
from src.indexer.version import CURRENT_INDEXER_VERSION
from src.storage.sqlite import connect_db, init_schema


def _tokens(query: str) -> list[str]:
    raw_tokens = [token.lower() for token in re.findall(r"[\w一-鿿]+", query) if token.strip()]
    expanded = list(raw_tokens)
    synonym_map = {
        "路线": ["route"],
        "重算": ["recalc", "recalculation"],
        "押镖": ["escort"],
        "风险": ["risk"],
        "调研": ["research"],
        "记忆": ["memory"],
    }
    for token in raw_tokens:
        for key, synonyms in synonym_map.items():
            if key in token:
                expanded.extend(synonyms)
    return expanded


def _score(row: dict, tokens: list[str]) -> int:
    haystack = " ".join(str(row.get(key) or "") for key in row).lower()
    return sum(haystack.count(token) for token in tokens)


def _json_list(value: str | None) -> list:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


class ProjectIndexRepository:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path).expanduser()

    def init(self) -> None:
        with connect_db(self.db_path) as conn:
            init_schema(conn)

    def start_run(self, project_root: str, indexer_version: str = CURRENT_INDEXER_VERSION) -> int:
        with connect_db(self.db_path) as conn:
            init_schema(conn)
            cur = conn.execute(
                "INSERT INTO index_runs(project_root, started_at, status, indexer_version) VALUES (?, datetime('now'), ?, ?)",
                (project_root, "running", indexer_version),
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

    def needs_reindex(self, file: ProjectFile, indexer_version: str = CURRENT_INDEXER_VERSION) -> bool:
        with connect_db(self.db_path) as conn:
            init_schema(conn)
            existing = conn.execute("SELECT * FROM files WHERE path = ?", (file.path,)).fetchone()
            if existing is None or existing["content_hash"] != file.content_hash or existing["status"] != "active":
                return True
            summary = conn.execute("SELECT * FROM file_summaries WHERE path = ?", (file.path,)).fetchone()
            if summary is None:
                return True
            return summary["content_hash"] != file.content_hash or summary["indexer_version"] != indexer_version

    def clear_artifacts_for_path(self, path: str) -> None:
        with connect_db(self.db_path) as conn:
            init_schema(conn)
            conn.execute("DELETE FROM file_summaries WHERE path = ?", (path,))
            conn.execute("DELETE FROM symbols WHERE path = ?", (path,))
            conn.execute("DELETE FROM consistency_flags WHERE path = ?", (path,))
            conn.commit()

    def mark_deleted_missing_paths(self, active_paths: Iterable[str]) -> None:
        active = set(active_paths)
        with connect_db(self.db_path) as conn:
            init_schema(conn)
            rows = conn.execute("SELECT path FROM files WHERE status = 'active'").fetchall()
            deleted_paths = [row["path"] for row in rows if row["path"] not in active]
            for path in deleted_paths:
                conn.execute("UPDATE files SET status = 'deleted' WHERE path = ?", (path,))
                conn.execute("DELETE FROM file_summaries WHERE path = ?", (path,))
                conn.execute("DELETE FROM symbols WHERE path = ?", (path,))
                conn.execute("DELETE FROM consistency_flags WHERE path = ?", (path,))
            conn.commit()

    def upsert_summary(
        self,
        summary: FileSummary,
        content_hash: str = "",
        run_id: int | None = None,
        indexer_version: str = CURRENT_INDEXER_VERSION,
    ) -> None:
        with connect_db(self.db_path) as conn:
            init_schema(conn)
            conn.execute(
                """
                INSERT INTO file_summaries(
                    path, summary, responsibilities, key_points, dependencies, risks,
                    evidence, inconsistencies, confidence, content_hash, index_run_id,
                    indexer_version, evidence_spans, confidence_score, confidence_reasons, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(path) DO UPDATE SET
                    summary = excluded.summary,
                    responsibilities = excluded.responsibilities,
                    key_points = excluded.key_points,
                    dependencies = excluded.dependencies,
                    risks = excluded.risks,
                    evidence = excluded.evidence,
                    inconsistencies = excluded.inconsistencies,
                    confidence = excluded.confidence,
                    content_hash = excluded.content_hash,
                    index_run_id = excluded.index_run_id,
                    indexer_version = excluded.indexer_version,
                    evidence_spans = excluded.evidence_spans,
                    confidence_score = excluded.confidence_score,
                    confidence_reasons = excluded.confidence_reasons,
                    updated_at = excluded.updated_at
                """,
                (
                    summary.path,
                    summary.summary,
                    summary.responsibilities,
                    summary.key_points,
                    summary.dependencies,
                    summary.risks,
                    summary.evidence,
                    summary.inconsistencies,
                    summary.confidence,
                    content_hash,
                    run_id,
                    indexer_version,
                    summary.evidence_spans,
                    summary.confidence_score,
                    summary.confidence_reasons,
                ),
            )
            conn.commit()

    def replace_symbols(
        self,
        path: str,
        symbols: list[SymbolInfo],
        content_hash: str = "",
        run_id: int | None = None,
        indexer_version: str = CURRENT_INDEXER_VERSION,
    ) -> None:
        with connect_db(self.db_path) as conn:
            init_schema(conn)
            conn.execute("DELETE FROM symbols WHERE path = ?", (path,))
            conn.executemany(
                """
                INSERT INTO symbols(
                    path, symbol_type, name, signature, line_start, line_end,
                    summary, observed_behavior, side_effects, confidence,
                    content_hash, index_run_id, indexer_version, body_hash, evidence_preview
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        s.path,
                        s.symbol_type,
                        s.name,
                        s.signature,
                        s.line_start,
                        s.line_end,
                        s.summary,
                        s.observed_behavior,
                        s.side_effects,
                        s.confidence,
                        content_hash,
                        run_id,
                        indexer_version,
                        s.body_hash,
                        s.evidence_preview,
                    )
                    for s in symbols
                ],
            )
            conn.commit()

    def replace_consistency_flags(
        self,
        path: str,
        flags: list[ConsistencyFlag],
        content_hash: str = "",
        run_id: int | None = None,
        indexer_version: str = CURRENT_INDEXER_VERSION,
    ) -> None:
        with connect_db(self.db_path) as conn:
            init_schema(conn)
            conn.execute("DELETE FROM consistency_flags WHERE path = ?", (path,))
            conn.executemany(
                """
                INSERT INTO consistency_flags(
                    path, line_start, line_end, flag_type, subject, claimed_behavior,
                    observed_behavior, evidence, severity, status, created_at,
                    content_hash, index_run_id, indexer_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?, ?)
                """,
                [
                    (
                        f.path,
                        f.line_start,
                        f.line_end,
                        f.flag_type,
                        f.subject,
                        f.claimed_behavior,
                        f.observed_behavior,
                        f.evidence,
                        f.severity,
                        f.status,
                        content_hash,
                        run_id,
                        indexer_version,
                    )
                    for f in flags
                ],
            )
            conn.commit()

    def insert_research_note(self, note: ResearchNote) -> int:
        with connect_db(self.db_path) as conn:
            init_schema(conn)
            cur = conn.execute(
                """
                INSERT INTO research_notes(
                    thread_id, request_type, question, answer_summary,
                    related_paths, open_questions, created_at, project_root,
                    source_note_ids, internal_memory_summary, user_answer_summary, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?, ?, ?, ?, ?)
                """,
                (
                    note.thread_id,
                    note.request_type,
                    note.question,
                    note.answer_summary,
                    note.related_paths,
                    note.open_questions,
                    note.project_root,
                    note.source_note_ids,
                    note.internal_memory_summary,
                    note.user_answer_summary,
                    note.confidence,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def search_research_notes(
        self,
        query: str,
        *,
        project_root: str = "",
        request_type: str | None = None,
        limit: int = 5,
    ) -> list[dict]:
        tokens = _tokens(query)
        if not tokens:
            return []
        clauses = []
        params: list[str] = []
        if project_root:
            clauses.append("project_root = ?")
            params.append(project_root)
        if request_type:
            clauses.append("request_type = ?")
            params.append(request_type)
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        with connect_db(self.db_path) as conn:
            init_schema(conn)
            rows = conn.execute(
                f"""
                SELECT * FROM research_notes
                {where}
                ORDER BY created_at DESC, id DESC
                """,
                params,
            ).fetchall()
        hits: list[dict] = []
        for row in rows:
            item = dict(row)
            item["score"] = _score(item, tokens)
            if item["score"] <= 0:
                continue
            item["source"] = "research_note"
            item["related_paths"] = _json_list(item.get("related_paths"))
            item["open_questions"] = _json_list(item.get("open_questions"))
            item["source_note_ids"] = _json_list(item.get("source_note_ids"))
            hits.append(item)
        return sorted(hits, key=lambda item: item["score"], reverse=True)[:limit]

    def list_recent_research_notes(
        self,
        *,
        project_root: str = "",
        thread_id: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        clauses = []
        params: list[str | int] = []
        if project_root:
            clauses.append("project_root = ?")
            params.append(project_root)
        if thread_id:
            clauses.append("thread_id = ?")
            params.append(thread_id)
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        params.append(limit)
        with connect_db(self.db_path) as conn:
            init_schema(conn)
            rows = conn.execute(
                f"SELECT * FROM research_notes {where} ORDER BY created_at DESC, id DESC LIMIT ?",
                params,
            ).fetchall()
        return [dict(row) for row in rows]

    def insert_improvement_proposal(self, proposal: ImprovementProposal) -> int:
        with connect_db(self.db_path) as conn:
            init_schema(conn)
            cur = conn.execute(
                """
                INSERT INTO improvement_proposals(
                    proposal_type, source_note_ids, target_component, proposed_change,
                    rationale, evidence, risk, status, created_at, applied_at, flow_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), NULL, ?)
                """,
                (
                    proposal.proposal_type,
                    proposal.source_note_ids,
                    proposal.target_component,
                    proposal.proposed_change,
                    proposal.rationale,
                    proposal.evidence,
                    proposal.risk,
                    proposal.status,
                    proposal.flow_version,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def list_improvement_proposals(
        self,
        *,
        status: str | None = None,
        proposal_type: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        clauses = []
        params: list[str | int] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        if proposal_type is not None:
            clauses.append("proposal_type = ?")
            params.append(proposal_type)
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        params.append(limit)
        with connect_db(self.db_path) as conn:
            init_schema(conn)
            rows = conn.execute(
                f"SELECT * FROM improvement_proposals {where} ORDER BY created_at DESC, id DESC LIMIT ?",
                params,
            ).fetchall()
        proposals = []
        for row in rows:
            item = dict(row)
            item["source_note_ids"] = _json_list(item.get("source_note_ids"))
            proposals.append(item)
        return proposals
