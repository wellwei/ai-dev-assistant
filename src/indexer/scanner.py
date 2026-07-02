from pathlib import Path
import hashlib

from src.indexer.classifier import classify_path
from src.indexer.models import ProjectFile

SKIP_DIRS = {
    ".git",
    "build",
    "cmake-build-debug",
    "cmake-build-release",
    "__pycache__",
    ".venv",
    "venv",
    ".cache",
    ".idea",
}

SKIP_SUFFIXES = {
    ".o",
    ".so",
    ".a",
    ".tar",
    ".gz",
    ".zip",
    ".pckl",
    ".pyc",
}

INCLUDE_PREFIXES = (
    "src/",
    "doc/",
    "linux_prj/",
)

INCLUDE_NAMES = {
    "CMakeLists.txt",
}


def compute_content_hash(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_skipped(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if any(part in SKIP_DIRS for part in rel.parts):
        return True
    if path.suffix.lower() in SKIP_SUFFIXES:
        return True
    if path.name.endswith(".tar.gz"):
        return True
    return False


def _is_included(rel_path: str) -> bool:
    if rel_path in INCLUDE_NAMES:
        return True
    if rel_path.endswith(".AFCfile"):
        return True
    return rel_path.startswith(INCLUDE_PREFIXES)


def scan_project(project_root: str | Path) -> list[ProjectFile]:
    root = Path(project_root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Target project root does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Target project root is not a directory: {root}")

    results: list[ProjectFile] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if _is_skipped(path, root):
            continue
        rel_path = path.relative_to(root).as_posix()
        if not _is_included(rel_path):
            continue
        file_type, language = classify_path(rel_path)
        stat = path.stat()
        results.append(
            ProjectFile(
                path=rel_path,
                abs_path=str(path),
                file_type=file_type,
                language=language,
                size_bytes=stat.st_size,
                mtime=stat.st_mtime,
                content_hash=compute_content_hash(path),
                status="active",
            )
        )
    return results
