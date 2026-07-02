from pathlib import Path

from src.config import settings
from src.indexer.consistency import detect_consistency_flags
from src.indexer.models import ConsistencyFlag, FileSummary, ProjectFile, SymbolInfo
from src.indexer.scanner import scan_project
from src.indexer.summarizer import summarize_implementation
from src.indexer.symbol_extractor import extract_symbols
from src.state import IndexState
from src.storage.project_index import ProjectIndexRepository


def _repo(state: IndexState, default_repo: ProjectIndexRepository | None = None) -> ProjectIndexRepository:
    if default_repo is not None:
        return default_repo
    return ProjectIndexRepository(state.get("index_db_path") or settings.PROJECT_INDEX_DB)


def scan_project_node(state: IndexState, repo: ProjectIndexRepository | None = None) -> dict:
    project_root = state.get("project_root") or settings.TARGET_PROJECT_ROOT
    repository = _repo(state, repo)
    run_id = repository.start_run(project_root)
    try:
        scanned = scan_project(project_root)
        repository.mark_deleted_missing_paths(file.path for file in scanned)
        return {
            "project_root": project_root,
            "run_id": run_id,
            "scanned_files": scanned,
            "run_status": "running",
        }
    except Exception as exc:
        repository.finish_run(run_id, "failed", 0, 0, 0, str(exc))
        return {"run_id": run_id, "run_status": "failed", "errors": [str(exc)]}


def detect_changed_files_node(state: IndexState, repo: ProjectIndexRepository | None = None) -> dict:
    repository = _repo(state, repo)
    changed: list[ProjectFile] = []
    for file in state.get("scanned_files", []):
        existing = repository.get_file(file.path)
        if existing is None or existing["content_hash"] != file.content_hash or existing["status"] != "active":
            changed.append(file)
    return {"changed_files": changed}


def classify_files_node(state: IndexState) -> dict:
    return {"skipped_files": []}


def extract_symbols_node(state: IndexState) -> dict:
    all_symbols: list[SymbolInfo] = []
    errors: list[str] = []
    for file in state.get("changed_files", []):
        if file.language != "cpp":
            continue
        try:
            content = Path(file.abs_path).read_text(encoding="utf-8", errors="ignore")
            all_symbols.extend(extract_symbols(file.path, content))
        except Exception as exc:
            errors.append(f"{file.path}: {exc}")
    return {"symbols": all_symbols, "errors": errors}


def _symbols_for_path(symbols: list[SymbolInfo], path: str) -> list[SymbolInfo]:
    return [symbol for symbol in symbols if symbol.path == path]


def detect_consistency_flags_node(state: IndexState) -> dict:
    flags: list[ConsistencyFlag] = []
    errors: list[str] = []
    symbols = state.get("symbols", [])
    for file in state.get("changed_files", []):
        try:
            content = Path(file.abs_path).read_text(encoding="utf-8", errors="ignore")
            flags.extend(detect_consistency_flags(file.path, content, _symbols_for_path(symbols, file.path)))
        except Exception as exc:
            errors.append(f"{file.path}: {exc}")
    return {"consistency_flags": flags, "errors": errors}


def summarize_implementation_node(state: IndexState) -> dict:
    summaries: list[FileSummary] = []
    errors: list[str] = []
    symbols = state.get("symbols", [])
    flags = state.get("consistency_flags", [])
    for file in state.get("changed_files", []):
        try:
            content = Path(file.abs_path).read_text(encoding="utf-8", errors="ignore")
            file_symbols = _symbols_for_path(symbols, file.path)
            file_flags = [flag for flag in flags if flag.path == file.path]
            summaries.append(summarize_implementation(file, content, file_symbols, file_flags))
        except Exception as exc:
            errors.append(f"{file.path}: {exc}")
    return {"summaries": summaries, "errors": errors}


def write_index_node(state: IndexState, repo: ProjectIndexRepository | None = None) -> dict:
    repository = _repo(state, repo)
    run_id = state.get("run_id")
    scanned = state.get("scanned_files", [])
    changed = state.get("changed_files", [])
    summaries = state.get("summaries", [])
    symbols = state.get("symbols", [])
    flags = state.get("consistency_flags", [])
    errors = state.get("errors", [])

    try:
        for file in scanned:
            repository.upsert_file(file)
        for summary in summaries:
            repository.upsert_summary(summary)
        for file in changed:
            repository.replace_symbols(file.path, _symbols_for_path(symbols, file.path))
            repository.replace_consistency_flags(file.path, [flag for flag in flags if flag.path == file.path])
        status = "partial_success" if errors else "success"
        if run_id is not None:
            repository.finish_run(run_id, status, len(scanned), len(changed), len(summaries), "\n".join(errors) or None)
        return {"run_status": status}
    except Exception as exc:
        if run_id is not None:
            repository.finish_run(run_id, "failed", len(scanned), len(changed), len(summaries), str(exc))
        return {"run_status": "failed", "errors": [str(exc)]}
