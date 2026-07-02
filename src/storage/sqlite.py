from pathlib import Path
import sqlite3

from src.storage.migrations import apply_migrations


SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def ensure_parent_dir(path: str | Path) -> Path:
    db_path = Path(path).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def connect_db(path: str | Path) -> sqlite3.Connection:
    db_path = ensure_parent_dir(path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema)
    apply_migrations(conn)
    conn.commit()
