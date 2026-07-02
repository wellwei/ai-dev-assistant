from pathlib import Path

from src.storage.project_index import ProjectIndexRepository


def search_research_memory(
    db_path: str | Path,
    query: str,
    *,
    project_root: str = "",
    request_type: str | None = None,
    limit: int = 5,
) -> list[dict]:
    repo = ProjectIndexRepository(db_path)
    return repo.search_research_notes(query, project_root=project_root, request_type=request_type, limit=limit)
