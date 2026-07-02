import json

from src.config import settings
from src.indexer.models import ResearchNote
from src.retriever.context_builder import build_context
from src.retriever.keyword_search import search_project_index
from src.state import AssistantState
from src.storage.project_index import ProjectIndexRepository


def _repo(state: AssistantState, default_repo: ProjectIndexRepository | None = None) -> ProjectIndexRepository:
    if default_repo is not None:
        return default_repo
    return ProjectIndexRepository(state.get("index_db_path") or settings.PROJECT_INDEX_DB)


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


def retrieve_project_context_node(state: AssistantState, repo: ProjectIndexRepository | None = None) -> dict:
    repository = _repo(state, repo)
    results = search_project_index(repository.db_path, state.get("question", ""))
    return {
        "retrieved_context": results,
        "related_paths": [item["path"] for item in results],
    }


def analyze_request_node(state: AssistantState) -> dict:
    request_type = state.get("request_type", "unclear")
    context = build_context(state.get("retrieved_context", []))

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
            f"{context}"
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
        f"{context}"
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
        lines.append(f"- `{path}`：索引命中；证据={evidence}；不一致标记={inconsistencies}；confidence={confidence}。")
    return lines


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


def synthesize_response_node(state: AssistantState) -> dict:
    request_type = state.get("request_type", "unclear")
    related_paths = state.get("related_paths", [])
    retrieved_context = state.get("retrieved_context", [])
    open_questions = state.get("open_questions", [])
    suggested_commands = state.get("suggested_commands", [])

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
        )
    )
    return {"research_note_id": note_id}
