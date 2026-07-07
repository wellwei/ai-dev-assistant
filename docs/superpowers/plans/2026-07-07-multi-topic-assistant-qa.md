# Multi-Topic Agent-Facing Assistant Q&A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the assistant to English agent-facing output and make multi-topic questions return balanced movement/sync, combat/damage, and mount evidence without changing the public JSON field contract.

**Architecture:** Keep `ask_project.py` as a thin wrapper. Implement topic detection, per-topic retrieval, deduplicated path merging, and English synthesis inside `src/nodes/assistant_nodes.py`. Preserve the existing graph shape and JSON fields while attaching internal topic metadata to retrieved context items for answer rendering.

**Tech Stack:** Python 3.14, LangGraph, pytest, SQLite-backed `ProjectIndexRepository`, existing `hybrid_search_project()` and `search_project_index()` retrieval functions.

## Global Constraints

- Target C++ project remains read-only: do not edit, build, clean, commit, push, delete, or otherwise mutate `/Users/cltx/projects/escort_server/doll_escort_game_svr`.
- Public `ask_project.py --output json` fields remain: `answer`, `request_type`, `related_paths`, `approval_required`, `open_questions`, `suggested_commands`, `research_note_id`, `thread_id`, `flow_version`.
- Do not expose `topic_groups` in JSON in this change.
- New and updated project behavior should use English for CLI text answers, JSON answer strings, documentation, workflow recipes, tests, and assistant-written research note summaries.
- Internal model-facing text remains English.
- Follow TDD: write each behavioral test, run it and observe failure, then implement the minimal code to pass.
- Update `docs/superpowers/history/2026-07-07-development-history.md` before completion.
- Run focused tests, retrieval evaluation, full test suite, and target-project status check before claiming completion.

---

## File Structure

- Modify `src/nodes/assistant_nodes.py`
  - Add internal gameplay topic definitions.
  - Add topic detection and per-topic retrieval helpers.
  - Update `retrieve_project_context_node()` to use topic-aware retrieval only when at least two known topics match.
  - Convert user-facing synthesis helper functions from Chinese to English.
  - Add topic-section rendering while preserving flat rendering for non-topic results.

- Modify `tests/test_assistant_graph.py`
  - Update existing Chinese-output assertions to English-output assertions.
  - Strengthen the multi-topic test with noise and topic section expectations.
  - Add coverage that topic metadata remains internal and `related_paths` covers all three themes.

- Modify `tests/test_assistant_cli.py`
  - Update text and development-advice assertions to English.
  - Add or extend a CLI JSON contract test proving no `topic_groups` field is emitted and English topic sections appear for a multi-topic question.

- Modify `AGENTS.md`
  - Replace Chinese final-answer rule with English agent-facing output guidance.
  - Update CLI description from “synthesized Chinese answer” to “synthesized English agent-facing answer.”

- Modify `README.md`
  - Update Assistant Graph and CLI descriptions that currently say final answer is Chinese.
  - Update examples and baseline if test count changes.

- Modify `docs/superpowers/guides/agent-workflows.md`
  - Replace Chinese-answer instructions with English agent-readable answer instructions.

- Modify `docs/superpowers/history/2026-07-07-development-history.md`
  - Add a final entry for language-policy convergence and multi-topic assistant Q&A.

---

### Task 1: Assistant Graph English Output Tests

**Files:**
- Modify: `tests/test_assistant_graph.py`
- Test: `tests/test_assistant_graph.py`

**Interfaces:**
- Consumes: existing `create_assistant_graph(repo=..., checkpointer=...)` and `ProjectIndexRepository` test setup.
- Produces: failing tests defining English agent-facing output for existing graph behavior.

- [ ] **Step 1: Update the project-memory display test to expect English answer labels**

In `tests/test_assistant_graph.py`, replace the answer assertions in `test_assistant_graph_retrieves_and_displays_project_memories()`:

```python
    assert "Project memories" in result["answer"]
    assert "current indexed implementation evidence wins" in result["answer"]
    assert "memory#" in result["answer"]
    assert "Long-term project memory only" not in result["answer"]
    assert "Project memory #" not in result["answer"]
```

Remove the old assertions:

```python
    assert "长期项目记忆" in result["answer"]
    assert "当前实现索引证据优先" in result["answer"]
    assert "current implementation evidence wins" not in result["answer"]
```

- [ ] **Step 2: Update the no-memory test to expect no English memory section**

In `test_assistant_graph_omits_project_memory_section_when_no_match()`, replace:

```python
    assert "长期项目记忆" not in result["answer"]
```

with:

```python
    assert "Project memories" not in result["answer"]
```

- [ ] **Step 3: Update the flat project question test to expect English output**

In `test_assistant_graph_answers_project_question_and_persists_note()`, replace the answer assertions with:

```python
    assert "This is a project question or requirement research request." in result["analysis"]
    assert "Request type: Project Q&A" in result["answer"]
    assert "src/route.cpp" in result["answer"]
    assert "Confidence" in result["answer"]
    assert "comments" in result["answer"] or "names" in result["answer"]
    assert "This is a project question or requirement research request." not in result["answer"]
    assert "结论" not in result["answer"]
    assert result["research_note_id"] is not None
```

- [ ] **Step 4: Update key-symbol test to expect English label**

In `test_assistant_graph_answer_surfaces_key_symbols_for_movement_context()`, replace:

```python
    assert "关键函数/符号" in result["answer"]
```

with:

```python
    assert "Key symbols" in result["answer"]
```

Keep the existing symbol assertions.

- [ ] **Step 5: Update development-advice test to expect English read-only guidance**

In `test_assistant_graph_classifies_development_advice()`, replace:

```python
    assert "建议" in result["answer"]
    assert "需要审批" in result["answer"]
    assert "不要直接修改" in result["answer"]
```

with:

```python
    assert "Recommendation" in result["answer"]
    assert "approval required" in result["answer"]
    assert "Do not directly modify the target C++ project" in result["answer"]
```

- [ ] **Step 6: Update unclear-answer test to expect English user-facing text**

Rename `test_assistant_graph_keeps_unclear_internal_text_english_and_user_answer_chinese` to:

```python
def test_assistant_graph_keeps_unclear_answer_agent_facing_english(tmp_path):
```

Replace the answer assertions with:

```python
    assert "The current index does not contain enough information" in result["answer"]
    assert "The user question is empty or unclear" not in result["answer"]
    assert "当前索引" not in result["answer"]
```

- [ ] **Step 7: Update research-memory answer assertions to English**

In `test_assistant_graph_reuses_prior_research_memory()`, replace:

```python
    assert "历史调研记忆" in second["answer"]
    assert "Prior research" not in second["answer"]
```

with:

```python
    assert "Prior research memory" in second["answer"]
    assert "Historical assistant conclusion" in second["answer"]
```

- [ ] **Step 8: Run the focused graph tests and verify failure**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph venv/bin/python -m pytest tests/test_assistant_graph.py -q
```

Expected: FAIL. Failures should be assertion failures showing current answers still use Chinese labels such as `结论`, `置信度`, `长期项目记忆`, or `需要审批`.

Do not implement before seeing these failures.

---

### Task 2: Multi-Topic Assistant Graph Regression Test

**Files:**
- Modify: `tests/test_assistant_graph.py`
- Test: `tests/test_assistant_graph.py::test_assistant_graph_answers_gameplay_movement_combat_mount_context_in_english_topic_sections`

**Interfaces:**
- Consumes: `ProjectIndexRepository.upsert_file()`, `ProjectIndexRepository.upsert_summary()`, and graph invocation.
- Produces: failing regression test for balanced multi-topic retrieval and English topic-section synthesis.

- [ ] **Step 1: Rename and replace the existing multi-topic test body**

Rename `test_assistant_graph_answers_gameplay_movement_combat_mount_context_in_chinese` to:

```python
def test_assistant_graph_answers_gameplay_movement_combat_mount_context_in_english_topic_sections(tmp_path):
```

Replace its `files = [...]` list with this richer fixture:

```python
    files = [
        (
            "src/task/sync/process_sync_rs_task.cpp",
            "Processes role server position synchronization and broadcasts sync data.",
            "process_sync_position, sync_role_position, write_instance_position",
            "movement, position, sync",
        ),
        (
            "src/task/tcp/process_cli_role_move_tcp_task.cpp",
            "Handles client role movement packets and position updates.",
            "process_role_move, validate_move_position, update_move_position",
            "movement, move, position",
        ),
        (
            "src/battle_calculate/battle_calculate.cpp",
            "Calculates battle damage, hp changes, and attack statistics.",
            "update_damage_me_data, update_obj_hp, calculate_damage",
            "battle, combat, damage, hp",
        ),
        (
            "src/battle_calculate/effect_calculate_process.cpp",
            "Processes damage effects, restore effects, and fatal battle effects.",
            "process_effect__hp, battle_effect__fatal, process_effect__restore",
            "battle, damage, effect, hp",
        ),
        (
            "src/rtb_proc/character/rtb_proc_character_horse.cpp",
            "Handles mount state transitions and mounted movement speed.",
            "mount_up, dismount, sync_mount_position",
            "mount, horse, ride, speed, sync",
        ),
        (
            "src/task/tcp/process_cli_summoning_mount_tcp_task.cpp",
            "Handles client mount summon requests and mount state updates.",
            "process_mount_summon, summon_mount, update_mount_state",
            "mount, summon, horse",
        ),
        (
            "src/rtb_proc/character/rtb_proc_character_persist_attack.cpp",
            "Handles persistent attack checks and can dominate generic battle queries.",
            "check_normal_skill_config, persist_attack, attack_state",
            "battle, attack, skill",
        ),
        (
            "src/task/work/battle_statistics_complex_task.cpp",
            "Aggregates battle statistics and combat notifications.",
            "battle_statistics, collect_damage_stats, notify_battle_result",
            "battle, statistics, damage",
        ),
    ]
```

Keep the existing loop that inserts files, summaries, and the graph invocation.

- [ ] **Step 2: Replace multi-topic assertions**

Replace the assertions after graph invocation with:

```python
    answer = result["answer"]
    related_paths = result["related_paths"]

    assert "Movement / position sync" in answer
    assert "Combat damage" in answer
    assert "Mount logic" in answer
    assert "Current indexed evidence" in answer

    assert "src/task/sync/process_sync_rs_task.cpp" in answer
    assert "src/battle_calculate/battle_calculate.cpp" in answer
    assert "src/rtb_proc/character/rtb_proc_character_horse.cpp" in answer
    assert "Key symbols" in answer
    assert "process_sync_position" in answer
    assert "update_damage_me_data" in answer
    assert "mount_up" in answer

    assert any("sync" in path or "move" in path for path in related_paths)
    assert any("battle" in path or "damage" in path for path in related_paths)
    assert any("horse" in path or "mount" in path for path in related_paths)
    assert len(related_paths) == len(dict.fromkeys(related_paths))

    assert "topic_groups" not in result
    assert "结论" not in answer
    assert "关键函数/符号" not in answer
    assert "This is a project question" not in answer
    assert "Key points:" not in answer
```

- [ ] **Step 3: Run the single regression test and verify failure**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph venv/bin/python -m pytest tests/test_assistant_graph.py::test_assistant_graph_answers_gameplay_movement_combat_mount_context_in_english_topic_sections -q
```

Expected: FAIL because current synthesis does not render English topic sections and may still use Chinese labels.

---

### Task 3: CLI English Output and JSON Contract Tests

**Files:**
- Modify: `tests/test_assistant_cli.py`
- Test: `tests/test_assistant_cli.py`

**Interfaces:**
- Consumes: `scripts/ask_project.py` CLI, existing `_run_cli()` helper, temporary seeded DB.
- Produces: failing CLI tests for English output and stable JSON fields.

- [ ] **Step 1: Update the text-output test to expect English**

Rename `test_assistant_cli_text_outputs_chinese_answer` to:

```python
def test_assistant_cli_text_outputs_english_agent_answer(tmp_path):
```

Replace assertions:

```python
    assert "src/route.cpp" in result.stdout
    assert "Confidence" in result.stdout
    assert "Request type: Project Q&A" in result.stdout
    assert "This is a project question" not in result.stdout
    assert "置信度" not in result.stdout
```

- [ ] **Step 2: Update development-advice CLI assertions to English**

In `test_assistant_cli_development_advice_preserves_readonly_gate()`, replace:

```python
    assert "需要审批" in payload["answer"]
    assert "不要直接修改" in payload["answer"]
```

with:

```python
    assert "approval required" in payload["answer"]
    assert "Do not directly modify the target C++ project" in payload["answer"]
```

Keep the `suggested_commands` assertion unchanged because those commands are already English machine-facing values.

- [ ] **Step 3: Add a multi-topic seed helper**

Below `_seed_repo()`, add:

```python
def _seed_multi_topic_repo(db_path: Path) -> None:
    repo = ProjectIndexRepository(db_path)
    repo.init()
    files = [
        (
            "src/task/sync/process_sync_rs_task.cpp",
            "Processes role server position synchronization and broadcasts sync data.",
            "process_sync_position, sync_role_position",
            "movement, position, sync",
        ),
        (
            "src/battle_calculate/battle_calculate.cpp",
            "Calculates battle damage and hp changes.",
            "update_damage_me_data, update_obj_hp",
            "battle, combat, damage, hp",
        ),
        (
            "src/rtb_proc/character/rtb_proc_character_horse.cpp",
            "Handles mount state transitions and mounted speed sync.",
            "mount_up, dismount, sync_mount_position",
            "mount, horse, speed, sync",
        ),
        (
            "src/rtb_proc/character/rtb_proc_character_persist_attack.cpp",
            "Handles persistent attack checks and generic battle state.",
            "persist_attack, attack_state",
            "battle, attack, skill",
        ),
    ]
    for path, summary, key_points, dependencies in files:
        repo.upsert_file(ProjectFile(path, f"/tmp/{path}", "source", "cpp", 10, 1.0, f"hash-{path}"))
        repo.upsert_summary(
            FileSummary(
                path=path,
                summary=summary,
                responsibilities=summary,
                key_points=key_points,
                dependencies=dependencies,
                risks="verify implementation",
                evidence="symbol scan; side effects: state_write,network_send",
                inconsistencies="none",
                confidence="medium",
            )
        )
```

- [ ] **Step 4: Add CLI JSON multi-topic contract test**

Add this test after `test_assistant_cli_json_outputs_machine_contract()`:

```python
def test_assistant_cli_json_keeps_contract_for_multi_topic_english_answer(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    _seed_multi_topic_repo(db_path)

    result = _run_cli(
        "--question",
        "移动位置同步、战斗伤害、坐骑逻辑分别在哪里？",
        "--db",
        str(db_path),
        "--project-root",
        "/tmp/project",
        "--thread-id",
        "cli-multi-topic-test",
        "--output",
        "json",
    )

    assert result.returncode == 0
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert set(payload) == {
        "answer",
        "request_type",
        "related_paths",
        "approval_required",
        "open_questions",
        "suggested_commands",
        "research_note_id",
        "thread_id",
        "flow_version",
    }
    assert "topic_groups" not in payload
    assert payload["request_type"] == "project_qa"
    assert payload["thread_id"] == "cli-multi-topic-test"
    assert "Movement / position sync" in payload["answer"]
    assert "Combat damage" in payload["answer"]
    assert "Mount logic" in payload["answer"]
    assert any("sync" in path for path in payload["related_paths"])
    assert any("battle" in path or "damage" in path for path in payload["related_paths"])
    assert any("horse" in path or "mount" in path for path in payload["related_paths"])
    assert "结论" not in payload["answer"]
```

- [ ] **Step 5: Run CLI tests and verify failure**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph venv/bin/python -m pytest tests/test_assistant_cli.py -q
```

Expected: FAIL because current CLI answers still use Chinese labels and no topic sections.

---

### Task 4: Topic Detection and Topic-Aware Retrieval

**Files:**
- Modify: `src/nodes/assistant_nodes.py`
- Test: `tests/test_assistant_graph.py::test_assistant_graph_answers_gameplay_movement_combat_mount_context_in_english_topic_sections`

**Interfaces:**
- Consumes: `hybrid_search_project(db_path, query)` and `search_project_index(db_path, query)`.
- Produces:
  - `_detect_gameplay_topics(question: str) -> list[dict[str, object]]`
  - `_search_project_context(repository: ProjectIndexRepository, query: str) -> list[dict]`
  - `_topic_aware_project_context(repository: ProjectIndexRepository, question: str) -> list[dict]`
  - `retrieve_project_context_node()` returning topic-balanced `retrieved_context` and flat `related_paths`.

- [ ] **Step 1: Add topic definitions near `ASSISTANT_FLOW_VERSION`**

In `src/nodes/assistant_nodes.py`, below `ASSISTANT_FLOW_VERSION`, add:

```python
TOPIC_RESULT_LIMIT = 4

GAMEPLAY_TOPICS = [
    {
        "topic_id": "movement_position_sync",
        "topic_label": "Movement / position sync",
        "query": "movement position sync move 移动 位置 同步",
        "keywords": ("movement", "move", "position", "sync", "移动", "位置", "同步"),
    },
    {
        "topic_id": "combat_damage",
        "topic_label": "Combat damage",
        "query": "combat battle damage hp hit 战斗 伤害 扣血 命中",
        "keywords": ("combat", "battle", "damage", "hp", "hit", "战斗", "伤害", "扣血", "命中"),
    },
    {
        "topic_id": "mount_logic",
        "topic_label": "Mount logic",
        "query": "mount horse ride dismount speed sync 坐骑 上马 下马 速度 同步",
        "keywords": ("mount", "horse", "ride", "dismount", "speed", "坐骑", "上马", "下马", "速度"),
    },
]
```

- [ ] **Step 2: Add topic helper functions above `retrieve_project_context_node()`**

Add:

```python
def _detect_gameplay_topics(question: str) -> list[dict]:
    lowered = question.lower()
    topics: list[dict] = []
    for topic in GAMEPLAY_TOPICS:
        if any(keyword in lowered or keyword in question for keyword in topic["keywords"]):
            topics.append(topic)
    return topics


def _search_project_context(repository: ProjectIndexRepository, query: str) -> list[dict]:
    try:
        return hybrid_search_project(repository.db_path, query)
    except Exception:
        return search_project_index(repository.db_path, query)


def _topic_aware_project_context(repository: ProjectIndexRepository, question: str) -> list[dict]:
    topics = _detect_gameplay_topics(question)
    if len(topics) < 2:
        return _search_project_context(repository, question)

    merged: list[dict] = []
    seen_paths: set[str] = set()
    for topic in topics:
        query = f"{question} {topic['query']}"
        for item in _search_project_context(repository, query)[:TOPIC_RESULT_LIMIT]:
            path = item.get("path")
            if not path or path in seen_paths:
                continue
            enriched = dict(item)
            enriched["topic_id"] = topic["topic_id"]
            enriched["topic_label"] = topic["topic_label"]
            enriched["topic_query"] = topic["query"]
            merged.append(enriched)
            seen_paths.add(path)
    return merged
```

- [ ] **Step 3: Use topic-aware retrieval in `retrieve_project_context_node()`**

Replace the body of `retrieve_project_context_node()` with:

```python
def retrieve_project_context_node(state: AssistantState, repo: ProjectIndexRepository | None = None) -> dict:
    repository = _repo(state, repo)
    question = state.get("question", "")
    results = _topic_aware_project_context(repository, question)
    return {
        "retrieved_context": results,
        "related_paths": [item["path"] for item in results if item.get("path")],
    }
```

- [ ] **Step 4: Run the single multi-topic graph test and verify it still fails for synthesis**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph venv/bin/python -m pytest tests/test_assistant_graph.py::test_assistant_graph_answers_gameplay_movement_combat_mount_context_in_english_topic_sections -q
```

Expected: FAIL, but `related_paths` assertions may now pass. Remaining failures should be English topic-section rendering and old Chinese labels.

---

### Task 5: English Synthesis Helpers

**Files:**
- Modify: `src/nodes/assistant_nodes.py`
- Test: `tests/test_assistant_graph.py`

**Interfaces:**
- Consumes: existing retrieved context dicts with optional `topic_label` metadata.
- Produces English helper outputs:
  - `_request_type_label(request_type: str) -> str`
  - `_context_summary_for_user(results: list[dict]) -> list[str]`
  - `_suggested_command_label(command: str) -> str`
  - `_open_question_label(question: str) -> str`
  - `_memory_summary_for_user(memory: list[dict]) -> list[str]`
  - `_project_memory_summary_for_user(memories: list[dict]) -> list[str]`

- [ ] **Step 1: Replace request type labels with English**

Replace `_request_type_label()` with:

```python
def _request_type_label(request_type: str) -> str:
    labels = {
        "project_qa": "Project Q&A",
        "requirement_research": "Requirement research",
        "development_advice": "Development advice",
        "index_request": "Index refresh",
        "unclear": "Unclear request",
    }
    return labels.get(request_type, request_type)
```

- [ ] **Step 2: Replace context summary rendering with English**

Replace `_context_summary_for_user()` with:

```python
def _context_summary_for_user(results: list[dict]) -> list[str]:
    lines: list[str] = []
    for item in results:
        path = item.get("path")
        if not path:
            continue
        confidence = item.get("confidence") or "low"
        inconsistencies = item.get("inconsistencies") or "none"
        evidence = item.get("evidence") or "indexed summary"
        key_symbols = _key_symbols_for_user(item)
        symbol_text = f" Key symbols: {', '.join(f'`{name}`' for name in key_symbols)}." if key_symbols else ""
        lines.append(
            f"- `{path}`: indexed hit.{symbol_text} Evidence: {evidence}. "
            f"Inconsistencies: {inconsistencies}. Confidence: {confidence}."
        )
    return lines
```

- [ ] **Step 3: Replace suggested command labels with English**

Replace `_suggested_command_label()` with:

```python
def _suggested_command_label(command: str) -> str:
    labels = {
        "Run index_graph to scan the target project.": "Run index_graph to refresh the target project index.",
        "Read the relevant files locally to confirm implementation evidence.": (
            "Read the relevant files locally to confirm implementation evidence."
        ),
        "If a build is needed, ask the user before running company project build commands.": (
            "If a build is needed, ask the user before running target-project build commands."
        ),
    }
    return labels.get(command, command)
```

- [ ] **Step 4: Replace open question labels with English**

Replace `_open_question_label()` with:

```python
def _open_question_label(question: str) -> str:
    labels = {
        "Which business area, file, or requirement do you want to investigate?": (
            "Which business area, file, or requirement should be investigated?"
        ),
        "Should the index_graph be run to refresh the project knowledge base?": (
            "Should index_graph be run to refresh the project knowledge base?"
        ),
    }
    return labels.get(question, question)
```

- [ ] **Step 5: Replace memory summary rendering with English**

Replace `_memory_summary_for_user()` with:

```python
def _memory_summary_for_user(memory: list[dict]) -> list[str]:
    lines: list[str] = []
    for item in memory:
        note_id = item.get("id")
        paths = item.get("related_paths") or []
        summary = item.get("user_answer_summary") or item.get("answer_summary") or "Historical research note."
        lines.append(
            f"- note#{note_id} covered {', '.join(paths) or 'no recorded paths'}: "
            f"{summary} Historical assistant conclusion; current indexed implementation evidence wins."
        )
    return lines
```

Replace `_project_memory_summary_for_user()` with:

```python
def _project_memory_summary_for_user(memories: list[dict]) -> list[str]:
    lines: list[str] = []
    for item in memories:
        memory_id = item.get("id")
        memory_type = item.get("memory_type") or "project_memory"
        paths = item.get("related_paths") or []
        summary = item.get("summary") or "Long-term project memory."
        lines.append(
            f"- memory#{memory_id} ({memory_type}) covers {', '.join(paths) or 'no recorded paths'}: "
            f"{summary} Long-term project memory only; current indexed implementation evidence wins."
        )
    return lines
```

- [ ] **Step 6: Run graph tests and verify remaining failures are answer structure**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph venv/bin/python -m pytest tests/test_assistant_graph.py -q
```

Expected: FAIL until `synthesize_response_node()` is converted to English and topic sections are rendered.

---

### Task 6: English Flat and Topic-Section Answer Synthesis

**Files:**
- Modify: `src/nodes/assistant_nodes.py`
- Test: `tests/test_assistant_graph.py`

**Interfaces:**
- Consumes: `retrieved_context` with optional `topic_label` and the English helper functions from Task 5.
- Produces:
  - `_has_topic_context(results: list[dict]) -> bool`
  - `_group_context_by_topic(results: list[dict]) -> list[tuple[str, list[dict]]]`
  - `_topic_context_summary_for_user(results: list[dict]) -> list[str]`
  - English `synthesize_response_node()` output for empty, flat, development-advice, and topic-aware cases.

- [ ] **Step 1: Add topic grouping helpers above `synthesize_response_node()`**

Add:

```python
def _has_topic_context(results: list[dict]) -> bool:
    return any(item.get("topic_label") for item in results)


def _group_context_by_topic(results: list[dict]) -> list[tuple[str, list[dict]]]:
    grouped: list[tuple[str, list[dict]]] = []
    by_label: dict[str, list[dict]] = {}
    for item in results:
        label = item.get("topic_label") or "Other relevant evidence"
        if label not in by_label:
            by_label[label] = []
            grouped.append((label, by_label[label]))
        by_label[label].append(item)
    return grouped


def _topic_context_summary_for_user(results: list[dict]) -> list[str]:
    lines: list[str] = []
    for label, items in _group_context_by_topic(results):
        lines.extend([label, *_context_summary_for_user(items), ""])
    if lines and lines[-1] == "":
        lines.pop()
    return lines
```

- [ ] **Step 2: Replace the empty-answer block in `synthesize_response_node()`**

Inside `synthesize_response_node()`, replace the `if not related_paths:` block with:

```python
    if not related_paths:
        answer = (
            "Conclusion: The current index does not contain enough information to answer this request.\n\n"
            "Basis: The assistant analysis found an unclear question or no matching indexed project context.\n\n"
            "Risk: Do not invent project structure from an empty result set.\n\n"
            "Next step: Refresh the project index or provide a more specific module, file, or business keyword."
        )
        if suggested_commands:
            answer += "\n\nSuggested verification actions:\n" + "\n".join(
                f"- {_suggested_command_label(command)}" for command in suggested_commands
            )
        if open_questions:
            answer += "\n\nOpen questions:\n" + "\n".join(
                f"- {_open_question_label(question)}" for question in open_questions
            )
        return {"answer": answer}
```

- [ ] **Step 3: Replace the main `answer_lines` construction**

Replace the current Chinese `answer_lines = [...]` block through the confidence line with:

```python
    if _has_topic_context(retrieved_context):
        evidence_lines = _topic_context_summary_for_user(retrieved_context)
        answer_lines = [
            f"Conclusion: This {_request_type_label(request_type)} request spans multiple project topics. "
            f"The most relevant indexed paths are: {', '.join(related_paths)}.",
            "",
            "Current indexed evidence:",
            *evidence_lines,
            "",
            "Risks and verification notes: The C++ project may contain stale comments, misleading names, "
            "and hidden side effects. Verify current source files and call chains before editing.",
            "",
            "Confidence: Use each file's confidence and inconsistency flags. Lower confidence for entries with inconsistency flags.",
        ]
    else:
        answer_lines = [
            f"Conclusion: This is a {_request_type_label(request_type)} request. "
            f"The most relevant indexed paths are: {', '.join(related_paths)}.",
            "",
            "Current indexed evidence:",
            *_context_summary_for_user(retrieved_context),
            "",
            "Risks and verification notes: The C++ project may contain stale comments, misleading names, "
            "and hidden side effects. Verify current source files and call chains before editing.",
            "",
            "Confidence: Use each file's confidence and inconsistency flags. Lower confidence for entries with inconsistency flags.",
        ]
```

- [ ] **Step 4: Replace development advice extension**

Replace the development-advice `answer_lines.extend(...)` block with:

```python
    if request_type == "development_advice":
        answer_lines.extend(
            [
                "",
                "Recommendation: Do not directly modify the target C++ project. First read the relevant files, "
                "confirm actual reads/writes, side effects, thread/frame boundaries, and then propose a patch."
            ]
        )
```

- [ ] **Step 5: Replace workflow approval text and section labels**

Replace the selected workflow block with:

```python
    if selected_workflow:
        approval_text = "approval required" if approval_required else "read-only by default; no approval required"
        answer_lines.extend(
            [
                "",
                f"Suggested workflow: {selected_workflow.get('workflow_name')} ({approval_text}).",
            ]
        )
```

Replace remaining section labels with:

```python
    if retrieved_project_memories:
        answer_lines.extend(["", "Project memories:", *_project_memory_summary_for_user(retrieved_project_memories)])
    if retrieved_memory:
        answer_lines.extend(["", "Prior research memory:", *_memory_summary_for_user(retrieved_memory)])
    if suggested_commands:
        answer_lines.extend(["", "Suggested verification actions:", *[f"- {_suggested_command_label(cmd)}" for cmd in suggested_commands]])
    if open_questions:
        answer_lines.extend(["", "Open questions:", *[f"- {_open_question_label(question)}" for question in open_questions]])
```

- [ ] **Step 6: Run graph tests and fix only direct synthesis issues**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph venv/bin/python -m pytest tests/test_assistant_graph.py -q
```

Expected: PASS for graph tests after this task. If failures remain, adjust only the helper strings or topic merge behavior needed to satisfy the tests. Do not add JSON fields.

---

### Task 7: CLI Test Green Pass

**Files:**
- Modify: `src/nodes/assistant_nodes.py` only if CLI exposes graph behavior failures.
- Test: `tests/test_assistant_cli.py`

**Interfaces:**
- Consumes: graph behavior from Tasks 4-6 and `scripts/ask_project.py` unchanged JSON field allowlist.
- Produces: passing CLI tests proving English output and stable JSON contract.

- [ ] **Step 1: Run CLI tests**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph venv/bin/python -m pytest tests/test_assistant_cli.py -q
```

Expected: PASS. If it fails, inspect assertion output.

- [ ] **Step 2: If JSON field set differs, keep `scripts/ask_project.py` unchanged**

If the new multi-topic test fails because `topic_groups` appears, remove any code that exposed it. `scripts/ask_project.py` should keep:

```python
JSON_FIELDS = (
    "answer",
    "request_type",
    "related_paths",
    "approval_required",
    "open_questions",
    "suggested_commands",
    "research_note_id",
    "thread_id",
    "flow_version",
)
```

- [ ] **Step 3: If answer text is wrong, change synthesis, not CLI wrapper**

Do not add presentation logic to `scripts/ask_project.py`. Keep it a thin wrapper that prints `result.get("answer", "")` or `_json_payload(result, thread_id)`.

- [ ] **Step 4: Run combined assistant/CLI tests**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph venv/bin/python -m pytest tests/test_assistant_graph.py tests/test_assistant_cli.py -q
```

Expected: PASS.

---

### Task 8: Documentation Language Convergence

**Files:**
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `docs/superpowers/guides/agent-workflows.md`
- Test: `tests/test_agent_guides.py` if strings need to be adjusted

**Interfaces:**
- Consumes: approved language policy from `docs/superpowers/specs/2026-07-07-multi-topic-assistant-qa-design.md`.
- Produces: docs that describe English agent-facing output and no longer claim default Chinese answers.

- [ ] **Step 1: Update `AGENTS.md` hard rules**

In `AGENTS.md`, replace:

```markdown
- Final user-facing answers must be Chinese.
- Do not paste English internal analysis into final Chinese answers.
```

with:

```markdown
- Agent-facing answers, CLI output, documentation, tests, and assistant-written summaries should be English by default.
- Use Chinese only when the user explicitly requests Chinese end-user-facing output.
- Do not expose raw internal `analysis` in final answers or CLI JSON output.
```

- [ ] **Step 2: Update `AGENTS.md` CLI wording**

Replace:

```markdown
Use `scripts/ask_project.py` when you need a synthesized Chinese answer:
```

with:

```markdown
Use `scripts/ask_project.py` when you need a synthesized English agent-facing answer:
```

Replace:

```markdown
- `ask_project.py --output text` prints only the final Chinese `answer`.
```

with:

```markdown
- `ask_project.py --output text` prints only the final English agent-facing `answer`.
```

Replace:

```markdown
4. If evidence is weak, stale, or conflicting, say so in Chinese and identify what should be inspected next.
```

with:

```markdown
4. If evidence is weak, stale, or conflicting, say so clearly in English and identify what should be inspected next.
```

- [ ] **Step 3: Update README language statements**

In `README.md`, replace statements equivalent to:

```markdown
Final user-facing `answer` text must be Chinese.
Do not paste English internal analysis into the final Chinese answer.
Text output is only the final Chinese `answer`.
Development-advice questions preserve `approval_required` and include Chinese safety wording in the answer.
Use `ask_project.py` when you want the assistant graph to synthesize a final Chinese answer and record the investigation as a research note.
```

with:

```markdown
Agent-facing `answer` text should be English by default.
Use Chinese only when the user explicitly requests Chinese end-user-facing output.
Do not expose raw internal `analysis` in final answers or CLI JSON output.
Text output is only the final English agent-facing `answer`.
Development-advice questions preserve `approval_required` and include English read-only safety wording in the answer.
Use `ask_project.py` when you want the assistant graph to synthesize a final English agent-facing answer and record the investigation as a research note.
```

- [ ] **Step 4: Update workflow guide language statements**

In `docs/superpowers/guides/agent-workflows.md`, replace Chinese-output instructions with English-output instructions:

```markdown
The final answer should be English and agent-readable. Separate evidence types when relevant:
- Current source evidence
- Indexed summaries
- Historical research memory
- Long-term project memory
```

Replace:

```markdown
The final Chinese answer should distinguish what is confirmed by current source from what is an assistant recommendation.
```

with:

```markdown
The final English answer should distinguish source-confirmed facts from assistant recommendations.
```

Replace:

```markdown
- provide Chinese read-only development advice
```

with:

```markdown
- provide English read-only development advice
```

- [ ] **Step 5: Run guide tests**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph venv/bin/python -m pytest tests/test_agent_guides.py -q
```

Expected: PASS. If it fails because the test expects old strings, update the test to assert the guide still references `scripts/search_project.py`, `scripts/ask_project.py`, `Read`, `read-only`, `project_memories`, and `research_notes`.

---

### Task 9: History Entry and Verification

**Files:**
- Modify: `docs/superpowers/history/2026-07-07-development-history.md`
- Test: full verification commands below

**Interfaces:**
- Consumes: all changed tests, code, and docs.
- Produces: dated history entry and fresh verification evidence.

- [ ] **Step 1: Add history entry before final verification**

Append a new section before the `Search-Only Project Retrieval CLI` section or near the latest 2026-07-07 entries:

```markdown
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
  - `AGENTS.md`
  - `README.md`
  - `docs/superpowers/guides/agent-workflows.md`
  - `docs/superpowers/specs/2026-07-07-multi-topic-assistant-qa-design.md`
  - `docs/superpowers/history/2026-07-07-development-history.md`
- Verification:
  - Pending until final verification commands below are run after the implementation.
- Follow-ups:
  - Consider exposing `topic_groups` in JSON only after the internal topic grouping has proven stable.
  - Extend topic detection beyond movement/combat/mount when real repeated questions justify it.
```

- [ ] **Step 2: Run focused assistant and CLI tests**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph venv/bin/python -m pytest tests/test_assistant_graph.py tests/test_assistant_cli.py -q
```

Expected: PASS.

- [ ] **Step 3: Run guide tests**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph venv/bin/python -m pytest tests/test_agent_guides.py -q
```

Expected: PASS.

- [ ] **Step 4: Run retrieval evaluation**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph venv/bin/python scripts/run_retrieval_eval.py --db checkpoints/project_index.sqlite --cases tests/fixtures/retrieval_eval
```

Expected: `Retrieval eval: 15/15 passed`.

- [ ] **Step 5: Run full test suite**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph venv/bin/python -m pytest tests -q
```

Expected: all tests pass. If the test count changes, update README baseline and history verification output to the fresh count.

- [ ] **Step 6: Smoke test search CLI**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph venv/bin/python scripts/search_project.py --db checkpoints/project_index.sqlite --query "移动位置同步" --limit 8 --output json
```

Expected: JSON output with `result_count` 8 and top paths including movement/sync files such as `src/task/sync/process_sync_rs_task.cpp` or `src/task/tcp/process_cli_role_move_tcp_task.cpp`.

- [ ] **Step 7: Smoke test ask CLI multi-topic JSON**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph venv/bin/python scripts/ask_project.py --db checkpoints/project_index.sqlite --project-root /Users/cltx/projects/escort_server/doll_escort_game_svr --question "移动位置同步、战斗伤害、坐骑逻辑分别在哪里？" --output json
```

Expected: JSON output has the stable field set, no `topic_groups`, English `answer`, and topic sections for `Movement / position sync`, `Combat damage`, and `Mount logic` when indexed evidence exists.

- [ ] **Step 8: Check target project status**

Run:

```bash
git -C /Users/cltx/projects/escort_server/doll_escort_game_svr status --short
```

Expected: report existing status only. Do not change or clean the target C++ project.

- [ ] **Step 9: Replace pending verification text in history**

After commands complete, replace the pending verification bullet in the history entry with actual results, for example:

```markdown
- Verification:
  - Focused assistant and CLI tests passed with `<N> passed`.
  - Agent guide tests passed with `2 passed`.
  - Retrieval evaluation passed with `15/15 passed`.
  - Full test suite passed with `<N> passed`.
  - Search CLI smoke test returned movement/sync ranked paths.
  - Ask CLI multi-topic JSON smoke test returned English topic sections and no `topic_groups` field.
  - Target C++ project status was checked read-only; no target-project mutations were made by this work.
```

Then rerun the affected guide/history test if one exists, and rerun full tests if README baseline changed.

---

## Final Review Checklist

Before final response, verify all items below with fresh command output from this implementation session:

- [ ] Assistant graph tests pass.
- [ ] Assistant CLI tests pass.
- [ ] Agent guide tests pass.
- [ ] Retrieval evaluation passes `15/15`.
- [ ] Full test suite passes.
- [ ] Search CLI smoke test returns ranked movement/sync paths.
- [ ] Ask CLI smoke test returns English topic sections and no `topic_groups` field.
- [ ] Target C++ project status was checked and not mutated.
- [ ] `docs/superpowers/history/2026-07-07-development-history.md` contains actual verification results, not pending text.
- [ ] `AGENTS.md`, `README.md`, and `docs/superpowers/guides/agent-workflows.md` no longer state that default final answers must be Chinese.

## Self-Review Notes

- Spec coverage: The plan covers English output, topic-aware retrieval, topic synthesis, JSON contract preservation, tests, docs, history, retrieval evaluation, full suite, and read-only target-project verification.
- Placeholder scan: No `TBD`, `TODO`, or unspecified implementation steps remain. Each code change step includes concrete code or exact replacement text.
- Type consistency: Helper names and signatures are consistent across tasks: `_detect_gameplay_topics(question: str) -> list[dict]`, `_search_project_context(repository, query) -> list[dict]`, `_topic_aware_project_context(repository, question) -> list[dict]`, `_has_topic_context(results) -> bool`, `_group_context_by_topic(results) -> list[tuple[str, list[dict]]]`, and `_topic_context_summary_for_user(results) -> list[str]`.
