from pathlib import Path
import re

from src.storage.sqlite import connect_db, init_schema


def _tokens(query: str) -> list[str]:
    raw_tokens = [token.lower() for token in re.findall(r"[\w一-鿿]+", query) if token.strip()]
    expanded = list(raw_tokens)
    synonym_map = {
        "路线": ["route"],
        "重算": ["recalc", "recalculation"],
        "押镖": ["escort"],
        "地图": ["map"],
        "资源": ["resource"],
    }
    for token in raw_tokens:
        for key, synonyms in synonym_map.items():
            if key in token:
                expanded.extend(synonyms)
    return expanded


def _score(row: dict, tokens: list[str]) -> int:
    haystack = " ".join(str(row.get(key) or "") for key in row).lower()
    return sum(haystack.count(token) for token in tokens)


def search_project_index(db_path: str | Path, query: str, limit: int = 8) -> list[dict]:
    tokens = _tokens(query)
    if not tokens:
        return []

    with connect_db(db_path) as conn:
        init_schema(conn)
        rows = conn.execute(
            """
            SELECT
                f.path,
                f.file_type,
                f.language,
                s.summary,
                s.responsibilities,
                s.key_points,
                s.dependencies,
                s.risks,
                s.evidence,
                s.inconsistencies,
                s.confidence
            FROM files f
            LEFT JOIN file_summaries s ON s.path = f.path
            WHERE f.status = 'active'
            """
        ).fetchall()

        results: list[dict] = []
        for row in rows:
            item = dict(row)
            item["score"] = _score(item, tokens)
            if item["score"] > 0:
                results.append(item)

        symbol_rows = conn.execute(
            """
            SELECT path, name, summary, observed_behavior, side_effects, confidence
            FROM symbols
            """
        ).fetchall()
        symbol_by_path: dict[str, list[dict]] = {}
        for row in symbol_rows:
            item = dict(row)
            score = _score(item, tokens)
            if score > 0:
                symbol_by_path.setdefault(item["path"], []).append(item)

    by_path = {item["path"]: item for item in results}
    for path, symbols in symbol_by_path.items():
        if path not in by_path:
            by_path[path] = {
                "path": path,
                "file_type": "unknown",
                "language": "unknown",
                "summary": "Matched by symbol table.",
                "responsibilities": "",
                "key_points": ", ".join(symbol["name"] for symbol in symbols),
                "dependencies": "",
                "risks": "Verify implementation before editing.",
                "evidence": "symbol match",
                "inconsistencies": "",
                "confidence": "low",
                "score": 0,
            }
        by_path[path]["score"] += sum(_score(symbol, tokens) for symbol in symbols)
        by_path[path]["matched_symbols"] = symbols

    return sorted(by_path.values(), key=lambda item: item["score"], reverse=True)[:limit]
