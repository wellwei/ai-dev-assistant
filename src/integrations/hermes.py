from dataclasses import asdict, dataclass
from typing import Literal, Protocol

HermesHandoffStatus = Literal["disabled", "candidate", "unavailable", "error"]


@dataclass(frozen=True)
class HermesHandoffRequest:
    question: str
    request_type: str
    project_root: str
    related_paths: list[str]
    retrieved_context: list[dict]
    retrieved_memory: list[dict]
    selected_workflow: dict | None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class HermesCandidate:
    status: HermesHandoffStatus
    summary: str
    payload: dict
    approval_required: bool
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


class HermesAdapter(Protocol):
    def enabled(self) -> bool: ...

    def propose_handoff(self, request: HermesHandoffRequest) -> HermesCandidate: ...


class NullHermesAdapter:
    def enabled(self) -> bool:
        return False

    def propose_handoff(self, request: HermesHandoffRequest) -> HermesCandidate:
        return HermesCandidate(
            status="disabled",
            summary="",
            payload={},
            approval_required=True,
            reason="Hermes adapter is disabled.",
        )
