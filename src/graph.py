import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

from src.assistant_graph import create_assistant_graph
from src.config import settings
from src.storage.sqlite import ensure_parent_dir


def create_graph():
    db_path = ensure_parent_dir(settings.CHECKPOINT_DB)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    checkpointer.setup()
    return create_assistant_graph(checkpointer=checkpointer)
