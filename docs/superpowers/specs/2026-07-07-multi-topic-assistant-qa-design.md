# Multi-Topic Agent-Facing Assistant Q&A Design

Date: 2026-07-07

## Goal

Make the project assistant better suited for Claude Code, Codex, and similar agent callers by converging output language to English and improving multi-topic project questions.

The motivating query is:

```text
移动位置同步、战斗伤害、坐骑逻辑分别在哪里？
```

The assistant should return an English, agent-readable answer that separates evidence for movement/position sync, combat damage, and mount logic instead of over-focusing on one topic.

## Non-Goals

- Do not modify, build, clean, commit, push, delete, or otherwise mutate the target C++ project.
- Do not add an MCP server or a reusable skill in this change.
- Do not expand the `ask_project.py --output json` public contract with `topic_groups` yet.
- Do not redesign retrieval evaluation broadly; add only targeted coverage needed for this behavior.

## Language Policy

This repository is an agent-facing LangGraph assistant. New and updated project behavior should use English for:

- CLI text answers.
- JSON answer strings.
- Documentation and workflow recipes.
- Tests and expected output assertions.
- Research note summaries written by the assistant.

Internal model-facing text already uses English and should remain English. The previous Chinese-answer rule should be removed or narrowed to cases where the user explicitly asks for Chinese end-user output.

## Current Behavior

`ask_project.py` invokes `create_assistant_graph()` and prints either `answer` or a stable JSON subset.

The assistant graph currently retrieves project context once with the whole question:

```text
retrieve_project_context_node -> hybrid_search_project(question) -> related_paths = flat top-N paths
```

`synthesize_response_node()` then renders a single flat answer. This works for narrow questions, but multi-topic questions can be dominated by one strong topic. In the real smoke test, the combined movement/combat/mount question produced `related_paths` biased toward battle files even though `search_project.py` can independently find good movement and mount paths.

## Recommended Design

Use internal topic-aware retrieval and synthesis while preserving the public CLI JSON contract.

### Topic Detection

Add a small internal detector for known gameplay topics. The first version should cover:

- `movement_position_sync`: movement, move, position, sync, 移动, 位置, 同步
- `combat_damage`: combat, battle, damage, hp, hit, 战斗, 伤害, 扣血, 命中
- `mount_logic`: mount, horse, ride, speed, 坐骑, 上马, 下马, 速度

If fewer than two topics match, keep the existing single-query path.

### Per-Topic Retrieval

For multi-topic questions, run retrieval once per detected topic using a stable expanded query. Example queries:

- Movement / position sync: `movement position sync move 移动 位置 同步`
- Combat damage: `combat battle damage hp hit 战斗 伤害 扣血 命中`
- Mount logic: `mount horse ride dismount speed sync 坐骑 上马 下马 速度 同步`

Each topic should keep a small number of high-signal results, such as 3 to 5 paths. The implementation should reuse `hybrid_search_project()` and the existing keyword fallback. Results should be merged in topic order with path de-duplication.

Attach internal metadata to result dictionaries before synthesis:

- `topic_id`
- `topic_label`
- `topic_query`

These fields remain internal graph state. `ask_project.py --output json` should still expose the existing fields only:

- `answer`
- `request_type`
- `related_paths`
- `approval_required`
- `open_questions`
- `suggested_commands`
- `research_note_id`
- `thread_id`
- `flow_version`

### Answer Synthesis

When retrieved context contains topic metadata, `synthesize_response_node()` should render an English answer with sections:

```text
Conclusion
Current indexed evidence
Movement / position sync
Combat damage
Mount logic
Risks and verification notes
Memory context, if any
Suggested workflow, if any
```

Each topic section should include:

- Relevant paths.
- Key symbols when available.
- Indexed evidence and confidence.
- A short warning to verify current source before editing.

When a detected topic has no results, the answer should say the current index did not provide enough evidence for that topic. It must not invent paths.

When there is no topic metadata, keep a simple English version of the existing flat answer.

### Related Paths

`related_paths` remains a flat list for compatibility. In multi-topic mode, its order should be topic-balanced:

1. Movement / position sync results.
2. Combat damage results.
3. Mount logic results.
4. Any remaining deduplicated results.

This is sufficient for existing agent callers to discover representative files without a contract change.

## Testing Strategy

Follow TDD.

First add failing tests that encode the new behavior:

1. Assistant graph multi-topic test with realistic seeded files and noise:
   - Seed movement/sync files.
   - Seed combat/damage files.
   - Seed mount files.
   - Seed extra battle/noise files that could dominate flat retrieval.
   - Ask the combined movement/combat/mount question.
   - Assert English topic sections are present.
   - Assert `related_paths` covers all three themes.
   - Assert no old Chinese-only framing such as `结论：这是项目问答` is required.

2. CLI JSON contract test:
   - Run `scripts/ask_project.py --output json` against a temporary seeded DB.
   - Assert the payload fields remain the current stable field set.
   - Assert `answer` contains English topic sections.
   - Assert no `topic_groups` field is exposed yet.

3. Existing Chinese-output tests should be updated to English-output expectations.

Focused verification commands:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph venv/bin/python -m pytest tests/test_assistant_graph.py tests/test_assistant_cli.py -q
```

Full verification commands:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph venv/bin/python scripts/run_retrieval_eval.py --db checkpoints/project_index.sqlite --cases tests/fixtures/retrieval_eval
PYTHONPATH=/Users/cltx/projects/langgraph venv/bin/python -m pytest tests -q
```

## Documentation Updates

Update documentation and history to match the English agent-facing policy:

- `AGENTS.md`: replace the Chinese final-answer rule with English agent-facing output guidance.
- `README.md`: update CLI descriptions, examples, and tests baseline if it changes.
- `docs/superpowers/guides/agent-workflows.md`: update the final-answer recipe from Chinese to English agent-readable answers.
- `docs/superpowers/history/2026-07-07-development-history.md`: record the language-policy convergence and multi-topic Q&A change.

## Risks

- Changing the output language affects existing tests and any caller expecting Chinese. The repository is now explicitly agent-facing, so this is intentional.
- Per-topic retrieval increases retrieval calls for multi-topic questions. The scope is limited to detected multi-topic gameplay questions, so cost and latency remain bounded.
- Hard-coded topic detection can miss future domains. This is acceptable for the first fix because it addresses the verified movement/combat/mount failure without adding a larger query planner.
- Exposing `topic_groups` too early would make the contract harder to change. Keeping topic grouping internal avoids that risk.

## Success Criteria

- Multi-topic `ask_project.py` answers are English and topic-organized.
- Existing JSON field contract remains stable and does not expose `topic_groups`.
- `related_paths` covers movement/sync, combat/damage, and mount logic for the motivating question.
- Existing single-topic behavior remains compatible except for the intended language change to English.
- Focused assistant/CLI tests pass.
- Retrieval evaluation passes.
- Full test suite passes.
- The target C++ project remains read-only.
