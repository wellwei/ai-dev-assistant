from collections import Counter

from src.indexer.models import ConsistencyFlag, FileSummary, ProjectFile, SymbolInfo
from src.indexer.symbol_extractor import detect_side_effects


def _top_symbol_names(symbols: list[SymbolInfo], limit: int = 8) -> str:
    names = [symbol.name for symbol in symbols[:limit]]
    return ", ".join(names) if names else "No symbols extracted by lightweight parser."


def _dependency_hints(content: str) -> str:
    hints = []
    lowered = content.lower()
    for label in ["redis", "db", "map", "route", "frame", "battle", "resource", "packet", "broadcast"]:
        if label in lowered:
            hints.append(label)
    return ", ".join(hints) if hints else "No dependency hints detected."


def _confidence(symbols: list[SymbolInfo], flags: list[ConsistencyFlag], content: str) -> str:
    if symbols and flags:
        return "medium"
    if symbols and detect_side_effects(content):
        return "medium"
    if symbols:
        return "low"
    return "low"


def summarize_implementation(
    project_file: ProjectFile,
    content: str,
    symbols: list[SymbolInfo],
    flags: list[ConsistencyFlag],
) -> FileSummary:
    symbol_counts = Counter(symbol.symbol_type for symbol in symbols)
    side_effects = detect_side_effects(content)
    symbol_summary = ", ".join(f"{kind}:{count}" for kind, count in sorted(symbol_counts.items()))
    if not symbol_summary:
        symbol_summary = "no symbols extracted"

    flag_summary = ", ".join(sorted({flag.flag_type for flag in flags})) if flags else "none"
    evidence_parts = [f"symbol scan: {symbol_summary}"]
    if side_effects:
        evidence_parts.append(f"side effects: {side_effects}")
    if flags:
        evidence_parts.append(f"consistency flags: {flag_summary}")

    return FileSummary(
        path=project_file.path,
        summary=(
            f"{project_file.file_type} file `{project_file.path}` summarized from implementation text. "
            f"Extracted {len(symbols)} symbols; confidence depends on lightweight parsing, not comments."
        ),
        responsibilities=f"Likely responsibilities inferred from path and extracted symbols: {_dependency_hints(content)}.",
        key_points=_top_symbol_names(symbols),
        dependencies=_dependency_hints(content),
        risks=(
            "Comments and names may be stale; verify actual call sites before editing."
            if flags
            else "Lightweight summary only; verify against source before editing."
        ),
        evidence="; ".join(evidence_parts),
        inconsistencies=flag_summary,
        confidence=_confidence(symbols, flags, content),
    )
