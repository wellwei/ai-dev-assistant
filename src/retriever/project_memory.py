from pathlib import Path

from src.storage.project_index import ProjectIndexRepository


def search_project_memory(
    db_path: str | Path,
    query: str,
    *,
    project_root: str = "",
    memory_type: str | None = None,
    status: str = "active",
    limit: int = 5,
) -> list[dict]:
    repo = ProjectIndexRepository(db_path)
    return repo.search_project_memories(
        query,
        project_root=project_root,
        memory_type=memory_type,
        status=status,
        limit=limit,
    )
