from src.indexer.symbol_extractor import detect_side_effects, extract_symbols


CPP_CONTENT = """
#define ROUTE_FLAG 1

struct route_ctx_t {
    int state;
};

class route_manager {
public:
    int query_route(route_ctx_t* ctx);
};

int query_route(route_ctx_t* ctx) {
    ctx->state = 1;
    send_packet(ctx);
    return ctx->state;
}
"""


def test_extract_symbols_finds_macros_structs_classes_and_functions():
    symbols = extract_symbols("src/route.cpp", CPP_CONTENT)
    names = {(s.symbol_type, s.name) for s in symbols}

    assert ("macro", "ROUTE_FLAG") in names
    assert ("struct", "route_ctx_t") in names
    assert ("class", "route_manager") in names
    assert ("function", "query_route") in names

    query = next(s for s in symbols if s.name == "query_route" and s.symbol_type == "function")
    assert query.line_start > 0
    assert query.line_end == 17
    assert "query_route" in query.signature
    assert "state_write" in query.side_effects
    assert "network_send" in query.side_effects
    assert query.body_hash
    assert "ctx->state = 1" in query.evidence_preview
    assert len(query.evidence_preview) <= 400


def test_detect_side_effects_reports_state_and_network_writes():
    side_effects = detect_side_effects(CPP_CONTENT)
    assert "state_write" in side_effects
    assert "network_send" in side_effects
