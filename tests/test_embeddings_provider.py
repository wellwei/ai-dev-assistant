from src.embeddings.provider import tokenize


def test_tokenize_expands_gameplay_movement_terms():
    tokens = tokenize("移动位置同步")

    assert "move" in tokens or "movement" in tokens
    assert "position" in tokens
    assert "sync" in tokens


def test_tokenize_expands_combat_damage_charge_mount_terms():
    tokens = tokenize("战斗伤害冲锋坐骑")

    assert "battle" in tokens or "combat" in tokens
    assert "damage" in tokens
    assert "charge" in tokens
    assert "mount" in tokens
