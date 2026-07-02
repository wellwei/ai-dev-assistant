import json

from src.indexer.models import ImprovementProposal
from src.storage.project_index import ProjectIndexRepository


def _note_text(note: dict) -> str:
    parts = [
        note.get("question", ""),
        note.get("internal_memory_summary", ""),
        note.get("answer_summary", ""),
        " ".join(note.get("open_questions") or []),
        " ".join(note.get("related_paths") or []),
    ]
    return " ".join(str(part) for part in parts).lower()


def _looks_like_repeated_route_risk(notes: list[dict]) -> bool:
    matches = 0
    for note in notes:
        text = _note_text(note)
        if "route" in text and "risk" in text:
            matches += 1
    return matches >= 2


def draft_research_memory_proposals(
    repo: ProjectIndexRepository,
    *,
    project_root: str,
    flow_version: str = "",
    limit: int = 20,
) -> list[int]:
    notes = repo.list_recent_research_notes(project_root=project_root, limit=limit)
    if not _looks_like_repeated_route_risk(notes):
        return []

    source_note_ids = [note["id"] for note in notes[:5]]
    proposal = ImprovementProposal(
        proposal_type="retrieval_synonym_update",
        source_note_ids=json.dumps(source_note_ids),
        target_component="src/retriever/keyword_search.py",
        proposed_change=(
            "Review retrieval synonyms for route risk questions so future escort route research "
            "can recall prior route risk findings more reliably."
        ),
        rationale=(
            "Multiple low-confidence research notes mention route risk and unresolved side-effect checks, "
            "which suggests a reusable retrieval synonym or workflow hint may be useful."
        ),
        evidence=f"Source research notes: {source_note_ids}",
        risk="Low. This is a pending proposal only and does not mutate retrieval behavior automatically.",
        flow_version=flow_version,
    )
    return [repo.insert_improvement_proposal(proposal)]
