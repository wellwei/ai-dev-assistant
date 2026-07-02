# LangGraph Project Knowledge Assistant Development History

Date: 2026-07-02

## Recording Rule

Every implementation change, behavior change, design update, retrieval or ranking adjustment, schema migration, safety boundary change, and documentation rule change must add an entry here before the task is considered complete.

Each entry should include:

- Date or session.
- Change summary.
- Completed or modified functionality.
- Affected files or modules.
- Verification result.
- Remaining follow-ups, if any.

## 2026-07-02

### Internal Language Boundary and Legacy Node Removal

- Change summary: Replaced model-facing conversation and internal assistant state text with English while keeping final user-facing answers in Chinese.
- Completed or modified functionality:
  - Removed the old autonomous `planner -> coder -> tester -> reviewer` node path from the active project.
  - Added tests to ensure legacy nodes are no longer part of the assistant surface.
  - Added a design principle requiring internal model/node content to be English and final `answer` content to be Chinese.
- Affected files or modules:
  - `src/nodes/assistant_nodes.py`
  - `tests/test_assistant_graph.py`
  - `tests/test_legacy_nodes_removed.py`
  - `docs/superpowers/specs/2026-07-02-langgraph-project-knowledge-assistant-design.md`
- Verification: Covered by assistant graph and legacy-node removal tests.
- Follow-ups: Continue auditing any new state fields, prompts, workflow steps, and stored memory summaries to keep the same language boundary.

### Foundation Stabilization

- Change summary: Stabilized the assistant graph foundation for Studio compatibility and safer graph construction.
- Completed or modified functionality:
  - Added `flow_version` to `AssistantState`.
  - Made `assistant_graph` compatible with LangGraph Studio config dictionaries.
  - Kept graph factories free of side effects, including avoiding checkpoint directory creation during factory construction.
- Affected files or modules:
  - `src/state.py`
  - `src/assistant_graph.py`
  - `src/nodes/assistant_nodes.py`
  - `tests/test_assistant_graph.py`
- Verification: Covered by assistant graph tests and full test-suite runs.
- Follow-ups: Keep future graph factories deterministic and side-effect free.

### Index Provenance and Schema Migration Base

- Change summary: Added provenance fields and idempotent SQLite schema migration support so index data can be trusted and refreshed safely.
- Completed or modified functionality:
  - Added indexer version tracking.
  - Added content hashes, index run ids, indexer versions, evidence previews, confidence fields, and evidence span storage across summaries, symbols, and consistency flags.
  - Ensured unchanged file hashes are reindexed when `CURRENT_INDEXER_VERSION` changes.
  - Prevented deleted files from leaking through symbol-only retrieval.
  - Added idempotent migration support so old SQLite databases can be brought forward by `init_schema()`.
- Affected files or modules:
  - `src/indexer/version.py`
  - `src/storage/migrations.py`
  - `src/storage/schema.sql`
  - `src/storage/sqlite.py`
  - `src/storage/project_index.py`
  - `src/nodes/index_nodes.py`
  - `src/retriever/keyword_search.py`
  - `tests/test_storage.py`
  - `tests/test_index_graph.py`
  - `tests/test_retriever.py`
- Verification: Covered by storage, index graph, and retriever tests.
- Follow-ups: Use provenance fields in future ranking explanations and stale-index diagnostics.

### Evidence Spans and Confidence Reasons

- Change summary: Made summaries and symbols more evidence-oriented instead of treating regex-only extraction as high confidence.
- Completed or modified functionality:
  - Added conservative confidence scoring helpers.
  - Extracted `line_end`, `body_hash`, and `evidence_preview` for function symbols.
  - Generated `evidence_spans`, `confidence_score`, and `confidence_reasons` for file summaries.
  - Lowered trust when consistency flags indicate possible mismatch between implementation and names, comments, or documentation.
- Affected files or modules:
  - `src/indexer/confidence.py`
  - `src/indexer/symbol_extractor.py`
  - `src/indexer/summarizer.py`
  - `src/indexer/models.py`
  - `tests/test_symbol_extractor.py`
  - `tests/test_summarizer_consistency.py`
- Verification: Covered by symbol extractor and summarizer consistency tests.
- Follow-ups: Later replace regex-only evidence with AST or LSP-backed spans when the project needs finer precision.

### Research Memory Reuse

- Change summary: Added reusable research memory so follow-up questions can recall earlier assistant conclusions without treating them as current code evidence.
- Completed or modified functionality:
  - Added research memory retrieval before project context retrieval.
  - Split research notes into internal English memory summaries and Chinese user-answer summaries.
  - Added `project_root`, `source_note_ids`, and confidence metadata to research notes.
  - Added a Chinese answer section for historical research memory and labeled it as historical assistant conclusions.
  - Preserved the rule that current index evidence outranks historical memory.
- Affected files or modules:
  - `src/retriever/research_memory.py`
  - `src/storage/project_index.py`
  - `src/nodes/assistant_nodes.py`
  - `src/assistant_graph.py`
  - `tests/test_assistant_graph.py`
  - `tests/test_storage.py`
  - `tests/test_retriever.py`
- Verification: Covered by assistant graph, storage, and retriever tests.
- Follow-ups: Add reflection and expiry policies so stale research notes can be demoted or superseded.

### Local Embedding and Hybrid Retrieval

- Change summary: Added a local deterministic embedding boundary and hybrid retrieval layer without requiring external embedding APIs or secrets.
- Completed or modified functionality:
  - Added local hash-based embedding provider.
  - Added vector search storage and refresh behavior keyed by source hash and text hash.
  - Added hybrid search combining exact/path/symbol matches with vector-like semantic recall.
  - Added lightweight Chinese-to-English synonym expansion for business questions.
  - Kept exact path and symbol hits ahead of weak vector-only matches.
- Affected files or modules:
  - `src/embeddings/provider.py`
  - `src/retriever/vector_search.py`
  - `src/retriever/hybrid_search.py`
  - `src/storage/schema.sql`
  - `src/storage/project_index.py`
  - `tests/test_retriever.py`
- Verification: Covered by vector refresh and hybrid ranking regression tests.
- Follow-ups: Replace deterministic hash embeddings with a real local or approved external embedding provider behind the same interface.

### Skill-Like Workflow Registry

- Change summary: Added a workflow registry that recommends structured read-only workflows before any action execution layer exists.
- Completed or modified functionality:
  - Added workflows for project QA, requirement research, development advice, and index refresh suggestions.
  - Added structured output fields for `selected_workflow`, `workflow_steps`, and `approval_required`.
  - Marked development advice as approval-required.
  - Displayed the selected workflow in the Chinese answer.
- Affected files or modules:
  - `src/workflows/__init__.py`
  - `src/workflows/registry.py`
  - `src/nodes/assistant_nodes.py`
  - `src/assistant_graph.py`
  - `tests/test_workflows.py`
  - `tests/test_assistant_graph.py`
- Verification: Covered by workflow and assistant graph tests.
- Follow-ups: Convert approval-required workflows to real LangGraph human-in-the-loop interrupts.

### Hermes No-Op Boundary

- Change summary: Added a safe Hermes integration boundary without connecting to a real Hermes runtime.
- Completed or modified functionality:
  - Added `NullHermesAdapter`, `HermesHandoffRequest`, and `HermesCandidate`.
  - Made the default Hermes state disabled, approval-gated, and side-effect free.
  - Ensured importing or constructing the adapter does not call external systems.
- Affected files or modules:
  - `src/integrations/__init__.py`
  - `src/integrations/hermes.py`
  - `tests/test_hermes_integration.py`
- Verification: Covered by Hermes integration boundary tests.
- Follow-ups: Only connect a real Hermes adapter after an explicit approval gate and a concrete handoff protocol are designed.

### Self-Improvement Proposal Layer

- Change summary: Added the first self-improvement layer as proposal generation only, without automatic application.
- Completed or modified functionality:
  - Added an `ImprovementProposal` model.
  - Added `improvement_proposals` schema support and repository methods.
  - Added self-improvement proposal generation for observed quality gaps.
  - Kept all proposals pending and non-executing by default.
- Affected files or modules:
  - `src/indexer/models.py`
  - `src/storage/schema.sql`
  - `src/storage/project_index.py`
  - `src/self_improvement/__init__.py`
  - `src/self_improvement/proposals.py`
  - `tests/test_self_improvement.py`
- Verification: Covered by self-improvement tests and full test-suite runs.
- Follow-ups: Add a memory reflection graph, proposal review workflow, and explicit approval path before any proposal can change behavior.

### Retrieval Ranking Quality Improvements

- Change summary: Improved retrieval ordering so real project business implementation files rank above configuration, build, and generic support files.
- Completed or modified functionality:
  - Added weighted keyword scoring with repeated-token caps.
  - Boosted business source paths, C++ implementation files, side-effect evidence, and path token matches.
  - Capped per-file symbol contribution to reduce noisy symbol-heavy files.
  - Penalized config, build, AFC metadata, and generic database configuration files.
  - Filtered non-positive final scores.
  - Added `ranking_reason` so ranking decisions can be inspected.
  - Fixed old database initialization so indexes over migrated columns are created after migration.
  - Refreshed the real project index in read-only mode; the workspace SQLite index was updated, but the target C++ project was not modified.
- Affected files or modules:
  - `src/retriever/keyword_search.py`
  - `src/storage/schema.sql`
  - `tests/test_retriever.py`
  - `tests/test_storage.py`
  - `checkpoints/project_index.sqlite`
- Verification:
  - Full suite passed with `44 passed`.
  - Real project index refresh scanned 673 files, wrote 673 summaries, extracted 7317 symbols, and produced 848 consistency flags.
  - Real sample retrieval no longer placed `.AFCfile`, config files, or `db_config.cpp` at the top; business implementation files ranked first.
- Follow-ups: Add query evaluation fixtures from real user questions, tune business synonym expansion, and consider a real embedding provider once ranking baselines are stable.

### Development History Discipline

- Change summary: Added a durable history file and made history updates a core project rule.
- Completed or modified functionality:
  - Created the development history file for chronological change tracking.
  - Backfilled the major changes completed during the current improvement session.
  - Added a core design principle that every future change must update the development history.
- Affected files or modules:
  - `docs/superpowers/history/2026-07-02-development-history.md`
  - `docs/superpowers/specs/2026-07-02-langgraph-project-knowledge-assistant-design.md`
- Verification: Documentation review and test-suite run for the current workspace.
- Follow-ups: Append a new entry here during every future change before final verification.

### Agent README Operating Guide

- Change summary: Added a root README for Codex, Claude Code, and similar agents.
- Completed or modified functionality:
  - Documented the read-first file order for incoming agents.
  - Documented project safety rules, especially the read-only boundary for the target C++ project.
  - Documented the internal English and final Chinese language boundary.
  - Documented index graph and assistant graph usage examples.
  - Documented retrieval, memory, schema migration, testing, and history-update expectations.
  - Clarified that Codex skill support exists, but a reusable skill should use `SKILL.md` rather than a skill-local README.
- Affected files or modules:
  - `README.md`
  - `docs/superpowers/history/2026-07-02-development-history.md`
- Verification: README content review, history-rule grep check, and full test-suite run with `45 passed`.
- Follow-ups: Optionally add short `AGENTS.md` or `CLAUDE.md` pointer files later if stronger auto-discovery is desired for specific agent tools.
