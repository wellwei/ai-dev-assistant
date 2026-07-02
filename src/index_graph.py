from langgraph.graph import END, START, StateGraph

from src.nodes.index_nodes import (
    classify_files_node,
    detect_changed_files_node,
    detect_consistency_flags_node,
    extract_symbols_node,
    scan_project_node,
    summarize_implementation_node,
    write_index_node,
)
from src.state import IndexState
from src.storage.project_index import ProjectIndexRepository


def create_index_graph(repo: ProjectIndexRepository | None = None):
    builder = StateGraph(IndexState)

    builder.add_node("scan_project", lambda state: scan_project_node(state, repo))
    builder.add_node("detect_changed_files", lambda state: detect_changed_files_node(state, repo))
    builder.add_node("classify_files", classify_files_node)
    builder.add_node("extract_symbols", extract_symbols_node)
    builder.add_node("detect_consistency_flags", detect_consistency_flags_node)
    builder.add_node("summarize_implementation", summarize_implementation_node)
    builder.add_node("write_index", lambda state: write_index_node(state, repo))

    builder.add_edge(START, "scan_project")
    builder.add_edge("scan_project", "detect_changed_files")
    builder.add_edge("detect_changed_files", "classify_files")
    builder.add_edge("classify_files", "extract_symbols")
    builder.add_edge("extract_symbols", "detect_consistency_flags")
    builder.add_edge("detect_consistency_flags", "summarize_implementation")
    builder.add_edge("summarize_implementation", "write_index")
    builder.add_edge("write_index", END)

    return builder.compile()
