from typing import Annotated, TypedDict
import operator

from src.indexer.models import ConsistencyFlag, FileSummary, ProjectFile, SymbolInfo


class IndexState(TypedDict, total=False):
    project_root: str
    index_db_path: str
    run_id: int
    run_status: str
    scanned_files: Annotated[list[ProjectFile], operator.add]
    changed_files: Annotated[list[ProjectFile], operator.add]
    skipped_files: Annotated[list[str], operator.add]
    summaries: Annotated[list[FileSummary], operator.add]
    symbols: Annotated[list[SymbolInfo], operator.add]
    consistency_flags: Annotated[list[ConsistencyFlag], operator.add]
    errors: Annotated[list[str], operator.add]


class AssistantState(TypedDict, total=False):
    project_root: str
    index_db_path: str
    thread_id: str
    flow_version: str
    question: str
    request_type: str
    retrieved_context: Annotated[list[dict], operator.add]
    retrieved_memory: Annotated[list[dict], operator.add]
    retrieved_project_memories: Annotated[list[dict], operator.add]
    related_paths: Annotated[list[str], operator.add]
    memory_note_ids: Annotated[list[int], operator.add]
    project_memory_ids: Annotated[list[int], operator.add]
    source_note_ids: Annotated[list[int], operator.add]
    selected_workflow: dict
    workflow_steps: Annotated[list[dict], operator.add]
    approval_required: bool
    analysis: str
    answer: str
    open_questions: Annotated[list[str], operator.add]
    suggested_commands: Annotated[list[str], operator.add]
    research_note_id: int | None
