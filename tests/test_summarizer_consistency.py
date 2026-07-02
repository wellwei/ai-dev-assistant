from src.indexer.consistency import detect_consistency_flags
from src.indexer.symbol_extractor import extract_symbols


def test_consistency_flags_query_name_with_mutation_as_hidden_side_effect():
    content = """
int query_resource(Context* ctx) {
    ctx->mutable_resource()->set_state(1);
    broadcast_resource(ctx);
    return 0;
}
"""
    symbols = extract_symbols("src/resource.cpp", content)

    flags = detect_consistency_flags("src/resource.cpp", content, symbols)

    assert any(flag.flag_type == "side_effect_hidden" for flag in flags)
    assert any(flag.subject == "query_resource" for flag in flags)


def test_consistency_flags_stale_comment_when_comment_claims_no_write_but_body_writes():
    content = """
// only query route, no state changes
int get_route(Context* ctx) {
    ctx->route = 42;
    return ctx->route;
}
"""
    symbols = extract_symbols("src/route.cpp", content)

    flags = detect_consistency_flags("src/route.cpp", content, symbols)

    assert any(flag.flag_type == "comment_mismatch" for flag in flags)

from src.indexer.models import ProjectFile
from src.indexer.summarizer import summarize_implementation


def test_summarize_implementation_prioritizes_behavior_and_reports_confidence():
    content = """
// query only
int query_resource(Context* ctx) {
    ctx->mutable_resource()->set_state(1);
    broadcast_resource(ctx);
    return 0;
}
"""
    project_file = ProjectFile(
        path="src/resource.cpp",
        abs_path="/tmp/project/src/resource.cpp",
        file_type="source",
        language="cpp",
        size_bytes=len(content),
        mtime=1.0,
        content_hash="hash",
    )
    symbols = extract_symbols(project_file.path, content)
    flags = detect_consistency_flags(project_file.path, content, symbols)

    summary = summarize_implementation(project_file, content, symbols, flags)

    assert "source" in summary.summary
    assert "query_resource" in summary.key_points
    assert "side effects" in summary.evidence
    assert "comment_mismatch" in summary.inconsistencies
    assert summary.confidence == "medium"
    assert "query_resource" in summary.evidence_spans
    assert summary.confidence_score < 0.7
    assert "consistency flags reduce trust" in summary.confidence_reasons
