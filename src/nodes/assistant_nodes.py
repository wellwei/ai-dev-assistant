import json

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


def retrieve_project_context_node(state: AssistantState, repo: ProjectIndexRepository | None = None) -> dict:
    repository = _repo(state, repo)
    question = state.get("question", "")
    try:
        results = hybrid_search_project(repository.db_path, question)
    except Exception:
        results = search_project_index(repository.db_path, question)
    return {
        "retrieved_context": results,
        "related_paths": [item["path"] for item in results],
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
        "project_qa": "项目问答",
        "requirement_research": "需求调研",
        "development_advice": "开发建议",
        "index_request": "索引刷新",
        "unclear": "信息不明确",
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
        symbol_text = f"；关键函数/符号={', '.join(f'`{name}`' for name in key_symbols)}" if key_symbols else ""
        lines.append(
            f"- `{path}`：索引命中{symbol_text}；证据={evidence}；不一致标记={inconsistencies}；confidence={confidence}。"
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


def _suggested_command_label(command: str) -> str:
    labels = {
        "Run index_graph to scan the target project.": "运行 index_graph 扫描目标项目。",
        "Read the relevant files locally to confirm implementation evidence.": "先局部阅读相关文件，确认实际实现证据。",
        "If a build is needed, ask the user before running company project build commands.": (
            "如需构建，先征得用户确认，再运行公司项目构建命令。"
        ),
    }
    return labels.get(command, command)


def _open_question_label(question: str) -> str:
    labels = {
        "Which business area, file, or requirement do you want to investigate?": (
            "请说明你想了解的业务点、文件或需求背景。"
        ),
        "Should the index_graph be run to refresh the project knowledge base?": (
            "是否先运行 index_graph 刷新项目知识库？"
        ),
    }
    return labels.get(question, question)


def _memory_summary_for_user(memory: list[dict]) -> list[str]:
    lines: list[str] = []
    for item in memory:
        note_id = item.get("id")
        paths = item.get("related_paths") or []
        summary = item.get("user_answer_summary") or item.get("answer_summary") or "历史调研记录。"
        lines.append(f"- note#{note_id} 曾涉及 {', '.join(paths) or '未记录路径'}：{summary} 这是历史助手结论，当前实现证据优先。")
    return lines


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
            "结论：当前索引中没有找到足够信息。\n\n"
            "依据：助手内部分析认为问题不清楚，或当前 SQLite 项目索引没有匹配到足够上下文。\n\n"
            "风险/不确定性：不能根据空索引编造项目结构。\n\n"
            "下一步建议：先刷新项目索引，或提供更具体的模块、文件、业务关键词。"
        )
        if suggested_commands:
            answer += "\n\n建议验证命令/动作：\n" + "\n".join(
                f"- {_suggested_command_label(command)}" for command in suggested_commands
            )
        if open_questions:
            answer += "\n\n待确认问题：\n" + "\n".join(
                f"- {_open_question_label(question)}" for question in open_questions
            )
        return {"answer": answer}

    answer_lines = [
        f"结论：这是{_request_type_label(request_type)}请求，相关信息主要集中在以下文件：{', '.join(related_paths)}。",
        "",
        "依据：以下结论来自 SQLite 项目索引中的实现摘要、符号扫描、副作用线索和一致性标记。",
        *_context_summary_for_user(retrieved_context),
        "",
        "风险/不确定性：老 C++ 项目中注释、文档、函数名和字段名可能过时或误导；以上判断不能只按命名理解，改动前必须核对实际实现和调用链。",
        "",
        "置信度：以各文件摘要中的 confidence 为准；包含 inconsistency flags 的位置应降低信任并人工核对。",
    ]
    if request_type == "development_advice":
        answer_lines.extend(
            [
                "",
                "建议：不要直接修改公司 C++ 项目。先局部阅读相关文件，确认实际读写、副作用、线程/帧边界，再提出补丁。",
            ]
        )
    if selected_workflow:
        approval_text = "需要审批" if approval_required else "默认只读，无需审批"
        answer_lines.extend(
            [
                "",
                f"建议工作流：{selected_workflow.get('workflow_name')}（{approval_text}）。",
            ]
        )
    if retrieved_project_memories:
        answer_lines.extend(["", "长期项目记忆：", *_project_memory_summary_for_user(retrieved_project_memories)])
    if retrieved_memory:
        answer_lines.extend(["", "历史调研记忆：", *_memory_summary_for_user(retrieved_memory)])
    if suggested_commands:
        answer_lines.extend(["", "建议验证命令/动作：", *[f"- {_suggested_command_label(cmd)}" for cmd in suggested_commands]])
    if open_questions:
        answer_lines.extend(["", "待确认问题：", *[f"- {_open_question_label(question)}" for question in open_questions]])

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
