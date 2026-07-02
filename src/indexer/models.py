from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectFile:
    path: str
    abs_path: str
    file_type: str
    language: str
    size_bytes: int
    mtime: float
    content_hash: str
    status: str = "active"


@dataclass(frozen=True)
class FileSummary:
    path: str
    summary: str
    responsibilities: str
    key_points: str
    dependencies: str
    risks: str
    evidence: str
    inconsistencies: str
    confidence: str


@dataclass(frozen=True)
class SymbolInfo:
    path: str
    symbol_type: str
    name: str
    signature: str
    line_start: int
    line_end: int | None
    summary: str
    observed_behavior: str
    side_effects: str
    confidence: str


@dataclass(frozen=True)
class ConsistencyFlag:
    path: str
    line_start: int | None
    line_end: int | None
    flag_type: str
    subject: str
    claimed_behavior: str | None
    observed_behavior: str
    evidence: str
    severity: str
    status: str = "open"


@dataclass(frozen=True)
class ResearchNote:
    thread_id: str
    request_type: str
    question: str
    answer_summary: str
    related_paths: str
    open_questions: str
