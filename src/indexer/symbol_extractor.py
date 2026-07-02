import re

from src.indexer.models import SymbolInfo

MACRO_RE = re.compile(r"^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)
STRUCT_RE = re.compile(r"^\s*struct\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.MULTILINE)
CLASS_RE = re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.MULTILINE)
ENUM_RE = re.compile(r"^\s*enum(?:\s+class)?\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.MULTILINE)
FUNCTION_RE = re.compile(
    r"^\s*(?:static\s+|inline\s+|virtual\s+|const\s+|unsigned\s+|signed\s+|long\s+|short\s+|[A-Za-z_][A-Za-z0-9_:<>*&\s]+\s+)"
    r"([A-Za-z_][A-Za-z0-9_:~]*)\s*\([^;{}]*\)\s*(?:const\s*)?\{",
    re.MULTILINE,
)

SIDE_EFFECT_PATTERNS = {
    "redis_write": ("redis", "set", "del", "expire", "hset"),
    "db_write": ("insert", "update", "delete", "replace"),
    "state_write": ("mutable_", "set_", "->state", ".state", "push_back", "erase", "clear", "insert", "="),
    "network_send": ("send", "broadcast", "notify", "packet"),
    "frame_or_timer": ("frame", "timer", "add_task", "post_task"),
}


def _line_number(content: str, offset: int) -> int:
    return content.count("\n", 0, offset) + 1


def detect_side_effects(content: str) -> str:
    lowered = content.lower()
    found: list[str] = []
    for label, needles in SIDE_EFFECT_PATTERNS.items():
        if any(needle in lowered for needle in needles):
            found.append(label)
    return ",".join(found)


def _symbol_summary(symbol_type: str, name: str, side_effects: str) -> str:
    if side_effects:
        return f"{symbol_type} {name} has potential side effects: {side_effects}."
    return f"{symbol_type} {name} declaration or implementation."


def _add_matches(path: str, content: str, regex: re.Pattern[str], symbol_type: str, symbols: list[SymbolInfo]) -> None:
    for match in regex.finditer(content):
        name = match.group(1).split("::")[-1]
        signature = match.group(0).strip().split("{")[0].strip()
        line_start = _line_number(content, match.start())
        window = content[match.start() : match.start() + 1200]
        side_effects = detect_side_effects(window)
        symbols.append(
            SymbolInfo(
                path=path,
                symbol_type=symbol_type,
                name=name,
                signature=signature,
                line_start=line_start,
                line_end=None,
                summary=_symbol_summary(symbol_type, name, side_effects),
                observed_behavior="Potential behavior inferred from implementation text; verify against full code before editing.",
                side_effects=side_effects,
                confidence="medium" if side_effects else "low",
            )
        )


def extract_symbols(path: str, content: str) -> list[SymbolInfo]:
    symbols: list[SymbolInfo] = []
    _add_matches(path, content, MACRO_RE, "macro", symbols)
    _add_matches(path, content, STRUCT_RE, "struct", symbols)
    _add_matches(path, content, CLASS_RE, "class", symbols)
    _add_matches(path, content, ENUM_RE, "enum", symbols)
    _add_matches(path, content, FUNCTION_RE, "function", symbols)
    return symbols
