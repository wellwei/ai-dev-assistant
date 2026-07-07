# Agent Guide for This LangGraph Project

This repository is a LangGraph-based project knowledge assistant for the target C++ project:

```text
/Users/cltx/projects/escort_server/doll_escort_game_svr
```

Use this file as the short operating guide for Codex, Claude Code, and similar agents. For full architecture, graph flow, schema notes, and examples, read `README.md`.

## First Steps

1. Read `README.md`.
2. Check `langgraph.json` for exposed graph names.
3. Read the latest dated file under `docs/superpowers/history/`.
4. Inspect relevant tests before changing behavior.
5. Prefer current implementation evidence over comments, docs, names, historical notes, and project memory.

## Hard Rules

- Treat the target C++ project as read-only by default.
- Do not edit, build, commit, push, clean, delete, or otherwise mutate the target C++ project unless the user explicitly approves that action.
- This LangGraph repository may be modified when implementing the assistant itself.
- Internal model-facing text must be English, including prompts, `analysis`, workflow steps, memory summaries, and suggested commands.
- Agent-facing answers, CLI output, documentation, tests, and assistant-written summaries should be English by default.
- Use Chinese only when the user explicitly requests Chinese end-user-facing output.
- Do not expose raw internal `analysis` in final answers or CLI JSON output.
- Current indexed implementation evidence outranks project memories and historical research notes.
- Historical notes are context only; label them as historical assistant conclusions if surfaced.
- Update the correct dated file in `docs/superpowers/history/` for every code, behavior, retrieval, schema, safety, or documentation rule change.

## Entrypoints

`langgraph.json` exposes:

- `assistant`: `./src/graph.py:create_graph`
- `indexer`: `./src/index_graph.py:create_index_graph`

Use `assistant` for project Q&A, requirement research, and read-only development advice.
Use `indexer` only when refreshing the SQLite project index is appropriate or approved.

## Workflow Recipes

For the default target-project workflow, read `docs/superpowers/guides/agent-workflows.md`. It explains when to use `scripts/search_project.py`, when to inspect current source with `Read`, when to use `scripts/ask_project.py`, and how to separate current source evidence from index summaries, `research_notes`, and `project_memories`.

## Agent-Friendly CLI

Use the CLI when an agent needs to ask the local project knowledge assistant from a shell command.

Use `scripts/search_project.py` when you need ranked paths/evidence only, before reading files or building a prompt:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph \
/Users/cltx/projects/langgraph/venv/bin/python \
/Users/cltx/projects/langgraph/scripts/search_project.py \
--query "移动位置同步" \
--output json
```

Use `scripts/ask_project.py` when you need a synthesized English agent-facing answer:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph \
/Users/cltx/projects/langgraph/venv/bin/python \
/Users/cltx/projects/langgraph/scripts/ask_project.py \
--question "移动位置同步、战斗伤害、坐骑逻辑分别在哪里？" \
--output text
```

Use JSON when the caller needs stable machine-facing fields:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph \
/Users/cltx/projects/langgraph/venv/bin/python \
/Users/cltx/projects/langgraph/scripts/ask_project.py \
--question "我要修改移动位置同步逻辑，影响哪些文件？" \
--output json
```

Expected behavior:

- `search_project.py --output text|json` prints ranked paths and evidence only, without invoking the assistant graph or persisting research notes.
- `ask_project.py --output text` prints only the final English agent-facing `answer`.
- `ask_project.py --output json` prints stable fields such as `answer`, `request_type`, `related_paths`, `approval_required`, `open_questions`, `suggested_commands`, `research_note_id`, `thread_id`, and `flow_version`.
- JSON output intentionally excludes internal English `analysis` and raw retrieved context.
- Missing index DB or empty question returns exit code `2`.
- Runtime graph failures return exit code `1`.

If CLI behavior differs, inspect `scripts/ask_project.py` and trust the implementation.

## Working With Evidence

When answering target-project questions:

1. Retrieve current project context first.
2. Separate current implementation evidence from project memory and historical research notes.
3. Prefer exact paths, symbols, and implementation side-effect evidence over weak semantic matches.
4. If evidence is weak, stale, or conflicting, say so clearly in English and identify what should be inspected next.
5. Do not invent facts from memory or names alone.

## Testing and Documentation

- Add or update tests when changing retrieval, memory, CLI behavior, graph flow, schemas, or safety rules.
- Run focused tests for the changed area first.
- Run retrieval evaluation before and after ranking, synonym, embedding, or memory-retrieval changes.
- Run the full test suite before claiming completion.
- Use the active date's history file, for example `docs/superpowers/history/2026-07-07-development-history.md` for current work.
