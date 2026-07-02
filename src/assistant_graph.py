from langgraph.graph import END, START, StateGraph

from src.nodes.assistant_nodes import (
    analyze_request_node,
    classify_request_node,
    persist_research_note_node,
    retrieve_project_context_node,
    synthesize_response_node,
)
from src.state import AssistantState
from src.storage.project_index import ProjectIndexRepository


def create_assistant_graph(repo: ProjectIndexRepository | None = None, checkpointer=None):
    builder = StateGraph(AssistantState)

    builder.add_node("classify_request", classify_request_node)
    builder.add_node("retrieve_project_context", lambda state: retrieve_project_context_node(state, repo))
    builder.add_node("analyze_request", analyze_request_node)
    builder.add_node("synthesize_response", synthesize_response_node)
    builder.add_node("persist_research_note", lambda state: persist_research_note_node(state, repo))

    builder.add_edge(START, "classify_request")
    builder.add_edge("classify_request", "retrieve_project_context")
    builder.add_edge("retrieve_project_context", "analyze_request")
    builder.add_edge("analyze_request", "synthesize_response")
    builder.add_edge("synthesize_response", "persist_research_note")
    builder.add_edge("persist_research_note", END)

    return builder.compile(checkpointer=checkpointer)
