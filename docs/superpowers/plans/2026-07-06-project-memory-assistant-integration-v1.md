# Project Memory Assistant Integration v1 Implementation Plan

> **For agentic workers:** Execute this plan with TDD. Each production behavior change must first have a failing test observed. Keep this repository as the only editable project; do not modify `/Users/cltx/projects/escort_server/doll_escort_game_svr`.

Date: 2026-07-06

## Goal

Wire the existing SQLite-backed `project_memories` layer into the assistant graph as read-only auxiliary context:

```text
retrieve_research_memory
  -> retrieve_project_memories
  -> retrieve_project_context
```

The assistant should include active project memories in English internal `analysis`, and show matched memories in the final Chinese `answer` under a separate `长期项目记忆` section. Current indexed implementation evidence remains higher authority than project memories.

## Scope

### In scope

- Add `retrieved_project_memories` and `project_memory_ids` to `AssistantState`.
- Add `retrieve_project_memories_node()`.
- Add project-memory context to `analyze_request_node()` for project QA, requirement research, and development advice.
- Add a Chinese project-memory section to `synthesize_response_node()` when memories matched.
- Add non-blocking failure behavior for project-memory search.
- Update assistant graph wiring.
- Add assistant graph tests.
- Update README and development history.

### Out of scope

- Do not generate new `project_memories` from assistant answers.
- Do not update project-memory status.
- Do not implement reflection, stale demotion, deduplication, or automatic conflict detection.
- Do not change project-context retrieval ranking.
- Do not replace project-index retrieval with memory retrieval.
- Do not integrate Hermes.
- Do not modify the target C++ project.
- Do not commit unless the user explicitly asks for commits.

## Authority and language rules

Authority order:

```text
current source implementation evidence
  > current index summaries / symbols / consistency flags
  > active project memories
  > historical research notes
  > comments / documentation / names alone
```

Language rules:

- Internal `analysis` must stay English.
- Final user-facing `answer` must stay Chinese.
- Final answer must not leak English phrases such as `Project memory #`, `Long-term project memory only`, or `current implementation evidence wins`.
- Every shown project memory must include the Chinese demotion label: `这是长期项目记忆，仅供参考；当前实现索引证据优先。`

## Files to modify

- `src/state.py`
- `src/nodes/assistant_nodes.py`
- `src/assistant_graph.py`
- `tests/test_assistant_graph.py`
- `README.md`
- `docs/superpowers/history/2026-07-03-development-history.md`

## Task 1: Extend assistant state

**Files:**

- Modify: `src/state.py`
- Modify: `tests/test_assistant_graph.py`

**TDD steps:**

- [ ] Add a focused assistant graph test that seeds one active `ProjectMemory`, invokes the graph, and asserts the result contains `retrieved_project_memories` and `project_memory_ids`.
- [ ] Run the new test and observe failure because the graph does not retrieve project memories yet.
- [ ] Add these fields to `AssistantState`:

```python
retrieved_project_memories: Annotated[list[dict], operator.add]
project_memory_ids: Annotated[list[int], operator.add]
```

- [ ] Keep these fields adjacent to existing memory fields for readability.

Expected intermediate result: test still fails until the retrieval node and graph wiring are added.

## Task 2: Add project memory retrieval node

**Files:**

- Modify: `src/nodes/assistant_nodes.py`
- Modify: `tests/test_assistant_graph.py`

**TDD steps:**

- [ ] Extend the test from Task 1 to seed:

```python
ProjectMemory(
    project_root="/tmp/project",
    memory_type="risk_note",
    subject="Escort route risk",
    summary="Route recalculation may update escort state.",
    related_paths='["src/route.cpp"]',
    confidence="medium",
)
```

- [ ] Assert:

```python
result["retrieved_project_memories"][0]["id"] == memory_id
memory_id in result["project_memory_ids"]
```

- [ ] Run the test and observe failure.
- [ ] Import `search_project_memory` in `src/nodes/assistant_nodes.py`.
- [ ] Add:

```python
def retrieve_project_memories_node(
    state: AssistantState,
    repo: ProjectIndexRepository | None = None,
) -> dict:
    repository = _repo(state, repo)
    try:
        hits = search_project_memory(
            repository.db_path,
            state.get("question", ""),
            project_root=state.get("project_root", ""),
        )
    except Exception:
        hits = []
    return {
        "retrieved_project_memories": hits,
        "project_memory_ids": [int(item["id"]) for item in hits],
    }
```

- [ ] Do not add user-visible error text when project-memory retrieval fails.

Expected intermediate result: direct node tests can pass if added, but graph-level test still fails until graph wiring is added.

## Task 3: Wire assistant graph flow

**Files:**

- Modify: `src/assistant_graph.py`
- Modify: `tests/test_assistant_graph.py`

**TDD steps:**

- [ ] Keep the graph-level seeded-memory test failing before wiring.
- [ ] Import `retrieve_project_memories_node`.
- [ ] Register:

```python
builder.add_node("retrieve_project_memories", lambda state: retrieve_project_memories_node(state, repository))
```

- [ ] Replace the edge:

```python
builder.add_edge("retrieve_research_memory", "retrieve_project_context")
```

with:

```python
builder.add_edge("retrieve_research_memory", "retrieve_project_memories")
builder.add_edge("retrieve_project_memories", "retrieve_project_context")
```

- [ ] Run the focused graph retrieval test and confirm it passes the retrieval-state assertions.

## Task 4: Add English internal project-memory context

**Files:**

- Modify: `src/nodes/assistant_nodes.py`
- Modify: `tests/test_assistant_graph.py`

**TDD steps:**

- [ ] Extend the seeded-memory graph test to assert:

```python
"Project memory #" in result["analysis"]
"Long-term project memory only" in result["analysis"]
```

- [ ] Run the test and observe failure.
- [ ] Add helper:

```python
def _project_memory_context(memories: list[dict]) -> str:
    if not memories:
        return "No long-term project memory matched the request."
    lines = []
    for item in memories:
        lines.append(
            f"Project memory #{item.get('id')} [{item.get('memory_type') or 'unknown'}]: "
            f"{item.get('summary') or ''} Paths={item.get('related_paths') or []}. "
            "Long-term project memory only; current implementation evidence wins."
        )
    return "\n".join(lines)
```

- [ ] In `analyze_request_node()`, compute:

```python
project_memory_context = _project_memory_context(state.get("retrieved_project_memories", []))
```

- [ ] Include this section in both development-advice and project-QA / requirement-research analysis:

```text
Project memories:
...
```

- [ ] Preserve existing prior research memory text and behavior.
- [ ] Do not add project-memory context to the unclear/no-index answer path unless current indexed context exists; v1 should not answer from memory alone.

## Task 5: Add Chinese final answer section

**Files:**

- Modify: `src/nodes/assistant_nodes.py`
- Modify: `tests/test_assistant_graph.py`

**TDD steps:**

- [ ] Extend the seeded-memory graph test to assert:

```python
"长期项目记忆" in result["answer"]
"当前实现索引证据优先" in result["answer"]
"memory#" in result["answer"]
```

- [ ] Add a separate leak test or extend the same test to assert:

```python
"Long-term project memory only" not in result["answer"]
"Project memory #" not in result["answer"]
"current implementation evidence wins" not in result["answer"]
```

- [ ] Run the tests and observe failure.
- [ ] Add helper:

```python
def _project_memory_summary_for_user(memories: list[dict]) -> list[str]:
    lines: list[str] = []
    for item in memories:
        memory_id = item.get("id")
        memory_type = item.get("memory_type") or "project_memory"
        paths = item.get("related_paths") or []
        summary = item.get("summary") or "长期项目记忆。"
        lines.append(
            f"- memory#{memory_id}（{memory_type}）涉及 {', '.join(paths) or '未记录路径'}："
            f"{summary} 这是长期项目记忆，仅供参考；当前实现索引证据优先。"
        )
    return lines
```

- [ ] In `synthesize_response_node()`, read:

```python
retrieved_project_memories = state.get("retrieved_project_memories", [])
```

- [ ] Insert the section after confidence / workflow guidance and before `历史调研记忆`:

```python
if retrieved_project_memories:
    answer_lines.extend(["", "长期项目记忆：", *_project_memory_summary_for_user(retrieved_project_memories)])
```

- [ ] Confirm final answer remains Chinese and does not leak English internal phrases.

## Task 6: Add no-memory and failure tests

**Files:**

- Modify: `tests/test_assistant_graph.py`
- Modify: `src/nodes/assistant_nodes.py` only if a test exposes a defect.

**TDD steps:**

- [ ] Add `test_assistant_graph_omits_project_memory_section_when_no_match`:
  - Seed only current indexed context.
  - Invoke a normal project question.
  - Assert `result["retrieved_project_memories"] == []` or the field is empty after graph execution.
  - Assert `"长期项目记忆" not in result["answer"]`.

- [ ] Add `test_assistant_graph_project_memory_failure_is_non_blocking`:
  - Monkeypatch `src.nodes.assistant_nodes.search_project_memory` to raise `RuntimeError("memory unavailable")`.
  - Invoke the graph with seeded current indexed context.
  - Assert:

```python
result["retrieved_project_memories"] == []
result["project_memory_ids"] == []
"src/route.cpp" in result["answer"]
```

- [ ] Run the two new tests and observe failures before the final production fix if the behavior is not already implemented.
- [ ] Keep exception handling local to project-memory retrieval only; do not broaden unrelated graph failures.

## Task 7: Run focused assistant tests

**Files:**

- No planned production changes.

**Commands:**

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests/test_assistant_graph.py -v
```

Expected: all assistant graph tests pass.

If any existing research-memory assertions fail, preserve the existing `retrieved_memory`, `memory_note_ids`, and `source_note_ids` behavior; project-memory IDs must not replace source research note IDs.

## Task 8: Update README

**Files:**

- Modify: `README.md`

**Required documentation changes:**

- Update Assistant Graph purpose and flow to include `retrieve_project_memories` between research memory and current project context.
- Update Retrieval and Memory section to say assistant answers may show `project_memories` separately from `research_notes`.
- Keep the current-code-evidence priority explicit.
- State that project memories are read-only guidance in assistant v1 and are not automatically generated or promoted from answers.
- After final full-suite verification, update the expected test baseline to the observed final count.

## Task 9: Update development history

**Files:**

- Modify: `docs/superpowers/history/2026-07-03-development-history.md`

Append a new entry titled:

```markdown
### Project Memory Assistant Integration v1
```

Entry must include:

- Change summary: assistant graph now retrieves active project memories as read-only auxiliary context.
- Completed functionality:
  - Added assistant state fields.
  - Added `retrieve_project_memories_node`.
  - Wired the graph between research memory and project context retrieval.
  - Included project memories in English internal analysis.
  - Added Chinese `长期项目记忆` answer section with the required demotion label.
  - Preserved current-index evidence priority.
  - Kept retrieval failure non-blocking.
  - Did not modify the target C++ project.
- Affected files.
- Verification commands and exact observed results.
- Follow-ups:
  - Design memory reflection separately.
  - Design stale-memory demotion separately.
  - Add conflict/staleness detection only with explicit tests.

## Task 10: Final verification

**Commands:**

Run focused assistant tests:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests/test_assistant_graph.py -v
```

Run storage and retriever tests to ensure the existing project-memory layer still works:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests/test_storage.py /Users/cltx/projects/langgraph/tests/test_retriever.py -v
```

Run full suite:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests -v
```

Check target C++ project status without modifying it:

```bash
git -C /Users/cltx/projects/escort_server/doll_escort_game_svr status --short
```

Expected final state:

- Focused tests pass.
- Full suite passes.
- README expected baseline matches the observed full-suite count.
- Development history records exact verification results.
- Target C++ project was not modified by this work.

## Self-review checklist

- [ ] The plan implements `docs/superpowers/specs/2026-07-06-project-memory-assistant-integration-v1-design.md`.
- [ ] The plan does not add automatic project-memory generation.
- [ ] The plan does not add stale-memory or conflict detection.
- [ ] The plan preserves research-memory persistence behavior.
- [ ] The plan keeps final answers Chinese-only.
- [ ] The plan keeps internal analysis English-only.
- [ ] The plan does not ask workers to mutate the target C++ project.
- [ ] The plan does not require commits unless the user explicitly asks.
