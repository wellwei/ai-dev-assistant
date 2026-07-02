def build_context(results: list[dict]) -> str:
    if not results:
        return "No indexed project context matched the request."

    sections: list[str] = []
    for item in results:
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
                    f"confidence={item.get('confidence') or 'low'}",
                ]
            )
        )
    return "\n\n---\n\n".join(sections)
