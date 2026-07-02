from src.integrations.hermes import HermesHandoffRequest, NullHermesAdapter


def test_null_hermes_adapter_returns_disabled_candidate():
    adapter = NullHermesAdapter()
    request = HermesHandoffRequest(
        question="押镖路线风险？",
        request_type="requirement_research",
        project_root="/tmp/project",
        related_paths=["src/route.cpp"],
        retrieved_context=[],
        retrieved_memory=[],
        selected_workflow={"workflow_id": "requirement_research_readonly"},
    )

    candidate = adapter.propose_handoff(request)

    assert adapter.enabled() is False
    assert candidate.status == "disabled"
    assert candidate.approval_required is True
    assert candidate.payload == {}


def test_hermes_handoff_payload_is_serializable_when_disabled():
    adapter = NullHermesAdapter()
    request = HermesHandoffRequest(
        question="押镖路线风险？",
        request_type="requirement_research",
        project_root="/tmp/project",
        related_paths=["src/route.cpp"],
        retrieved_context=[],
        retrieved_memory=[],
        selected_workflow=None,
    )

    candidate = adapter.propose_handoff(request).to_dict()

    assert candidate["status"] == "disabled"
    assert candidate["approval_required"] is True
