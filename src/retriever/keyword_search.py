from pathlib import Path
import re

from src.storage.sqlite import connect_db, init_schema


def _tokens(query: str) -> list[str]:
    raw_tokens = [token.lower() for token in re.findall(r"[\w一-鿿]+", query) if token.strip()]
    expanded = list(raw_tokens)
    synonym_map = {
        "路线": ["route"],
        "移动": ["move", "movement"],
        "位移": ["move", "movement", "position"],
        "跟随": ["follow"],
        "重算": ["recalc", "recalculation"],
        "押镖": ["escort"],
        "地图": ["map"],
        "位置": ["position", "pos", "curr_pos", "location"],
        "坐标": ["position", "pos", "curr_pos", "coord", "coordinate"],
        "同步": ["sync", "synchronize"],
        "停止": ["stop"],
        "异常": ["outside", "status"],
        "跳跃": ["jump", "skip"],
        "超时": ["timeout"],
        "迁移": ["migration"],
        "离线": ["offline"],
        "死亡": ["dead"],
        "战斗": ["battle", "combat", "fight"],
        "伤害": ["damage", "hurt", "hp", "attack"],
        "扣血": ["damage", "hp"],
        "冲锋": ["charge", "dash", "rush"],
        "命中": ["hit", "target"],
        "坐骑": ["mount", "mounting", "rider", "horse"],
        "上马": ["mount", "mounting"],
        "下马": ["dismount"],
        "速度": ["speed"],
        "距离": ["distance"],
        "半径": ["radius"],
        "变化": ["change", "chg", "update"],
        "原因": ["reason"],
        "日志": ["log"],
        "资源": ["resource"],
    }
    for token in raw_tokens:
        for key, synonyms in synonym_map.items():
            if key in token:
                expanded.extend(synonyms)
    return expanded


def _is_ascii_token(token: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9_]+", token))


def _split_ascii_identifier(part: str) -> list[str]:
    pieces: list[str] = []
    for snake_piece in part.split("_"):
        if not snake_piece:
            continue
        pieces.append(snake_piece.lower())
        camel_pieces = re.findall(r"[A-Z]+(?=[A-Z][a-z]|[0-9]|$)|[A-Z]?[a-z]+|[0-9]+", snake_piece)
        pieces.extend(piece.lower() for piece in camel_pieces if piece)
    return pieces


def _text_terms(text: str) -> list[str]:
    raw = [part for part in re.split(r"[^0-9a-zA-Z_一-鿿]+", text) if part]
    terms: list[str] = []
    for part in raw:
        lowered = part.lower()
        terms.append(lowered)
        if re.search(r"[A-Za-z0-9_]", part):
            terms.extend(_split_ascii_identifier(part))
    return terms


def _count_token(text: str, token: str) -> int:
    lowered_token = token.lower()
    if not lowered_token:
        return 0
    if _is_ascii_token(lowered_token):
        return sum(1 for term in _text_terms(text) if term == lowered_token)
    return text.lower().count(lowered_token)


def _score(row: dict, tokens: list[str]) -> int:
    haystack = " ".join(str(row.get(key) or "") for key in row)
    return sum(_count_token(haystack, token) for token in tokens)


def _field_score(text: str, tokens: list[str], weight: float, cap: int = 3) -> float:
    return sum(min(_count_token(text, token), cap) * weight for token in tokens)


def _weighted_text_score(item: dict, tokens: list[str]) -> float:
    fields = [
        ("path", 4.0),
        ("key_points", 3.5),
        ("summary", 2.0),
        ("responsibilities", 2.0),
        ("evidence", 2.5),
        ("dependencies", 1.0),
        ("risks", 1.0),
        ("inconsistencies", 1.0),
    ]
    return sum(_field_score(str(item.get(field) or ""), tokens, weight) for field, weight in fields)


def _path_token_boost(path: str, tokens: list[str]) -> tuple[float, list[str]]:
    path_terms = set(_text_terms(path))
    matched = {
        token
        for token in tokens
        if len(token) >= 3 and ((_is_ascii_token(token) and token in path_terms) or (not _is_ascii_token(token) and token in path.lower()))
    }
    if not matched:
        return 0.0, []
    return min(len(matched) * 28.0, 70.0), [f"path token match: {', '.join(sorted(matched))}"]


_GAMEPLAY_INTENT_TERMS = {
    "movement": [
        "移动",
        "位移",
        "move",
        "movement",
        "follow",
        "跟随",
        "位置",
        "坐标",
        "position",
        "pos",
        "location",
        "coord",
        "coordinate",
        "同步",
        "sync",
        "synchronize",
        "变化",
        "change",
        "chg",
        "update",
        "sport_status",
        "stop",
    ],
    "combat": ["战斗", "battle", "combat", "fight"],
    "damage": ["伤害", "扣血", "damage", "hurt", "hp", "attack"],
    "charge": ["冲锋", "charge", "dash", "rush"],
    "mount": ["坐骑", "上马", "下马", "mount", "mounting", "dismount", "rider", "horse"],
}

_GAMEPLAY_PATH_TERMS = {
    "movement": {"move", "movement", "position", "pos", "sync", "location", "coord", "character", "role"},
    "combat": {"battle", "combat", "fight", "attack"},
    "damage": {"damage", "hurt", "hp", "attack", "battle"},
    "charge": {"charge", "dash", "rush", "skill"},
    "mount": {"mount", "mounting", "dismount", "horse", "rider"},
}


def _query_has_term(query: str, term: str) -> bool:
    lowered = query.lower()
    if _is_ascii_token(term):
        return term in set(_text_terms(query))
    return term in lowered


def _gameplay_domain_intents(query: str) -> set[str]:
    lowered = query.lower()
    intents: set[str] = set()
    has_escort_context = any(word in lowered for word in ["押镖", "镖车", "escort"])
    escort_movement_state_terms = [
        "停止",
        "异常",
        "跳跃",
        "超时",
        "迁移",
        "离线",
        "死亡",
        "速度",
        "距离",
        "半径",
        "原因",
        "日志",
        "timeout",
        "migration",
        "offline",
        "dead",
        "speed",
        "distance",
        "radius",
        "jump",
        "skip",
    ]

    for intent, terms in _GAMEPLAY_INTENT_TERMS.items():
        if any(_query_has_term(query, term) for term in terms):
            intents.add(intent)
    if has_escort_context and any(_query_has_term(query, term) for term in escort_movement_state_terms):
        intents.add("movement")
    if any(_query_has_term(query, term) for term in ["海路", "地图", "map", "sea_route", "sea", "route"]):
        if "sea route" in lowered or "sea_route" in lowered or "海路" in lowered:
            intents.add("sea_route")
        elif any(_query_has_term(query, term) for term in ["地图", "map"]):
            intents.add("sea_route")
    if any(_query_has_term(query, term) for term in ["重算", "recalc", "recalculation", "cost", "耗时"]):
        intents.add("route_recalc")
    if any(_query_has_term(query, term) for term in ["客户端", "查询", "query", "client"]):
        intents.add("client_route_query")
    if "second route" in lowered:
        intents.add("client_route_query")
    if any(_query_has_term(query, term) for term in ["押镖", "escort"]):
        intents.add("escort")
    return intents


def _escort_domain_intents(query: str) -> set[str]:
    return _gameplay_domain_intents(query)


def _gameplay_domain_boost(path: str, query: str) -> tuple[float, list[str]]:
    intents = _gameplay_domain_intents(query)
    if not intents:
        return 0.0, []
    lowered_path = path.lower()
    has_escort_context = any(word in query.lower() for word in ["押镖", "镖车", "escort"])
    path_terms = set(_text_terms(path))
    boost = 0.0
    reasons: list[str] = []
    matched: list[str] = []

    for intent in ["movement", "combat", "damage", "charge", "mount"]:
        if intent in intents and path_terms.intersection(_GAMEPLAY_PATH_TERMS[intent]):
            boost += 58.0
            matched.append(intent)
    if "movement" in intents and any(part in lowered_path for part in ["process_sync_rs_task", "process_cli_role_move_tcp_task"]):
        boost += 28.0
        if "movement" not in matched:
            matched.append("movement")
    if "damage" in intents and "effect_calculate_process" in lowered_path:
        boost += 16.0
        if "damage" not in matched:
            matched.append("damage")
    if "damage" in intents and "send_escort_battle_notify" in lowered_path:
        boost += 18.0
        if "damage" not in matched:
            matched.append("damage")
    if "mount" in intents and "process_cli_summoning_mount" in lowered_path:
        boost += 18.0
        if "mount" not in matched:
            matched.append("mount")
    if "movement" in intents and any(part in lowered_path for part in ["escort_car_move", "/move/", "follow_escort_car_move"]):
        boost += 22.0
        if "movement" not in matched:
            matched.append("movement")
    if "movement" in intents and has_escort_context and "rtb_proc_escort_car_move" in lowered_path:
        boost += 8.0
        if "movement" not in matched:
            matched.append("movement")
    if "sea_route" in intents and any(part in lowered_path for part in ["sea_route", "map_data"]):
        boost += 70.0
        matched.append("sea_route")
    if "route_recalc" in intents and any(part in lowered_path for part in ["recalc_rout", "recalc_route", "cal_cross_map_route_cost"]):
        boost += 58.0
        matched.append("route_recalc")
    if "client_route_query" in intents and any(part in lowered_path for part in ["process_cli_query_second_route", "/tcp/"]):
        boost += 62.0
        matched.append("client_route_query")
    if "escort" in intents and "/escort_car/" in lowered_path:
        boost += 18.0
        matched.append("escort_car")

    if matched:
        reasons.append(f"gameplay domain intent: {', '.join(sorted(set(matched)))}")
    return boost, reasons


def _escort_domain_boost(path: str, query: str) -> tuple[float, list[str]]:
    return _gameplay_domain_boost(path, query)


def _implementation_boost(item: dict, tokens: list[str], symbols: list[dict], query: str) -> tuple[float, list[str]]:
    path = str(item.get("path") or "")
    file_type = str(item.get("file_type") or "")
    language = str(item.get("language") or "")
    evidence = str(item.get("evidence") or "")
    confidence = str(item.get("confidence") or "")
    boost = 0.0
    reasons: list[str] = []
    is_source_path = path.startswith("src/") or "/src/" in path
    is_cpp_like = language in {"cpp", "c", "hpp", "h", "cc", "cxx"}
    is_implementation = (is_source_path and is_cpp_like) or file_type == "source"
    path_boost, path_reasons = _path_token_boost(path, tokens)

    if is_source_path and is_cpp_like:
        boost += 30.0
        reasons.append("source implementation path")
    elif is_source_path:
        boost += 12.0
        reasons.append("source path")

    if file_type == "source":
        boost += 12.0
        reasons.append("source file type")
    if is_cpp_like:
        boost += 8.0
        reasons.append("implementation language")

    if is_implementation and any(
        marker in evidence for marker in ["side effects", "state_write", "network_send", "db_write", "redis_write"]
    ):
        boost += 14.0
        reasons.append("implementation side-effect evidence")
    if symbols:
        boost += 8.0
        reasons.append("matched implementation symbols")
        if any(symbol.get("side_effects") for symbol in symbols):
            boost += 8.0
            reasons.append("symbol side-effect evidence")

    if confidence == "medium":
        boost += 4.0
    elif confidence == "low":
        boost -= 4.0

    boost += path_boost
    reasons.extend(path_reasons)
    domain_boost, domain_reasons = _gameplay_domain_boost(path, query)
    boost += domain_boost
    reasons.extend(domain_reasons)

    if is_implementation and any(part in path.lower() for part in ["/db/", "db_", "config"]):
        boost -= 24.0
        reasons.append("generic db/config implementation penalty")

    if path == "CMakeLists.txt" or file_type == "build" or language == "cmake":
        boost -= 25.0
        reasons.append("build/config penalty")
    if path.startswith("linux_prj/") or file_type == "config" or language in {"ini", "sh"}:
        boost -= 14.0
        reasons.append("runtime/config penalty")
    if path.endswith(".AFCfile"):
        boost -= 18.0
        reasons.append("AFC/config penalty")
    if file_type == "doc":
        boost -= 6.0
        reasons.append("documentation penalty")

    return boost, reasons


def _rank_item(item: dict, tokens: list[str], query: str, symbols: list[dict] | None = None) -> None:
    matched_symbols = symbols or []
    symbol_score = min(sum(_weighted_text_score(symbol, tokens) for symbol in matched_symbols), 80.0)
    boost, reasons = _implementation_boost(item, tokens, matched_symbols, query)
    item["raw_keyword_score"] = _score(item, tokens)
    item["score"] = round(_weighted_text_score(item, tokens) + symbol_score + boost, 4)
    item["ranking_reason"] = "; ".join(reasons) if reasons else "keyword match"


def search_project_index(
    db_path: str | Path,
    query: str,
    limit: int = 8,
    *,
    initialize_schema: bool = True,
) -> list[dict]:
    tokens = _tokens(query)
    if not tokens:
        return []

    with connect_db(db_path) as conn:
        if initialize_schema:
            init_schema(conn)
        rows = conn.execute(
            """
            SELECT
                f.path,
                f.file_type,
                f.language,
                f.content_hash AS file_content_hash,
                s.summary,
                s.responsibilities,
                s.key_points,
                s.dependencies,
                s.risks,
                s.evidence,
                s.inconsistencies,
                s.confidence,
                s.content_hash,
                s.index_run_id,
                s.indexer_version,
                s.evidence_spans,
                s.confidence_score,
                s.confidence_reasons
            FROM files f
            LEFT JOIN file_summaries s ON s.path = f.path
            WHERE f.status = 'active'
            """
        ).fetchall()

        results: list[dict] = []
        for row in rows:
            item = dict(row)
            if _score(item, tokens) > 0:
                results.append(item)

        symbol_rows = conn.execute(
            """
            SELECT
                sym.path,
                sym.name,
                sym.summary,
                sym.observed_behavior,
                sym.side_effects,
                sym.confidence,
                sym.content_hash,
                sym.index_run_id,
                sym.indexer_version,
                sym.body_hash,
                sym.evidence_preview,
                f.file_type,
                f.language
            FROM symbols sym
            JOIN files f ON f.path = sym.path
            WHERE f.status = 'active'
            """
        ).fetchall()
        symbol_by_path: dict[str, list[dict]] = {}
        for row in symbol_rows:
            item = dict(row)
            score = _score(item, tokens)
            if score > 0:
                symbol_by_path.setdefault(item["path"], []).append(item)

    by_path = {item["path"]: item for item in results}
    for path, symbols in symbol_by_path.items():
        if path not in by_path:
            by_path[path] = {
                "path": path,
                "file_type": "unknown",
                "language": "unknown",
                "summary": "Matched by symbol table.",
                "responsibilities": "",
                "key_points": ", ".join(symbol["name"] for symbol in symbols),
                "dependencies": "",
                "risks": "Verify implementation before editing.",
                "evidence": "symbol match",
                "inconsistencies": "",
                "confidence": "low",
            }
        by_path[path]["matched_symbols"] = symbols

    for item in by_path.values():
        _rank_item(item, tokens, query, item.get("matched_symbols") or [])

    ranked = [item for item in by_path.values() if item["score"] > 0]
    return sorted(ranked, key=lambda item: item["score"], reverse=True)[:limit]
