# LangGraph Project Knowledge Assistant Development History

Date: 2026-07-07

## Recording Rule

Every implementation change, behavior change, design update, retrieval or ranking adjustment, schema migration, safety boundary change, and documentation rule change must add an entry to the dated history file for the active work date before the task is considered complete.

### Agent-Friendly Project Knowledge CLI Entrypoint

- Date/session: 2026-07-07.
- Change summary: Added the first Codex/Claude Code-friendly CLI entrypoint for asking the local project knowledge assistant from a shell command.
- Completed or modified functionality:
  - Added `scripts/ask_project.py` as a thin CLI wrapper around `create_assistant_graph()`.
  - Added `--question`, `--db`, `--project-root`, `--thread-id`, and `--output text|json` arguments.
  - Added text output that prints only the final Chinese `answer`, avoiding internal English `analysis` leakage.
  - Added JSON output with a stable agent-facing field allowlist: `answer`, `request_type`, `related_paths`, `approval_required`, `open_questions`, `suggested_commands`, `research_note_id`, `thread_id`, and `flow_version`.
  - Added input/environment errors with exit code `2` for empty questions and missing project index DB.
  - Preserved development-advice approval gating so JSON callers can inspect `approval_required` and the Chinese answer still warns `需要审批` / `不要直接修改`.
  - Chose CLI before MCP or skill packaging because the CLI is the smallest stable runtime contract for Codex, Claude Code, terminals, and future wrappers.
  - Updated README with text and JSON CLI examples and clarified that the CLI reads from SQLite and does not mutate the target C++ project.
- Affected files or modules:
  - `scripts/ask_project.py`
  - `tests/test_assistant_cli.py`
  - `README.md`
  - `docs/superpowers/history/2026-07-07-development-history.md`
- Verification:
  - CLI tests were first observed failing before implementation because `scripts/ask_project.py` did not exist.
  - Focused CLI tests passed with `5 passed`.
  - Focused CLI, assistant graph, and retrieval evaluation tests passed with `28 passed`.
  - Full test suite passed with `82 passed`.
  - Manual CLI smoke test succeeded for `移动位置同步、战斗伤害、坐骑逻辑分别在哪里？` and produced a Chinese project answer.
  - Target project status checked read-only: `M CMakeLists.txt` and `?? ../.idea/` were present and not created or modified by this work.
- Follow-ups:
  - After the CLI contract is used in practice, consider wrapping it as an MCP tool with typed inputs/outputs.
  - Add a concise Codex/Claude Code skill or short `AGENTS.md` / `CLAUDE.md` pointers only after the preferred invocation workflow is stable.
  - Consider adding a separate search-only CLI if agents need ranked paths without a synthesized answer.

### Root Agent Guide and Claude Pointer

- Date/session: 2026-07-07.
- Change summary: Added concise in-repository guidance so Codex, Claude Code, and similar agents know how to use this LangGraph project and its CLI safely.
- Completed or modified functionality:
  - Added root `AGENTS.md` as the canonical short operating guide for agents entering this repository.
  - Added root `CLAUDE.md` as a tiny Claude Code pointer to `AGENTS.md` and `README.md`.
  - Documented the agent-facing CLI command `scripts/ask_project.py` and when to use `--output text` versus `--output json`.
  - Repeated only the hard safety, language, evidence-priority, and history-discipline rules needed for quick agent discovery, while keeping `README.md` as the full source of truth.
  - Clarified in `README.md` that `AGENTS.md` and `CLAUDE.md` now exist, and that a full external skill can be added later if reuse outside this repo is needed.
- Affected files or modules:
  - `AGENTS.md`
  - `CLAUDE.md`
  - `tests/test_agent_guides.py`
  - `README.md`
  - `docs/superpowers/history/2026-07-07-development-history.md`
- Verification:
  - Added a lightweight guide regression test covering the existence of `AGENTS.md` / `CLAUDE.md` and references to `scripts/ask_project.py`, `assistant`, `indexer`, `README.md`, and dated history.
- Follow-ups:
  - If the guide needs to be reused outside this repository, package a small `SKILL.md` that points back to `AGENTS.md`, `README.md`, and `scripts/ask_project.py` rather than duplicating the full guide.

### Agent Workflow Recipes Guide

- Date/session: 2026-07-07.
- Change summary: Added an explicit Codex/Claude Code workflow recipe so agents combine the repository guide, search CLI, source inspection, ask CLI, memory layers, and read-only target-project boundary consistently.
- Completed or modified functionality:
  - Added `docs/superpowers/guides/agent-workflows.md` with recipes for project Q&A, read-only development advice, retrieval quality tuning, memory distillation, and safety boundaries.
  - Documented the default question-answering sequence: read `AGENTS.md`, run `scripts/search_project.py --output json`, inspect top source paths with `Read`, run `scripts/ask_project.py` when synthesized Chinese output or `research_notes` persistence is useful, then answer in Chinese with evidence layers separated.
  - Clarified when current source evidence outranks index summaries, `project_memories`, and historical `research_notes`.
  - Clarified that development advice for the target C++ project is read-only and approval-gated, with verification concerns such as call chains, side effects, protocol boundaries, and frame/tick timing called out before future edits.
  - Linked the workflow guide from `AGENTS.md` and the README's Codex/Claude Code notes.
  - Added a lightweight documentation regression test to ensure the guide path and core workflow terms remain discoverable.
- Affected files or modules:
  - `docs/superpowers/guides/agent-workflows.md`
  - `AGENTS.md`
  - `README.md`
  - `tests/test_agent_guides.py`
  - `docs/superpowers/history/2026-07-07-development-history.md`
- Verification:
  - The new workflow-guide test was first observed failing because `docs/superpowers/guides/agent-workflows.md` did not exist.
  - Focused agent guide tests passed with `2 passed`.
- Follow-ups:
  - After this recipe is stable in daily use, consider packaging the same workflow as a Claude Code or Codex skill.
  - Consider wrapping `scripts/search_project.py` and `scripts/ask_project.py` as typed MCP tools only after the CLI contract has remained stable.

### Documentation Convergence and Project Verification

- Date/session: 2026-07-07.
- Change summary: Converged the agent-facing documentation layers after adding the workflow recipe and refreshed the project verification baseline.
- Completed or modified functionality:
  - Kept `CLAUDE.md` as a tiny pointer, `AGENTS.md` as the short operating guide, `README.md` as the full architecture and CLI reference, and `docs/superpowers/guides/agent-workflows.md` as the practical recipe layer.
  - Tightened the workflow guide introduction so it states that split explicitly instead of duplicating architecture scope.
  - Updated README's test baseline from `90 passed` to `91 passed` after the new documentation regression test was added.
  - Updated README's safe extension path so Codex/Claude Code integration refers to the now-existing `AGENTS.md`, `CLAUDE.md`, and workflow guide instead of future optional pointer files.
- Affected files or modules:
  - `README.md`
  - `docs/superpowers/guides/agent-workflows.md`
  - `docs/superpowers/history/2026-07-07-development-history.md`
- Verification:
  - Focused agent/CLI tests passed with `14 passed`.
  - Retrieval evaluation passed with `15/15 passed`.
  - `scripts/search_project.py --output json` smoke test for `移动位置同步` returned 8 ranked results, led by movement/sync implementation paths such as `src/task/sync/process_sync_rs_task.cpp` and `src/task/tcp/process_cli_role_move_tcp_task.cpp`.
  - `scripts/ask_project.py --output json` smoke test returned stable JSON fields including `answer`, `request_type`, `related_paths`, `approval_required`, `research_note_id`, `thread_id`, and `flow_version`; it also persisted a new `research_notes` row as designed.
- Follow-ups:
  - If the test baseline becomes noisy again, replace the fixed README count with a pointer to the latest dated history and the full-suite command.
  - The combined `ask_project.py` smoke question still favored battle-related paths in `related_paths`; future retrieval/synthesis tuning should improve balanced multi-topic answers for movement + combat + mount questions while preserving the search CLI's stronger ranked coverage.

### English Agent-Facing Multi-Topic Assistant Q&A

- Date/session: 2026-07-07.
- Change summary: Converted assistant answers and agent-facing docs from default Chinese output to English, and added internal topic-aware retrieval/synthesis for multi-topic project questions.
- Completed or modified functionality:
  - Added internal gameplay topic detection for movement/position sync, combat damage, and mount logic.
  - Added per-topic retrieval using existing hybrid search with keyword fallback, then merged related paths in topic-balanced order without exposing a new JSON field.
  - Updated assistant synthesis to render English agent-facing answers, including topic sections when topic metadata is present.
  - Preserved the public `ask_project.py --output json` contract and intentionally did not expose `topic_groups`.
  - Updated tests from Chinese-answer assertions to English agent-facing assertions.
  - Updated `AGENTS.md`, `README.md`, and `docs/superpowers/guides/agent-workflows.md` to document English output by default.
- Affected files or modules:
  - `src/nodes/assistant_nodes.py`
  - `tests/test_assistant_graph.py`
  - `tests/test_assistant_cli.py`
  - `tests/test_index_graph.py`
  - `AGENTS.md`
  - `README.md`
  - `docs/superpowers/guides/agent-workflows.md`
  - `docs/superpowers/specs/2026-07-07-multi-topic-assistant-qa-design.md`
  - `docs/superpowers/history/2026-07-07-development-history.md`
- Verification:
  - Focused assistant and CLI tests passed with `20 passed` using `PYTHONPATH=/Users/cltx/projects/langgraph/.claude/worktrees/multi-topic-agent-qa /Users/cltx/projects/langgraph/venv/bin/python -m pytest /Users/cltx/projects/langgraph/.claude/worktrees/multi-topic-agent-qa/tests/test_assistant_graph.py /Users/cltx/projects/langgraph/.claude/worktrees/multi-topic-agent-qa/tests/test_assistant_cli.py -q`.
  - Agent guide tests passed with `3 passed` using `PYTHONPATH=/Users/cltx/projects/langgraph/.claude/worktrees/multi-topic-agent-qa /Users/cltx/projects/langgraph/venv/bin/python -m pytest /Users/cltx/projects/langgraph/.claude/worktrees/multi-topic-agent-qa/tests/test_agent_guides.py -q`.
  - Retrieval evaluation passed with `15/15 passed` using the worktree `scripts/run_retrieval_eval.py`, worktree `checkpoints/project_index.sqlite`, and worktree retrieval fixtures.
  - Full test suite initially failed because `tests/test_index_graph.py::test_index_then_assistant_answer_end_to_end` still asserted Chinese output (`置信度`, `注释`, `命名`) after the assistant was converted to English. The test was updated to assert English output (`Confidence`, `comment`, `name`) and passed with `1 passed` in focused rerun.
  - Full test suite passed with `93 passed` using `PYTHONPATH=/Users/cltx/projects/langgraph/.claude/worktrees/multi-topic-agent-qa /Users/cltx/projects/langgraph/venv/bin/python -m pytest /Users/cltx/projects/langgraph/.claude/worktrees/multi-topic-agent-qa/tests -q`.
  - README test baseline was updated from `91 passed` to `93 passed`.
  - Search CLI smoke test returned `result_count` 8 and movement/sync ranked paths led by `src/task/sync/process_sync_rs_task.cpp` and `src/task/tcp/process_cli_role_move_tcp_task.cpp`.
  - Ask CLI multi-topic JSON smoke test returned English topic sections for `Movement / position sync`, `Combat damage`, and `Mount logic`, stable JSON fields, and no `topic_groups` field.
  - Target C++ project status was checked read-only with `git -C /Users/cltx/projects/escort_server/doll_escort_game_svr status --short`; existing status was `M CMakeLists.txt` and `?? ../.idea/`. No target-project mutations were made by this work.
- Follow-ups:
  - Consider exposing `topic_groups` in JSON only after the internal topic grouping has proven stable.
  - Extend topic detection beyond movement/combat/mount when real repeated questions justify it.

### Search-Only Project Retrieval CLI

- Date/session: 2026-07-07.
- Change summary: Added a read-only search CLI for Codex, Claude Code, and similar agents to retrieve ranked project paths and indexed evidence without synthesizing an assistant answer.
- Completed or modified functionality:
  - Added `scripts/search_project.py` with `--query`, `--db`, `--limit`, and `--output text|json` arguments.
  - Reused `hybrid_search_project()` with keyword-search fallback.
  - Added stable text output with ranked paths, scores, ranking reasons, summaries, key points, evidence, and risks.
  - Added stable JSON output with `query`, `db`, `limit`, `result_count`, and per-result rank/path/score/evidence fields.
  - Kept the CLI search-only: it does not invoke the assistant graph, synthesize an answer, or persist `research_notes`.
  - Updated `README.md` and `AGENTS.md` to distinguish `search_project.py` for ranked paths from `ask_project.py` for full Chinese answers.
- Affected files or modules:
  - `scripts/search_project.py`
  - `tests/test_search_project_cli.py`
  - `README.md`
  - `AGENTS.md`
  - `docs/superpowers/history/2026-07-07-development-history.md`
- Verification:
  - Search CLI tests were first observed failing before implementation because `scripts/search_project.py` did not exist.
  - Focused search CLI tests passed with `7 passed`.
  - Neighboring retriever and retrieval evaluation tests passed with `27 passed`.
  - Full test suite passed with `90 passed`.
  - Manual text smoke test for `移动位置同步` returned ranked paths including `src/task/sync/process_sync_rs_task.cpp` and `src/task/tcp/process_cli_role_move_tcp_task.cpp`.
  - Manual JSON smoke test for `战斗 伤害 冲锋` returned ranked battle paths including `src/battle_calculate/battle_calculate.cpp`.
- Follow-ups:
  - Consider adding a future `--verbose` mode for full matched symbol details if agents need symbol-level routing.

### Task 6 English Flat and Topic-Section Answer Synthesis

- Date/session: 2026-07-07.
- Change summary: Converted assistant answer synthesis to English flat and topic-section output for the Task 6 slice of multi-topic assistant QA work.
- Completed or modified functionality:
  - Added topic-context helper functions for detecting topic-labeled retrieval results, preserving first-seen topic order, and rendering grouped evidence sections.
  - Replaced empty-result answer synthesis with English conclusion, basis, risk, next-step, suggested-action, and open-question wording.
  - Replaced the main answer construction with English flat output for normal retrieval and topic-section output when retrieved context has `topic_label`.
  - Updated development-advice recommendation, workflow approval text, and memory/action/question section headings to English.
  - Preserved the existing public JSON contract; no `topic_groups` or other new output fields were added.
  - Adjusted two direct synthesis strings to satisfy existing graph assertions: retained `Request type: Project Q&A` in flat answers and kept project-memory user summaries from leaking the internal phrase `Long-term project memory only`.
- Affected files or modules:
  - `src/nodes/assistant_nodes.py`
  - `docs/superpowers/history/2026-07-07-development-history.md`
- Verification:
  - Focused assistant graph tests passed with `14 passed` using `PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/python -m pytest /Users/cltx/projects/langgraph/.claude/worktrees/multi-topic-agent-qa/tests/test_assistant_graph.py -q`.
- Follow-ups:
  - None for this task.

### Task 6 Review Fixes: Topic Deduplication and Empty-Result Wording

- Date/session: 2026-07-07.
- Change summary: Fixed Task 6 review findings in assistant answer synthesis.
- Completed or modified functionality:
  - Updated `_group_context_by_topic()` to deduplicate retrieved context by first-seen path before adding evidence to topic sections, preserving deterministic input order and first-seen topic order.
  - Reworded empty-result answer basis text so user-facing output no longer refers to internal assistant analysis framing.
  - Preserved Task 4 topic detection and retrieval helpers unchanged.
- Affected files or modules:
  - `src/nodes/assistant_nodes.py`
  - `docs/superpowers/history/2026-07-07-development-history.md`
- Verification:
  - Focused assistant graph tests passed with `14 passed` using `PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/python -m pytest /Users/cltx/projects/langgraph/.claude/worktrees/multi-topic-agent-qa/tests/test_assistant_graph.py -q`.
- Follow-ups:
  - None.


- Date/session: 2026-07-07.
- Change summary: Converted assistant response helper rendering functions from Chinese labels to English internal helper output as the Task 5 slice of multi-topic assistant QA work.
- Completed or modified functionality:
  - Updated `_request_type_label()` to return English request type labels.
  - Updated `_context_summary_for_user()` to render indexed hit summaries, key symbols, evidence, inconsistency flags, and confidence in English.
  - Updated suggested-command and open-question label helpers to return English agent-facing text.
  - Updated research-memory and project-memory summary helpers to render English provenance and evidence-priority warnings.
  - Intentionally did not rewrite `synthesize_response_node()` answer structure or topic-section rendering; that remains Task 6 scope.
- Affected files or modules:
  - `src/nodes/assistant_nodes.py`
  - `docs/superpowers/history/2026-07-07-development-history.md`
- Verification:
  - Baseline assistant graph tests failed before implementation with 7 failures and 7 passes, mostly due to English answer-structure expectations not yet implemented.
  - Focused assistant graph tests after helper conversion ran with 6 failures and 8 passes; remaining failures are in `synthesize_response_node()` answer structure, section headings, and topic-section rendering owned by Task 6.
- Follow-ups:
  - Task 6 should convert `synthesize_response_node()` structure and topic-section rendering, then refresh the assistant graph test baseline.


### Final Review Fixes Before Commit

- Date/session: 2026-07-07.
- Change summary: Fixed final review blockers found after the English multi-topic assistant implementation and search CLI additions.
- Completed or modified functionality:
  - Updated assistant gameplay topic detection to require ASCII token-boundary matches for ASCII keywords, preventing terms such as `move` from matching `remove` while preserving CJK substring matching.
  - Updated multi-topic retrieval to combine each topic query with the original user question so constraints such as `押镖车` are preserved while retaining topic-specific recall.
  - Updated topic-section grouping to deduplicate evidence within each topic section only, so shared strong evidence can appear under multiple relevant topic headings while `related_paths` remains globally unique.
  - Updated keyword retrieval tokenization to split camelCase and PascalCase identifiers, restoring exact-token recall for symbols such as `syncRolePosition` and `updateDamageMeData`.
  - Restored explicit English route-intent phrase handling for `sea route`, `second route`, `client`, and `recalculation` queries.
  - Updated gameplay retrieval-gap proposal detection so confirmed Chinese notes such as `已确认` are not treated as unresolved uncertainty.
  - Added non-mutating search mode switches to keyword, vector, and hybrid retrieval, and made `scripts/search_project.py` use them so search-only CLI calls against existing legacy SQLite files do not initialize or migrate schema.
- Affected files or modules:
  - `src/nodes/assistant_nodes.py`
  - `src/retriever/keyword_search.py`
  - `src/retriever/vector_search.py`
  - `src/retriever/hybrid_search.py`
  - `src/self_improvement/proposals.py`
  - `scripts/search_project.py`
  - `docs/superpowers/history/2026-07-07-development-history.md`
- Verification:
  - RED baseline for the final blocker regressions failed with 5 failures: ASCII topic boundary, shared topic evidence, camelCase retrieval recall, confirmed Chinese note filtering, and search CLI legacy DB non-mutation.
  - After fixes, the same focused regression command passed with `5 passed`.
  - Related review coverage for constrained multi-topic retrieval, English multi-topic assistant output, CLI JSON contract stability, and English route-intent phrases passed with `4 passed`.
- Follow-ups:
  - Affected verification suites passed with `68 passed`.
  - Retrieval evaluation passed with `15/15 passed` after ranking tuning for movement sync, combat damage, escort follow distance, and mount CLI summoning coverage.
  - Full test suite passed with `101 passed`.
  - Search CLI smoke test for `移动位置同步` returned `result_count` 8 with `src/task/sync/process_sync_rs_task.cpp` and `src/task/tcp/process_cli_role_move_tcp_task.cpp` ranked first and second.
  - Ask CLI multi-topic JSON smoke test returned stable JSON fields, English topic sections, no `topic_groups` field, and persisted a research note as designed.
  - README test baseline was updated from `93 passed` to `101 passed`.
  - Target C++ project status was checked read-only with `git -C /Users/cltx/projects/escort_server/doll_escort_game_svr status --short`; existing status was `M CMakeLists.txt`, `M src/rtb_models/rtb_unit_character.h`, and `?? ../.idea/`. No target-project mutations were made by this work.
