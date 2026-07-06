# Project Memory Layer v1 Design

Date: 2026-07-06

## Purpose

This design defines the first self-developed project knowledge memory layer for the LangGraph Project Knowledge Assistant.

The project has explicitly moved away from Hermes Agent integration. Future memory and self-improvement work should be owned by this repository through local SQLite-backed project memory, retrieval evaluation, proposal-only self-improvement, and approval-aware workflows.

The first version should build the storage and retrieval foundation only. It should not add autonomous coding, target-project mutation, automatic memory application, or Hermes handoff behavior.

## Goals

- Add a durable `project_memories` table separate from `research_notes`.
- Keep `research_notes` as per-question/per-investigation history.
- Store reusable long-term project knowledge in `project_memories`.
- Support typed memories for core project-assistant use cases.
- Preserve evidence, related paths, source note links, status, confidence, and flow version.
- Provide repository APIs and a thin retriever wrapper for listing and searching project memories.
- Keep current implementation evidence higher authority than historical notes or project memories.
- Keep the target C++ project read-only by default.

## Non-Goals

- Do not integrate Hermes.
- Do not add a non-null Hermes adapter.
- Do not add autonomous coding or target C++ project mutation.
- Do not auto-apply improvement proposals.
- Do not automatically generate or promote memories from assistant answers in v1.
- Do not wire project memories into final assistant answers in v1.
- Do not replace current project-index retrieval with project memory retrieval.
- Do not introduce external embedding providers.

## Core Boundary

`research_notes` and `project_memories` serve different purposes.

### `research_notes`

`research_notes` are historical records of individual assistant interactions or investigations.

They are useful for follow-up context, but they are not authoritative current facts. They may be repeated, incomplete, stale, or based on earlier assistant conclusions.

### `project_memories`

`project_memories` are curated long-term project knowledge entries.

They should be reusable across sessions and structured enough to support future memory reflection, retrieval lessons, stale-memory demotion, and proposal review. They still do not outrank current indexed implementation evidence.

Authority order remains:

```text
current source implementation evidence
  > current index summaries / symbols / consistency flags
  > active project memories
  > historical research notes
  > comments / documentation / names alone
```

## Memory Types

Version 1 supports five memory types:

```text
domain_concept
implementation_fact
risk_note
open_question
retrieval_lesson
```

### `domain_concept`

A reusable business or technical concept, such as escort-car movement, second-route queries, or cross-map route cost.

Expected use:

- Explain business terms.
- Help future retrieval and research workflows find relevant code areas.
- Link business language to implementation paths.

### `implementation_fact`

A current implementation fact grounded in indexed code evidence.

Expected use:

- Record which files or symbols implement a behavior.
- Preserve implementation understanding across sessions.
- Support impact analysis.

Requirement:

- Must include `related_paths`.
- Should include `evidence_refs` when available.

### `risk_note`

A reusable risk or caution discovered through code evidence or repeated research.

Expected use:

- Warn during development advice.
- Preserve known risky areas such as route recalculation side effects, misleading names, stale comments, or hidden writes.

### `open_question`

An unresolved question that should not be answered as fact.

Expected use:

- Prevent the assistant from pretending uncertainty is resolved.
- Provide future research entry points.

### `retrieval_lesson`

A reusable lesson about retrieval behavior, ranking, query intent, synonyms, or eval results.

Expected use:

- Inform future retrieval proposals.
- Record why a ranking rule exists.
- Connect retrieval eval failures to future improvements.

Requirement:

- Must not directly mutate retrieval rules.
- Can be used as evidence for a pending improvement proposal.

## SQLite Schema

Add a new table:

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
```

Add indexes:

```sql
CREATE INDEX IF NOT EXISTS idx_project_memories_project_root ON project_memories(project_root);
CREATE INDEX IF NOT EXISTS idx_project_memories_type ON project_memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_project_memories_status ON project_memories(status);
CREATE INDEX IF NOT EXISTS idx_project_memories_updated_at ON project_memories(updated_at);
```

Do not add a uniqueness constraint in v1. Memory deduplication should be designed later after real usage reveals whether the natural key should be based on project root, memory type, subject, related paths, source notes, or evidence refs.

## Data Model

Add a dataclass in `src/indexer/models.py`:

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

All JSON-like fields are stored as strings in SQLite and returned as lists by repository search/list APIs.

## Repository API

Extend `ProjectIndexRepository` with:

```python
def insert_project_memory(self, memory: ProjectMemory) -> int: ...
```

```python
def list_project_memories(
    self,
    *,
    project_root: str = "",
    memory_type: str | None = None,
    status: str = "active",
    limit: int = 20,
) -> list[dict]: ...
```

```python
def search_project_memories(
    self,
    query: str,
    *,
    project_root: str = "",
    memory_type: str | None = None,
    status: str = "active",
    limit: int = 5,
) -> list[dict]: ...
```

```python
def update_project_memory_status(self, memory_id: int, status: str) -> None: ...
```

Repository output must be serializable. It should parse these JSON fields into lists:

- `evidence_refs`
- `related_paths`
- `source_note_ids`

Search results should include:

```python
{
    "source": "project_memory",
    "score": <int>,
    ...
}
```

## Search Behavior

`search_project_memories()` should use simple deterministic token scoring in v1.

Searchable fields:

- `memory_type`
- `subject`
- `summary`
- `evidence_refs`
- `related_paths`
- `source_note_ids`
- `confidence`
- `status`

Use the existing lightweight Chinese/English synonym style already used for research notes and keyword retrieval. At minimum, support useful project terms such as:

```text
路线 -> route
重算 -> recalc, recalculation
押镖 -> escort
风险 -> risk
调研 -> research
记忆 -> memory
移动 -> move, movement
查询 -> query
二段 -> second route
```

Default search should return only `status="active"` memories unless a caller explicitly asks for another status.

Supported statuses in v1:

```text
active
stale
rejected
superseded
```

The repository should not enforce an enum at the SQLite level in v1, but tests should cover the expected statuses.

## Retriever Wrapper

Create a thin wrapper:

```text
src/retriever/project_memory.py
```

Public function:

```python
def search_project_memory(
    db_path: str | Path,
    query: str,
    *,
    project_root: str = "",
    memory_type: str | None = None,
    status: str = "active",
    limit: int = 5,
) -> list[dict]: ...
```

This should mirror `src/retriever/research_memory.py` and delegate to `ProjectIndexRepository.search_project_memories()`.

## Assistant Integration Policy

Version 1 should not automatically include project memories in final assistant answers.

Rationale:

- The assistant already combines current index context and research memory.
- Adding project memories to final synthesis changes answer semantics and needs separate tests for conflict handling.
- The first layer should stabilize storage and retrieval before answer integration.

A later version may add:

```text
retrieve_project_memories_node
  -> analyze_request
  -> synthesize_response
```

When that happens, final Chinese answers must label project memories separately and must say that current implementation evidence wins if memory conflicts with current index evidence.

## Migration Requirements

Schema changes must be backward compatible.

Implementation must update:

- `src/storage/schema.sql`
- `src/storage/migrations.py`
- `src/indexer/models.py`
- `src/storage/project_index.py`
- `src/retriever/project_memory.py`
- tests
- README/history docs

`init_schema()` must create the table on a fresh DB and migrate an old DB idempotently.

## Testing Requirements

Add or extend tests to cover:

### Storage and migration

- Fresh DB includes `project_memories`.
- Running `init_schema()` repeatedly is safe.
- Existing DBs are migrated with `project_memories` and indexes.

### Repository APIs

- Insert a `ProjectMemory` and get an integer ID.
- List active memories by project root.
- Filter by `memory_type`.
- Filter by `status`.
- Search by Chinese query and match English summaries via synonym expansion.
- JSON string fields return as Python lists.
- `update_project_memory_status()` changes visibility under default active search/list behavior.

### Retriever wrapper

- `search_project_memory()` returns serializable `source="project_memory"` hits.
- `project_root` filtering works.
- inactive/stale memories do not appear by default.

## Documentation Requirements

Update README to mention:

- `project_memories` as the self-developed long-term memory layer.
- `research_notes` versus `project_memories` boundary.
- Current-code-evidence authority over project memories.

Append the dated development history entry with:

- Change summary.
- Completed functionality.
- Affected files.
- Verification commands and results.
- Follow-ups.

## Safety Requirements

This work must not modify the target C++ project:

```text
/Users/cltx/projects/escort_server/doll_escort_game_svr
```

It may only modify this LangGraph assistant repository and local test SQLite databases.

No build, edit, commit, push, clean, delete, or dependency-changing action may be run against the target C++ project without explicit user approval.

## Success Criteria

The v1 project memory layer is complete when:

- `project_memories` exists on fresh and migrated SQLite databases.
- Project memories can be inserted, listed, searched, and status-updated through repository APIs.
- A thin retriever wrapper exists.
- Search supports mixed Chinese/English project queries.
- JSON fields are returned as lists.
- Default listing/search excludes non-active memories.
- Current tests and new focused tests pass.
- README and dated history are updated.
- No assistant answer behavior changes are introduced in v1.
