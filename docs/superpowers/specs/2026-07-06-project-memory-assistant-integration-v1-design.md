# Project Memory Assistant Integration v1 Design

Date: 2026-07-06

## Purpose

This design defines the first assistant-graph integration for the self-developed project memory layer.

Project Memory Layer v1 already provides durable `project_memories`, repository APIs, and `search_project_memory()`. This integration adds read-only assistant retrieval and answer presentation for those memories while preserving the core authority rule: current indexed implementation evidence wins over project memories and historical research notes.

## Goals

- Add project memory retrieval to the assistant graph.
- Include active project memories in internal English analysis.
- Show project memories in the final Chinese answer under a separate section.
- Label project memories as long-term guidance, not source-of-truth evidence.
- Preserve the current-code-evidence authority rule.
- Keep project memory retrieval non-blocking.
- Keep the integration read-only.

## Non-Goals

- Do not generate new `project_memories` from assistant answers.
- Do not update project memory status.
- Do not implement memory reflection.
- Do not implement stale-memory demotion.
- Do not implement automatic conflict detection between project memories and current index evidence.
- Do not change retrieval ranking for project files.
- Do not replace project-index retrieval with memory retrieval.
- Do not alter `research_notes` persistence behavior except for carrying existing source note IDs as before.
- Do not integrate Hermes.
- Do not modify the target C++ project.

## Current Assistant Graph

The current assistant graph is linear:

```text
ensure_flow_version
  -> classify_request
  -> select_workflow
  -> retrieve_research_memory
  -> retrieve_project_context
  -> analyze_request
  -> synthesize_response
  -> persist_research_note
```

It already retrieves:

- historical research notes through `retrieve_research_memory_node`
- current indexed project context through `retrieve_project_context_node`

It does not yet retrieve `project_memories`.

## Proposed Graph Flow

Add a new read-only project memory retrieval node after research memory and before current project context:

```text
ensure_flow_version
  -> classify_request
  -> select_workflow
  -> retrieve_research_memory
  -> retrieve_project_memories
  -> retrieve_project_context
  -> analyze_request
  -> synthesize_response
  -> persist_research_note
```

Rationale:

- `research_notes` are historical interaction records.
- `project_memories` are curated long-term guidance.
- `retrieved_context` remains current indexed implementation evidence.

The authority order remains:

```text
current source implementation evidence
  > current index summaries / symbols / consistency flags
  > active project memories
  > historical research notes
  > comments / documentation / names alone
```

## State Changes

Extend `AssistantState` in `src/state.py` with:

```python
retrieved_project_memories: Annotated[list[dict], operator.add]
project_memory_ids: Annotated[list[int], operator.add]
```

These fields mirror the existing research memory fields:

```python
retrieved_memory: Annotated[list[dict], operator.add]
memory_note_ids: Annotated[list[int], operator.add]
```

`retrieved_project_memories` stores serializable hits from `search_project_memory()`.

`project_memory_ids` stores the hit IDs for traceability and future source linking.

## New Node

Add a node in `src/nodes/assistant_nodes.py`:

```python
def retrieve_project_memories_node(
    state: AssistantState,
    repo: ProjectIndexRepository | None = None,
) -> dict:
    ...
```

Behavior:

```python
repository = _repo(state, repo)
hits = search_project_memory(
    repository.db_path,
    state.get("question", ""),
    project_root=state.get("project_root", ""),
)
return {
    "retrieved_project_memories": hits,
    "project_memory_ids": [int(item["id"]) for item in hits],
}
```

Project memory retrieval is auxiliary. If search fails, the node should not block the assistant answer. It should return:

```python
{
    "retrieved_project_memories": [],
    "project_memory_ids": [],
}
```

This mirrors the product rule that project memory is helpful context, not a mandatory source of truth.

## Internal Analysis Integration

Add helper:

```python
def _project_memory_context(memories: list[dict]) -> str:
    ...
```

If no memories match:

```text
No long-term project memory matched the request.
```

For each memory:

```text
Project memory #<id> [<memory_type>]: <summary> Paths=<related_paths>. Long-term project memory only; current implementation evidence wins.
```

Update `analyze_request_node()` to include:

```python
project_memory_context = _project_memory_context(state.get("retrieved_project_memories", []))
```

Both development-advice and project-QA / requirement-research analysis should include:

```text
Project memories:
<project_memory_context>
```

Keep internal analysis in English.

## Final Chinese Answer Integration

Add helper:

```python
def _project_memory_summary_for_user(memories: list[dict]) -> list[str]:
    ...
```

Each item should render as Chinese text:

```text
- memory#<id>（<memory_type>）涉及 <paths>：<summary> 这是长期项目记忆，仅供参考；当前实现索引证据优先。
```

If `related_paths` is empty, use:

```text
未记录路径
```

If `summary` is empty, use:

```text
长期项目记忆。
```

Update `synthesize_response_node()` to add a separate section when project memories exist:

```text
长期项目记忆：
- memory#...
```

This section should appear after the indexed evidence / risk / confidence sections and before historical research memory.

Recommended order:

```text
结论
依据：current indexed context
风险/不确定性
置信度
长期项目记忆
历史调研记忆
建议验证命令/动作
待确认问题
```

The final answer must not leak English internal analysis phrases such as:

```text
Project memory #
Long-term project memory only
current implementation evidence wins
```

Use Chinese wording only in the final answer.

## Conflict Strategy

Version 1 uses a uniform demotion label.

Do not attempt automatic conflict detection.

Do not compare memory summaries against current context.

Do not mark memories stale based on path mismatch.

Every project memory shown to the user must include:

```text
这是长期项目记忆，仅供参考；当前实现索引证据优先。
```

Every project memory included in internal analysis must include:

```text
Long-term project memory only; current implementation evidence wins.
```

## Error Handling

Project memory search is non-blocking.

If `search_project_memory()` raises, `retrieve_project_memories_node()` should return empty memory fields and allow `retrieve_project_context_node` and later nodes to continue.

Do not add broad error text to the final answer for project memory search failure in v1. The absence of project memory is acceptable because current indexed project context remains the primary source.

## Testing Requirements

Add assistant graph tests in `tests/test_assistant_graph.py`.

### Test 1: assistant retrieves and displays project memories

Seed:

- current index context for `src/route.cpp`
- one active project memory with:
  - `memory_type="risk_note"`
  - `subject="Escort route risk"`
  - `summary="Route recalculation may update escort state."`
  - `related_paths='["src/route.cpp"]'`
  - `confidence="medium"`

Invoke assistant with a matching route-risk question.

Assert:

```python
result["retrieved_project_memories"][0]["id"] == memory_id
memory_id in result["project_memory_ids"]
"Project memory #" in result["analysis"]
"Long-term project memory only" in result["analysis"]
"长期项目记忆" in result["answer"]
"当前实现索引证据优先" in result["answer"]
"memory#" in result["answer"]
```

### Test 2: final answer does not leak English project-memory analysis

Assert in the same or a separate test:

```python
"Long-term project memory only" not in result["answer"]
"Project memory #" not in result["answer"]
```

### Test 3: no project memory omits section

Invoke assistant without seeded project memory.

Assert:

```python
"长期项目记忆" not in result["answer"]
```

### Test 4: project memory retrieval failure is non-blocking

Monkeypatch `src.nodes.assistant_nodes.search_project_memory` to raise `RuntimeError("memory unavailable")`.

Assert:

```python
result["retrieved_project_memories"] == []
result["project_memory_ids"] == []
"src/route.cpp" in result["answer"]
```

## Files to Modify

- `src/state.py`
  - Add `retrieved_project_memories` and `project_memory_ids` fields.

- `src/nodes/assistant_nodes.py`
  - Import `search_project_memory`.
  - Add `retrieve_project_memories_node`.
  - Add `_project_memory_context`.
  - Add `_project_memory_summary_for_user`.
  - Include project memory context in `analyze_request_node()`.
  - Include project memory section in `synthesize_response_node()`.

- `src/assistant_graph.py`
  - Import `retrieve_project_memories_node`.
  - Register node.
  - Add edge between `retrieve_research_memory` and `retrieve_project_memories`.
  - Add edge from `retrieve_project_memories` to `retrieve_project_context`.

- `tests/test_assistant_graph.py`
  - Add tests described above.
  - Import `ProjectMemory` if not already imported.

- `README.md`
  - Document that assistant answers can show project memories separately from historical research memory.
  - Keep current-code-evidence priority explicit.
  - Update full-suite baseline if the count changes.

- `docs/superpowers/history/2026-07-03-development-history.md`
  - Append a dated implementation entry after implementation.

## Safety Requirements

This work must not modify the target C++ project:

```text
/Users/cltx/projects/escort_server/doll_escort_game_svr
```

It may only modify the LangGraph assistant repository.

No edit, build, commit, push, clean, delete, dependency change, or external publish action may be run against the target C++ project without explicit user approval.

## Success Criteria

The integration is complete when:

- Assistant state includes project memory fields.
- Assistant graph retrieves active project memories.
- Assistant analysis includes English project memory context.
- Final Chinese answer includes a separate `长期项目记忆` section when memories match.
- Final Chinese answer does not leak English internal analysis.
- Project memory retrieval failure does not block answers from current indexed context.
- Answers always label project memories as long-term guidance and say current implementation index evidence wins.
- Existing research memory behavior still works.
- Full test suite passes.
- README and development history are updated.
