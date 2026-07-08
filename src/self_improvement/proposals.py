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


def _looks_like_repeated_gameplay_retrieval_gap(notes: list[dict]) -> bool:
    domain_terms = [
        "移动",
        "move",
        "movement",
        "position",
        "sync",
        "战斗",
        "battle",
        "combat",
        "伤害",
        "damage",
        "hurt",
        "冲锋",
        "charge",
        "坐骑",
        "mount",
        "上马",
        "下马",
    ]
    uncertainty_terms = ["low", "unresolved", "open", "gap", "未确认", "待确认", "确认"]
    matches = 0
    for note in notes:
        text = _note_text(note)
        if any(term in text for term in domain_terms) and any(term in text for term in uncertainty_terms):
            matches += 1
    return matches >= 2


def _route_risk_proposal(source_note_ids: list[int], flow_version: str) -> ImprovementProposal:
    return ImprovementProposal(
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


def _gameplay_retrieval_proposal(source_note_ids: list[int], flow_version: str) -> ImprovementProposal:
    return ImprovementProposal(
        proposal_type="retrieval_synonym_update",
        source_note_ids=json.dumps(source_note_ids),
        target_component="src/retriever/keyword_search.py",
        proposed_change=(
            "Review gameplay retrieval synonyms for movement position sync, battle damage, charge, "
            "and mount questions so future gameplay research recalls implementation files more reliably."
        ),
        rationale=(
            "Multiple low-confidence research notes mention gameplay movement/combat/mount retrieval gaps, "
            "which suggests reusable keyword and intent tuning may be useful."
        ),
        evidence=f"Source research notes: {source_note_ids}",
        risk="Low. This is a pending proposal only and does not mutate retrieval behavior automatically.",
        flow_version=flow_version,
    )


def draft_research_memory_proposals(
    repo: ProjectIndexRepository,
    *,
    project_root: str,
    flow_version: str = "",
    limit: int = 20,
) -> list[int]:
    notes = repo.list_recent_research_notes(project_root=project_root, limit=limit)
    source_note_ids = [note["id"] for note in notes[:5]]
    if _looks_like_repeated_route_risk(notes):
        return [repo.insert_improvement_proposal(_route_risk_proposal(source_note_ids, flow_version))]
    if _looks_like_repeated_gameplay_retrieval_gap(notes):
        return [repo.insert_improvement_proposal(_gameplay_retrieval_proposal(source_note_ids, flow_version))]
    return []
