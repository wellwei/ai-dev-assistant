from pathlib import Path

from src.retriever.keyword_search import search_project_index
from src.retriever.vector_search import search_vector_index


def _exact_boost(query: str, path: str, key_points: str = "") -> float:
    lowered = query.lower()
    boost = 0.0
    if path and path.lower() in lowered:
        boost += 100.0
    for token in [part.strip().lower() for part in key_points.split(",") if part.strip()]:
        if token and token in lowered:
            boost += 50.0
    return boost


def hybrid_search_project(db_path: str | Path, query: str, limit: int = 8) -> list[dict]:
    by_path: dict[str, dict] = {}
    for item in search_project_index(db_path, query, limit=limit):
        path = item["path"]
        merged = dict(item)
        merged["keyword_score"] = item.get("score", 0)
        merged["vector_score"] = 0.0
        merged["hybrid_score"] = float(merged["keyword_score"]) + _exact_boost(query, path, item.get("key_points") or "")
        by_path[path] = merged

    for item in search_vector_index(db_path, query, limit=limit):
        path = item.get("source_path") or item.get("source_id")
        if not path:
            continue
        if path not in by_path:
            by_path[path] = {
                "path": path,
                "file_type": "unknown",
                "language": "unknown",
                "summary": item.get("text") or "Matched by vector index.",
                "responsibilities": "",
                "key_points": "",
                "dependencies": "",
                "risks": "Verify implementation before editing.",
                "evidence": "vector semantic match",
                "inconsistencies": "",
                "confidence": "low",
                "keyword_score": 0,
                "vector_score": 0.0,
            }
        by_path[path]["vector_score"] = max(float(by_path[path].get("vector_score") or 0.0), float(item["vector_score"]))
        by_path[path]["hybrid_score"] = (
            float(by_path[path].get("keyword_score") or 0)
            + float(by_path[path].get("vector_score") or 0.0)
            + _exact_boost(query, path, by_path[path].get("key_points") or "")
        )

    return sorted(by_path.values(), key=lambda item: item["hybrid_score"], reverse=True)[:limit]
