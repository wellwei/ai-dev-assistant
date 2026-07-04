# LangGraph Project Knowledge Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a half-automatic LangGraph project knowledge assistant that indexes `~/projects/escort_server/doll_escort_game_svr` into SQLite and answers project questions, requirement research, and development-advice requests without modifying the C++ project.

**Architecture:** Keep two graph flows: `index_graph` builds and refreshes a SQLite project knowledge index; `assistant_graph` classifies user requests, retrieves indexed context, synthesizes Chinese answers, and persists reusable research notes. Use SQLite checkpointer for LangGraph thread persistence and a separate SQLite project-index database for files, summaries, symbols, consistency flags, and research notes.

**Route Update (2026-07-03):** Do not continue Hermes Agent introduction work. Future memory and self-improvement work should use a self-developed project memory layer, with later Codex/Claude Code integration, Docker deployment, and skill capability.

**Tech Stack:** Python 3.10+, LangChain 1.x, LangGraph 1.x, `langchain-openai`, `langgraph-checkpoint-sqlite`, SQLite, pytest.

## Global Constraints

- Target C++ project path is `~/projects/escort_server/doll_escort_game_svr`.
- Target C++ project git worktree root is `~/projects/escort_server`; treat it as read-only by default.
- Do not edit, build, commit, push, or otherwise change the C++ project unless the user explicitly approves.
- The assistant must prioritize actual implementation, call/data flow, and side effects over comments, docs, file names, function names, and field names.
- Comments, docs, file names, function names, and field names are clues only, not facts.
- Low-confidence conclusions must be labeled.
- Do not store complete large file contents in graph state or SQLite checkpoints.
- Use incremental indexing based on content hash; mtime is only a fast hint.
- Do not add full C++ AST parsing, Deep Agents, or Hermes Agent in the first implementation. Hermes Agent is no longer a future direction after the 2026-07-03 route update.
- Existing target C++ git changes must not be touched.

---

## File Structure

Create or modify these files in `/Users/cltx/projects/langgraph`:

```text
requirements.txt
.env.example
langgraph.json
src/__init__.py
src/config.py
src/state.py
src/graph.py
src/index_graph.py
src/assistant_graph.py
src/storage/__init__.py
src/storage/schema.sql
src/storage/sqlite.py
src/storage/project_index.py
src/indexer/__init__.py
src/indexer/models.py
src/indexer/scanner.py
src/indexer/classifier.py
src/indexer/symbol_extractor.py
src/indexer/summarizer.py
src/indexer/consistency.py
src/nodes/__init__.py
src/nodes/index_nodes.py
src/nodes/assistant_nodes.py
src/retriever/__init__.py
src/retriever/keyword_search.py
src/retriever/context_builder.py
tests/test_config.py
tests/test_storage.py
tests/test_scanner_classifier.py
tests/test_symbol_extractor.py
tests/test_summarizer_consistency.py
tests/test_index_graph.py
tests/test_retriever.py
tests/test_assistant_graph.py
```

Responsibility map:

| Path | Responsibility |
| --- | --- |
| `src/config.py` | Environment-driven settings and safe path defaults. |
| `src/state.py` | TypedDict graph state definitions with reducers. |
| `src/storage/schema.sql` | Project-index database schema. |
| `src/storage/sqlite.py` | SQLite connection and schema initialization helpers. |
| `src/storage/project_index.py` | Repository functions for project index reads/writes. |
| `src/indexer/*` | Pure indexing utilities: scan, classify, extract symbols, summarize implementation, flag inconsistencies. |
| `src/nodes/index_nodes.py` | LangGraph node wrappers for indexing. |
| `src/index_graph.py` | Build and compile the indexing graph. |
| `src/retriever/*` | Keyword retrieval and context formatting from SQLite. |
| `src/nodes/assistant_nodes.py` | Request classification, analysis, answer synthesis, research-note persistence. |
| `src/assistant_graph.py` | Build and compile the assistant graph. |
| `src/graph.py` | LangGraph CLI entrypoint exporting the assistant graph. |
| `tests/*` | Unit and graph smoke tests with temporary projects and SQLite DBs. |

---

### Task 1: Dependencies, Settings, and SQLite Schema

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.example`
- Modify: `src/config.py`
- Create: `src/__init__.py`
- Create: `src/storage/__init__.py`
- Create: `src/storage/schema.sql`
- Create: `src/storage/sqlite.py`
- Test: `tests/test_config.py`
- Test: `tests/test_storage.py`

**Interfaces:**
- Produces: `src.config.Settings`, `src.config.settings`
- Produces: `src.storage.sqlite.connect_db(path: str | Path) -> sqlite3.Connection`
- Produces: `src.storage.sqlite.init_schema(conn: sqlite3.Connection) -> None`
- Produces: `src.storage.sqlite.ensure_parent_dir(path: str | Path) -> Path`

- [ ] **Step 1: Write failing config tests**

Create `tests/test_config.py`:

```python
from pathlib import Path

from src.config import Settings


def test_settings_defaults_point_to_target_project_and_sqlite_files(monkeypatch):
    monkeypatch.delenv("TARGET_PROJECT_ROOT", raising=False)
    monkeypatch.delenv("CHECKPOINT_DB", raising=False)
    monkeypatch.delenv("PROJECT_INDEX_DB", raising=False)

    settings = Settings()

    assert settings.TARGET_PROJECT_ROOT == str(
        Path.home() / "projects/escort_server/doll_escort_game_svr"
    )
    assert settings.CHECKPOINT_DB == "./checkpoints/langgraph.sqlite"
    assert settings.PROJECT_INDEX_DB == "./checkpoints/project_index.sqlite"


def test_settings_allows_environment_overrides(monkeypatch, tmp_path):
    project_root = tmp_path / "target"
    checkpoint = tmp_path / "checkpoints" / "graph.sqlite"
    index_db = tmp_path / "index" / "project.sqlite"

    monkeypatch.setenv("TARGET_PROJECT_ROOT", str(project_root))
    monkeypatch.setenv("CHECKPOINT_DB", str(checkpoint))
    monkeypatch.setenv("PROJECT_INDEX_DB", str(index_db))
    monkeypatch.setenv("MODEL_NAME", "company-model")

    settings = Settings()

    assert settings.TARGET_PROJECT_ROOT == str(project_root)
    assert settings.CHECKPOINT_DB == str(checkpoint)
    assert settings.PROJECT_INDEX_DB == str(index_db)
    assert settings.MODEL_NAME == "company-model"
```

- [ ] **Step 2: Write failing storage tests**

Create `tests/test_storage.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
/Users/cltx/projects/langgraph/venv/bin/python -m pytest tests/test_config.py tests/test_storage.py -v
```

Expected: FAIL because `pytest` is not installed and the storage modules do not exist. If pytest is missing, that is the expected first failure for this task.

- [ ] **Step 4: Update dependencies**

Replace `requirements.txt` with:

```text
langchain>=1.0,<2.0
langchain-core>=1.0,<2.0
langgraph>=1.0,<2.0
langsmith>=0.3.0
langchain-openai>=1.0,<2.0
langgraph-checkpoint-sqlite>=3.0,<4.0
python-dotenv>=1.0.0
pytest>=8.0,<9.0
```

Install dependencies if the environment has not already been updated:

```bash
/Users/cltx/projects/langgraph/venv/bin/python -m pip install -r requirements.txt
```

Expected: installation succeeds. If network access is unavailable, stop and report the dependency installation blocker.

- [ ] **Step 5: Update env example**

Replace `.env.example` with:

```env
# Company OpenAI-compatible model API
OPENAI_API_KEY=sk-your-company-key
OPENAI_BASE_URL=https://your-company-api-endpoint.com/v1
MODEL_NAME=gpt-4o

# Target C++ project. This project is read-only by default for the assistant.
TARGET_PROJECT_ROOT=~/projects/escort_server/doll_escort_game_svr

# SQLite persistence
CHECKPOINT_DB=./checkpoints/langgraph.sqlite
PROJECT_INDEX_DB=./checkpoints/project_index.sqlite

# LangSmith observability, optional but recommended
LANGSMITH_API_KEY=your-langsmith-key
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=langgraph-project-knowledge-assistant

LOG_LEVEL=INFO
```

- [ ] **Step 6: Implement settings**

Replace `src/config.py` with:

```python
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _default_target_project_root() -> str:
    return str(Path.home() / "projects/escort_server/doll_escort_game_svr")


@dataclass(frozen=True)
class Settings:
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o")

    TARGET_PROJECT_ROOT: str = os.getenv(
        "TARGET_PROJECT_ROOT",
        _default_target_project_root(),
    )

    CHECKPOINT_DB: str = os.getenv("CHECKPOINT_DB", "./checkpoints/langgraph.sqlite")
    PROJECT_INDEX_DB: str = os.getenv("PROJECT_INDEX_DB", "./checkpoints/project_index.sqlite")

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
```

- [ ] **Step 7: Add package marker files**

Create `src/__init__.py`:

```python
"""LangGraph project knowledge assistant."""
```

Create `src/storage/__init__.py`:

```python
"""SQLite storage helpers for project knowledge indexing."""
```

- [ ] **Step 8: Add schema**

Create `src/storage/schema.sql`:

```sql
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
```

- [ ] **Step 9: Implement SQLite helpers**

Create `src/storage/sqlite.py`:

```python
from pathlib import Path
import sqlite3


SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def ensure_parent_dir(path: str | Path) -> Path:
    db_path = Path(path).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def connect_db(path: str | Path) -> sqlite3.Connection:
    db_path = ensure_parent_dir(path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.commit()
```

- [ ] **Step 10: Run tests to verify they pass**

Run:

```bash
/Users/cltx/projects/langgraph/venv/bin/python -m pytest tests/test_config.py tests/test_storage.py -v
```

Expected: all tests pass.

- [ ] **Step 11: Commit**

```bash
git add requirements.txt .env.example src/__init__.py src/config.py src/storage/__init__.py src/storage/schema.sql src/storage/sqlite.py tests/test_config.py tests/test_storage.py
git commit -m "feat: add settings and sqlite schema"
```

---

### Task 2: Project Index Repository

**Files:**
- Create: `src/indexer/__init__.py`
- Create: `src/indexer/models.py`
- Create: `src/storage/project_index.py`
- Test: `tests/test_storage.py`

**Interfaces:**
- Consumes: `connect_db`, `init_schema`
- Produces dataclasses: `ProjectFile`, `FileSummary`, `SymbolInfo`, `ConsistencyFlag`, `ResearchNote`
- Produces repository: `ProjectIndexRepository`
- Produces methods:
  - `start_run(project_root: str) -> int`
  - `finish_run(run_id: int, status: str, scanned_files: int, changed_files: int, summarized_files: int, error: str | None = None) -> None`
  - `upsert_file(file: ProjectFile) -> None`
  - `get_file(path: str) -> sqlite3.Row | None`
  - `replace_symbols(path: str, symbols: list[SymbolInfo]) -> None`
  - `upsert_summary(summary: FileSummary) -> None`
  - `replace_consistency_flags(path: str, flags: list[ConsistencyFlag]) -> None`
  - `insert_research_note(note: ResearchNote) -> int`

- [ ] **Step 1: Extend storage tests for repository behavior**

Append this to `tests/test_storage.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
/Users/cltx/projects/langgraph/venv/bin/python -m pytest tests/test_storage.py::test_repository_upserts_file_summary_symbols_flags_and_notes -v
```

Expected: FAIL because `src.indexer.models` and `src.storage.project_index` do not exist.

- [ ] **Step 3: Add indexer package and models**

Create `src/indexer/__init__.py`:

```python
"""Project indexing utilities."""
```

Create `src/indexer/models.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectFile:
    path: str
    abs_path: str
    file_type: str
    language: str
    size_bytes: int
    mtime: float
    content_hash: str
    status: str = "active"


@dataclass(frozen=True)
class FileSummary:
    path: str
    summary: str
    responsibilities: str
    key_points: str
    dependencies: str
    risks: str
    evidence: str
    inconsistencies: str
    confidence: str


@dataclass(frozen=True)
class SymbolInfo:
    path: str
    symbol_type: str
    name: str
    signature: str
    line_start: int
    line_end: int | None
    summary: str
    observed_behavior: str
    side_effects: str
    confidence: str


@dataclass(frozen=True)
class ConsistencyFlag:
    path: str
    line_start: int | None
    line_end: int | None
    flag_type: str
    subject: str
    claimed_behavior: str | None
    observed_behavior: str
    evidence: str
    severity: str
    status: str = "open"


@dataclass(frozen=True)
class ResearchNote:
    thread_id: str
    request_type: str
    question: str
    answer_summary: str
    related_paths: str
    open_questions: str
```

- [ ] **Step 4: Implement project index repository**

Create `src/storage/project_index.py`:

```python
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
                (
                    file.path,
                    file.abs_path,
                    file.file_type,
                    file.language,
                    file.size_bytes,
                    file.mtime,
                    file.content_hash,
                    file.status,
                ),
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
                ),
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
                [
                    (
                        symbol.path,
                        symbol.symbol_type,
                        symbol.name,
                        symbol.signature,
                        symbol.line_start,
                        symbol.line_end,
                        symbol.summary,
                        symbol.observed_behavior,
                        symbol.side_effects,
                        symbol.confidence,
                    )
                    for symbol in symbols
                ],
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
                [
                    (
                        flag.path,
                        flag.line_start,
                        flag.line_end,
                        flag.flag_type,
                        flag.subject,
                        flag.claimed_behavior,
                        flag.observed_behavior,
                        flag.evidence,
                        flag.severity,
                        flag.status,
                    )
                    for flag in flags
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
                    related_paths, open_questions, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    note.thread_id,
                    note.request_type,
                    note.question,
                    note.answer_summary,
                    note.related_paths,
                    note.open_questions,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)
```

- [ ] **Step 5: Run tests**

Run:

```bash
/Users/cltx/projects/langgraph/venv/bin/python -m pytest tests/test_storage.py -v
```

Expected: all storage tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/indexer/__init__.py src/indexer/models.py src/storage/project_index.py tests/test_storage.py
git commit -m "feat: add project index repository"
```

---

### Task 3: File Scanner and Classifier

**Files:**
- Create: `src/indexer/scanner.py`
- Create: `src/indexer/classifier.py`
- Test: `tests/test_scanner_classifier.py`

**Interfaces:**
- Produces: `src.indexer.scanner.scan_project(project_root: str | Path) -> list[ProjectFile]`
- Produces: `src.indexer.scanner.compute_content_hash(path: str | Path) -> str`
- Produces: `src.indexer.classifier.classify_path(path: str) -> tuple[str, str]`
- Consumes: `ProjectFile`

- [ ] **Step 1: Write failing scanner/classifier tests**

Create `tests/test_scanner_classifier.py`:

```python
from src.indexer.classifier import classify_path
from src.indexer.scanner import compute_content_hash, scan_project


def test_classify_path_recognizes_project_file_types():
    assert classify_path("src/map_data/sea_route.cpp") == ("source", "cpp")
    assert classify_path("src/map_data/sea_route.h") == ("header", "cpp")
    assert classify_path("doc/readme.md") == ("doc", "markdown")
    assert classify_path("doc/chase.txt") == ("doc", "text")
    assert classify_path("CMakeLists.txt") == ("build_config", "cmake")
    assert classify_path("linux_prj/build.sh") == ("script", "shell")
    assert classify_path("linux_prj/config.ini") == ("config", "ini")
    assert classify_path("project.AFCfile") == ("config", "afc")


def test_scan_project_includes_relevant_files_and_skips_build_outputs(tmp_path):
    project = tmp_path / "doll_escort_game_svr"
    (project / "src/map_data").mkdir(parents=True)
    (project / "doc").mkdir()
    (project / "linux_prj").mkdir()
    (project / "build").mkdir()

    (project / "src/map_data/sea_route.cpp").write_text("int route() { return 1; }", encoding="utf-8")
    (project / "src/map_data/sea_route.h").write_text("int route();", encoding="utf-8")
    (project / "doc/readme.md").write_text("# readme", encoding="utf-8")
    (project / "linux_prj/build.sh").write_text("#!/bin/bash", encoding="utf-8")
    (project / "build/generated.cpp").write_text("int generated;", encoding="utf-8")
    (project / "libx.so").write_bytes(b"binary")

    files = scan_project(project)
    paths = {f.path for f in files}

    assert "src/map_data/sea_route.cpp" in paths
    assert "src/map_data/sea_route.h" in paths
    assert "doc/readme.md" in paths
    assert "linux_prj/build.sh" in paths
    assert "build/generated.cpp" not in paths
    assert "libx.so" not in paths

    route_file = next(f for f in files if f.path == "src/map_data/sea_route.cpp")
    assert route_file.file_type == "source"
    assert route_file.language == "cpp"
    assert route_file.content_hash == compute_content_hash(project / "src/map_data/sea_route.cpp")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
/Users/cltx/projects/langgraph/venv/bin/python -m pytest tests/test_scanner_classifier.py -v
```

Expected: FAIL because scanner/classifier modules do not exist.

- [ ] **Step 3: Implement classifier**

Create `src/indexer/classifier.py`:

```python
from pathlib import PurePosixPath


def classify_path(path: str) -> tuple[str, str]:
    normalized = path.replace("\\", "/")
    p = PurePosixPath(normalized)
    name = p.name
    suffix = p.suffix.lower()

    if normalized == "CMakeLists.txt" or suffix == ".cmake":
        return "build_config", "cmake"
    if normalized.startswith("doc/") and suffix == ".md":
        return "doc", "markdown"
    if normalized.startswith("doc/") and suffix == ".txt":
        return "doc", "text"
    if suffix == ".cpp" or suffix == ".cc" or suffix == ".cxx":
        return "source", "cpp"
    if suffix == ".h" or suffix == ".hpp" or suffix == ".hh":
        return "header", "cpp"
    if suffix == ".sh":
        return "script", "shell"
    if suffix == ".ini":
        return "config", "ini"
    if suffix == ".afcfile" or name.endswith(".AFCfile"):
        return "config", "afc"
    return "other", "text"
```

- [ ] **Step 4: Implement scanner**

Create `src/indexer/scanner.py`:

```python
from pathlib import Path
import hashlib

from src.indexer.classifier import classify_path
from src.indexer.models import ProjectFile

SKIP_DIRS = {
    ".git",
    "build",
    "cmake-build-debug",
    "cmake-build-release",
    "__pycache__",
    ".venv",
    "venv",
    ".cache",
    ".idea",
}

SKIP_SUFFIXES = {
    ".o",
    ".so",
    ".a",
    ".tar",
    ".gz",
    ".zip",
    ".pckl",
    ".pyc",
}

INCLUDE_PREFIXES = (
    "src/",
    "doc/",
    "linux_prj/",
)

INCLUDE_NAMES = {
    "CMakeLists.txt",
}


def compute_content_hash(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_skipped(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if any(part in SKIP_DIRS for part in rel.parts):
        return True
    if path.suffix.lower() in SKIP_SUFFIXES:
        return True
    if path.name.endswith(".tar.gz"):
        return True
    return False


def _is_included(rel_path: str) -> bool:
    if rel_path in INCLUDE_NAMES:
        return True
    if rel_path.endswith(".AFCfile"):
        return True
    return rel_path.startswith(INCLUDE_PREFIXES)


def scan_project(project_root: str | Path) -> list[ProjectFile]:
    root = Path(project_root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Target project root does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Target project root is not a directory: {root}")

    results: list[ProjectFile] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if _is_skipped(path, root):
            continue
        rel_path = path.relative_to(root).as_posix()
        if not _is_included(rel_path):
            continue
        file_type, language = classify_path(rel_path)
        stat = path.stat()
        results.append(
            ProjectFile(
                path=rel_path,
                abs_path=str(path),
                file_type=file_type,
                language=language,
                size_bytes=stat.st_size,
                mtime=stat.st_mtime,
                content_hash=compute_content_hash(path),
                status="active",
            )
        )
    return results
```

- [ ] **Step 5: Run tests**

Run:

```bash
/Users/cltx/projects/langgraph/venv/bin/python -m pytest tests/test_scanner_classifier.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/indexer/classifier.py src/indexer/scanner.py tests/test_scanner_classifier.py
git commit -m "feat: add project scanner and classifier"
```

---

### Task 4: Symbol Extraction and Consistency Flags

**Files:**
- Create: `src/indexer/symbol_extractor.py`
- Create: `src/indexer/consistency.py`
- Test: `tests/test_symbol_extractor.py`
- Test: `tests/test_summarizer_consistency.py`

**Interfaces:**
- Produces: `extract_symbols(path: str, content: str) -> list[SymbolInfo]`
- Produces: `detect_side_effects(content: str) -> str`
- Produces: `detect_consistency_flags(path: str, content: str, symbols: list[SymbolInfo]) -> list[ConsistencyFlag]`

- [ ] **Step 1: Write failing symbol tests**

Create `tests/test_symbol_extractor.py`:

```python
from src.indexer.symbol_extractor import detect_side_effects, extract_symbols


CPP_CONTENT = """
#define ROUTE_FLAG 1

struct route_ctx_t {
    int state;
};

class route_manager {
public:
    int query_route(route_ctx_t* ctx);
};

int query_route(route_ctx_t* ctx) {
    ctx->state = 1;
    send_packet(ctx);
    return ctx->state;
}
"""


def test_extract_symbols_finds_macros_structs_classes_and_functions():
    symbols = extract_symbols("src/route.cpp", CPP_CONTENT)
    names = {(s.symbol_type, s.name) for s in symbols}

    assert ("macro", "ROUTE_FLAG") in names
    assert ("struct", "route_ctx_t") in names
    assert ("class", "route_manager") in names
    assert ("function", "query_route") in names

    query = next(s for s in symbols if s.name == "query_route" and s.symbol_type == "function")
    assert query.line_start > 0
    assert "query_route" in query.signature
    assert "state_write" in query.side_effects
    assert "network_send" in query.side_effects


def test_detect_side_effects_reports_state_and_network_writes():
    side_effects = detect_side_effects(CPP_CONTENT)
    assert "state_write" in side_effects
    assert "network_send" in side_effects
```

- [ ] **Step 2: Write failing consistency tests**

Create `tests/test_summarizer_consistency.py`:

```python
from src.indexer.consistency import detect_consistency_flags
from src.indexer.symbol_extractor import extract_symbols


def test_consistency_flags_query_name_with_mutation_as_hidden_side_effect():
    content = """
int query_resource(Context* ctx) {
    ctx->mutable_resource()->set_state(1);
    broadcast_resource(ctx);
    return 0;
}
"""
    symbols = extract_symbols("src/resource.cpp", content)

    flags = detect_consistency_flags("src/resource.cpp", content, symbols)

    assert any(flag.flag_type == "side_effect_hidden" for flag in flags)
    assert any(flag.subject == "query_resource" for flag in flags)


def test_consistency_flags_stale_comment_when_comment_claims_no_write_but_body_writes():
    content = """
// only query route, no state changes
int get_route(Context* ctx) {
    ctx->route = 42;
    return ctx->route;
}
"""
    symbols = extract_symbols("src/route.cpp", content)

    flags = detect_consistency_flags("src/route.cpp", content, symbols)

    assert any(flag.flag_type == "comment_mismatch" for flag in flags)
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
/Users/cltx/projects/langgraph/venv/bin/python -m pytest tests/test_symbol_extractor.py tests/test_summarizer_consistency.py -v
```

Expected: FAIL because modules do not exist.

- [ ] **Step 4: Implement symbol extractor**

Create `src/indexer/symbol_extractor.py`:

```python
import re

from src.indexer.models import SymbolInfo

MACRO_RE = re.compile(r"^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)
STRUCT_RE = re.compile(r"^\s*struct\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.MULTILINE)
CLASS_RE = re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.MULTILINE)
ENUM_RE = re.compile(r"^\s*enum(?:\s+class)?\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.MULTILINE)
FUNCTION_RE = re.compile(
    r"^\s*(?:static\s+|inline\s+|virtual\s+|const\s+|unsigned\s+|signed\s+|long\s+|short\s+|[A-Za-z_][A-Za-z0-9_:<>*&\s]+\s+)"
    r"([A-Za-z_][A-Za-z0-9_:~]*)\s*\([^;{}]*\)\s*(?:const\s*)?\{",
    re.MULTILINE,
)

SIDE_EFFECT_PATTERNS = {
    "redis_write": ("redis", "set", "del", "expire", "hset"),
    "db_write": ("insert", "update", "delete", "replace"),
    "state_write": ("mutable_", "set_", "->state", ".state", "push_back", "erase", "clear", "insert"),
    "network_send": ("send", "broadcast", "notify", "packet"),
    "frame_or_timer": ("frame", "timer", "add_task", "post_task"),
}


def _line_number(content: str, offset: int) -> int:
    return content.count("\n", 0, offset) + 1


def detect_side_effects(content: str) -> str:
    lowered = content.lower()
    found: list[str] = []
    for label, needles in SIDE_EFFECT_PATTERNS.items():
        if any(needle in lowered for needle in needles):
            found.append(label)
    return ",".join(found)


def _symbol_summary(symbol_type: str, name: str, side_effects: str) -> str:
    if side_effects:
        return f"{symbol_type} {name} has potential side effects: {side_effects}."
    return f"{symbol_type} {name} declaration or implementation."


def _add_matches(path: str, content: str, regex: re.Pattern[str], symbol_type: str, symbols: list[SymbolInfo]) -> None:
    for match in regex.finditer(content):
        name = match.group(1).split("::")[-1]
        signature = match.group(0).strip().split("{")[0].strip()
        line_start = _line_number(content, match.start())
        window = content[match.start() : match.start() + 1200]
        side_effects = detect_side_effects(window)
        symbols.append(
            SymbolInfo(
                path=path,
                symbol_type=symbol_type,
                name=name,
                signature=signature,
                line_start=line_start,
                line_end=None,
                summary=_symbol_summary(symbol_type, name, side_effects),
                observed_behavior="Potential behavior inferred from implementation text; verify against full code before editing.",
                side_effects=side_effects,
                confidence="medium" if side_effects else "low",
            )
        )


def extract_symbols(path: str, content: str) -> list[SymbolInfo]:
    symbols: list[SymbolInfo] = []
    _add_matches(path, content, MACRO_RE, "macro", symbols)
    _add_matches(path, content, STRUCT_RE, "struct", symbols)
    _add_matches(path, content, CLASS_RE, "class", symbols)
    _add_matches(path, content, ENUM_RE, "enum", symbols)
    _add_matches(path, content, FUNCTION_RE, "function", symbols)
    return symbols
```

- [ ] **Step 5: Implement consistency detector**

Create `src/indexer/consistency.py`:

```python
from src.indexer.models import ConsistencyFlag, SymbolInfo
from src.indexer.symbol_extractor import detect_side_effects

READ_ONLY_PREFIXES = (
    "get",
    "query",
    "check",
    "is",
    "has",
    "find",
)

NO_WRITE_COMMENT_MARKERS = (
    "no state changes",
    "no write",
    "readonly",
    "read only",
    "只读",
    "不修改",
    "不写",
    "仅查询",
)


def _looks_read_only(name: str) -> bool:
    lowered = name.lower()
    return any(lowered.startswith(prefix) or f"_{prefix}_" in lowered for prefix in READ_ONLY_PREFIXES)


def _has_write_side_effect(side_effects: str) -> bool:
    return any(
        label in side_effects
        for label in ("redis_write", "db_write", "state_write", "network_send", "frame_or_timer")
    )


def detect_consistency_flags(path: str, content: str, symbols: list[SymbolInfo]) -> list[ConsistencyFlag]:
    flags: list[ConsistencyFlag] = []

    for symbol in symbols:
        if _looks_read_only(symbol.name) and _has_write_side_effect(symbol.side_effects):
            flags.append(
                ConsistencyFlag(
                    path=path,
                    line_start=symbol.line_start,
                    line_end=symbol.line_end,
                    flag_type="side_effect_hidden",
                    subject=symbol.name,
                    claimed_behavior=f"Name looks read-only: {symbol.name}",
                    observed_behavior=f"Implementation text shows side effects: {symbol.side_effects}",
                    evidence=symbol.signature,
                    severity="warning",
                    status="open",
                )
            )

    lowered = content.lower()
    if any(marker in lowered for marker in NO_WRITE_COMMENT_MARKERS):
        side_effects = detect_side_effects(content)
        if _has_write_side_effect(side_effects):
            flags.append(
                ConsistencyFlag(
                    path=path,
                    line_start=None,
                    line_end=None,
                    flag_type="comment_mismatch",
                    subject=path,
                    claimed_behavior="Comment claims read-only or no writes.",
                    observed_behavior=f"Implementation text shows side effects: {side_effects}",
                    evidence="Matched no-write comment marker and write-like implementation marker.",
                    severity="warning",
                    status="open",
                )
            )

    return flags
```

- [ ] **Step 6: Run tests**

Run:

```bash
/Users/cltx/projects/langgraph/venv/bin/python -m pytest tests/test_symbol_extractor.py tests/test_summarizer_consistency.py -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/indexer/symbol_extractor.py src/indexer/consistency.py tests/test_symbol_extractor.py tests/test_summarizer_consistency.py
git commit -m "feat: add symbol extraction and consistency flags"
```

---

### Task 5: Implementation Summaries

**Files:**
- Create: `src/indexer/summarizer.py`
- Modify: `tests/test_summarizer_consistency.py`

**Interfaces:**
- Consumes: `ProjectFile`, `SymbolInfo`, `ConsistencyFlag`
- Produces: `summarize_implementation(project_file: ProjectFile, content: str, symbols: list[SymbolInfo], flags: list[ConsistencyFlag]) -> FileSummary`

- [ ] **Step 1: Add failing summary test**

Append this to `tests/test_summarizer_consistency.py`:

```python
from src.indexer.models import ProjectFile
from src.indexer.summarizer import summarize_implementation


def test_summarize_implementation_prioritizes_behavior_and_reports_confidence():
    content = """
// query only
int query_resource(Context* ctx) {
    ctx->mutable_resource()->set_state(1);
    broadcast_resource(ctx);
    return 0;
}
"""
    project_file = ProjectFile(
        path="src/resource.cpp",
        abs_path="/tmp/project/src/resource.cpp",
        file_type="source",
        language="cpp",
        size_bytes=len(content),
        mtime=1.0,
        content_hash="hash",
    )
    symbols = extract_symbols(project_file.path, content)
    flags = detect_consistency_flags(project_file.path, content, symbols)

    summary = summarize_implementation(project_file, content, symbols, flags)

    assert "source" in summary.summary
    assert "query_resource" in summary.key_points
    assert "side effects" in summary.evidence
    assert "comment_mismatch" in summary.inconsistencies
    assert summary.confidence == "medium"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
/Users/cltx/projects/langgraph/venv/bin/python -m pytest tests/test_summarizer_consistency.py::test_summarize_implementation_prioritizes_behavior_and_reports_confidence -v
```

Expected: FAIL because `src.indexer.summarizer` does not exist.

- [ ] **Step 3: Implement deterministic summarizer**

Create `src/indexer/summarizer.py`:

```python
from collections import Counter

from src.indexer.models import ConsistencyFlag, FileSummary, ProjectFile, SymbolInfo
from src.indexer.symbol_extractor import detect_side_effects


def _top_symbol_names(symbols: list[SymbolInfo], limit: int = 8) -> str:
    names = [symbol.name for symbol in symbols[:limit]]
    return ", ".join(names) if names else "No symbols extracted by lightweight parser."


def _dependency_hints(content: str) -> str:
    hints = []
    lowered = content.lower()
    for label in ["redis", "db", "map", "route", "frame", "battle", "resource", "packet", "broadcast"]:
        if label in lowered:
            hints.append(label)
    return ", ".join(hints) if hints else "No dependency hints detected."


def _confidence(symbols: list[SymbolInfo], flags: list[ConsistencyFlag], content: str) -> str:
    if symbols and flags:
        return "medium"
    if symbols and detect_side_effects(content):
        return "medium"
    if symbols:
        return "low"
    return "low"


def summarize_implementation(
    project_file: ProjectFile,
    content: str,
    symbols: list[SymbolInfo],
    flags: list[ConsistencyFlag],
) -> FileSummary:
    symbol_counts = Counter(symbol.symbol_type for symbol in symbols)
    side_effects = detect_side_effects(content)
    symbol_summary = ", ".join(f"{kind}:{count}" for kind, count in sorted(symbol_counts.items()))
    if not symbol_summary:
        symbol_summary = "no symbols extracted"

    flag_summary = ", ".join(sorted({flag.flag_type for flag in flags})) if flags else "none"
    evidence_parts = [f"symbol scan: {symbol_summary}"]
    if side_effects:
        evidence_parts.append(f"side effects: {side_effects}")
    if flags:
        evidence_parts.append(f"consistency flags: {flag_summary}")

    return FileSummary(
        path=project_file.path,
        summary=(
            f"{project_file.file_type} file `{project_file.path}` summarized from implementation text. "
            f"Extracted {len(symbols)} symbols; confidence depends on lightweight parsing, not comments."
        ),
        responsibilities=f"Likely responsibilities inferred from path and extracted symbols: {_dependency_hints(content)}.",
        key_points=_top_symbol_names(symbols),
        dependencies=_dependency_hints(content),
        risks=(
            "Comments and names may be stale; verify actual call sites before editing."
            if flags
            else "Lightweight summary only; verify against source before editing."
        ),
        evidence="; ".join(evidence_parts),
        inconsistencies=flag_summary,
        confidence=_confidence(symbols, flags, content),
    )
```

- [ ] **Step 4: Run tests**

Run:

```bash
/Users/cltx/projects/langgraph/venv/bin/python -m pytest tests/test_summarizer_consistency.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/indexer/summarizer.py tests/test_summarizer_consistency.py
git commit -m "feat: add implementation summarizer"
```

---

### Task 6: Index Graph Nodes and Graph Compile

**Files:**
- Modify: `src/state.py`
- Create: `src/nodes/__init__.py`
- Create: `src/nodes/index_nodes.py`
- Create: `src/index_graph.py`
- Test: `tests/test_index_graph.py`

**Interfaces:**
- Produces: `IndexState`
- Produces node functions: `scan_project_node`, `detect_changed_files_node`, `classify_files_node`, `extract_symbols_node`, `summarize_implementation_node`, `detect_consistency_flags_node`, `write_index_node`
- Produces: `create_index_graph(repo: ProjectIndexRepository | None = None)`

- [ ] **Step 1: Write failing index graph test**

Create `tests/test_index_graph.py`:

```python
from src.index_graph import create_index_graph
from src.storage.project_index import ProjectIndexRepository
from src.storage.sqlite import connect_db


def test_index_graph_scans_and_writes_changed_files(tmp_path):
    project = tmp_path / "doll_escort_game_svr"
    (project / "src").mkdir(parents=True)
    (project / "doc").mkdir()
    (project / "src/resource.cpp").write_text(
        """
// query only
int query_resource(Context* ctx) {
    ctx->mutable_resource()->set_state(1);
    broadcast_resource(ctx);
    return 0;
}
""",
        encoding="utf-8",
    )
    (project / "doc/readme.md").write_text("# 押镖服务\n启动和资源说明", encoding="utf-8")

    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    graph = create_index_graph(repo)

    result = graph.invoke({"project_root": str(project), "index_db_path": str(db_path)})

    assert result["run_status"] == "success"
    assert len(result["scanned_files"]) == 2
    assert len(result["changed_files"]) == 2
    assert result["errors"] == []

    with connect_db(db_path) as conn:
        file_count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        summary_count = conn.execute("SELECT COUNT(*) FROM file_summaries").fetchone()[0]
        flag_count = conn.execute("SELECT COUNT(*) FROM consistency_flags").fetchone()[0]

    assert file_count == 2
    assert summary_count == 2
    assert flag_count >= 1


def test_index_graph_skips_unchanged_files_on_second_run(tmp_path):
    project = tmp_path / "doll_escort_game_svr"
    (project / "src").mkdir(parents=True)
    (project / "src/a.cpp").write_text("int a() { return 1; }", encoding="utf-8")

    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    graph = create_index_graph(repo)

    first = graph.invoke({"project_root": str(project), "index_db_path": str(db_path)})
    second = graph.invoke({"project_root": str(project), "index_db_path": str(db_path)})

    assert len(first["changed_files"]) == 1
    assert len(second["changed_files"]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
/Users/cltx/projects/langgraph/venv/bin/python -m pytest tests/test_index_graph.py -v
```

Expected: FAIL because `src.index_graph` and index nodes do not exist.

- [ ] **Step 3: Replace state definitions**

Replace `src/state.py` with:

```python
from typing import Annotated, TypedDict
import operator

from src.indexer.models import ConsistencyFlag, FileSummary, ProjectFile, SymbolInfo


class IndexState(TypedDict, total=False):
    project_root: str
    index_db_path: str
    run_id: int
    run_status: str
    scanned_files: Annotated[list[ProjectFile], operator.add]
    changed_files: Annotated[list[ProjectFile], operator.add]
    skipped_files: Annotated[list[str], operator.add]
    summaries: Annotated[list[FileSummary], operator.add]
    symbols: Annotated[list[SymbolInfo], operator.add]
    consistency_flags: Annotated[list[ConsistencyFlag], operator.add]
    errors: Annotated[list[str], operator.add]


class AssistantState(TypedDict, total=False):
    project_root: str
    index_db_path: str
    thread_id: str
    question: str
    request_type: str
    retrieved_context: Annotated[list[dict], operator.add]
    related_paths: Annotated[list[str], operator.add]
    analysis: str
    answer: str
    open_questions: Annotated[list[str], operator.add]
    suggested_commands: Annotated[list[str], operator.add]
    research_note_id: int | None
```

- [ ] **Step 4: Create nodes package marker**

Create `src/nodes/__init__.py`:

```python
"""LangGraph node functions."""
```

- [ ] **Step 5: Implement index nodes**

Create `src/nodes/index_nodes.py`:

```python
from pathlib import Path

from src.config import settings
from src.indexer.consistency import detect_consistency_flags
from src.indexer.models import ConsistencyFlag, FileSummary, ProjectFile, SymbolInfo
from src.indexer.scanner import scan_project
from src.indexer.summarizer import summarize_implementation
from src.indexer.symbol_extractor import extract_symbols
from src.state import IndexState
from src.storage.project_index import ProjectIndexRepository


def _repo(state: IndexState, default_repo: ProjectIndexRepository | None = None) -> ProjectIndexRepository:
    if default_repo is not None:
        return default_repo
    return ProjectIndexRepository(state.get("index_db_path") or settings.PROJECT_INDEX_DB)


def scan_project_node(state: IndexState, repo: ProjectIndexRepository | None = None) -> dict:
    project_root = state.get("project_root") or settings.TARGET_PROJECT_ROOT
    repository = _repo(state, repo)
    run_id = repository.start_run(project_root)
    try:
        scanned = scan_project(project_root)
        repository.mark_deleted_missing_paths(file.path for file in scanned)
        return {
            "project_root": project_root,
            "run_id": run_id,
            "scanned_files": scanned,
            "run_status": "running",
        }
    except Exception as exc:
        repository.finish_run(run_id, "failed", 0, 0, 0, str(exc))
        return {"run_id": run_id, "run_status": "failed", "errors": [str(exc)]}


def detect_changed_files_node(state: IndexState, repo: ProjectIndexRepository | None = None) -> dict:
    repository = _repo(state, repo)
    changed: list[ProjectFile] = []
    for file in state.get("scanned_files", []):
        existing = repository.get_file(file.path)
        if existing is None or existing["content_hash"] != file.content_hash or existing["status"] != "active":
            changed.append(file)
    return {"changed_files": changed}


def classify_files_node(state: IndexState) -> dict:
    return {"skipped_files": []}


def extract_symbols_node(state: IndexState) -> dict:
    all_symbols: list[SymbolInfo] = []
    errors: list[str] = []
    for file in state.get("changed_files", []):
        if file.language != "cpp":
            continue
        try:
            content = Path(file.abs_path).read_text(encoding="utf-8", errors="ignore")
            all_symbols.extend(extract_symbols(file.path, content))
        except Exception as exc:
            errors.append(f"{file.path}: {exc}")
    return {"symbols": all_symbols, "errors": errors}


def _symbols_for_path(symbols: list[SymbolInfo], path: str) -> list[SymbolInfo]:
    return [symbol for symbol in symbols if symbol.path == path]


def detect_consistency_flags_node(state: IndexState) -> dict:
    flags: list[ConsistencyFlag] = []
    errors: list[str] = []
    symbols = state.get("symbols", [])
    for file in state.get("changed_files", []):
        try:
            content = Path(file.abs_path).read_text(encoding="utf-8", errors="ignore")
            flags.extend(detect_consistency_flags(file.path, content, _symbols_for_path(symbols, file.path)))
        except Exception as exc:
            errors.append(f"{file.path}: {exc}")
    return {"consistency_flags": flags, "errors": errors}


def summarize_implementation_node(state: IndexState) -> dict:
    summaries: list[FileSummary] = []
    errors: list[str] = []
    symbols = state.get("symbols", [])
    flags = state.get("consistency_flags", [])
    for file in state.get("changed_files", []):
        try:
            content = Path(file.abs_path).read_text(encoding="utf-8", errors="ignore")
            file_symbols = _symbols_for_path(symbols, file.path)
            file_flags = [flag for flag in flags if flag.path == file.path]
            summaries.append(summarize_implementation(file, content, file_symbols, file_flags))
        except Exception as exc:
            errors.append(f"{file.path}: {exc}")
    return {"summaries": summaries, "errors": errors}


def write_index_node(state: IndexState, repo: ProjectIndexRepository | None = None) -> dict:
    repository = _repo(state, repo)
    run_id = state.get("run_id")
    scanned = state.get("scanned_files", [])
    changed = state.get("changed_files", [])
    summaries = state.get("summaries", [])
    symbols = state.get("symbols", [])
    flags = state.get("consistency_flags", [])
    errors = state.get("errors", [])

    try:
        for file in scanned:
            repository.upsert_file(file)
        for summary in summaries:
            repository.upsert_summary(summary)
        for file in changed:
            repository.replace_symbols(file.path, _symbols_for_path(symbols, file.path))
            repository.replace_consistency_flags(file.path, [flag for flag in flags if flag.path == file.path])
        status = "partial_success" if errors else "success"
        if run_id is not None:
            repository.finish_run(run_id, status, len(scanned), len(changed), len(summaries), "\n".join(errors) or None)
        return {"run_status": status}
    except Exception as exc:
        if run_id is not None:
            repository.finish_run(run_id, "failed", len(scanned), len(changed), len(summaries), str(exc))
        return {"run_status": "failed", "errors": [str(exc)]}
```

- [ ] **Step 6: Implement index graph**

Create `src/index_graph.py`:

```python
from langgraph.graph import END, START, StateGraph

from src.nodes.index_nodes import (
    classify_files_node,
    detect_changed_files_node,
    detect_consistency_flags_node,
    extract_symbols_node,
    scan_project_node,
    summarize_implementation_node,
    write_index_node,
)
from src.state import IndexState
from src.storage.project_index import ProjectIndexRepository


def create_index_graph(repo: ProjectIndexRepository | None = None):
    builder = StateGraph(IndexState)

    builder.add_node("scan_project", lambda state: scan_project_node(state, repo))
    builder.add_node("detect_changed_files", lambda state: detect_changed_files_node(state, repo))
    builder.add_node("classify_files", classify_files_node)
    builder.add_node("extract_symbols", extract_symbols_node)
    builder.add_node("detect_consistency_flags", detect_consistency_flags_node)
    builder.add_node("summarize_implementation", summarize_implementation_node)
    builder.add_node("write_index", lambda state: write_index_node(state, repo))

    builder.add_edge(START, "scan_project")
    builder.add_edge("scan_project", "detect_changed_files")
    builder.add_edge("detect_changed_files", "classify_files")
    builder.add_edge("classify_files", "extract_symbols")
    builder.add_edge("extract_symbols", "detect_consistency_flags")
    builder.add_edge("detect_consistency_flags", "summarize_implementation")
    builder.add_edge("summarize_implementation", "write_index")
    builder.add_edge("write_index", END)

    return builder.compile()
```

- [ ] **Step 7: Run tests**

Run:

```bash
/Users/cltx/projects/langgraph/venv/bin/python -m pytest tests/test_index_graph.py -v
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add src/state.py src/nodes/__init__.py src/nodes/index_nodes.py src/index_graph.py tests/test_index_graph.py
git commit -m "feat: add project indexing graph"
```

---

### Task 7: Keyword Retriever and Context Builder

**Files:**
- Create: `src/retriever/__init__.py`
- Create: `src/retriever/keyword_search.py`
- Create: `src/retriever/context_builder.py`
- Test: `tests/test_retriever.py`

**Interfaces:**
- Produces: `search_project_index(db_path: str | Path, query: str, limit: int = 8) -> list[dict]`
- Produces: `build_context(results: list[dict]) -> str`

- [ ] **Step 1: Write failing retriever tests**

Create `tests/test_retriever.py`:

```python
from src.indexer.models import FileSummary, ProjectFile, SymbolInfo
from src.retriever.context_builder import build_context
from src.retriever.keyword_search import search_project_index
from src.storage.project_index import ProjectIndexRepository


def test_search_project_index_returns_matching_summaries_and_symbols(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()
    repo.upsert_file(
        ProjectFile("src/route.cpp", "/tmp/src/route.cpp", "source", "cpp", 10, 1.0, "hash")
    )
    repo.upsert_summary(
        FileSummary(
            path="src/route.cpp",
            summary="Handles escort route recalculation.",
            responsibilities="route",
            key_points="recalc_route_main_work_handler",
            dependencies="map, route",
            risks="verify implementation",
            evidence="symbol scan",
            inconsistencies="none",
            confidence="medium",
        )
    )
    repo.replace_symbols(
        "src/route.cpp",
        [
            SymbolInfo(
                path="src/route.cpp",
                symbol_type="function",
                name="recalc_route_main_work_handler",
                signature="int recalc_route_main_work_handler(Context*)",
                line_start=12,
                line_end=None,
                summary="Recalculates route.",
                observed_behavior="route update",
                side_effects="state_write",
                confidence="medium",
            )
        ],
    )

    results = search_project_index(db_path, "route recalc")

    assert results
    assert results[0]["path"] == "src/route.cpp"
    assert "route" in results[0]["summary"].lower()


def test_build_context_includes_confidence_and_evidence():
    context = build_context(
        [
            {
                "path": "src/route.cpp",
                "summary": "Handles route.",
                "confidence": "medium",
                "evidence": "symbol scan; side effects: state_write",
                "inconsistencies": "side_effect_hidden",
            }
        ]
    )

    assert "src/route.cpp" in context
    assert "confidence=medium" in context
    assert "side_effect_hidden" in context
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
/Users/cltx/projects/langgraph/venv/bin/python -m pytest tests/test_retriever.py -v
```

Expected: FAIL because retriever modules do not exist.

- [ ] **Step 3: Create retriever package marker**

Create `src/retriever/__init__.py`:

```python
"""SQLite-backed retrieval for project knowledge."""
```

- [ ] **Step 4: Implement keyword search**

Create `src/retriever/keyword_search.py`:

```python
from pathlib import Path
import re

from src.storage.sqlite import connect_db, init_schema


def _tokens(query: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[\w一-鿿]+", query) if token.strip()]


def _score(row: dict, tokens: list[str]) -> int:
    haystack = " ".join(str(row.get(key) or "") for key in row).lower()
    return sum(haystack.count(token) for token in tokens)


def search_project_index(db_path: str | Path, query: str, limit: int = 8) -> list[dict]:
    tokens = _tokens(query)
    if not tokens:
        return []

    with connect_db(db_path) as conn:
        init_schema(conn)
        rows = conn.execute(
            """
            SELECT
                f.path,
                f.file_type,
                f.language,
                s.summary,
                s.responsibilities,
                s.key_points,
                s.dependencies,
                s.risks,
                s.evidence,
                s.inconsistencies,
                s.confidence
            FROM files f
            LEFT JOIN file_summaries s ON s.path = f.path
            WHERE f.status = 'active'
            """
        ).fetchall()

        results: list[dict] = []
        for row in rows:
            item = dict(row)
            item["score"] = _score(item, tokens)
            if item["score"] > 0:
                results.append(item)

        symbol_rows = conn.execute(
            """
            SELECT path, name, summary, observed_behavior, side_effects, confidence
            FROM symbols
            """
        ).fetchall()
        symbol_by_path: dict[str, list[dict]] = {}
        for row in symbol_rows:
            item = dict(row)
            score = _score(item, tokens)
            if score > 0:
                symbol_by_path.setdefault(item["path"], []).append(item)

    by_path = {item["path"]: item for item in results}
    for path, symbols in symbol_by_path.items():
        if path not in by_path:
            by_path[path] = {
                "path": path,
                "file_type": "unknown",
                "language": "unknown",
                "summary": "Matched by symbol table.",
                "responsibilities": "",
                "key_points": ", ".join(symbol["name"] for symbol in symbols),
                "dependencies": "",
                "risks": "Verify implementation before editing.",
                "evidence": "symbol match",
                "inconsistencies": "",
                "confidence": "low",
                "score": 0,
            }
        by_path[path]["score"] += sum(_score(symbol, tokens) for symbol in symbols)
        by_path[path]["matched_symbols"] = symbols

    return sorted(by_path.values(), key=lambda item: item["score"], reverse=True)[:limit]
```

- [ ] **Step 5: Implement context builder**

Create `src/retriever/context_builder.py`:

```python

def build_context(results: list[dict]) -> str:
    if not results:
        return "No indexed project context matched the request."

    sections: list[str] = []
    for item in results:
        sections.append(
            "\n".join(
                [
                    f"File: {item.get('path')}",
                    f"Type: {item.get('file_type')} / {item.get('language')}",
                    f"Summary: {item.get('summary') or ''}",
                    f"Key points: {item.get('key_points') or ''}",
                    f"Dependencies: {item.get('dependencies') or ''}",
                    f"Risks: {item.get('risks') or ''}",
                    f"Evidence: {item.get('evidence') or ''}",
                    f"Inconsistencies: {item.get('inconsistencies') or ''}",
                    f"confidence={item.get('confidence') or 'low'}",
                ]
            )
        )
    return "\n\n---\n\n".join(sections)
```

- [ ] **Step 6: Run tests**

Run:

```bash
/Users/cltx/projects/langgraph/venv/bin/python -m pytest tests/test_retriever.py -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/retriever/__init__.py src/retriever/keyword_search.py src/retriever/context_builder.py tests/test_retriever.py
git commit -m "feat: add sqlite keyword retriever"
```

---

### Task 8: Assistant Graph and SQLite Checkpointer

**Files:**
- Create: `src/nodes/assistant_nodes.py`
- Create: `src/assistant_graph.py`
- Modify: `src/graph.py`
- Modify: `langgraph.json`
- Test: `tests/test_assistant_graph.py`

**Interfaces:**
- Produces nodes: `classify_request_node`, `retrieve_project_context_node`, `analyze_request_node`, `synthesize_response_node`, `persist_research_note_node`
- Produces: `create_assistant_graph(repo: ProjectIndexRepository | None = None, checkpointer=None)`
- Produces: `create_graph()` as LangGraph CLI entrypoint

- [ ] **Step 1: Write failing assistant graph tests**

Create `tests/test_assistant_graph.py`:

```python
from langgraph.checkpoint.memory import InMemorySaver

from src.assistant_graph import create_assistant_graph
from src.indexer.models import FileSummary, ProjectFile
from src.storage.project_index import ProjectIndexRepository
from src.storage.sqlite import connect_db


def _seed_repo(db_path):
    repo = ProjectIndexRepository(db_path)
    repo.init()
    repo.upsert_file(ProjectFile("src/route.cpp", "/tmp/src/route.cpp", "source", "cpp", 10, 1, "hash"))
    repo.upsert_summary(
        FileSummary(
            path="src/route.cpp",
            summary="Handles escort route recalculation based on implementation evidence.",
            responsibilities="route recalculation",
            key_points="recalc_route_main_work_handler",
            dependencies="map, route",
            risks="names and comments may be stale",
            evidence="symbol scan; side effects: state_write",
            inconsistencies="side_effect_hidden",
            confidence="medium",
        )
    )
    return repo


def test_assistant_graph_answers_project_question_and_persists_note(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = _seed_repo(db_path)
    graph = create_assistant_graph(repo=repo, checkpointer=InMemorySaver())

    result = graph.invoke(
        {
            "question": "押镖 route 重算在哪里？",
            "project_root": "/tmp/project",
            "index_db_path": str(db_path),
            "thread_id": "thread-route",
        },
        {"configurable": {"thread_id": "thread-route"}},
    )

    assert result["request_type"] == "project_qa"
    assert "src/route.cpp" in result["answer"]
    assert "置信度" in result["answer"]
    assert "注释" in result["answer"] or "命名" in result["answer"]
    assert result["research_note_id"] is not None

    with connect_db(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM research_notes").fetchone()[0] == 1


def test_assistant_graph_classifies_development_advice(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = _seed_repo(db_path)
    graph = create_assistant_graph(repo=repo, checkpointer=InMemorySaver())

    result = graph.invoke(
        {
            "question": "我要修改押镖路线重算逻辑，影响哪些文件？",
            "project_root": "/tmp/project",
            "index_db_path": str(db_path),
            "thread_id": "thread-dev",
        },
        {"configurable": {"thread_id": "thread-dev"}},
    )

    assert result["request_type"] == "development_advice"
    assert "建议" in result["answer"]
    assert "不要直接修改" in result["answer"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
/Users/cltx/projects/langgraph/venv/bin/python -m pytest tests/test_assistant_graph.py -v
```

Expected: FAIL because assistant modules do not exist or `src.graph` still points to the old development pipeline.

- [ ] **Step 3: Implement assistant nodes**

Create `src/nodes/assistant_nodes.py`:

```python
import json

from src.config import settings
from src.indexer.models import ResearchNote
from src.retriever.context_builder import build_context
from src.retriever.keyword_search import search_project_index
from src.state import AssistantState
from src.storage.project_index import ProjectIndexRepository


def _repo(state: AssistantState, default_repo: ProjectIndexRepository | None = None) -> ProjectIndexRepository:
    if default_repo is not None:
        return default_repo
    return ProjectIndexRepository(state.get("index_db_path") or settings.PROJECT_INDEX_DB)


def classify_request_node(state: AssistantState) -> dict:
    question = state.get("question", "")
    lowered = question.lower()
    if any(word in question for word in ["修改", "开发", "实现", "加一个", "影响哪些文件", "怎么改"]):
        request_type = "development_advice"
    elif any(word in question for word in ["调研", "影响范围", "风险", "方案"]):
        request_type = "requirement_research"
    elif any(word in lowered for word in ["index", "索引", "刷新"]):
        request_type = "index_request"
    elif question.strip():
        request_type = "project_qa"
    else:
        request_type = "unclear"
    return {"request_type": request_type}


def retrieve_project_context_node(state: AssistantState, repo: ProjectIndexRepository | None = None) -> dict:
    repository = _repo(state, repo)
    results = search_project_index(repository.db_path, state.get("question", ""))
    return {
        "retrieved_context": results,
        "related_paths": [item["path"] for item in results],
    }


def analyze_request_node(state: AssistantState) -> dict:
    request_type = state.get("request_type", "unclear")
    context = build_context(state.get("retrieved_context", []))

    if request_type == "unclear":
        return {
            "analysis": "用户问题为空或不清楚，需要补充要了解的模块、需求或文件范围。",
            "open_questions": ["请说明你想了解的业务点、文件或需求背景。"],
        }

    if context.startswith("No indexed project context"):
        return {
            "analysis": "索引中没有找到足够上下文。需要先运行或刷新项目索引。",
            "open_questions": ["是否先运行 index_graph 刷新项目知识库？"],
            "suggested_commands": ["运行 index_graph 扫描目标项目"],
        }

    if request_type == "development_advice":
        analysis = (
            "这是开发建议请求。基于已索引上下文，先给影响范围、风险、建议修改顺序和验证命令；"
            "首期不要直接修改公司 C++ 项目。\n\n"
            f"{context}"
        )
        return {
            "analysis": analysis,
            "suggested_commands": [
                "先针对相关文件做局部阅读确认实现证据",
                "如需构建，先征得用户确认后再运行公司项目构建命令",
            ],
        }

    analysis = (
        "这是项目问答或需求调研请求。回答必须区分实现证据与命名/注释线索；"
        "如存在 inconsistency flags，要明确提示。\n\n"
        f"{context}"
    )
    return {"analysis": analysis}


def synthesize_response_node(state: AssistantState) -> dict:
    request_type = state.get("request_type", "unclear")
    related_paths = state.get("related_paths", [])
    analysis = state.get("analysis", "")
    open_questions = state.get("open_questions", [])
    suggested_commands = state.get("suggested_commands", [])

    if not related_paths:
        answer = (
            "结论：当前索引中没有找到足够信息。\n\n"
            f"依据：{analysis}\n\n"
            "风险/不确定性：不能根据空索引编造项目结构。\n\n"
            "下一步建议：先刷新项目索引，或提供更具体的模块、文件、业务关键词。"
        )
        return {"answer": answer}

    answer_lines = [
        f"结论：这是 `{request_type}` 请求，相关信息主要集中在以下文件：{', '.join(related_paths)}。",
        "",
        "依据：以下结论来自 SQLite 项目索引中的实现摘要、符号扫描、副作用线索和一致性标记。",
        analysis,
        "",
        "风险/不确定性：老 C++ 项目中注释、文档、函数名和字段名可能过时或误导；以上判断不能只按命名理解，改动前必须核对实际实现和调用链。",
        "",
        "置信度：以各文件摘要中的 confidence 为准；包含 inconsistency flags 的位置应降低信任并人工核对。",
    ]
    if request_type == "development_advice":
        answer_lines.extend(
            [
                "",
                "建议：不要直接修改公司 C++ 项目。先局部阅读相关文件，确认实际读写、副作用、线程/帧边界，再提出补丁。",
            ]
        )
    if suggested_commands:
        answer_lines.extend(["", "建议验证命令/动作：", *[f"- {cmd}" for cmd in suggested_commands]])
    if open_questions:
        answer_lines.extend(["", "待确认问题：", *[f"- {question}" for question in open_questions]])

    return {"answer": "\n".join(answer_lines)}


def persist_research_note_node(state: AssistantState, repo: ProjectIndexRepository | None = None) -> dict:
    if state.get("request_type") in {"unclear", "index_request"}:
        return {"research_note_id": None}
    answer = state.get("answer", "")
    if not answer:
        return {"research_note_id": None}
    repository = _repo(state, repo)
    note_id = repository.insert_research_note(
        ResearchNote(
            thread_id=state.get("thread_id") or "default",
            request_type=state.get("request_type", "project_qa"),
            question=state.get("question", ""),
            answer_summary=answer[:1000],
            related_paths=json.dumps(state.get("related_paths", []), ensure_ascii=False),
            open_questions=json.dumps(state.get("open_questions", []), ensure_ascii=False),
        )
    )
    return {"research_note_id": note_id}
```

- [ ] **Step 4: Implement assistant graph**

Create `src/assistant_graph.py`:

```python
from langgraph.graph import END, START, StateGraph

from src.nodes.assistant_nodes import (
    analyze_request_node,
    classify_request_node,
    persist_research_note_node,
    retrieve_project_context_node,
    synthesize_response_node,
)
from src.state import AssistantState
from src.storage.project_index import ProjectIndexRepository


def create_assistant_graph(repo: ProjectIndexRepository | None = None, checkpointer=None):
    builder = StateGraph(AssistantState)

    builder.add_node("classify_request", classify_request_node)
    builder.add_node("retrieve_project_context", lambda state: retrieve_project_context_node(state, repo))
    builder.add_node("analyze_request", analyze_request_node)
    builder.add_node("synthesize_response", synthesize_response_node)
    builder.add_node("persist_research_note", lambda state: persist_research_note_node(state, repo))

    builder.add_edge(START, "classify_request")
    builder.add_edge("classify_request", "retrieve_project_context")
    builder.add_edge("retrieve_project_context", "analyze_request")
    builder.add_edge("analyze_request", "synthesize_response")
    builder.add_edge("synthesize_response", "persist_research_note")
    builder.add_edge("persist_research_note", END)

    return builder.compile(checkpointer=checkpointer)
```

- [ ] **Step 5: Replace graph entrypoint with SQLite checkpointer**

Replace `src/graph.py` with:

```python
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

from src.assistant_graph import create_assistant_graph
from src.config import settings
from src.storage.sqlite import ensure_parent_dir


def create_graph():
    db_path = ensure_parent_dir(settings.CHECKPOINT_DB)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    checkpointer.setup()
    return create_assistant_graph(checkpointer=checkpointer)
```

- [ ] **Step 6: Update LangGraph config**

Replace `langgraph.json` with:

```json
{
  "dependencies": [
    "."
  ],
  "graphs": {
    "assistant": "./src/graph.py:create_graph",
    "indexer": "./src/index_graph.py:create_index_graph"
  },
  "env": ".env"
}
```

- [ ] **Step 7: Run tests**

Run:

```bash
/Users/cltx/projects/langgraph/venv/bin/python -m pytest tests/test_assistant_graph.py -v
```

Expected: all tests pass.

- [ ] **Step 8: Verify graph compile manually**

Run:

```bash
/Users/cltx/projects/langgraph/venv/bin/python - <<'PY'
from src.graph import create_graph
app = create_graph()
print(type(app).__name__)
print(sorted(app.get_graph().nodes.keys()))
PY
```

Expected output includes:

```text
CompiledStateGraph
['__end__', '__start__', 'analyze_request', 'classify_request', 'persist_research_note', 'retrieve_project_context', 'synthesize_response']
```

- [ ] **Step 9: Commit**

```bash
git add src/nodes/assistant_nodes.py src/assistant_graph.py src/graph.py langgraph.json tests/test_assistant_graph.py
git commit -m "feat: add assistant graph with sqlite checkpointing"
```

---

### Task 9: Integration Smoke Test and Documentation Updates

**Files:**
- Modify: `tests/test_index_graph.py`
- Modify: `docs/superpowers/specs/2026-07-02-langgraph-project-knowledge-assistant-design.md`

**Interfaces:**
- Consumes all previous task outputs.
- Produces verified smoke coverage for indexing and answering against a temporary C++ project.

- [ ] **Step 1: Add end-to-end smoke test**

Append this to `tests/test_index_graph.py`:

```python
from langgraph.checkpoint.memory import InMemorySaver

from src.assistant_graph import create_assistant_graph


def test_index_then_assistant_answer_end_to_end(tmp_path):
    project = tmp_path / "doll_escort_game_svr"
    (project / "src/map_data").mkdir(parents=True)
    (project / "doc").mkdir()
    (project / "src/map_data/sea_route.cpp").write_text(
        """
// only query route
int query_route(Context* ctx) {
    ctx->mutable_route()->set_state(1);
    send_route_packet(ctx);
    return 0;
}
""",
        encoding="utf-8",
    )
    (project / "doc/readme.md").write_text("# route\n押镖路线说明", encoding="utf-8")

    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    index_graph = create_index_graph(repo)
    index_result = index_graph.invoke({"project_root": str(project), "index_db_path": str(db_path)})
    assert index_result["run_status"] == "success"

    assistant_graph = create_assistant_graph(repo=repo, checkpointer=InMemorySaver())
    answer = assistant_graph.invoke(
        {
            "question": "押镖 route 逻辑在哪里，改动有什么风险？",
            "project_root": str(project),
            "index_db_path": str(db_path),
            "thread_id": "thread-e2e",
        },
        {"configurable": {"thread_id": "thread-e2e"}},
    )

    assert "src/map_data/sea_route.cpp" in answer["answer"]
    assert "置信度" in answer["answer"]
    assert "注释" in answer["answer"] or "命名" in answer["answer"]
```

- [ ] **Step 2: Run smoke test to verify it passes**

Run:

```bash
/Users/cltx/projects/langgraph/venv/bin/python -m pytest tests/test_index_graph.py::test_index_then_assistant_answer_end_to_end -v
```

Expected: PASS.

- [ ] **Step 3: Run full test suite**

Run:

```bash
/Users/cltx/projects/langgraph/venv/bin/python -m pytest tests -v
```

Expected: all tests pass.

- [ ] **Step 4: Run real project read-only scan smoke**

This reads `~/projects/escort_server/doll_escort_game_svr` and writes only this LangGraph project's SQLite index DB. It must not modify the C++ project.

Run:

```bash
/Users/cltx/projects/langgraph/venv/bin/python - <<'PY'
from src.config import settings
from src.index_graph import create_index_graph
from src.storage.project_index import ProjectIndexRepository

repo = ProjectIndexRepository(settings.PROJECT_INDEX_DB)
graph = create_index_graph(repo)
result = graph.invoke({
    "project_root": settings.TARGET_PROJECT_ROOT,
    "index_db_path": settings.PROJECT_INDEX_DB,
})
print("run_status=", result.get("run_status"))
print("scanned_files=", len(result.get("scanned_files", [])))
print("changed_files=", len(result.get("changed_files", [])))
print("errors=", result.get("errors", []))
PY
```

Expected:

```text
run_status= success
scanned_files= <positive integer>
changed_files= <positive integer on first run, possibly 0 on later runs>
errors= []
```

If some files cannot be decoded or read, expected status may be `partial_success`; report exact errors and do not call it complete.

- [ ] **Step 5: Verify target C++ git worktree was not modified**

Run:

```bash
git -C /Users/cltx/projects/escort_server status --short
```

Expected: output must not contain new changes caused by this implementation. Pre-existing changes such as ` M CMakeLists.txt` or `?? ../.idea/` may still appear and must be reported as pre-existing.

- [ ] **Step 6: Update spec implementation status**

Append this section to `docs/superpowers/specs/2026-07-02-langgraph-project-knowledge-assistant-design.md`:

```markdown

## Implementation Status

Initial implementation completed when the corresponding plan at `docs/superpowers/plans/2026-07-02-langgraph-project-knowledge-assistant.md` passes the full test suite and the read-only real-project indexing smoke test. The target C++ project remains read-only unless the user explicitly approves stronger actions.
```

- [ ] **Step 7: Commit**

```bash
git add tests/test_index_graph.py docs/superpowers/specs/2026-07-02-langgraph-project-knowledge-assistant-design.md
git commit -m "test: add project assistant integration smoke test"
```

---

## Self-Review Notes

- Spec coverage: The plan covers SQLite checkpointer, separate project-index SQLite DB, project scanner, incremental content-hash indexing, file summaries, symbols, consistency flags, retriever, assistant graph, research note persistence, target C++ read-only boundary, and old C++ comment/name mismatch risk.
- Scope held: Full AST parsing and Deep Agents are not implemented in this plan. Hermes Agent is not implemented and no longer remains in the evolution route after the 2026-07-03 route update; future memory work moves to the self-developed project memory layer.
- Placeholder scan: This plan contains no intentionally unresolved implementation placeholders. Every task includes concrete file paths, test code, implementation code, commands, and expected outcomes.
- Type consistency: Dataclasses in `src/indexer/models.py`, state keys in `src/state.py`, repository method names in `src/storage/project_index.py`, and graph node names are used consistently across tasks.
