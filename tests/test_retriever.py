from src.indexer.models import FileSummary, ProjectFile, SymbolInfo
from src.retriever.context_builder import build_context
from src.retriever.keyword_search import search_project_index
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
