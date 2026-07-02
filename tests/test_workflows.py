from src.workflows.registry import get_workflow_specs, select_workflow


def test_select_workflow_for_development_advice_requires_approval():
    workflow = select_workflow("我要修改押镖路线重算逻辑", "development_advice")

    assert workflow["workflow_id"] == "development_advice_readonly"
    assert workflow["approval_required"] is True
    assert any(step["approval_required"] for step in workflow["workflow_steps"])
    assert all("command" not in step for step in workflow["workflow_steps"])


def test_select_workflow_for_project_qa_is_read_only():
    workflow = select_workflow("押镖路线逻辑在哪里？", "project_qa")

    assert workflow["workflow_id"] == "project_qa_readonly"
    assert workflow["approval_required"] is False
    assert all(step["read_only"] for step in workflow["workflow_steps"])


def test_workflow_specs_are_serializable_dicts():
    specs = get_workflow_specs()

    assert specs
    for spec in specs:
        assert isinstance(spec["workflow_id"], str)
        assert isinstance(spec["workflow_steps"], list)
        assert isinstance(spec["approval_required"], bool)
