# LangGraph Project Knowledge Assistant

Agent operating guide for Codex, Claude Code, and similar coding agents.

This repository implements a LangGraph-based project knowledge assistant for the read-only target C++ project:

```text
/Users/cltx/projects/escort_server/doll_escort_game_svr
```

The assistant indexes that project into local SQLite storage, answers project questions, supports requirement research, produces read-only development advice, reuses research memory, and records self-improvement proposals without applying them automatically.

## Read This First

Before making changes, agents should read these files in order:

1. `README.md`
2. `docs/superpowers/specs/2026-07-02-langgraph-project-knowledge-assistant-design.md`
3. The latest dated file in `docs/superpowers/history/`
4. `docs/superpowers/plans/2026-07-02-langgraph-project-knowledge-assistant.md` when executing or extending the implementation plan
5. Relevant tests for the module being changed

The development history is mandatory. Every code, design, behavior, retrieval ranking, schema, safety boundary, or documentation rule change must append an entry to:

```text
docs/superpowers/history/YYYY-MM-DD-development-history.md
```

## Agent Rules

- Keep the target C++ project read-only unless the user explicitly approves stronger actions.
- Do not edit, build, commit, push, clean, delete, or otherwise mutate `/Users/cltx/projects/escort_server/doll_escort_game_svr` by default.
- It is acceptable to update this repository's SQLite index files under `checkpoints/` when refreshing the project index.
- Internal model-facing text must be English, including prompts, node analysis, `analysis`, `open_questions`, `suggested_commands`, workflow steps, and internal memory summaries.
- Final user-facing `answer` text must be Chinese.
- Do not paste English internal analysis into the final Chinese answer.
- Current implementation evidence outranks comments, documentation, names, and historical assistant memory.
- Historical research notes are useful context, but they must be labeled as historical assistant conclusions and must not outrank current index evidence.
- Development advice is read-only and approval-gated. Do not directly modify the target C++ project from this assistant.
- Do not continue Hermes Agent integration work. The existing Hermes no-op boundary is historical and disabled; keep it inert until an explicit cleanup removes it.
- Self-improvement proposals must remain proposals until an explicit review and approval workflow exists.
- Future memory and self-improvement work should use a self-developed project memory layer, not Hermes Agent.

## Project Structure

```text
src/
  assistant_graph.py          # Main assistant graph factory
  index_graph.py              # Project indexing graph factory
  graph.py                    # LangGraph Studio assistant entrypoint
  state.py                    # IndexState and AssistantState

  nodes/
    assistant_nodes.py        # Assistant graph node implementations
    index_nodes.py            # Index graph node implementations

  indexer/
    scanner.py                # File scanning
    classifier.py             # File classification
    symbol_extractor.py       # C++ symbol extraction
    summarizer.py             # File summary generation
    consistency.py            # Consistency flag detection
    confidence.py             # Conservative confidence helpers
    version.py                # Indexer version

  retriever/
    keyword_search.py         # Weighted keyword retrieval
    vector_search.py          # Local vector-like search storage
    hybrid_search.py          # Hybrid retrieval orchestration
    research_memory.py        # Prior research note retrieval
    context_builder.py        # Context assembly

  storage/
    schema.sql                # SQLite schema
    migrations.py             # Idempotent migrations
    sqlite.py                 # Connection and schema initialization
    project_index.py          # Repository API

  workflows/
    registry.py               # Skill-like read-only workflow registry

  integrations/
    hermes.py                 # Deprecated disabled Hermes no-op boundary

  self_improvement/
    proposals.py              # Pending improvement proposal generation
```

The old autonomous `planner -> coder -> tester -> reviewer` path has been removed from the active design. Do not reintroduce it as the main assistant flow.

## Environment

Default configuration lives in `src/config.py` and `.env.example`.

Important variables:

```text
TARGET_PROJECT_ROOT=/Users/cltx/projects/escort_server/doll_escort_game_svr
CHECKPOINT_DB=./checkpoints/langgraph.sqlite
PROJECT_INDEX_DB=./checkpoints/project_index.sqlite
MODEL_NAME=gpt-4o
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
```

Current embedding support is local and deterministic. It does not require an external embedding API or secret.

## LangGraph Entrypoints

`langgraph.json` exposes two graphs:

```json
{
  "graphs": {
    "assistant": "./src/graph.py:create_graph",
    "indexer": "./src/index_graph.py:create_index_graph"
  }
}
```

### Index Graph

Purpose: scan the target project, detect changed files, extract symbols, summarize files, detect consistency flags, and write the SQLite project index.

Flow:

```text
scan_project
  -> detect_changed_files
  -> classify_files
  -> extract_symbols
  -> summarize_implementation
  -> detect_consistency_flags
  -> write_index
```

Programmatic use:

```python
from src.index_graph import create_index_graph

graph = create_index_graph()
result = graph.invoke({
    "project_root": "/Users/cltx/projects/escort_server/doll_escort_game_svr",
    "index_db_path": "./checkpoints/project_index.sqlite",
})
```

### Assistant Graph

Purpose: classify the user request, select a read-only workflow, retrieve prior research memory, retrieve current project context, analyze, synthesize a Chinese answer, and persist the research note.

Flow:

```text
classify_request
  -> select_workflow
  -> retrieve_research_memory
  -> retrieve_project_context
  -> analyze_request
  -> synthesize_response
  -> persist_research_note
```

Programmatic use:

```python
from langgraph.checkpoint.memory import InMemorySaver
from src.assistant_graph import create_assistant_graph

graph = create_assistant_graph(checkpointer=InMemorySaver())
result = graph.invoke(
    {
        "question": "押镖 route 重算在哪里？",
        "project_root": "/Users/cltx/projects/escort_server/doll_escort_game_svr",
        "index_db_path": "./checkpoints/project_index.sqlite",
        "thread_id": "doll_escort_game_svr:research:route-recalc",
    },
    {"configurable": {"thread_id": "doll_escort_game_svr:research:route-recalc"}},
)
```

## Retrieval and Memory

Retrieval currently combines:

- Weighted keyword search.
- Path, symbol, and file-type signals.
- Business-source boosts and config/build noise penalties.
- Local deterministic vector-like retrieval.
- Prior research memory retrieval.

The assistant's project-context retrieval path uses `hybrid_search_project()` first, with keyword retrieval as a conservative fallback if hybrid retrieval is unavailable.

Ranking quality matters. When changing retrieval:

- Add or update regression tests with realistic query/file examples.
- Keep exact path and symbol hits above weak vector-only hits.
- Prefer current implementation evidence over historical notes.
- Preserve `ranking_reason` or equivalent inspectability.
- Record the change in development history.

## Retrieval Evaluation

Run retrieval evaluation before and after ranking, synonym, embedding, or memory-retrieval changes:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/python /Users/cltx/projects/langgraph/scripts/run_retrieval_eval.py --db /Users/cltx/projects/langgraph/checkpoints/project_index.sqlite --cases /Users/cltx/projects/langgraph/tests/fixtures/retrieval_eval
```

Use the report to check that expected business implementation files remain near the top and config/build/noise files do not move ahead of them. If the real project index is stale or missing, ask the user before refreshing it.

## Schema and Migrations

SQLite schema changes must be backward-compatible through `src/storage/migrations.py` and `init_schema()`.

When changing schema:

- Update `src/storage/schema.sql`.
- Add idempotent migration support for existing databases.
- Add tests for old database upgrade paths.
- Keep deleted files from leaking through secondary search tables.
- Record the schema change in development history.

## Testing

Run the full test suite before claiming completion:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests -q
```

Expected current baseline:

```text
61 passed
```

For focused work, run the relevant test file first, then the full suite before final response.

## Documentation and History Checklist

Before finishing any change:

1. Verify the code or docs that changed.
2. Run focused tests when applicable.
3. Run the full test suite before a completion claim.
4. Append an entry to the current dated file in `docs/superpowers/history/`.
5. Include what changed, what functionality was completed or modified, affected files, verification, and follow-ups.

## Codex Skills and Claude Code Notes

This repository currently uses a project-level README as the shared operating guide for agents.

Codex also supports dedicated skills. If this assistant should become a reusable Codex skill later, use the `skill-creator` guidance and create a concise skill folder such as:

```text
~/.codex/skills/project-memory-assistant/
  SKILL.md
  references/
```

Skill instructions should live in `SKILL.md`, not in a skill-local README. Keep the skill concise and move large project-specific details into `references/`.

Claude Code often benefits from a root `CLAUDE.md`, and other agents often read `AGENTS.md`. If those files are added later, keep them short and point back to this README, the design spec, and the development history rule so there is one source of truth.

## Safe Extension Path

Recommended next layers:

1. Improve retrieval ranking with real query evaluation fixtures.
2. Split the assistant into layered subgraphs: retrieval, QA, research, development advice, and memory reflection.
3. Add real human-in-the-loop interrupts for approval-required workflows.
4. Build the self-developed project memory layer: memory reflection, stale-memory demotion, proposal review, confidence tracking, and reusable project experience.
5. Integrate Codex and Claude Code through shared agent instructions, optional `AGENTS.md`/`CLAUDE.md` pointer files, and explicit approval-aware handoff workflows.
6. Add Docker deployment for repeatable local service startup, mounted SQLite/checkpoint storage, environment configuration, and health checks.
7. Add skill capability with a concise `SKILL.md` and optional references so the assistant can be reused as an agent skill.
