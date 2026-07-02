from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class WorkflowStep:
    id: str
    title: str
    description: str
    read_only: bool
    approval_required: bool


@dataclass(frozen=True)
class WorkflowSpec:
    workflow_id: str
    workflow_name: str
    request_types: tuple[str, ...]
    trigger_keywords: tuple[str, ...]
    description: str
    workflow_steps: tuple[WorkflowStep, ...]
    suggested_commands: tuple[str, ...]
    approval_required: bool


_WORKFLOWS = (
    WorkflowSpec(
        workflow_id="project_qa_readonly",
        workflow_name="Read-only project question answering",
        request_types=("project_qa",),
        trigger_keywords=(),
        description="Answer project questions from indexed implementation evidence and historical memory.",
        workflow_steps=(
            WorkflowStep(
                id="retrieve_evidence",
                title="Retrieve implementation evidence",
                description="Search the project index and memory without changing the target project.",
                read_only=True,
                approval_required=False,
            ),
            WorkflowStep(
                id="answer_with_uncertainty",
                title="Answer with uncertainty",
                description="Explain evidence, confidence, and stale-name/comment risks.",
                read_only=True,
                approval_required=False,
            ),
        ),
        suggested_commands=(),
        approval_required=False,
    ),
    WorkflowSpec(
        workflow_id="requirement_research_readonly",
        workflow_name="Read-only requirement research",
        request_types=("requirement_research",),
        trigger_keywords=("调研", "风险", "方案"),
        description="Research impact scope and risks without changing the target project.",
        workflow_steps=(
            WorkflowStep("collect_context", "Collect context", "Retrieve code, memory, and consistency flags.", True, False),
            WorkflowStep("summarize_risks", "Summarize risks", "Produce impact/risk/open-question report.", True, False),
        ),
        suggested_commands=("Read the relevant files locally to confirm implementation evidence.",),
        approval_required=False,
    ),
    WorkflowSpec(
        workflow_id="development_advice_readonly",
        workflow_name="Read-only development advice",
        request_types=("development_advice",),
        trigger_keywords=("修改", "开发", "实现", "怎么改"),
        description="Produce a change plan and validation advice; target-affecting actions require approval.",
        workflow_steps=(
            WorkflowStep(
                "confirm_impact_scope",
                "Confirm impacted files",
                "Use index and local reads to identify likely impact scope.",
                True,
                False,
            ),
            WorkflowStep(
                "draft_change_order",
                "Draft change order",
                "Suggest patch order and validation plan without editing files.",
                True,
                False,
            ),
            WorkflowStep(
                "request_approval_for_target_actions",
                "Request approval before target actions",
                "Any edit, build, commit, push, or target worktree-affecting action requires user approval.",
                False,
                True,
            ),
        ),
        suggested_commands=(
            "Read the relevant files locally to confirm implementation evidence.",
            "If a build is needed, ask the user before running company project build commands.",
        ),
        approval_required=True,
    ),
    WorkflowSpec(
        workflow_id="index_refresh_suggestion",
        workflow_name="Index refresh suggestion",
        request_types=("index_request",),
        trigger_keywords=("索引", "刷新", "index"),
        description="Suggest refreshing the project index.",
        workflow_steps=(WorkflowStep("suggest_refresh", "Suggest index refresh", "Ask the user to run or approve index refresh.", True, False),),
        suggested_commands=("Run index_graph to scan the target project.",),
        approval_required=False,
    ),
)


def _to_dict(spec: WorkflowSpec) -> dict:
    data = asdict(spec)
    data["workflow_steps"] = [asdict(step) for step in spec.workflow_steps]
    data["suggested_commands"] = list(spec.suggested_commands)
    data.pop("request_types", None)
    data.pop("trigger_keywords", None)
    return data


def get_workflow_specs() -> list[dict]:
    return [_to_dict(spec) for spec in _WORKFLOWS]


def select_workflow(question: str, request_type: str) -> dict:
    for spec in _WORKFLOWS:
        if request_type in spec.request_types:
            return _to_dict(spec)
    return {
        "workflow_id": "unclear_request",
        "workflow_name": "Clarify request",
        "description": "Ask the user for more specific project scope.",
        "workflow_steps": [
            {
                "id": "ask_clarifying_question",
                "title": "Ask clarifying question",
                "description": "Request business area, file, or requirement scope.",
                "read_only": True,
                "approval_required": False,
            }
        ],
        "suggested_commands": [],
        "approval_required": False,
    }
