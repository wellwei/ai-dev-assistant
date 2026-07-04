def build_context(results: list[dict]) -> str:
    if not results:
        return "No indexed project context matched the request."

    sections: list[str] = []
    for item in results:
        ranking_reason = item.get("ranking_reason") or ""
        scores = []
        if "hybrid_score" in item:
            scores.append(f"hybrid_score={item.get('hybrid_score')}")
        if "keyword_score" in item:
            scores.append(f"keyword_score={item.get('keyword_score')}")
        if "vector_score" in item:
            scores.append(f"vector_score={item.get('vector_score')}")
        sections.append(
            "\n".join(
                [
                    f"File: {item.get('path')}",
                    f"Type: {item.get('file_type')} / {item.get('language')}",
                    f"Summary: {item.get('summary') or ''}",
                    f"Key points: {item.get('key_points') or ''}",
                    f"Dependencies: {item.get('dependencies') or ''}",
                    f"Risks: {item.get('risks') or ''}",
                    f"Evidence: {item.get('evidence') or ''}",
                    f"Inconsistencies: {item.get('inconsistencies') or ''}",
                    f"Ranking reason: {ranking_reason}",
                    f"Scores: {', '.join(scores)}",
                    f"confidence={item.get('confidence') or 'low'}",
                ]
            )
        )
    return "\n\n---\n\n".join(sections)
