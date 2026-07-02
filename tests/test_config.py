from pathlib import Path

from src.config import Settings


def test_settings_defaults_point_to_target_project_and_sqlite_files(monkeypatch):
    monkeypatch.delenv("TARGET_PROJECT_ROOT", raising=False)
    monkeypatch.delenv("CHECKPOINT_DB", raising=False)
    monkeypatch.delenv("PROJECT_INDEX_DB", raising=False)

    settings = Settings()

    assert settings.TARGET_PROJECT_ROOT == str(
        Path.home() / "projects/escort_server/doll_escort_game_svr"
    )
    assert settings.CHECKPOINT_DB == "./checkpoints/langgraph.sqlite"
    assert settings.PROJECT_INDEX_DB == "./checkpoints/project_index.sqlite"


def test_settings_allows_environment_overrides(monkeypatch, tmp_path):
    project_root = tmp_path / "target"
    checkpoint = tmp_path / "checkpoints" / "graph.sqlite"
    index_db = tmp_path / "index" / "project.sqlite"

    monkeypatch.setenv("TARGET_PROJECT_ROOT", str(project_root))
    monkeypatch.setenv("CHECKPOINT_DB", str(checkpoint))
    monkeypatch.setenv("PROJECT_INDEX_DB", str(index_db))
    monkeypatch.setenv("MODEL_NAME", "company-model")

    settings = Settings()

    assert settings.TARGET_PROJECT_ROOT == str(project_root)
    assert settings.CHECKPOINT_DB == str(checkpoint)
    assert settings.PROJECT_INDEX_DB == str(index_db)
    assert settings.MODEL_NAME == "company-model"
