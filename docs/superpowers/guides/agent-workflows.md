# Agent Workflow Recipes

Date: 2026-07-07

This guide is the canonical workflow recipe for Codex, Claude Code, and similar agents answering questions about the target C++ project through this LangGraph assistant.

Keep the split simple:

- `AGENTS.md` is the short entrypoint and hard-rule checklist.
- `README.md` is the full architecture and CLI reference.
- This file explains how to combine the CLIs, source reads, and memory layers during real agent work.

The target C++ project is read-only by default. These recipes cover investigation, retrieval tuning, documentation, and read-only development advice unless the user explicitly approves stronger actions.

## Evidence Priority

Always rank evidence in this order:

1. Current source code read directly with `Read` after locating candidate paths.
2. Current indexed implementation evidence returned by `scripts/search_project.py` or the assistant graph.
3. Curated long-term `project_memories`.
4. Historical `research_notes` from prior assistant investigations.
5. Comments, file names, and historical documentation.

Do not directly trust memory, summaries, or symbol names when the current source can be inspected. If the evidence conflicts, say so in the final Chinese answer and identify which current files should be checked next.

## 1. Project Q&A Recipe

Use this recipe when the user asks where logic lives or how an existing C++ feature works, for example:

- 某逻辑在哪里？
- 移动同步在哪里？
- 战斗伤害怎么算？
- 坐骑相关逻辑在哪？

Preferred workflow:

1. Read `AGENTS.md` and relevant `README.md` sections if not already loaded.
2. Run `scripts/search_project.py --output json` with the user's key terms.
3. Select the top 3 to 8 high-signal paths, preferring business source files and exact path/symbol evidence over weak semantic matches.
4. Use `Read` on the key current source files to verify symbols, control flow, side effects, and call boundaries.
5. Run `scripts/ask_project.py` when a synthesized Chinese answer or saved `research_notes` entry is useful.
6. Final answer in Chinese, separating evidence types when relevant:
   - 当前源码证据
   - 索引摘要
   - 历史调研记忆
   - 长期项目记忆

Search command template:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph \
/Users/cltx/projects/langgraph/venv/bin/python \
/Users/cltx/projects/langgraph/scripts/search_project.py \
--query "移动位置同步" \
--limit 8 \
--output json
```

Ask command template:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph \
/Users/cltx/projects/langgraph/venv/bin/python \
/Users/cltx/projects/langgraph/scripts/ask_project.py \
--question "移动位置同步、战斗伤害、坐骑逻辑分别在哪里？" \
--output text
```

Do not skip the source read step for answers that depend on exact implementation behavior.

## 2. Development Advice Recipe

Use this recipe when the user asks for implementation planning or impact analysis, for example:

- 我要改移动同步，影响哪些文件？
- 我要改冲锋逻辑，怎么做？
- 这个需求可能碰到哪些副作用？

Preferred workflow:

1. Run `scripts/search_project.py --output json` to identify candidate implementation files, callers, handlers, configuration files, and tests if indexed.
2. Use `Read` to inspect current source before making claims about behavior or edit locations.
3. Run `scripts/ask_project.py --output json` when the assistant graph's request classification, `approval_required`, related paths, open questions, or Chinese synthesis are useful.
4. Tell the user explicitly that the output is read-only development advice.
5. Do not edit, build, clean, commit, push, delete, or otherwise mutate the target C++ project unless the user explicitly approves that action.
6. Identify verification needs before any future target-project modification, especially:
   - 调用链
   - 状态副作用
   - 网络包/协议边界
   - 帧边界或 tick 时序
   - 线程、锁、缓存或持久化影响

The final Chinese answer should distinguish what is confirmed by current source from what is an assistant recommendation.

## 3. Retrieval Quality Tuning Recipe

Use this recipe when an answer is inaccurate, important files rank too low, or noisy files outrank implementation files.

Preferred workflow:

1. Add the real user question and expected source paths to a retrieval evaluation fixture.
2. Run retrieval evaluation first and observe the failing or weak ranking.
3. Adjust keyword, hybrid, vector-like, synonym, path, symbol, or memory retrieval behavior minimally.
4. Run the focused retrieval tests and retrieval evaluation again.
5. Run the full test suite before completion.
6. Record the retrieval change, failure mode, affected files, and verification in the active dated history file.

Retrieval evaluation command:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph \
/Users/cltx/projects/langgraph/venv/bin/python \
/Users/cltx/projects/langgraph/scripts/run_retrieval_eval.py \
--db /Users/cltx/projects/langgraph/checkpoints/project_index.sqlite \
--cases /Users/cltx/projects/langgraph/tests/fixtures/retrieval_eval
```

Do not tune retrieval from intuition alone. Preserve inspectable ranking reasons so future agents can understand why a path appeared.

## 4. Memory Distillation Recipe

Use this recipe when the same target-project topic appears repeatedly or a durable risk/fact emerges.

Memory boundaries:

- `research_notes` are investigation records for a specific question or session.
- `project_memories` are curated long-term facts, domain concepts, risk notes, open questions, or retrieval lessons.
- Do not automatically promote `research_notes` into `project_memories`.
- Promote only after review or explicit approval, and only when the fact is expected to remain useful.

Preferred workflow:

1. Let `scripts/ask_project.py` persist ordinary investigations as `research_notes` when synthesis is useful.
2. Before adding or changing `project_memories`, verify the fact against current source or clearly label it as a durable open question/risk.
3. Keep `project_memories` concise and source-grounded.
4. In final answers, label historical research as historical assistant conclusions and keep it below current source evidence.

Never answer from memory alone when current code evidence is available.

## 5. Safety Boundary Recipe

The target C++ project at `/Users/cltx/projects/escort_server/doll_escort_game_svr` is read-only by default.

Without explicit user approval, do not run actions that mutate or stress the target project, including:

- edit files
- build
- clean
- commit
- push
- delete
- regenerate project files
- run destructive maintenance commands

Allowed by default for target-project investigation:

- read files
- inspect indexed evidence
- run the LangGraph repository's read-only CLIs against the existing index
- provide Chinese read-only development advice

This LangGraph repository may be modified when implementing the assistant itself, but changes still need tests and an entry in the active dated history file.
