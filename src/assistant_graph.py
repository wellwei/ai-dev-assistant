from langgraph.graph import END, START, StateGraph

from src.nodes.assistant_nodes import (
    analyze_request_node,
    classify_request_node,
    ensure_flow_version_node,
    persist_research_note_node,
    retrieve_project_context_node,
    retrieve_research_memory_node,
    select_workflow_node,
    synthesize_response_node,
)
from src.state import AssistantState
from src.storage.project_index import ProjectIndexRepository


def create_assistant_graph(repo: ProjectIndexRepository | None = None, checkpointer=None):
    repository = repo if isinstance(repo, ProjectIndexRepository) else None
    builder = StateGraph(AssistantState)

    builder.add_node("ensure_flow_version", ensure_flow_version_node)
    builder.add_node("classify_request", classify_request_node)
    builder.add_node("select_workflow", select_workflow_node)
    builder.add_node("retrieve_research_memory", lambda state: retrieve_research_memory_node(state, repository))
    builder.add_node("retrieve_project_context", lambda state: retrieve_project_context_node(state, repository))
    builder.add_node("analyze_request", analyze_request_node)
    builder.add_node("synthesize_response", synthesize_response_node)
    builder.add_node("persist_research_note", lambda state: persist_research_note_node(state, repository))

    builder.add_edge(START, "ensure_flow_version")
    builder.add_edge("ensure_flow_version", "classify_request")
    builder.add_edge("classify_request", "select_workflow")
    builder.add_edge("select_workflow", "retrieve_research_memory")
    builder.add_edge("retrieve_research_memory", "retrieve_project_context")
    builder.add_edge("retrieve_project_context", "analyze_request")
    builder.add_edge("analyze_request", "synthesize_response")
    builder.add_edge("synthesize_response", "persist_research_note")
    builder.add_edge("persist_research_note", END)

    return builder.compile(checkpointer=checkpointer)
