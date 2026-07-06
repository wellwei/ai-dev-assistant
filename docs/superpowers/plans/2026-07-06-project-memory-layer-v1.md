# Project Memory Layer v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first self-developed SQLite-backed project memory layer with durable `project_memories`, repository APIs, and a thin retriever wrapper.

**Architecture:** Keep `research_notes` as per-investigation history and add `project_memories` as curated long-term project knowledge. Implement this as an additive SQLite schema/migration plus repository methods and a wrapper in `src/retriever/project_memory.py`; do not wire project memories into assistant answers in v1.

**Tech Stack:** Python 3.14, LangGraph, SQLite, pytest, repository-local deterministic token scoring.

## Global Constraints

- Do not integrate Hermes.
- Do not add a non-null Hermes adapter.
- Do not add autonomous coding or target C++ project mutation.
- Do not auto-apply improvement proposals.
- Do not automatically generate or promote memories from assistant answers in v1.
- Do not wire project memories into final assistant answers in v1.
- Do not replace current project-index retrieval with project memory retrieval.
- Do not introduce external embedding providers.
- Current source implementation evidence outranks current index summaries / symbols / consistency flags, which outrank active project memories, which outrank historical research notes, which outrank comments / documentation / names alone.
- Do not modify `/Users/cltx/projects/escort_server/doll_escort_game_svr`.
- Update `README.md` and append an entry to `docs/superpowers/history/2026-07-03-development-history.md` for this implementation.
- Use TDD: every production behavior change must have a failing test observed first.

---

## File Structure

- Modify `src/indexer/models.py`
  - Add `ProjectMemory` dataclass for project memory inserts.

- Modify `src/storage/schema.sql`
  - Add fresh-DB `project_memories` table and indexes.

- Modify `src/storage/migrations.py`
  - Add idempotent migration for `project_memories` table and indexes.

- Modify `src/storage/project_index.py`
  - Import `ProjectMemory`.
  - Expand token synonyms for project-memory search terms.
  - Add helper for serializing `project_memories` rows.
  - Add `insert_project_memory()`.
  - Add `list_project_memories()`.
  - Add `search_project_memories()`.
  - Add `update_project_memory_status()`.

- Create `src/retriever/project_memory.py`
  - Add `search_project_memory()` wrapper mirroring `src/retriever/research_memory.py`.

- Modify `tests/test_storage.py`
  - Add schema/migration/repository tests for project memories.

- Modify `tests/test_retriever.py`
  - Add retriever wrapper tests for project memory search, project-root filtering, and inactive status exclusion.

- Modify `README.md`
  - Document the `research_notes` versus `project_memories` boundary.
  - Mention `project_memories` as self-developed long-term memory.
  - Keep current-code-evidence authority explicit.
  - Update expected test baseline if it changes.

- Modify `docs/superpowers/history/2026-07-03-development-history.md`
  - Append implementation history entry with verification results.

---

### Task 1: Add ProjectMemory schema and migration

**Files:**
- Modify: `src/indexer/models.py`
- Modify: `src/storage/schema.sql`
- Modify: `src/storage/migrations.py`
- Modify: `tests/test_storage.py`

**Interfaces:**
- Consumes: existing `connect_db()`, `init_schema()`, and SQLite migration pattern.
- Produces: `ProjectMemory` dataclass and fresh/migrated `project_memories` table with indexes.

- [ ] **Step 1: Write the failing schema/model test**

Add `ProjectMemory` to the import block in `tests/test_storage.py`:

```python
from src.indexer.models import (
    ConsistencyFlag,
    FileSummary,
    ProjectFile,
    ProjectMemory,
    ResearchNote,
    SymbolInfo,
)
```

Extend `EXPECTED_TABLES` near the top of `tests/test_storage.py`:

```python
EXPECTED_TABLES = {
    "files",
    "file_summaries",
    "symbols",
    "doc_summaries",
    "research_notes",
    "index_runs",
    "consistency_flags",
    "improvement_proposals",
    "embeddings",
    "project_memories",
}
```

Add this test after `test_init_schema_migrates_old_research_notes_before_creating_new_indexes`:

```python
def test_init_schema_adds_project_memories_table_and_indexes_idempotently(tmp_path):
    db_path = tmp_path / "project_index.sqlite"

    with connect_db(db_path) as conn:
        init_schema(conn)
        init_schema(conn)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(project_memories)").fetchall()}
        indexes = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'project_memories'"
            ).fetchall()
        }

    assert {
        "id",
        "project_root",
        "memory_type",
        "subject",
        "summary",
        "evidence_refs",
        "related_paths",
        "source_note_ids",
        "confidence",
        "status",
        "created_at",
        "updated_at",
        "flow_version",
    }.issubset(columns)
    assert {
        "idx_project_memories_project_root",
        "idx_project_memories_type",
        "idx_project_memories_status",
        "idx_project_memories_updated_at",
    }.issubset(indexes)
```

- [ ] **Step 2: Run the failing schema/model test**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests/test_storage.py::test_init_schema_adds_project_memories_table_and_indexes_idempotently -v
```

Expected: FAIL because `ProjectMemory` cannot be imported or `project_memories` does not exist yet.

- [ ] **Step 3: Add the `ProjectMemory` dataclass**

Append this to `src/indexer/models.py` after `ImprovementProposal`:

```python
@dataclass(frozen=True)
class ProjectMemory:
    project_root: str
    memory_type: str
    subject: str
    summary: str
    evidence_refs: str = "[]"
    related_paths: str = "[]"
    source_note_ids: str = "[]"
    confidence: str = "low"
    status: str = "active"
    flow_version: str = ""
```

- [ ] **Step 4: Add fresh schema table and indexes**

In `src/storage/schema.sql`, add this block after the `improvement_proposals` indexes and before `index_runs`:

```sql
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
);

CREATE INDEX IF NOT EXISTS idx_project_memories_project_root ON project_memories(project_root);
CREATE INDEX IF NOT EXISTS idx_project_memories_type ON project_memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_project_memories_status ON project_memories(status);
CREATE INDEX IF NOT EXISTS idx_project_memories_updated_at ON project_memories(updated_at);
```

- [ ] **Step 5: Add migration table and indexes**

In `src/storage/migrations.py`, add this block after the `improvement_proposals` table/index creation and before the `embeddings` table creation:

```python
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
```

- [ ] **Step 6: Run schema/model tests to verify green**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests/test_storage.py::test_init_schema_creates_project_index_tables /Users/cltx/projects/langgraph/tests/test_storage.py::test_init_schema_adds_project_memories_table_and_indexes_idempotently -v
```

Expected: PASS.

- [ ] **Step 7: Commit Task 1**

Run:

```bash
git -C /Users/cltx/projects/langgraph add src/indexer/models.py src/storage/schema.sql src/storage/migrations.py tests/test_storage.py
git -C /Users/cltx/projects/langgraph commit -m "feat: add project memories schema"
```

---

### Task 2: Add ProjectIndexRepository project memory APIs

**Files:**
- Modify: `src/storage/project_index.py`
- Modify: `tests/test_storage.py`

**Interfaces:**
- Consumes: `ProjectMemory` dataclass and `project_memories` table from Task 1.
- Produces:
  - `ProjectIndexRepository.insert_project_memory(memory: ProjectMemory) -> int`
  - `ProjectIndexRepository.list_project_memories(project_root='', memory_type=None, status='active', limit=20) -> list[dict]`
  - `ProjectIndexRepository.search_project_memories(query, project_root='', memory_type=None, status='active', limit=5) -> list[dict]`
  - `ProjectIndexRepository.update_project_memory_status(memory_id: int, status: str) -> None`

- [ ] **Step 1: Write the failing repository API test**

Add this test to `tests/test_storage.py` after `test_repository_searches_research_notes_by_project_root_and_summary`:

```python
def test_repository_inserts_lists_searches_and_updates_project_memories(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()

    first_id = repo.insert_project_memory(
        ProjectMemory(
            project_root="/tmp/project-a",
            memory_type="risk_note",
            subject="Escort route recalculation risk",
            summary="Route recalculation may update escort state and send packets.",
            evidence_refs='[{"path":"src/route.cpp","line_start":10,"line_end":20}]',
            related_paths='["src/route.cpp"]',
            source_note_ids="[1, 2]",
            confidence="medium",
            flow_version="test-flow",
        )
    )
    repo.insert_project_memory(
        ProjectMemory(
            project_root="/tmp/project-b",
            memory_type="risk_note",
            subject="Other project risk",
            summary="Other project route risk.",
            related_paths='["src/other.cpp"]',
            confidence="medium",
        )
    )
    repo.insert_project_memory(
        ProjectMemory(
            project_root="/tmp/project-a",
            memory_type="domain_concept",
            subject="Escort movement",
            summary="Escort car movement domain concept.",
            related_paths='["src/move.cpp"]',
            confidence="low",
            status="stale",
        )
    )

    listed = repo.list_project_memories(project_root="/tmp/project-a")
    searched = repo.search_project_memories("押镖 路线 风险", project_root="/tmp/project-a")
    stale = repo.list_project_memories(project_root="/tmp/project-a", status="stale")

    assert first_id == 1
    assert [item["id"] for item in listed] == [first_id]
    assert listed[0]["source"] == "project_memory"
    assert listed[0]["related_paths"] == ["src/route.cpp"]
    assert listed[0]["source_note_ids"] == [1, 2]
    assert listed[0]["evidence_refs"] == [{"path": "src/route.cpp", "line_start": 10, "line_end": 20}]
    assert searched[0]["id"] == first_id
    assert searched[0]["score"] > 0
    assert stale[0]["memory_type"] == "domain_concept"

    repo.update_project_memory_status(first_id, "stale")

    assert repo.list_project_memories(project_root="/tmp/project-a") == []
    assert repo.list_project_memories(project_root="/tmp/project-a", status="stale")[0]["id"] == first_id
```

- [ ] **Step 2: Run the failing repository API test**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests/test_storage.py::test_repository_inserts_lists_searches_and_updates_project_memories -v
```

Expected: FAIL because the repository methods do not exist.

- [ ] **Step 3: Import `ProjectMemory` in repository**

In `src/storage/project_index.py`, update the import block to include `ProjectMemory`:

```python
from src.indexer.models import (
    ConsistencyFlag,
    FileSummary,
    ImprovementProposal,
    ProjectFile,
    ProjectMemory,
    ResearchNote,
    SymbolInfo,
)
```

- [ ] **Step 4: Expand token synonyms for memory search**

In `_tokens()` in `src/storage/project_index.py`, extend `synonym_map` to include:

```python
        "移动": ["move", "movement"],
        "查询": ["query"],
        "二段": ["second route"],
```

The full map should remain a normal dictionary with the existing entries preserved.

- [ ] **Step 5: Add a project-memory row serializer helper**

In `src/storage/project_index.py`, add this helper near `_json_list()`:

```python
def _project_memory_item(row) -> dict:
    item = dict(row)
    item["source"] = "project_memory"
    item["evidence_refs"] = _json_list(item.get("evidence_refs"))
    item["related_paths"] = _json_list(item.get("related_paths"))
    item["source_note_ids"] = _json_list(item.get("source_note_ids"))
    return item
```

- [ ] **Step 6: Add `insert_project_memory()`**

In `ProjectIndexRepository`, add this method after `list_improvement_proposals()`:

```python
    def insert_project_memory(self, memory: ProjectMemory) -> int:
        with connect_db(self.db_path) as conn:
            init_schema(conn)
            cur = conn.execute(
                """
                INSERT INTO project_memories(
                    project_root, memory_type, subject, summary, evidence_refs,
                    related_paths, source_note_ids, confidence, status,
                    created_at, updated_at, flow_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), ?)
                """,
                (
                    memory.project_root,
                    memory.memory_type,
                    memory.subject,
                    memory.summary,
                    memory.evidence_refs,
                    memory.related_paths,
                    memory.source_note_ids,
                    memory.confidence,
                    memory.status,
                    memory.flow_version,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)
```

- [ ] **Step 7: Add `list_project_memories()`**

Add this method after `insert_project_memory()`:

```python
    def list_project_memories(
        self,
        *,
        project_root: str = "",
        memory_type: str | None = None,
        status: str = "active",
        limit: int = 20,
    ) -> list[dict]:
        clauses = []
        params: list[str | int] = []
        if project_root:
            clauses.append("project_root = ?")
            params.append(project_root)
        if memory_type is not None:
            clauses.append("memory_type = ?")
            params.append(memory_type)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        params.append(limit)
        with connect_db(self.db_path) as conn:
            init_schema(conn)
            rows = conn.execute(
                f"SELECT * FROM project_memories {where} ORDER BY updated_at DESC, id DESC LIMIT ?",
                params,
            ).fetchall()
        return [_project_memory_item(row) for row in rows]
```

- [ ] **Step 8: Add `search_project_memories()`**

Add this method after `list_project_memories()`:

```python
    def search_project_memories(
        self,
        query: str,
        *,
        project_root: str = "",
        memory_type: str | None = None,
        status: str = "active",
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
        if memory_type is not None:
            clauses.append("memory_type = ?")
            params.append(memory_type)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        with connect_db(self.db_path) as conn:
            init_schema(conn)
            rows = conn.execute(
                f"""
                SELECT * FROM project_memories
                {where}
                ORDER BY updated_at DESC, id DESC
                """,
                params,
            ).fetchall()
        hits: list[dict] = []
        for row in rows:
            item = _project_memory_item(row)
            item["score"] = _score(item, tokens)
            if item["score"] <= 0:
                continue
            hits.append(item)
        return sorted(hits, key=lambda item: item["score"], reverse=True)[:limit]
```

- [ ] **Step 9: Add `update_project_memory_status()`**

Add this method after `search_project_memories()`:

```python
    def update_project_memory_status(self, memory_id: int, status: str) -> None:
        with connect_db(self.db_path) as conn:
            init_schema(conn)
            conn.execute(
                """
                UPDATE project_memories
                SET status = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (status, memory_id),
            )
            conn.commit()
```

- [ ] **Step 10: Run the repository API test to verify green**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests/test_storage.py::test_repository_inserts_lists_searches_and_updates_project_memories -v
```

Expected: PASS.

- [ ] **Step 11: Run all storage tests**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests/test_storage.py -v
```

Expected: PASS.

- [ ] **Step 12: Commit Task 2**

Run:

```bash
git -C /Users/cltx/projects/langgraph add src/storage/project_index.py tests/test_storage.py
git -C /Users/cltx/projects/langgraph commit -m "feat: add project memory repository APIs"
```

---

### Task 3: Add project memory retriever wrapper

**Files:**
- Create: `src/retriever/project_memory.py`
- Modify: `tests/test_retriever.py`

**Interfaces:**
- Consumes: `ProjectIndexRepository.search_project_memories()` from Task 2.
- Produces:
  - `search_project_memory(db_path, query, project_root='', memory_type=None, status='active', limit=5) -> list[dict]`

- [ ] **Step 1: Write the failing retriever wrapper test**

Update imports at the top of `tests/test_retriever.py`:

```python
from src.indexer.models import FileSummary, ProjectFile, ProjectMemory, ResearchNote, SymbolInfo
```

Add this import:

```python
from src.retriever.project_memory import search_project_memory
```

Add this test after `test_search_research_memory_returns_serializable_note_hits`:

```python
def test_search_project_memory_returns_serializable_active_hits(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()
    memory_id = repo.insert_project_memory(
        ProjectMemory(
            project_root="/tmp/project",
            memory_type="implementation_fact",
            subject="Escort movement implementation",
            summary="Escort car movement is implemented by move handlers.",
            evidence_refs='[{"path":"src/move.cpp","line_start":1,"line_end":20}]',
            related_paths='["src/move.cpp"]',
            source_note_ids="[7]",
            confidence="medium",
        )
    )
    repo.insert_project_memory(
        ProjectMemory(
            project_root="/tmp/project",
            memory_type="implementation_fact",
            subject="Stale escort movement implementation",
            summary="Old movement note.",
            related_paths='["src/old_move.cpp"]',
            status="stale",
        )
    )
    repo.insert_project_memory(
        ProjectMemory(
            project_root="/tmp/other-project",
            memory_type="implementation_fact",
            subject="Other escort movement implementation",
            summary="Other project move handlers.",
            related_paths='["src/other.cpp"]',
        )
    )

    hits = search_project_memory(db_path, "押镖 移动", project_root="/tmp/project")

    assert [hit["id"] for hit in hits] == [memory_id]
    assert hits[0]["source"] == "project_memory"
    assert hits[0]["related_paths"] == ["src/move.cpp"]
    assert hits[0]["source_note_ids"] == [7]
    assert hits[0]["evidence_refs"] == [{"path": "src/move.cpp", "line_start": 1, "line_end": 20}]
```

- [ ] **Step 2: Run the failing retriever wrapper test**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests/test_retriever.py::test_search_project_memory_returns_serializable_active_hits -v
```

Expected: FAIL because `src.retriever.project_memory` does not exist.

- [ ] **Step 3: Create retriever wrapper**

Create `src/retriever/project_memory.py` with exactly:

```python
from pathlib import Path

from src.storage.project_index import ProjectIndexRepository


def search_project_memory(
    db_path: str | Path,
    query: str,
    *,
    project_root: str = "",
    memory_type: str | None = None,
    status: str = "active",
    limit: int = 5,
) -> list[dict]:
    repo = ProjectIndexRepository(db_path)
    return repo.search_project_memories(
        query,
        project_root=project_root,
        memory_type=memory_type,
        status=status,
        limit=limit,
    )
```

- [ ] **Step 4: Run retriever wrapper test to verify green**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests/test_retriever.py::test_search_project_memory_returns_serializable_active_hits -v
```

Expected: PASS.

- [ ] **Step 5: Run focused retriever/storage tests**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests/test_storage.py /Users/cltx/projects/langgraph/tests/test_retriever.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 3**

Run:

```bash
git -C /Users/cltx/projects/langgraph add src/retriever/project_memory.py tests/test_retriever.py
git -C /Users/cltx/projects/langgraph commit -m "feat: add project memory retriever"
```

---

### Task 4: Update documentation and development history

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/history/2026-07-03-development-history.md`

**Interfaces:**
- Consumes: implementation from Tasks 1-3.
- Produces: documented project memory boundary, verification history, and current test baseline.

- [ ] **Step 1: Update README project structure**

In `README.md`, under `src/retriever/`, add:

```text
    project_memory.py        # Long-term project memory retrieval
```

Under `src/storage/`, keep existing schema/repository entries and add no new directory.

- [ ] **Step 2: Update README retrieval and memory section**

In `README.md`, in `## Retrieval and Memory`, add this paragraph after the retrieval bullet list:

```markdown
Project memory uses two layers:

- `research_notes` record individual assistant investigations and historical answers.
- `project_memories` store curated long-term project knowledge such as domain concepts, implementation facts, risk notes, open questions, and retrieval lessons.

Current implementation evidence still outranks project memories. Project memories are durable guidance, not source-of-truth replacements for indexed code evidence.
```

- [ ] **Step 3: Update README expected test baseline**

After running the final full suite in Task 5, update the `Expected current baseline` block in `README.md` to the observed count. If the final full suite still reports `61 passed`, keep:

```text
61 passed
```

If the count changes because new tests were added, replace the number with the exact final result.

- [ ] **Step 4: Append development history entry**

Append this entry to `docs/superpowers/history/2026-07-03-development-history.md`. Replace the verification counts in Task 5 if the final counts differ:

```markdown

### Project Memory Layer v1 Foundation

- Change summary: Added the first self-developed long-term project memory layer foundation.
- Completed or modified functionality:
  - Added the `project_memories` SQLite table and idempotent migration indexes.
  - Added the `ProjectMemory` dataclass.
  - Added repository APIs to insert, list, search, and status-update project memories.
  - Added the `src/retriever/project_memory.py` wrapper for serializable memory search.
  - Kept project memories separate from `research_notes`; research notes remain per-investigation history, while project memories store curated long-term knowledge.
  - Kept project memories out of assistant answer synthesis in v1.
  - Did not modify the target C++ project.
- Affected files or modules:
  - `src/indexer/models.py`
  - `src/storage/schema.sql`
  - `src/storage/migrations.py`
  - `src/storage/project_index.py`
  - `src/retriever/project_memory.py`
  - `tests/test_storage.py`
  - `tests/test_retriever.py`
  - `README.md`
  - `docs/superpowers/history/2026-07-03-development-history.md`
- Verification:
  - Project memory schema test was first observed failing before implementation.
  - Project memory repository API test was first observed failing before implementation.
  - Project memory retriever wrapper test was first observed failing before implementation.
  - Focused storage and retriever tests passed.
  - Full test-suite run passed with `<FINAL_COUNT> passed`.
- Follow-ups:
  - Add `retrieve_project_memories_node` only after separate answer-conflict tests are designed.
  - Add memory reflection that drafts project memories from repeated research notes, but keep it proposal/review based.
  - Add stale-memory demotion and deduplication after real usage shows the right natural keys.
```

- [ ] **Step 5: Commit Task 4 after Task 5 verification updates counts**

Do not commit this task until Task 5 has run the final full suite and the history entry contains exact counts.

Run after updating counts:

```bash
git -C /Users/cltx/projects/langgraph add README.md docs/superpowers/history/2026-07-03-development-history.md
git -C /Users/cltx/projects/langgraph commit -m "docs: document project memory layer"
```

---

### Task 5: Final verification

**Files:**
- No new files; update README/history counts if needed.

**Interfaces:**
- Consumes: all implementation and docs from Tasks 1-4.
- Produces: final verified baseline and handoff-ready branch state.

- [ ] **Step 1: Run storage tests**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests/test_storage.py -v
```

Expected: PASS.

- [ ] **Step 2: Run retriever tests**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests/test_retriever.py -v
```

Expected: PASS.

- [ ] **Step 3: Run full test suite**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests -v
```

Expected: PASS. Record the exact final count.

- [ ] **Step 4: Update README/history counts if final count changed**

If the full suite count differs from the current README/history placeholders, edit:

- `README.md` expected baseline.
- `docs/superpowers/history/2026-07-03-development-history.md` Task 4 history entry.

Use the exact string from pytest, such as:

```text
64 passed
```

- [ ] **Step 5: Run final full suite again if docs/count edits changed tests or if any test changed**

If only README/history counts changed after a passing full suite, no second full suite is necessary. If any Python or test file changed after Step 3, rerun:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests -v
```

Expected: PASS.

- [ ] **Step 6: Confirm no target C++ project mutation**

Run:

```bash
git -C /Users/cltx/projects/escort_server/doll_escort_game_svr status --short
```

Expected: Either clean or only pre-existing user changes. Do not modify anything in that repository.

- [ ] **Step 7: Commit any final count/doc updates if Task 4 was not already committed**

If Task 4 commit was deferred until after final verification, run:

```bash
git -C /Users/cltx/projects/langgraph add README.md docs/superpowers/history/2026-07-03-development-history.md
git -C /Users/cltx/projects/langgraph commit -m "docs: record project memory verification"
```

- [ ] **Step 8: Report final status**

Report:

- Implemented files.
- Focused tests run.
- Full suite result.
- Target C++ project mutation status.
- Remaining follow-ups.

---

## Self-Review Notes

- Spec coverage: The plan covers schema, migration, dataclass, repository APIs, retriever wrapper, tests, README, history, and safety constraints from `docs/superpowers/specs/2026-07-06-project-memory-layer-v1-design.md`.
- Placeholder scan: The plan contains no TBD/TODO/fill-in placeholders. The only variable marker is `<FINAL_COUNT>` inside the history entry template, and Task 4/Task 5 explicitly require replacing it with the exact pytest count before committing.
- Type consistency: `ProjectMemory`, `insert_project_memory`, `list_project_memories`, `search_project_memories`, `update_project_memory_status`, and `search_project_memory` names are consistent across tasks.
- Scope check: The plan intentionally excludes assistant answer integration, memory reflection graph, Hermes, autonomous coding, and target C++ project mutation.
