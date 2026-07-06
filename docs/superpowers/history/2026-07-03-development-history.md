# LangGraph Project Knowledge Assistant Development History

Date: 2026-07-03

## Recording Rule

Every implementation change, behavior change, design update, retrieval or ranking adjustment, schema migration, safety boundary change, and documentation rule change must add an entry to the dated history file for the active work date before the task is considered complete.

Each entry should include:

- Date or session.
- Change summary.
- Completed or modified functionality.
- Affected files or modules.
- Verification result.
- Remaining follow-ups, if any.

## 2026-07-03

### Route Change: Self-Developed Memory Layer Instead of Hermes Agent

- Change summary: Updated the project roadmap to abandon further Hermes Agent introduction attempts and move future memory/self-improvement work into a self-developed project memory layer.
- Completed or modified functionality:
  - Marked Hermes Agent as no longer part of the future architecture route.
  - Kept the existing Hermes no-op boundary documented as historical and disabled, with no further expansion planned.
  - Replaced the old Hermes/Deep Agents evolution stage with a self-developed project memory layer stage.
  - Added future stages for Codex/Claude Code integration.
  - Added future stages for Docker deployment and skill capability.
  - Updated agent README history paths to use dated files under `docs/superpowers/history/` instead of a single fixed 2026-07-02 file.
  - Updated the implementation plan notes so future workers do not treat Hermes as a remaining evolution target.
  - Corrected the old design-spec wording that said no embedding would be introduced; the project now treats local deterministic embedding as an existing replaceable boundary while external providers still require design and approval.
- Affected files or modules:
  - `README.md`
  - `docs/superpowers/specs/2026-07-02-langgraph-project-knowledge-assistant-design.md`
  - `docs/superpowers/plans/2026-07-02-langgraph-project-knowledge-assistant.md`
  - `docs/superpowers/history/2026-07-03-development-history.md`
- Verification: Documentation grep checks and full test-suite run with `45 passed`.
- Follow-ups:
  - Add optional `AGENTS.md` and `CLAUDE.md` pointer files when stronger agent auto-discovery is needed.
  - Design the self-developed memory layer schema and reflection graph before adding behavior.
  - Design Docker deployment files after the core local workflow is stable.
  - Design Codex skill packaging as a concise `SKILL.md` with references, not as a README clone.

### Retrieval Evaluation Baseline Plan

- Change summary: Added a concrete implementation plan for the next improvement direction: retrieval quality evaluation.
- Completed or modified functionality:
  - Defined the plan scope as a retrieval evaluation baseline and initial eval runner.
  - Planned pure evaluator dataclasses and pass/fail ranking checks.
  - Planned JSON fixtures for realistic escort/route queries.
  - Planned seeded hybrid-search regression coverage.
  - Planned a local CLI for running eval cases against `project_index.sqlite`.
  - Planned README and history updates for the eventual implementation.
- Affected files or modules:
  - `docs/superpowers/plans/2026-07-03-retrieval-evaluation-baseline.md`
  - `docs/superpowers/history/2026-07-03-development-history.md`
- Verification: Plan document review, grep check, and full test-suite run for the current workspace.
- Follow-ups: Execute the plan with subagent-driven development or inline execution after user approval.

### Retrieval Evaluation Baseline

- Change summary: Added a retrieval evaluation baseline for measuring ranking quality.
- Completed or modified functionality:
  - Added pure retrieval eval dataclasses and pass/fail evaluation logic.
  - Added JSON fixture loading and report formatting.
  - Added seeded hybrid-search regression coverage.
  - Added a local CLI for running eval cases against `project_index.sqlite`.
  - Documented the eval workflow in the README.
- Affected files or modules:
  - `src/retriever/evaluation.py`
  - `scripts/run_retrieval_eval.py`
  - `tests/fixtures/retrieval_eval/escort_route.json`
  - `tests/test_retrieval_evaluation.py`
  - `README.md`
  - `docs/superpowers/history/2026-07-03-development-history.md`
- Verification:
  - Focused retrieval evaluation tests passed with `6 passed`.
  - Existing retriever tests passed with `8 passed`.
  - Full test-suite run passed with `51 passed`.
  - Local real-index eval command ran successfully and reported `1/2 passed`; `escort_route_recalc_business_impl` failed because `src/map_data/sea_route.cpp` was missing from the top 8 for `押镖 route 重算 风险`.
- Follow-ups:
  - Add more real user queries and expand the fixture set before major ranking rewrites.
  - Use the `escort_route_recalc_business_impl` failure as the next concrete ranking improvement target.

### Retrieval Evaluation Baseline Final Review Fixes

- Change summary: Addressed final review findings for the retrieval evaluation baseline.
- Completed or modified functionality:
  - Added a CLI guard so empty eval case sets print a clear error and exit with code `2` instead of reporting a false green.
  - Added subprocess coverage for empty case directories, passing CLI runs, and failing CLI runs with `PYTHONPATH` removed.
  - Updated the README full-suite baseline from `45 passed` to `54 passed`.
- Affected files or modules:
  - `scripts/run_retrieval_eval.py`
  - `tests/test_retrieval_evaluation.py`
  - `README.md`
  - `docs/superpowers/history/2026-07-03-development-history.md`
- Verification:
  - Focused retrieval evaluation tests passed with `9 passed`.
  - Existing retriever tests passed with `8 passed`.
  - Full test-suite run passed with `54 passed`.
  - Local real-index eval still reports `1/2 passed`, preserving the ranking follow-up signal for `escort_route_recalc_business_impl`.
- Follow-ups: None.

### Escort Route Retrieval Ranking Calibration

- Change summary: Fixed the first real-index retrieval eval failure by separating generic route-recalculation intent from client second-route query intent.
- Completed or modified functionality:
  - Investigated the failed `escort_route_recalc_business_impl` eval case and found the fixture mixed two different concepts: generic route recalculation risk and sea-route map data.
  - Removed `query_second_route` from the generic `route_recalc` domain boost so client query handlers no longer outrank stronger recalculation implementations for broad recalc-risk questions.
  - Added a focused regression test proving route recalculation queries keep `cal_cross_map_route_cost_time_complex_task.cpp` and `process_recalc_route_task.cpp` ahead of the client second-route query path.
  - Updated the real-project eval fixture so `押镖 route 重算 风险` expects recalculation implementation paths.
  - Added a separate `海路 地图 路线` eval case to preserve coverage for `src/map_data/sea_route.cpp` without conflating it with route recalculation risk.
- Affected files or modules:
  - `src/retriever/keyword_search.py`
  - `tests/test_retriever.py`
  - `tests/fixtures/retrieval_eval/escort_route.json`
  - `tests/test_retrieval_evaluation.py`
  - `docs/superpowers/history/2026-07-03-development-history.md`
- Verification:
  - Focused route-recalc regression passed with `1 passed`.
  - Fixture loading test passed with `1 passed`.
  - Local real-index retrieval eval passed with `3/3 passed`.
  - Existing retriever tests passed with `9 passed`.
  - Retrieval evaluation tests passed with `9 passed`.
  - Full test-suite run passed with `55 passed`.
- Follow-ups:
  - Add more real movement-logic queries to the eval fixture before broader ranking rewrites.
  - Consider a dedicated implementation-vs-header ranking rule if real answers start over-preferring `.h` files for implementation-focused questions.

### Escort Movement Retrieval Evaluation Pack

- Change summary: Added a movement-focused retrieval eval pack and improved Chinese movement-state intent handling for escort-car development questions.
- Completed or modified functionality:
  - Added real-project eval cases for escort-car core movement, follow movement, and position/sync/stop/abnormal movement-state questions.
  - Added a regression test proving Chinese movement-state terms such as `位置`, `同步`, `停止`, and `异常` promote `rtb_proc_escort_car_move.cpp` over generic escort headers or handlers.
  - Expanded keyword synonyms for Chinese movement terms, including movement, follow, position, sync, stop, and outside/status-style abnormal state language.
  - Expanded escort movement intent detection so Chinese movement-state questions receive the same domain boost as explicit `move`/`follow` questions.
  - Updated fixture-loading coverage to support multiple retrieval eval fixture files without brittle ordering assumptions.
- Affected files or modules:
  - `src/retriever/keyword_search.py`
  - `tests/test_retriever.py`
  - `tests/fixtures/retrieval_eval/escort_movement.json`
  - `tests/test_retrieval_evaluation.py`
  - `docs/superpowers/history/2026-07-03-development-history.md`
- Verification:
  - Movement-state regression was first observed failing because `rtb_proc_escort_def.h` ranked above `rtb_proc_escort_car_move.cpp`.
  - Focused movement-state regression passed with `1 passed` after the intent fix.
  - Fixture loading test passed with `1 passed`.
  - Local real-index retrieval eval passed with `6/6 passed`.
  - Existing retriever tests passed with `10 passed`.
  - Retrieval evaluation tests passed with `9 passed`.
  - Full test-suite run passed with `56 passed`.
- Follow-ups:
  - Add eval cases for path jump/second-route sync and timeout/migration movement exits once those questions appear in real use.
  - Consider source-vs-header ranking calibration if future movement queries still surface macro headers too early.

### Escort Movement Boundary Retrieval Expansion

- Change summary: Expanded movement retrieval coverage from basic movement questions to edge-case movement logic questions used during escort-car development.
- Completed or modified functionality:
  - Added regression coverage for second-route sync/jump-point questions so execution-side movement logic is not confused with client route-query TCP handlers.
  - Added regression coverage for `sport_status` change-reason/log questions so movement status updates rank above generic escort handlers.
  - Narrowed `client_route_query` intent detection by removing bare `二段` as a trigger; explicit client/query wording still preserves the client second-route query result.
  - Expanded Chinese movement-state synonyms for jump, timeout, migration, offline, dead, mounting, speed, distance, radius, change, reason, and log terminology.
  - Added eval cases for second-route sync jump points, timeout/migration movement exits, external stop conditions, sport-status change logs, and follow distance/radius checks.
- Affected files or modules:
  - `src/retriever/keyword_search.py`
  - `tests/test_retriever.py`
  - `tests/fixtures/retrieval_eval/escort_movement.json`
  - `tests/test_retrieval_evaluation.py`
  - `docs/superpowers/history/2026-07-03-development-history.md`
- Verification:
  - Second-route sync regression was first observed failing because generic `/tcp/` handlers received `client_route_query` ranking reasons.
  - Sport-status change regression was first observed failing because generic `rtb_proc_escort_car.cpp` ranked above `rtb_proc_escort_car_move.cpp`.
  - Focused regressions passed with `2 passed` after the ranking changes.
  - Fixture loading test passed with `1 passed`.
  - Local real-index retrieval eval passed with `11/11 passed`.
  - Existing retriever tests passed with `12 passed`.
  - Retrieval evaluation tests passed with `9 passed`.
  - Full test-suite run passed with `60 passed`.
- Follow-ups:
  - Add answer-quality checks that verify retrieved movement files are cited with the relevant function names, not only file paths.
  - Consider extracting escort-domain ranking rules into a small declarative table if more movement intents are added.

### Movement Answer Key Symbol Surfacing

- Change summary: Improved assistant answer quality for movement-logic questions by surfacing key functions and symbols from retrieved context.
- Completed or modified functionality:
  - Added a regression test for movement answers requiring `关键函数/符号` in the final Chinese answer.
  - Updated user-facing context summaries so each retrieved file can include key symbols from matched symbols and summary `key_points`.
  - Confirmed movement answers can now cite `escort_car_move6`, `stop_escort_car_outside_conditions`, and `calc_escort_car_sport_result` for stop-condition questions.
  - Kept internal analysis/context wording English while exposing only the final answer summary in Chinese.
  - Did not change retrieval ranking or write to the target C++ project.
- Affected files or modules:
  - `src/nodes/assistant_nodes.py`
  - `tests/test_assistant_graph.py`
  - `docs/superpowers/history/2026-07-03-development-history.md`
- Verification:
  - Focused answer-quality regression was first observed failing because the final answer did not include `关键函数/符号`.
  - Focused answer-quality regression passed with `1 passed` after the answer summary change.
  - Assistant graph tests passed with `10 passed`.
  - Read-only real-index answer sampling showed `rtb_proc_escort_car_move.cpp` with `escort_car_move6`, `stop_escort_car_outside_conditions`, and `calc_escort_car_sport_result`.
  - Local real-index retrieval eval passed with `11/11 passed`.
  - Full test-suite run passed with `61 passed`.
- Follow-ups:
  - Improve symbol extraction for complex C++ return types so functions such as `update_escort_car_route_and_sport_status` can be indexed and cited.
  - Filter low-value macro/log symbols from user-facing key symbol lists if they continue to add noise.

### Assistant Hybrid Retrieval Main Path

- Change summary: Switched the assistant's project-context retrieval path from keyword-only retrieval to hybrid retrieval.
- Completed or modified functionality:
  - `retrieve_project_context_node` now calls `hybrid_search_project()` so normal assistant answers can use keyword, exact-match, and local vector retrieval results.
  - Added a conservative fallback to `search_project_index()` if hybrid retrieval is unavailable.
  - Extended context building with ranking reason and hybrid/keyword/vector score metadata for better retrieval explainability.
  - Added assistant graph regression coverage for vector-only hybrid context recall and keyword fallback behavior.
  - Updated the README retrieval notes and current full-suite baseline.
- Affected files or modules:
  - `src/nodes/assistant_nodes.py`
  - `src/retriever/context_builder.py`
  - `tests/test_assistant_graph.py`
  - `README.md`
  - `docs/superpowers/history/2026-07-03-development-history.md`
- Verification:
  - New hybrid-vector assistant test was first observed failing because assistant retrieval still returned the keyword-only `src/route.cpp` result.
  - Focused hybrid assistant/context tests passed with `3 passed`.
  - Assistant, retriever, and retrieval-evaluation tests passed with `30 passed`.
  - Local real-index retrieval eval passed with `6/6 passed` before later fixture expansions.
  - Full test-suite run passed with `60 passed` before later answer-quality changes; the latest recorded full-suite baseline is `61 passed`.
- Follow-ups:
  - Consider filtering or marking vector-only hits that point to paths not currently present in active `files` rows if future real-index results surface stale embedding-only paths.
  - Consider improving answer rendering so ranking reasons and scores can be shown selectively in Chinese user-facing evidence when helpful.

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
  - `docs/superpowers/history/2026-07-03-development-history.md`
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
