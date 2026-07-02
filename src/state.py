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
    question: str
    request_type: str
    retrieved_context: Annotated[list[dict], operator.add]
    related_paths: Annotated[list[str], operator.add]
    analysis: str
    answer: str
    open_questions: Annotated[list[str], operator.add]
    suggested_commands: Annotated[list[str], operator.add]
    research_note_id: int | None
