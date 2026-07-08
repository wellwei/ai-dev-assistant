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

### Main Branch Multi-Topic QA Coverage Port

- Date/session: 2026-07-08.
- Change summary: Compared `main` against the completed `worktree-multi-topic-agent-qa` branch and ported missing runtime behavior and regression coverage to latest `main`.
- Completed or modified functionality:
  - Ported English-by-default assistant answer synthesis and topic-section rendering for movement/position sync, combat damage, and mount logic.
  - Ported topic-aware retrieval that preserves original user constraints while using per-topic query expansion and globally unique `related_paths`.
  - Ported ASCII token-boundary topic detection so keywords such as `move` do not match `remove`.
  - Ported per-topic evidence grouping that allows shared evidence to appear in multiple relevant topic sections while keeping public JSON flat and stable.
  - Ported keyword retrieval fixes for camelCase/PascalCase token recall, English route intent phrases, gameplay ranking boosts, and non-mutating search paths.
  - Ported the search-only CLI legacy-database read-only behavior, embedding model version bump, and confirmed-Chinese-note self-improvement guard.
  - Ported missing assistant, CLI, retriever, search CLI, self-improvement, embedding, and agent-guide regression tests from the worktree branch.
- Affected files or modules:
  - `AGENTS.md`
  - `README.md`
  - `docs/superpowers/guides/agent-workflows.md`
  - `scripts/search_project.py`
  - `src/embeddings/provider.py`
  - `src/nodes/assistant_nodes.py`
  - `src/retriever/hybrid_search.py`
  - `src/retriever/keyword_search.py`
  - `src/retriever/vector_search.py`
  - `src/self_improvement/proposals.py`
  - `tests/test_agent_guides.py`
  - `tests/test_assistant_cli.py`
  - `tests/test_assistant_graph.py`
  - `tests/test_embeddings_provider.py`
  - `tests/test_retriever.py`
  - `tests/test_search_project_cli.py`
  - `tests/test_self_improvement.py`
  - `tests/test_index_graph.py`
- Verification:
  - Focused missing-behavior regression tests passed with `5 passed`.
  - Affected assistant, CLI, retriever, search CLI, self-improvement, embedding, and retrieval-evaluation suites passed with `68 passed`.
  - Retrieval evaluation passed with `15/15 passed`.
  - Full test suite initially failed because `tests/test_index_graph.py::test_index_then_assistant_answer_end_to_end` still asserted Chinese output (`置信度`, `注释`, `命名`) after the main branch received English answer synthesis; the test was updated to assert `Confidence` and `comment`/`name`, then passed with `1 passed`.
  - Full test suite passed with `100 passed`.
  - Search CLI smoke test for `移动位置同步` returned `result_count` 8 with `src/task/sync/process_sync_rs_task.cpp` and `src/task/tcp/process_cli_role_move_tcp_task.cpp` ranked first and second.
  - Ask CLI multi-topic JSON smoke test returned stable JSON fields, English topic sections, no `topic_groups` field, and persisted a research note as designed.
  - `git diff --check` passed with no whitespace errors.
  - README test baseline was updated from `101 passed` to `100 passed` after preserving latest main guide-skill tests.
- Follow-ups:
  - After the main branch commit is verified, the old `worktree-multi-topic-agent-qa` worktree can be removed if no additional diffs are needed.
