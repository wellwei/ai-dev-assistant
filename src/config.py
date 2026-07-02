import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _default_target_project_root() -> str:
    return str(Path.home() / "projects/escort_server/doll_escort_game_svr")


class Settings:
    def __init__(self) -> None:
        self.OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
        self.OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o")
        self.TARGET_PROJECT_ROOT: str = os.getenv(
            "TARGET_PROJECT_ROOT",
            _default_target_project_root(),
        )
        self.CHECKPOINT_DB: str = os.getenv("CHECKPOINT_DB", "./checkpoints/langgraph.sqlite")
        self.PROJECT_INDEX_DB: str = os.getenv("PROJECT_INDEX_DB", "./checkpoints/project_index.sqlite")
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
