from src.index_graph import create_index_graph
from src.storage.project_index import ProjectIndexRepository
from src.storage.sqlite import connect_db


def test_index_graph_scans_and_writes_changed_files(tmp_path):
    project = tmp_path / "doll_escort_game_svr"
    (project / "src").mkdir(parents=True)
    (project / "doc").mkdir()
    (project / "src/resource.cpp").write_text(
        """
// query only
int query_resource(Context* ctx) {
    ctx->mutable_resource()->set_state(1);
    broadcast_resource(ctx);
    return 0;
}
""",
        encoding="utf-8",
    )
    (project / "doc/readme.md").write_text("# 押镖服务\n启动和资源说明", encoding="utf-8")

    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    graph = create_index_graph(repo)

    result = graph.invoke({"project_root": str(project), "index_db_path": str(db_path)})

    assert result["run_status"] == "success"
    assert len(result["scanned_files"]) == 2
    assert len(result["changed_files"]) == 2
    assert result["errors"] == []

    with connect_db(db_path) as conn:
        file_count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        summary_count = conn.execute("SELECT COUNT(*) FROM file_summaries").fetchone()[0]
        flag_count = conn.execute("SELECT COUNT(*) FROM consistency_flags").fetchone()[0]

    assert file_count == 2
    assert summary_count == 2
    assert flag_count >= 1


def test_index_graph_skips_unchanged_files_on_second_run(tmp_path):
    project = tmp_path / "doll_escort_game_svr"
    (project / "src").mkdir(parents=True)
    (project / "src/a.cpp").write_text("int a() { return 1; }", encoding="utf-8")

    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    graph = create_index_graph(repo)

    first = graph.invoke({"project_root": str(project), "index_db_path": str(db_path)})
    second = graph.invoke({"project_root": str(project), "index_db_path": str(db_path)})

    assert len(first["changed_files"]) == 1
    assert len(second["changed_files"]) == 0


def test_index_graph_reindexes_when_artifact_indexer_version_is_stale(tmp_path):
    project = tmp_path / "doll_escort_game_svr"
    (project / "src").mkdir(parents=True)
    (project / "src/a.cpp").write_text("int a() { return 1; }", encoding="utf-8")

    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    graph = create_index_graph(repo)

    first = graph.invoke({"project_root": str(project), "index_db_path": str(db_path)})
    with connect_db(db_path) as conn:
        conn.execute("UPDATE file_summaries SET indexer_version = ? WHERE path = ?", ("stale-version", "src/a.cpp"))
        conn.commit()
    second = graph.invoke({"project_root": str(project), "index_db_path": str(db_path)})

    assert len(first["changed_files"]) == 1
    assert len(second["changed_files"]) == 1

from langgraph.checkpoint.memory import InMemorySaver

from src.assistant_graph import create_assistant_graph


def test_index_then_assistant_answer_end_to_end(tmp_path):
    project = tmp_path / "doll_escort_game_svr"
    (project / "src/map_data").mkdir(parents=True)
    (project / "doc").mkdir()
    (project / "src/map_data/sea_route.cpp").write_text(
        """
// only query route
int query_route(Context* ctx) {
    ctx->mutable_route()->set_state(1);
    send_route_packet(ctx);
    return 0;
}
""",
        encoding="utf-8",
    )
    (project / "doc/readme.md").write_text("# route\n押镖路线说明", encoding="utf-8")

    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    index_graph = create_index_graph(repo)
    index_result = index_graph.invoke({"project_root": str(project), "index_db_path": str(db_path)})
    assert index_result["run_status"] == "success"

    assistant_graph = create_assistant_graph(repo=repo, checkpointer=InMemorySaver())
    answer = assistant_graph.invoke(
        {
            "question": "押镖 route 逻辑在哪里，改动有什么风险？",
            "project_root": str(project),
            "index_db_path": str(db_path),
            "thread_id": "thread-e2e",
        },
        {"configurable": {"thread_id": "thread-e2e"}},
    )

    assert "src/map_data/sea_route.cpp" in answer["answer"]
    assert "Confidence" in answer["answer"]
    assert "comment" in answer["answer"] or "name" in answer["answer"]


def test_create_index_graph_ignores_langgraph_factory_config_dict(tmp_path):
    project = tmp_path / "doll_escort_game_svr"
    (project / "src").mkdir(parents=True)
    (project / "src/a.cpp").write_text("int a() { return 1; }", encoding="utf-8")
    db_path = tmp_path / "project_index.sqlite"

    app = create_index_graph({})
    result = app.invoke({"project_root": str(project), "index_db_path": str(db_path)})

    assert type(app).__name__ == "CompiledStateGraph"
    assert result["run_status"] == "success"
