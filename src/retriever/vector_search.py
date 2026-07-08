import json
from pathlib import Path

from src.embeddings.provider import DIMS, MODEL_NAME, cosine_similarity, embed_text, text_hash
from src.storage.sqlite import connect_db, init_schema


def upsert_embedding(
    db_path: str | Path,
    *,
    source_type: str,
    source_id: str,
    source_path: str,
    source_hash: str,
    text: str,
    embedding_model: str = MODEL_NAME,
) -> int:
    vector = embed_text(text)
    vector_json = json.dumps(vector)
    embedding_text_hash = text_hash(text)
    with connect_db(db_path) as conn:
        init_schema(conn)
        conn.execute(
            """
            INSERT INTO embeddings(
                source_type, source_id, source_path, source_hash, embedding_model,
                embedding_dim, embedding_text_hash, vector, text, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            ON CONFLICT(source_type, source_id, embedding_model) DO UPDATE SET
                source_path = excluded.source_path,
                source_hash = excluded.source_hash,
                embedding_dim = excluded.embedding_dim,
                embedding_text_hash = excluded.embedding_text_hash,
                vector = excluded.vector,
                text = excluded.text,
                updated_at = excluded.updated_at
            """,
            (source_type, source_id, source_path, source_hash, embedding_model, DIMS, embedding_text_hash, vector_json, text),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id FROM embeddings WHERE source_type = ? AND source_id = ? AND embedding_model = ?",
            (source_type, source_id, embedding_model),
        ).fetchone()
    return int(row["id"])


def search_vector_index(
    db_path: str | Path,
    query: str,
    *,
    limit: int = 8,
    embedding_model: str = MODEL_NAME,
    initialize_schema: bool = True,
) -> list[dict]:
    query_vector = embed_text(query)
    with connect_db(db_path) as conn:
        if initialize_schema:
            init_schema(conn)
        rows = conn.execute(
            "SELECT * FROM embeddings WHERE embedding_model = ?",
            (embedding_model,),
        ).fetchall()
    hits: list[dict] = []
    for row in rows:
        item = dict(row)
        vector = json.loads(item["vector"])
        score = cosine_similarity(query_vector, vector)
        if score <= 0:
            continue
        item["vector_score"] = score
        hits.append(item)
    return sorted(hits, key=lambda item: item["vector_score"], reverse=True)[:limit]
