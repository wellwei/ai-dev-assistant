from pathlib import PurePosixPath


def classify_path(path: str) -> tuple[str, str]:
    normalized = path.replace("\\", "/")
    p = PurePosixPath(normalized)
    name = p.name
    suffix = p.suffix.lower()

    if normalized == "CMakeLists.txt" or suffix == ".cmake":
        return "build_config", "cmake"
    if normalized.startswith("doc/") and suffix == ".md":
        return "doc", "markdown"
    if normalized.startswith("doc/") and suffix == ".txt":
        return "doc", "text"
    if suffix == ".cpp" or suffix == ".cc" or suffix == ".cxx":
        return "source", "cpp"
    if suffix == ".h" or suffix == ".hpp" or suffix == ".hh":
        return "header", "cpp"
    if suffix == ".sh":
        return "script", "shell"
    if suffix == ".ini":
        return "config", "ini"
    if suffix == ".afcfile" or name.endswith(".AFCfile"):
        return "config", "afc"
    return "other", "text"
