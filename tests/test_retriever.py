from src.indexer.models import FileSummary, ProjectFile, ProjectMemory, ResearchNote, SymbolInfo
from src.retriever.context_builder import build_context
from src.retriever.hybrid_search import hybrid_search_project
from src.retriever.keyword_search import search_project_index
from src.retriever.project_memory import search_project_memory
from src.retriever.research_memory import search_research_memory
from src.retriever.vector_search import search_vector_index, upsert_embedding
from src.storage.project_index import ProjectIndexRepository


def test_search_project_index_returns_matching_summaries_and_symbols(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()
    repo.upsert_file(
        ProjectFile("src/route.cpp", "/tmp/src/route.cpp", "source", "cpp", 10, 1.0, "hash")
    )
    repo.upsert_summary(
        FileSummary(
            path="src/route.cpp",
            summary="Handles escort route recalculation.",
            responsibilities="route",
            key_points="recalc_route_main_work_handler",
            dependencies="map, route",
            risks="verify implementation",
            evidence="symbol scan",
            inconsistencies="none",
            confidence="medium",
        )
    )
    repo.replace_symbols(
        "src/route.cpp",
        [
            SymbolInfo(
                path="src/route.cpp",
                symbol_type="function",
                name="recalc_route_main_work_handler",
                signature="int recalc_route_main_work_handler(Context*)",
                line_start=12,
                line_end=None,
                summary="Recalculates route.",
                observed_behavior="route update",
                side_effects="state_write",
                confidence="medium",
            )
        ],
    )

    results = search_project_index(db_path, "route recalc")

    assert results
    assert results[0]["path"] == "src/route.cpp"
    assert "route" in results[0]["summary"].lower()


def test_search_project_index_prioritizes_business_implementation_over_config_noise(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()
    repo.upsert_file(
        ProjectFile("src/map_data/sea_route.cpp", "/tmp/src/map_data/sea_route.cpp", "source", "cpp", 10, 1.0, "hash-src")
    )
    repo.upsert_summary(
        FileSummary(
            path="src/map_data/sea_route.cpp",
            summary="Implements escort route recalculation from implementation evidence.",
            responsibilities="escort route recalculation",
            key_points="recalc_route_main_work_handler",
            dependencies="map, route",
            risks="verify state writes",
            evidence="symbol scan; side effects: state_write,network_send",
            inconsistencies="none",
            confidence="medium",
            confidence_score=0.62,
        )
    )
    repo.replace_symbols(
        "src/map_data/sea_route.cpp",
        [
            SymbolInfo(
                path="src/map_data/sea_route.cpp",
                symbol_type="function",
                name="recalc_route_main_work_handler",
                signature="int recalc_route_main_work_handler(Context*)",
                line_start=20,
                line_end=40,
                summary="Recalculates escort route.",
                observed_behavior="updates route state and sends route packet",
                side_effects="state_write,network_send",
                confidence="medium",
            )
        ],
    )
    repo.upsert_file(
        ProjectFile("CMakeLists.txt", "/tmp/CMakeLists.txt", "build", "cmake", 10, 1.0, "hash-cmake")
    )
    repo.upsert_summary(
        FileSummary(
            path="CMakeLists.txt",
            summary=(
                "Build config mentions escort route recalc route route route route route route "
                "route route route route route route route route route route for compilation."
            ),
            responsibilities="build config for route route route route modules",
            key_points="route route route route route route recalc escort",
            dependencies="route, map",
            risks="not implementation evidence route risk",
            evidence="config text",
            inconsistencies="none",
            confidence="low",
            confidence_score=0.2,
        )
    )
    repo.upsert_file(
        ProjectFile("linux_prj/route.ini", "/tmp/linux_prj/route.ini", "config", "ini", 10, 1.0, "hash-ini")
    )
    repo.upsert_summary(
        FileSummary(
            path="linux_prj/route.ini",
            summary="Runtime config repeats route recalc escort route terms.",
            responsibilities="runtime config",
            key_points="route recalc escort",
            dependencies="route",
            risks="configuration only",
            evidence="config text",
            inconsistencies="none",
            confidence="low",
            confidence_score=0.1,
        )
    )
    repo.upsert_file(
        ProjectFile("worker_task.AFCfile", "/tmp/worker_task.AFCfile", "config", "unknown", 10, 1.0, "hash-afc")
    )
    repo.upsert_summary(
        FileSummary(
            path="worker_task.AFCfile",
            summary="Generic task config repeats route recalc escort risk terms.",
            responsibilities="task config",
            key_points="route recalc escort risk",
            dependencies="route",
            risks="configuration only",
            evidence="side effects: state_write",
            inconsistencies="none",
            confidence="low",
            confidence_score=0.1,
        )
    )
    repo.upsert_file(
        ProjectFile("src/db/db_config.cpp", "/tmp/src/db/db_config.cpp", "source", "cpp", 10, 1.0, "hash-db")
    )
    repo.upsert_summary(
        FileSummary(
            path="src/db/db_config.cpp",
            summary="Generic DB config source mentions escort route recalc terms across many config fields.",
            responsibilities="generic config loading",
            key_points="escort_route_config, route_table_config, recalc_route_config",
            dependencies="db, config",
            risks="broad shared config file",
            evidence="symbol scan; side effects: state_write",
            inconsistencies="none",
            confidence="medium",
            confidence_score=0.5,
        )
    )
    repo.replace_symbols(
        "src/db/db_config.cpp",
        [
            SymbolInfo(
                path="src/db/db_config.cpp",
                symbol_type="function",
                name=f"load_route_config_{idx}",
                signature=f"int load_route_config_{idx}(Context*)",
                line_start=idx,
                line_end=idx + 1,
                summary="Loads route config.",
                observed_behavior="updates route config state",
                side_effects="state_write",
                confidence="medium",
            )
            for idx in range(20)
        ],
    )

    results = search_project_index(db_path, "押镖 route 重算 风险")
    paths = [item["path"] for item in results]

    assert results[0]["path"] == "src/map_data/sea_route.cpp"
    assert results[0]["ranking_reason"].startswith("source implementation")
    assert paths.index("src/map_data/sea_route.cpp") < paths.index("src/db/db_config.cpp")
    assert paths.index("src/map_data/sea_route.cpp") < paths.index("CMakeLists.txt")
    if "worker_task.AFCfile" in paths:
        afc_result = next(item for item in results if item["path"] == "worker_task.AFCfile")
        assert "implementation side-effect evidence" not in afc_result["ranking_reason"]


def test_search_project_index_applies_escort_domain_intent_boosts(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()

    candidates = [
        ("src/rtb_proc/escort_car/rtb_proc_escort_car.cpp", "escort car main logic", "escort route car", "state_write"),
        ("src/rtb_proc/escort_car/rtb_proc_escort_car_move.cpp", "escort car movement logic", "escort car move route", "state_write"),
        ("src/task/move/follow_escort_car_move_task.cpp", "follow escort car movement task", "escort car move follow", "state_write"),
        ("src/map_data/sea_route_3d.cpp", "sea route map data and route geometry", "sea route map", "state_write"),
        ("src/task/tcp/process_cli_query_second_route_tcp_task.cpp", "client second route query task", "query second route", "network_send"),
        ("src/task/work/cal_cross_map_route_cost_time_complex_task.cpp", "cross map route cost recalculation", "route recalc cost", "state_write"),
        ("src/rtb_proc/character/rtb_proc_character_recalc_rout.cpp", "character route recalculation", "character route recalc", "state_write"),
    ]
    for path, summary, key_points, side_effects in candidates:
        repo.upsert_file(ProjectFile(path, f"/tmp/{path}", "source", "cpp", 10, 1.0, f"hash-{path}"))
        repo.upsert_summary(
            FileSummary(
                path=path,
                summary=summary,
                responsibilities=summary,
                key_points=key_points,
                dependencies="escort, route, map",
                risks="verify implementation",
                evidence=f"symbol scan; side effects: {side_effects}",
                inconsistencies="none",
                confidence="medium",
                confidence_score=0.6,
            )
        )
        repo.replace_symbols(
            path,
            [
                SymbolInfo(
                    path=path,
                    symbol_type="function",
                    name=key_points.replace(" ", "_"),
                    signature="int handler(Context*)",
                    line_start=1,
                    line_end=10,
                    summary=summary,
                    observed_behavior=summary,
                    side_effects=side_effects,
                    confidence="medium",
                )
            ],
        )

    movement = search_project_index(db_path, "押镖车移动 move", limit=5)
    sea_route = search_project_index(db_path, "海路 地图 路线", limit=5)
    recalc = search_project_index(db_path, "路线重算 recalc 影响哪些文件", limit=5)
    client_query = search_project_index(db_path, "客户端 查询 二段路线", limit=5)

    assert movement[0]["path"] == "src/rtb_proc/escort_car/rtb_proc_escort_car_move.cpp"
    assert "escort domain intent" in movement[0]["ranking_reason"]
    assert sea_route[0]["path"] == "src/map_data/sea_route_3d.cpp"
    assert recalc[0]["path"] in {
        "src/task/work/cal_cross_map_route_cost_time_complex_task.cpp",
        "src/rtb_proc/character/rtb_proc_character_recalc_rout.cpp",
    }
    assert client_query[0]["path"] == "src/task/tcp/process_cli_query_second_route_tcp_task.cpp"


def test_route_recalc_intent_does_not_promote_client_query_path(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()

    candidates = [
        (
            "src/task/tcp/process_cli_query_second_route_tcp_task.cpp",
            "client second route query task",
            "query_second_route route",
            "network_send",
            6,
        ),
        (
            "src/task/work/cal_cross_map_route_cost_time_complex_task.cpp",
            "cross map route cost recalculation",
            "route recalc cost",
            "state_write",
            2,
        ),
        (
            "src/task/tcp/process_recalc_route_task.cpp",
            "route recalculation task",
            "process recalc route",
            "state_write",
            2,
        ),
    ]
    for path, summary, key_points, side_effects, symbol_count in candidates:
        repo.upsert_file(ProjectFile(path, f"/tmp/{path}", "source", "cpp", 10, 1.0, f"hash-{path}"))
        repo.upsert_summary(
            FileSummary(
                path=path,
                summary=summary,
                responsibilities=summary,
                key_points=key_points,
                dependencies="route, map",
                risks="verify implementation",
                evidence=f"symbol scan; side effects: {side_effects}",
                inconsistencies="none",
                confidence="medium",
                confidence_score=0.6,
            )
        )
        repo.replace_symbols(
            path,
            [
                SymbolInfo(
                    path=path,
                    symbol_type="function",
                    name=f"{key_points.replace(' ', '_')}_{idx}",
                    signature="int handler(Context*)",
                    line_start=idx,
                    line_end=idx + 1,
                    summary=summary,
                    observed_behavior=summary,
                    side_effects=side_effects,
                    confidence="medium",
                )
                for idx in range(symbol_count)
            ],
        )

    recalc = search_project_index(db_path, "押镖 route 重算 风险", limit=5)
    recalc_paths = [item["path"] for item in recalc]
    client_query = search_project_index(db_path, "客户端 查询 二段路线", limit=5)

    assert recalc_paths.index("src/task/work/cal_cross_map_route_cost_time_complex_task.cpp") < recalc_paths.index(
        "src/task/tcp/process_cli_query_second_route_tcp_task.cpp"
    )
    assert recalc_paths.index("src/task/tcp/process_recalc_route_task.cpp") < recalc_paths.index(
        "src/task/tcp/process_cli_query_second_route_tcp_task.cpp"
    )
    assert client_query[0]["path"] == "src/task/tcp/process_cli_query_second_route_tcp_task.cpp"


def test_movement_state_terms_promote_escort_car_move_logic(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()

    candidates = [
        (
            "src/rtb_proc/escort_car/rtb_proc_escort_car.cpp",
            "escort car generic runtime handler",
            "escort car status attach",
            "state_write",
            6,
        ),
        (
            "src/rtb_proc/escort_car/rtb_proc_escort_car_move.cpp",
            "escort car movement state handler",
            "escort car move stop sync position",
            "state_write",
            2,
        ),
        (
            "src/rtb_proc/escort_car/rtb_proc_escort_def.h",
            "escort car status macros",
            "car move stop route macros",
            "",
            8,
        ),
    ]
    for path, summary, key_points, side_effects, symbol_count in candidates:
        repo.upsert_file(ProjectFile(path, f"/tmp/{path}", "source", "cpp", 10, 1.0, f"hash-{path}"))
        repo.upsert_summary(
            FileSummary(
                path=path,
                summary=summary,
                responsibilities=summary,
                key_points=key_points,
                dependencies="escort, route, status",
                risks="verify implementation",
                evidence=f"symbol scan; side effects: {side_effects}",
                inconsistencies="none",
                confidence="medium",
                confidence_score=0.6,
            )
        )
        repo.replace_symbols(
            path,
            [
                SymbolInfo(
                    path=path,
                    symbol_type="function",
                    name=f"{key_points.replace(' ', '_')}_{idx}",
                    signature="int handler(Context*)",
                    line_start=idx,
                    line_end=idx + 1,
                    summary=summary,
                    observed_behavior=summary,
                    side_effects=side_effects,
                    confidence="medium",
                )
                for idx in range(symbol_count)
            ],
        )

    results = search_project_index(db_path, "押镖车 位置 同步 停止 异常", limit=5)

    assert results[0]["path"] == "src/rtb_proc/escort_car/rtb_proc_escort_car_move.cpp"
    assert "movement" in results[0]["ranking_reason"]


def test_second_route_sync_prefers_movement_logic_over_client_tcp_handlers(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()

    candidates = [
        (
            "src/task/tcp/process_undo_escort_car_vertigo_tcp_task.cpp",
            "escort car tcp status handler",
            "escort tcp status",
            "network_send",
            6,
        ),
        (
            "src/task/tcp/process_cli_query_second_route_tcp_task.cpp",
            "client second route query task",
            "query second route",
            "network_send",
            4,
        ),
        (
            "src/rtb_proc/escort_car/rtb_proc_escort_car_move.cpp",
            "escort car movement synchronizes second route jump points",
            "sync second route jump route movement",
            "state_write",
            2,
        ),
    ]
    for path, summary, key_points, side_effects, symbol_count in candidates:
        repo.upsert_file(ProjectFile(path, f"/tmp/{path}", "source", "cpp", 10, 1.0, f"hash-{path}"))
        repo.upsert_summary(
            FileSummary(
                path=path,
                summary=summary,
                responsibilities=summary,
                key_points=key_points,
                dependencies="escort, route, sync",
                risks="verify implementation",
                evidence=f"symbol scan; side effects: {side_effects}",
                inconsistencies="none",
                confidence="medium",
                confidence_score=0.6,
            )
        )
        repo.replace_symbols(
            path,
            [
                SymbolInfo(
                    path=path,
                    symbol_type="function",
                    name=f"{key_points.replace(' ', '_')}_{idx}",
                    signature="int handler(Context*)",
                    line_start=idx,
                    line_end=idx + 1,
                    summary=summary,
                    observed_behavior=summary,
                    side_effects=side_effects,
                    confidence="medium",
                )
                for idx in range(symbol_count)
            ],
        )

    sync_results = search_project_index(db_path, "押镖车 同步 二段路线 跳跃点", limit=5)
    client_results = search_project_index(db_path, "客户端 查询 二段路线", limit=5)

    assert sync_results[0]["path"] == "src/rtb_proc/escort_car/rtb_proc_escort_car_move.cpp"
    assert "client_route_query" not in sync_results[0]["ranking_reason"]
    assert not any(
        item["path"] == "src/task/tcp/process_undo_escort_car_vertigo_tcp_task.cpp"
        and "client_route_query" in item["ranking_reason"]
        for item in sync_results
    )
    assert client_results[0]["path"] == "src/task/tcp/process_cli_query_second_route_tcp_task.cpp"


def test_sport_status_change_terms_promote_movement_logic(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()

    candidates = [
        (
            "src/rtb_proc/escort_car/rtb_proc_escort_car.cpp",
            "escort car generic runtime handler",
            "escort car attach status",
            "state_write",
            6,
        ),
        (
            "src/rtb_proc/escort_car/rtb_proc_escort_car_move.cpp",
            "escort car movement updates sport_status and change reason logs",
            "sport_status chg_reason movement log",
            "state_write",
            2,
        ),
    ]
    for path, summary, key_points, side_effects, symbol_count in candidates:
        repo.upsert_file(ProjectFile(path, f"/tmp/{path}", "source", "cpp", 10, 1.0, f"hash-{path}"))
        repo.upsert_summary(
            FileSummary(
                path=path,
                summary=summary,
                responsibilities=summary,
                key_points=key_points,
                dependencies="escort, status",
                risks="verify implementation",
                evidence=f"symbol scan; side effects: {side_effects}",
                inconsistencies="none",
                confidence="medium",
                confidence_score=0.6,
            )
        )
        repo.replace_symbols(
            path,
            [
                SymbolInfo(
                    path=path,
                    symbol_type="function",
                    name=f"{key_points.replace(' ', '_')}_{idx}",
                    signature="int handler(Context*)",
                    line_start=idx,
                    line_end=idx + 1,
                    summary=summary,
                    observed_behavior=summary,
                    side_effects=side_effects,
                    confidence="medium",
                )
                for idx in range(symbol_count)
            ],
        )

    results = search_project_index(db_path, "押镖车 sport_status 变化 原因 日志", limit=5)

    assert results[0]["path"] == "src/rtb_proc/escort_car/rtb_proc_escort_car_move.cpp"
    assert "movement" in results[0]["ranking_reason"]


def test_search_project_index_ignores_symbols_for_deleted_files(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()
    repo.upsert_file(ProjectFile("src/deleted.cpp", "/tmp/src/deleted.cpp", "source", "cpp", 10, 1.0, "hash", "deleted"))
    repo.replace_symbols(
        "src/deleted.cpp",
        [
            SymbolInfo(
                path="src/deleted.cpp",
                symbol_type="function",
                name="recalc_deleted_route",
                signature="int recalc_deleted_route(Context*)",
                line_start=12,
                line_end=None,
                summary="Recalculates deleted route.",
                observed_behavior="route update",
                side_effects="state_write",
                confidence="medium",
            )
        ],
    )

    results = search_project_index(db_path, "recalc_deleted_route")

    assert results == []


def test_search_research_memory_returns_serializable_note_hits(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()
    note_id = repo.insert_research_note(
        ResearchNote(
            thread_id="thread-1",
            request_type="project_qa",
            question="押镖路线重算风险？",
            answer_summary="route recalculation history",
            related_paths='["src/route.cpp"]',
            open_questions="[]",
            project_root="/tmp/project",
            source_note_ids="[]",
            internal_memory_summary="Prior research found route recalculation risk.",
            user_answer_summary="历史调研认为路线重算有风险。",
            confidence="medium",
        )
    )

    hits = search_research_memory(db_path, "路线 risk", project_root="/tmp/project")

    assert hits[0]["id"] == note_id
    assert hits[0]["related_paths"] == ["src/route.cpp"]
    assert hits[0]["source"] == "research_note"


def test_search_project_memory_returns_serializable_active_hits(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()
    memory_id = repo.insert_project_memory(
        ProjectMemory(
            project_root="/tmp/project",
            memory_type="implementation_fact",
            subject="Escort movement implementation",
            summary="Escort car movement is implemented by move handlers.",
            evidence_refs='[{"path":"src/move.cpp","line_start":1,"line_end":20}]',
            related_paths='["src/move.cpp"]',
            source_note_ids="[7]",
            confidence="medium",
        )
    )
    repo.insert_project_memory(
        ProjectMemory(
            project_root="/tmp/project",
            memory_type="implementation_fact",
            subject="Stale escort movement implementation",
            summary="Old movement note.",
            related_paths='["src/old_move.cpp"]',
            status="stale",
        )
    )
    repo.insert_project_memory(
        ProjectMemory(
            project_root="/tmp/other-project",
            memory_type="implementation_fact",
            subject="Other escort movement implementation",
            summary="Other project move handlers.",
            related_paths='["src/other.cpp"]',
        )
    )

    hits = search_project_memory(db_path, "押镖 移动", project_root="/tmp/project")

    assert [hit["id"] for hit in hits] == [memory_id]
    assert hits[0]["source"] == "project_memory"
    assert hits[0]["related_paths"] == ["src/move.cpp"]
    assert hits[0]["source_note_ids"] == [7]
    assert hits[0]["evidence_refs"] == [{"path": "src/move.cpp", "line_start": 1, "line_end": 20}]


def test_vector_search_recalls_semantic_summary_and_refreshes_changed_source(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()
    first_id = upsert_embedding(
        db_path,
        source_type="file_summary",
        source_id="src/route.cpp",
        source_path="src/route.cpp",
        source_hash="hash-1",
        text="escort route recalculation risk",
    )
    second_id = upsert_embedding(
        db_path,
        source_type="file_summary",
        source_id="src/route.cpp",
        source_path="src/route.cpp",
        source_hash="hash-2",
        text="escort route recalculation risk changed",
    )

    hits = search_vector_index(db_path, "押镖路线风险")

    assert first_id == second_id
    assert hits[0]["source_path"] == "src/route.cpp"
    assert hits[0]["source_hash"] == "hash-2"
    assert hits[0]["vector_score"] > 0


def test_hybrid_search_keeps_exact_path_match_ahead_of_vector_only_match(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()
    repo.upsert_file(ProjectFile("src/exact.cpp", "/tmp/src/exact.cpp", "source", "cpp", 10, 1.0, "hash"))
    repo.upsert_summary(
        FileSummary(
            path="src/exact.cpp",
            summary="Small exact path file.",
            responsibilities="exact path",
            key_points="exact_symbol",
            dependencies="",
            risks="",
            evidence="symbol scan",
            inconsistencies="none",
            confidence="medium",
        )
    )
    upsert_embedding(
        db_path,
        source_type="file_summary",
        source_id="vector-only",
        source_path="src/vector_only.cpp",
        source_hash="hash-v",
        text="escort route risk semantic match",
    )

    hits = hybrid_search_project(db_path, "src/exact.cpp route risk")

    assert hits[0]["path"] == "src/exact.cpp"
    assert hits[0]["hybrid_score"] >= hits[-1]["hybrid_score"]


def test_build_context_includes_confidence_and_evidence():
    context = build_context(
        [
            {
                "path": "src/route.cpp",
                "summary": "Handles route.",
                "confidence": "medium",
                "evidence": "symbol scan; side effects: state_write",
                "inconsistencies": "side_effect_hidden",
            }
        ]
    )

    assert "src/route.cpp" in context
    assert "confidence=medium" in context
    assert "side_effect_hidden" in context
