from dataclasses import dataclass
from typing import Literal

from src.indexer.models import ConsistencyFlag, SymbolInfo

ConfidenceLevel = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class ConfidenceAssessment:
    level: ConfidenceLevel
    score: float
    reasons: list[str]


def assess_confidence(symbols: list[SymbolInfo], flags: list[ConsistencyFlag], has_side_effects: bool) -> ConfidenceAssessment:
    score = 0.25
    reasons = ["lightweight regex parser"]

    if symbols:
        score += 0.2
        reasons.append("symbols extracted")
    if any(symbol.line_end is not None for symbol in symbols):
        score += 0.15
        reasons.append("evidence spans available")
    if has_side_effects:
        score += 0.1
        reasons.append("implementation side effects detected")
    if flags:
        score -= 0.2
        reasons.append("consistency flags reduce trust")

    score = max(0.0, min(score, 0.8))
    if score >= 0.7:
        level: ConfidenceLevel = "medium"
    elif score >= 0.45:
        level = "medium"
    else:
        level = "low"
    return ConfidenceAssessment(level=level, score=score, reasons=reasons)
