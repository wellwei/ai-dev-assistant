import json

from src.indexer.models import ImprovementProposal, ResearchNote
from src.self_improvement.proposals import draft_research_memory_proposals
from src.storage.project_index import ProjectIndexRepository
from src.storage.sqlite import connect_db, init_schema


def test_schema_includes_improvement_proposals_table(tmp_path):
    db_path = tmp_path / "project_index.sqlite"

    with connect_db(db_path) as conn:
        init_schema(conn)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'improvement_proposals'"
        ).fetchone()
        columns = {item["name"] for item in conn.execute("PRAGMA table_info(improvement_proposals)").fetchall()}

    assert row is not None
    assert {
        "proposal_type",
        "source_note_ids",
        "target_component",
        "proposed_change",
        "rationale",
        "evidence",
        "risk",
        "status",
        "flow_version",
    }.issubset(columns)


def test_repository_inserts_and_lists_pending_improvement_proposals(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()

    proposal_id = repo.insert_improvement_proposal(
        ImprovementProposal(
            proposal_type="retrieval_synonym_update",
            source_note_ids="[1, 2]",
            target_component="src/retriever/keyword_search.py",
            proposed_change="Add route-risk synonyms for escort route research questions.",
            rationale="Repeated research notes needed the same synonym bridge.",
            evidence="notes 1 and 2 matched route risk but used different business wording.",
            risk="Low; proposal is pending and does not mutate retrieval rules.",
            flow_version="2026-07-02.foundation-v1",
        )
    )

    pending = repo.list_improvement_proposals(status="pending")

    assert proposal_id == 1
    assert len(pending) == 1
    assert pending[0]["id"] == proposal_id
    assert pending[0]["status"] == "pending"
    assert pending[0]["source_note_ids"] == [1, 2]


def test_draft_research_memory_proposals_only_creates_pending_proposals(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()
    first = repo.insert_research_note(
        ResearchNote(
            thread_id="thread-1",
            request_type="requirement_research",
            question="押镖路线风险在哪里？",
            answer_summary="历史调研认为 route risk is around src/route.cpp.",
            related_paths=json.dumps(["src/route.cpp"]),
            open_questions=json.dumps(["Confirm route risk side effects."]),
            project_root="/tmp/project",
            internal_memory_summary="Prior research found route risk around escort route recalculation.",
            user_answer_summary="历史调研认为路线风险集中在 src/route.cpp。",
            confidence="low",
        )
    )
    second = repo.insert_research_note(
        ResearchNote(
            thread_id="thread-2",
            request_type="requirement_research",
            question="路线重算风险怎么确认？",
            answer_summary="历史调研仍需确认 route risk side effects.",
            related_paths=json.dumps(["src/route.cpp"]),
            open_questions=json.dumps(["Confirm route risk side effects."]),
            project_root="/tmp/project",
            source_note_ids=json.dumps([first]),
            internal_memory_summary="Follow-up research still needs route risk side effect confirmation.",
            user_answer_summary="后续调研仍需确认路线风险副作用。",
            confidence="low",
        )
    )

    proposals = draft_research_memory_proposals(repo, project_root="/tmp/project", flow_version="test-flow")
    pending = repo.list_improvement_proposals(status="pending")

    assert len(proposals) == 1
    assert len(pending) == 1
    assert pending[0]["proposal_type"] == "retrieval_synonym_update"
    assert pending[0]["status"] == "pending"
    assert pending[0]["flow_version"] == "test-flow"
    assert pending[0]["source_note_ids"] == [second, first]
    assert "route risk" in pending[0]["proposed_change"]


def test_draft_research_memory_proposals_detects_repeated_gameplay_retrieval_gaps(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()
    first = repo.insert_research_note(
        ResearchNote(
            thread_id="thread-gameplay-1",
            request_type="requirement_research",
            question="移动位置同步逻辑在哪里？",
            answer_summary="Low confidence: movement position sync retrieval needs confirmation.",
            related_paths=json.dumps(["src/rtb_proc/character/character_move.cpp"]),
            open_questions=json.dumps(["Confirm movement sync side effects."]),
            project_root="/tmp/project",
            internal_memory_summary="low confidence movement sync retrieval gap",
            user_answer_summary="移动同步检索结果待确认。",
            confidence="low",
        )
    )
    second = repo.insert_research_note(
        ResearchNote(
            thread_id="thread-gameplay-2",
            request_type="requirement_research",
            question="坐骑上马同步和伤害打断在哪里？",
            answer_summary="Low confidence: mount sync and damage interrupt paths need better retrieval.",
            related_paths=json.dumps(["src/rtb_proc/character/rtb_proc_character_horse.cpp"]),
            open_questions=json.dumps(["Confirm mount sync side effects."]),
            project_root="/tmp/project",
            source_note_ids=json.dumps([first]),
            internal_memory_summary="low confidence mount sync damage retrieval gap",
            user_answer_summary="坐骑同步和伤害打断检索结果待确认。",
            confidence="low",
        )
    )

    proposals = draft_research_memory_proposals(repo, project_root="/tmp/project", flow_version="test-flow")
    pending = repo.list_improvement_proposals(status="pending")

    assert len(proposals) == 1
    assert len(pending) == 1
    assert pending[0]["proposal_type"] == "retrieval_synonym_update"
    assert pending[0]["target_component"] == "src/retriever/keyword_search.py"
    assert pending[0]["source_note_ids"] == [second, first]
    assert "gameplay" in pending[0]["proposed_change"] or "movement" in pending[0]["proposed_change"]
