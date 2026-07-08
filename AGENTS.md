# Agent Guide for This LangGraph Project

## Project Overview

This repository builds a LangGraph-based project knowledge assistant for the read-only target C++ project at `/Users/cltx/projects/escort_server/doll_escort_game_svr`. It indexes the target project into SQLite, answers project questions, supports read-only development advice, and keeps research/project memory separate from current source evidence.

Primary stack: Python, LangGraph, SQLite, pytest, local deterministic retrieval, and agent-facing CLI scripts.

## Document Routing

Keep context small. Read only what the task needs.

| Need | Read |
| --- | --- |
| Entry rules, safety, commands, and routing | `AGENTS.md` |
| Target-project investigation workflow | `docs/superpowers/guides/agent-workflows.md` |
| LangGraph, LangChain, deep agents, RAG, persistence, CLI, human-in-the-loop, middleware, or swarm guidance | Matching `config/skills/<skill-name>/SKILL.md` |
| Full architecture or background not covered by focused docs | Relevant section of `README.md` only |
| Design history, behavior changes, or verification records | Today's `docs/superpowers/history/YYYY-MM-DD-development-history.md` |

Do not read `README.md` by default. Use it only when a focused document or current source does not answer the question.

## Project Skills

Project-level skills live under `config/skills/`. Codex and similar agents should treat them as task-specific project documentation, not as automatically loaded tools.

Read the relevant skill before answering or editing when the task concerns:

- `config/skills/langgraph-fundamentals/SKILL.md` — LangGraph graph concepts and patterns.
- `config/skills/langgraph-cli/SKILL.md` — LangGraph CLI usage.
- `config/skills/langgraph-persistence/SKILL.md` — checkpointing, persistence, threads, and state storage.
- `config/skills/langgraph-human-in-the-loop/SKILL.md` — interrupts, approvals, and human review loops.
- `config/skills/langchain-fundamentals/SKILL.md` — LangChain concepts.
- `config/skills/langchain-dependencies/SKILL.md` — LangChain package/dependency choices.
- `config/skills/langchain-middleware/SKILL.md` — middleware behavior.
- `config/skills/langchain-rag/SKILL.md` — RAG design and retrieval behavior.
- `config/skills/deep-agents-core/SKILL.md`, `deep-agents-memory`, `deep-agents-orchestration`, or `managed-deep-agents` — deep agent design.
- `config/skills/swarm/SKILL.md` — swarm patterns and its supporting scripts.
- `config/skills/ecosystem-primer/SKILL.md` — ecosystem orientation.

`skills-lock.json` records imported skill paths and hashes. Ordinary tasks do not need to read it unless verifying the skill import.

## Development Environment

Use the repository virtual environment when available:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph \
/Users/cltx/projects/langgraph/venv/bin/python -m pytest tests -q
```

Important environment defaults are defined in `src/config.py` and `.env.example`:

- `TARGET_PROJECT_ROOT=/Users/cltx/projects/escort_server/doll_escort_game_svr`
- `CHECKPOINT_DB=./checkpoints/langgraph.sqlite`
- `PROJECT_INDEX_DB=./checkpoints/project_index.sqlite`
- `MODEL_NAME=gpt-4o`

## Build and Test Commands

Focused tests:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph \
/Users/cltx/projects/langgraph/venv/bin/python -m pytest tests/test_agent_guides.py -q
```

Full tests:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph \
/Users/cltx/projects/langgraph/venv/bin/python -m pytest tests -q
```

Retrieval evaluation after ranking, synonym, embedding, or memory-retrieval changes:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph \
/Users/cltx/projects/langgraph/venv/bin/python scripts/run_retrieval_eval.py \
--db /Users/cltx/projects/langgraph/checkpoints/project_index.sqlite \
--cases /Users/cltx/projects/langgraph/tests/fixtures/retrieval_eval
```

Search-only target-project evidence:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph \
/Users/cltx/projects/langgraph/venv/bin/python scripts/search_project.py \
--query "移动位置同步" --output json
```

Synthesized assistant answer:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph \
/Users/cltx/projects/langgraph/venv/bin/python scripts/ask_project.py \
--question "移动位置同步、战斗伤害、坐骑逻辑分别在哪里？" --output text
```

## Code Style Guidelines

- Internal model-facing text must be English, including prompts, `analysis`, workflow steps, memory summaries, and suggested commands.
- Agent-facing answers, CLI output, documentation, tests, and assistant-written summaries should be English by default.
- Use Chinese only when the user explicitly requests Chinese end-user-facing output.
- Do not expose raw internal `analysis` in final answers or CLI JSON output.
- Prefer current implementation evidence over comments, docs, names, historical notes, and project memory.
- When changing retrieval, memory, CLI behavior, graph flow, schemas, or safety rules, update or add focused tests.

## Git and PR Workflow

- Do not commit, push, or create a PR unless the user explicitly asks.
- Before claiming completion, run focused verification for the changed area.
- Run the full test suite before broad behavior claims.
- Record every code, behavior, retrieval, schema, safety, or documentation rule change in today's dated history file.

## Boundaries

- Treat `/Users/cltx/projects/escort_server/doll_escort_game_svr` as read-only by default.
- Do not edit, build, commit, push, clean, delete, regenerate, or otherwise mutate the target C++ project unless the user explicitly approves that action.
- This LangGraph repository may be modified when implementing the assistant itself.
- Use `assistant` from `langgraph.json` for project Q&A, requirement research, and read-only development advice.
- Use `indexer` only when refreshing the SQLite project index is appropriate or approved.
- Do not continue Hermes Agent integration work. The existing Hermes no-op boundary is historical and disabled; keep it inert until an explicit cleanup removes it.
- Self-improvement proposals must remain proposals until an explicit review and approval workflow exists.
- Future memory and self-improvement work should use a self-developed project memory layer, not Hermes Agent.

## Development History Rule

Use today's date from the session context for history entries. Write to `docs/superpowers/history/YYYY-MM-DD-development-history.md`; create the file if it does not exist. Never append a new entry to the latest existing history file when that file is from a prior day.
