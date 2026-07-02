from src.indexer.models import ConsistencyFlag, SymbolInfo
from src.indexer.symbol_extractor import detect_side_effects

READ_ONLY_PREFIXES = (
    "get",
    "query",
    "check",
    "is",
    "has",
    "find",
)

NO_WRITE_COMMENT_MARKERS = (
    "no state changes",
    "no write",
    "readonly",
    "read only",
    "只读",
    "不修改",
    "不写",
    "仅查询",
)


def _looks_read_only(name: str) -> bool:
    lowered = name.lower()
    return any(lowered.startswith(prefix) or f"_{prefix}_" in lowered for prefix in READ_ONLY_PREFIXES)


def _has_write_side_effect(side_effects: str) -> bool:
    return any(
        label in side_effects
        for label in ("redis_write", "db_write", "state_write", "network_send", "frame_or_timer")
    )


def detect_consistency_flags(path: str, content: str, symbols: list[SymbolInfo]) -> list[ConsistencyFlag]:
    flags: list[ConsistencyFlag] = []

    for symbol in symbols:
        if _looks_read_only(symbol.name) and _has_write_side_effect(symbol.side_effects):
            flags.append(
                ConsistencyFlag(
                    path=path,
                    line_start=symbol.line_start,
                    line_end=symbol.line_end,
                    flag_type="side_effect_hidden",
                    subject=symbol.name,
                    claimed_behavior=f"Name looks read-only: {symbol.name}",
                    observed_behavior=f"Implementation text shows side effects: {symbol.side_effects}",
                    evidence=symbol.signature,
                    severity="warning",
                    status="open",
                )
            )

    lowered = content.lower()
    if any(marker in lowered for marker in NO_WRITE_COMMENT_MARKERS):
        side_effects = detect_side_effects(content)
        if _has_write_side_effect(side_effects):
            flags.append(
                ConsistencyFlag(
                    path=path,
                    line_start=None,
                    line_end=None,
                    flag_type="comment_mismatch",
                    subject=path,
                    claimed_behavior="Comment claims read-only or no writes.",
                    observed_behavior=f"Implementation text shows side effects: {side_effects}",
                    evidence="Matched no-write comment marker and write-like implementation marker.",
                    severity="warning",
                    status="open",
                )
            )

    return flags
