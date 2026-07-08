import json
import re

from src.config import settings
from src.indexer.models import ResearchNote
from src.retriever.context_builder import build_context
from src.retriever.hybrid_search import hybrid_search_project
from src.retriever.keyword_search import search_project_index
from src.retriever.project_memory import search_project_memory
from src.retriever.research_memory import search_research_memory
from src.state import AssistantState
from src.storage.project_index import ProjectIndexRepository
from src.workflows.registry import select_workflow


ASSISTANT_FLOW_VERSION = "2026-07-02.foundation-v1"

TOPIC_RESULT_LIMIT = 4

GAMEPLAY_TOPICS = [
    {
        "topic_id": "movement_position_sync",
        "topic_label": "Movement / position sync",
        "query": "movement position sync move 移动 位置 同步",
        "keywords": ("movement", "move", "position", "sync", "移动", "位置", "同步"),
        "context_keywords": (),
    },
    {
        "topic_id": "combat_damage",
        "topic_label": "Combat damage",
        "query": "combat battle damage hp hit 战斗 伤害 扣血 命中",
        "keywords": ("combat", "battle", "damage", "hp", "hit", "战斗", "伤害", "扣血", "命中"),
        "context_keywords": (),
    },
    {
        "topic_id": "mount_logic",
        "topic_label": "Mount logic",
        "query": "mount horse ride dismount speed sync 坐骑 上马 下马 速度 同步",
        "keywords": ("mount", "horse", "ride", "dismount", "坐骑", "上马", "下马"),
        "context_keywords": ("speed", "速度", "sync", "同步"),
    },
]


def _repo(state: AssistantState, default_repo: ProjectIndexRepository | None = None) -> ProjectIndexRepository:
    if default_repo is not None:
        return default_repo
    return ProjectIndexRepository(state.get("index_db_path") or settings.PROJECT_INDEX_DB)


def ensure_flow_version_node(state: AssistantState) -> dict:
    return {"flow_version": state.get("flow_version") or ASSISTANT_FLOW_VERSION}


def classify_request_node(state: AssistantState) -> dict:
    question = state.get("question", "")
    lowered = question.lower()
    if any(word in question for word in ["修改", "开发", "实现", "加一个", "影响哪些文件", "怎么改"]):
        request_type = "development_advice"
    elif any(word in question for word in ["调研", "影响范围", "风险", "方案"]):
        request_type = "requirement_research"
    elif any(word in lowered for word in ["index", "索引", "刷新"]):
        request_type = "index_request"
    elif question.strip():
        request_type = "project_qa"
    else:
        request_type = "unclear"
    return {"request_type": request_type}


def select_workflow_node(state: AssistantState) -> dict:
    workflow = select_workflow(state.get("question", ""), state.get("request_type", "unclear"))
    return {
        "selected_workflow": workflow,
        "workflow_steps": workflow.get("workflow_steps", []),
        "approval_required": bool(workflow.get("approval_required")),
    }


def retrieve_research_memory_node(state: AssistantState, repo: ProjectIndexRepository | None = None) -> dict:
    repository = _repo(state, repo)
    hits = search_research_memory(
        repository.db_path,
        state.get("question", ""),
        project_root=state.get("project_root", ""),
    )
    return {
        "retrieved_memory": hits,
        "memory_note_ids": [int(item["id"]) for item in hits],
        "source_note_ids": [int(item["id"]) for item in hits],
    }


def retrieve_project_memories_node(state: AssistantState, repo: ProjectIndexRepository | None = None) -> dict:
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


def _question_has_topic_keyword(question: str, keyword: str) -> bool:
    if re.fullmatch(r"[A-Za-z0-9_]+", keyword):
        return keyword.lower() in {token.lower() for token in re.findall(r"[A-Za-z0-9_]+", question)}
    return keyword in question.lower()


def _detect_gameplay_topics(question: str) -> list[dict]:
    topics: list[dict] = []
    for topic in GAMEPLAY_TOPICS:
        if any(_question_has_topic_keyword(question, keyword) for keyword in topic["keywords"]):
            topics.append(topic)
    return topics


def _topic_search_query(question: str, topic: dict) -> str:
    return f"{topic['query']} {question}".strip()


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
        topic_query = _topic_search_query(question, topic)
        for item in _search_project_context(repository, topic_query)[:TOPIC_RESULT_LIMIT]:
            path = item.get("path")
            if not path:
                continue
            enriched = dict(item)
            enriched["topic_id"] = topic["topic_id"]
            enriched["topic_label"] = topic["topic_label"]
            enriched["topic_query"] = topic_query
            if path in seen_paths:
                enriched["topic_duplicate"] = True
            else:
                seen_paths.add(path)
            merged.append(enriched)
    return merged


def _unique_paths(results: list[dict]) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for item in results:
        path = item.get("path")
        if not path or path in seen:
            continue
        paths.append(path)
        seen.add(path)
    return paths


def retrieve_project_context_node(state: AssistantState, repo: ProjectIndexRepository | None = None) -> dict:
    repository = _repo(state, repo)
    question = state.get("question", "")
    results = _topic_aware_project_context(repository, question)
    return {
        "retrieved_context": results,
        "related_paths": _unique_paths(results),
    }


def _memory_context(memory: list[dict]) -> str:
    if not memory:
        return "No prior research memory matched the request."
    lines = []
    for item in memory:
        lines.append(
            f"Research note #{item.get('id')}: {item.get('internal_memory_summary') or item.get('answer_summary') or ''} "
            f"Paths={item.get('related_paths') or []}. Historical assistant memory only; current implementation evidence wins."
        )
    return "\n".join(lines)


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


def analyze_request_node(state: AssistantState) -> dict:
    request_type = state.get("request_type", "unclear")
    context = build_context(state.get("retrieved_context", []))
    memory_context = _memory_context(state.get("retrieved_memory", []))
    project_memory_context = _project_memory_context(state.get("retrieved_project_memories", []))

    if request_type == "unclear":
        return {
            "analysis": "The user question is empty or unclear; ask for the module, requirement, or file scope.",
            "open_questions": ["Which business area, file, or requirement do you want to investigate?"],
        }

    if context.startswith("No indexed project context"):
        return {
            "analysis": "The project index did not return enough context; refresh the project index before answering.",
            "open_questions": ["Should the index_graph be run to refresh the project knowledge base?"],
            "suggested_commands": ["Run index_graph to scan the target project."],
        }

    if request_type == "development_advice":
        analysis = (
            "This is a development-advice request. Use the indexed context to identify impact scope, risks, "
            "recommended change order, and verification actions. Do not directly modify the company C++ project "
            "in the initial assistant flow.\n\n"
            f"{context}\n\nProject memories:\n{project_memory_context}\n\nPrior research memory:\n{memory_context}"
        )
        return {
            "analysis": analysis,
            "suggested_commands": [
                "Read the relevant files locally to confirm implementation evidence.",
                "If a build is needed, ask the user before running company project build commands.",
            ],
        }

    analysis = (
        "This is a project question or requirement research request. Distinguish implementation evidence from "
        "naming, comments, and documentation clues. Highlight any inconsistency flags explicitly.\n\n"
        f"{context}\n\nProject memories:\n{project_memory_context}\n\nPrior research memory:\n{memory_context}"
    )
    return {"analysis": analysis}


def _request_type_label(request_type: str) -> str:
    labels = {
        "project_qa": "Project Q&A",
        "requirement_research": "Requirement research",
        "development_advice": "Development advice",
        "index_request": "Index refresh",
        "unclear": "Unclear request",
    }
    return labels.get(request_type, request_type)


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


def _key_symbols_for_user(item: dict, limit: int = 6) -> list[str]:
    ignored = {"", "if", "for", "while", "switch", "return"}
    symbols: list[str] = []
    seen: set[str] = set()

    def add_symbol(raw_name: object) -> None:
        name = str(raw_name or "").strip()
        if not name or name.lower() in ignored or name in seen:
            return
        seen.add(name)
        symbols.append(name)

    for symbol in item.get("matched_symbols") or []:
        add_symbol(symbol.get("name"))
        if len(symbols) >= limit:
            return symbols

    key_points = str(item.get("key_points") or "")
    for part in key_points.replace("\n", ",").replace(";", ",").split(","):
        add_symbol(part)
        if len(symbols) >= limit:
            break

    return symbols


def _has_topic_context(results: list[dict]) -> bool:
    return any(item.get("topic_label") for item in results)


def _group_context_by_topic(results: list[dict]) -> list[tuple[str, list[dict]]]:
    grouped: list[tuple[str, list[dict]]] = []
    by_label: dict[str, list[dict]] = {}
    seen_paths_by_label: dict[str, set[str]] = {}
    for item in results:
        path = item.get("path")
        label = item.get("topic_label") or "Other relevant evidence"
        if label not in by_label:
            by_label[label] = []
            seen_paths_by_label[label] = set()
            grouped.append((label, by_label[label]))
        if path:
            if path in seen_paths_by_label[label]:
                continue
            seen_paths_by_label[label].add(path)
        by_label[label].append(item)
    return grouped


def _topic_context_summary_for_user(results: list[dict]) -> list[str]:
    lines: list[str] = []
    for label, items in _group_context_by_topic(results):
        lines.extend([label, *_context_summary_for_user(items), ""])
    if lines and lines[-1] == "":
        lines.pop()
    return lines


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


def _project_memory_summary_for_user(memories: list[dict]) -> list[str]:
    lines: list[str] = []
    for item in memories:
        memory_id = item.get("id")
        memory_type = item.get("memory_type") or "project_memory"
        paths = item.get("related_paths") or []
        summary = item.get("summary") or "Long-term project memory."
        lines.append(
            f"- memory#{memory_id} ({memory_type}) covers {', '.join(paths) or 'no recorded paths'}: "
            f"{summary} current indexed implementation evidence wins."
        )
    return lines


def synthesize_response_node(state: AssistantState) -> dict:
    request_type = state.get("request_type", "unclear")
    related_paths = state.get("related_paths", [])
    retrieved_context = state.get("retrieved_context", [])
    retrieved_memory = state.get("retrieved_memory", [])
    retrieved_project_memories = state.get("retrieved_project_memories", [])
    open_questions = state.get("open_questions", [])
    suggested_commands = state.get("suggested_commands", [])
    selected_workflow = state.get("selected_workflow", {})
    approval_required = state.get("approval_required", False)

    if not related_paths:
        answer = (
            "Conclusion: The current index does not contain enough information to answer this request.\n\n"
            "Basis: The question was unclear or the current SQLite project index did not return matching project context.\n\n"
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
            f"Request type: {_request_type_label(request_type)}",
            "",
            "Current indexed evidence:",
            *_context_summary_for_user(retrieved_context),
            "",
            "Risks and verification notes: The C++ project may contain stale comments, misleading names, "
            "and hidden side effects. Verify current source files and call chains before editing.",
            "",
            "Confidence: Use each file's confidence and inconsistency flags. Lower confidence for entries with inconsistency flags.",
        ]
    if request_type == "development_advice":
        answer_lines.extend(
            [
                "",
                "Recommendation: Do not directly modify the target C++ project. First read the relevant files, "
                "confirm actual reads/writes, side effects, thread/frame boundaries, and then propose a patch."
            ]
        )
    if selected_workflow:
        approval_text = "approval required" if approval_required else "read-only by default; no approval required"
        answer_lines.extend(
            [
                "",
                f"Suggested workflow: {selected_workflow.get('workflow_name')} ({approval_text}).",
            ]
        )
    if retrieved_project_memories:
        answer_lines.extend(["", "Project memories:", *_project_memory_summary_for_user(retrieved_project_memories)])
    if retrieved_memory:
        answer_lines.extend(["", "Prior research memory:", *_memory_summary_for_user(retrieved_memory)])
    if suggested_commands:
        answer_lines.extend(["", "Suggested verification actions:", *[f"- {_suggested_command_label(cmd)}" for cmd in suggested_commands]])
    if open_questions:
        answer_lines.extend(["", "Open questions:", *[f"- {_open_question_label(question)}" for question in open_questions]])

    return {"answer": "\n".join(answer_lines)}


def persist_research_note_node(state: AssistantState, repo: ProjectIndexRepository | None = None) -> dict:
    if state.get("request_type") in {"unclear", "index_request"}:
        return {"research_note_id": None}
    answer = state.get("answer", "")
    if not answer:
        return {"research_note_id": None}
    repository = _repo(state, repo)
    note_id = repository.insert_research_note(
        ResearchNote(
            thread_id=state.get("thread_id") or "default",
            request_type=state.get("request_type", "project_qa"),
            question=state.get("question", ""),
            answer_summary=answer[:1000],
            related_paths=json.dumps(state.get("related_paths", []), ensure_ascii=False),
            open_questions=json.dumps(state.get("open_questions", []), ensure_ascii=False),
            project_root=state.get("project_root", ""),
            source_note_ids=json.dumps(state.get("source_note_ids", []), ensure_ascii=False),
            internal_memory_summary=state.get("analysis", "")[:1000],
            user_answer_summary=answer[:1000],
            confidence="medium" if state.get("related_paths") else "low",
        )
    )
    return {"research_note_id": note_id}
