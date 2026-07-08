# LangGraph Project Knowledge Assistant Development History

Date: 2026-07-06

## Recording Rule

Every implementation change, behavior change, design update, retrieval or ranking adjustment, schema migration, safety boundary change, and documentation rule change must add an entry to the dated history file for the active work date before the task is considered complete.

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
  - `docs/superpowers/history/2026-07-06-development-history.md`
- Verification:
  - Project memory schema test was first observed failing before implementation.
  - Project memory repository API test was first observed failing before implementation.
  - Project memory retriever wrapper test was first observed failing before implementation.
  - Focused storage and retriever tests passed with `22 passed`.
  - Full test-suite run passed with `64 passed`.
- Follow-ups:
  - Add `retrieve_project_memories_node` only after separate answer-conflict tests are designed.
  - Add memory reflection that drafts project memories from repeated research notes, but keep it proposal/review based.
  - Add stale-memory demotion and deduplication after real usage shows the right natural keys.



### Project Memory Assistant Integration v1

- Change summary: Wired active project memories into the assistant graph as read-only auxiliary context.
- Completed or modified functionality:
  - Added assistant state fields for `retrieved_project_memories` and `project_memory_ids`.
  - Added `retrieve_project_memories_node` with non-blocking project-memory search failure behavior.
  - Wired the assistant graph so `retrieve_research_memory` flows into `retrieve_project_memories` before current project-context retrieval.
  - Included project memories in English internal analysis under a separate project-memory context section.
  - Added a Chinese `长期项目记忆` answer section with the required demotion label: current implementation index evidence wins.
  - Preserved existing research-memory persistence and `source_note_ids` behavior.
  - Kept the integration read-only and did not generate, promote, update, demote, or conflict-check project memories automatically.
  - Did not modify the target C++ project.
- Affected files or modules:
  - `src/state.py`
  - `src/nodes/assistant_nodes.py`
  - `src/assistant_graph.py`
  - `tests/test_assistant_graph.py`
  - `README.md`
  - `docs/superpowers/history/2026-07-06-development-history.md`
  - `docs/superpowers/plans/2026-07-06-project-memory-assistant-integration-v1.md`
- Verification:
  - New project-memory assistant tests were first observed failing before implementation because the graph did not retrieve project memories and `search_project_memory` was not imported in assistant nodes.
  - Focused assistant graph tests passed with `13 passed`.
  - Focused storage and retriever tests passed with `22 passed`.
  - Full test-suite run passed with `67 passed`.
- Follow-ups:
  - Design memory reflection separately and keep it proposal/review based.
  - Design stale-memory demotion separately after real usage clarifies natural keys.
  - Add automatic conflict or staleness detection only with explicit tests and authority-rule design.



### Gameplay Movement / Combat Retrieval Direction Tuning

- Date/session: 2026-07-06.
- Change summary: Retuned assistant retrieval direction away from route-only/escort-heavy defaults toward the user's current gameplay focus: movement position synchronization, combat, damage, charge, and mount logic.
- Completed or modified functionality:
  - Added token-aware ASCII matching in `src/retriever/keyword_search.py` so `move` no longer matches unrelated `remove_*` paths while snake_case movement identifiers still match.
  - Generalized escort-domain ranking boosts into gameplay-domain intent boosts covering movement, combat, damage, charge, mount, and existing route/escort regressions.
  - Expanded keyword, project-memory, research-memory, and local embedding synonym bridges for movement position sync, battle/combat, damage/hp, charge/dash, and mount/dismount terms.
  - Expanded index summary dependency hints for movement, position, sync, damage, charge, mount, and combat.
  - Added assistant graph coverage proving Chinese answers surface movement/combat/mount paths and key symbols without leaking English internal analysis.
  - Added retrieval regression tests for gameplay ranking and `move` versus `remove` false positives.
  - Added gameplay retrieval evaluation fixture while preserving existing escort route and escort movement fixtures as regression coverage.
  - Broadened self-improvement proposal detection for repeated low-confidence gameplay retrieval gaps while keeping proposals pending-only.
  - Updated README examples and retrieval guidance to reflect movement/combat/mount as first-class investigation directions.
  - Did not modify the target C++ project; status check showed pre-existing `M CMakeLists.txt` and `?? ../.idea/`.
- Affected files or modules:
  - `src/retriever/keyword_search.py`
  - `src/storage/project_index.py`
  - `src/embeddings/provider.py`
  - `src/indexer/summarizer.py`
  - `src/self_improvement/proposals.py`
  - `tests/test_retriever.py`
  - `tests/test_assistant_graph.py`
  - `tests/test_retrieval_evaluation.py`
  - `tests/test_embeddings_provider.py`
  - `tests/test_summarizer_consistency.py`
  - `tests/test_self_improvement.py`
  - `tests/fixtures/retrieval_eval/gameplay_movement_combat_mount.json`
  - `README.md`
  - `docs/superpowers/history/2026-07-06-development-history.md`
- Verification:
  - Focused gameplay/retrieval tests passed: `51 passed` with `tests/test_retriever.py`, `tests/test_assistant_graph.py`, `tests/test_retrieval_evaluation.py`, `tests/test_embeddings_provider.py`, `tests/test_summarizer_consistency.py`, and `tests/test_self_improvement.py`.
  - Full test suite passed: `77 passed`.
  - Real-index retrieval evaluation passed: `15/15 passed`.
  - Target project status checked read-only: `M CMakeLists.txt` and `?? ../.idea/` were present and not created or modified by this work.
- Follow-ups:
  - Use future real user questions to refine gameplay fixture expected paths if the target index changes.
  - Consider adding answer-level grouping for movement sync, combat/damage, charge, and mount sections after more evaluation data.
