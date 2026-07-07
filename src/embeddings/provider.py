import hashlib
import math
import re

DIMS = 16
MODEL_NAME = "local-hash-embedding-v2"

_SYNONYMS = {
    "路线": ["route"],
    "重算": ["recalc", "recalculation"],
    "押镖": ["escort"],
    "风险": ["risk"],
    "移动": ["move", "movement"],
    "位移": ["move", "movement", "position"],
    "位置": ["position", "pos", "location"],
    "坐标": ["position", "pos", "coord", "coordinate"],
    "同步": ["sync", "synchronize"],
    "变化": ["change", "update"],
    "战斗": ["battle", "combat", "fight"],
    "伤害": ["damage", "hurt", "hp", "attack"],
    "扣血": ["damage", "hp"],
    "冲锋": ["charge", "dash", "rush"],
    "坐骑": ["mount", "mounting", "rider", "horse"],
    "上马": ["mount", "mounting"],
    "下马": ["dismount"],
}


def tokenize(text: str) -> list[str]:
    raw = [token.lower() for token in re.findall(r"[\w一-鿿]+", text) if token.strip()]
    expanded = list(raw)
    for token in raw:
        for key, values in _SYNONYMS.items():
            if key in token:
                expanded.extend(values)
    return expanded


def embed_text(text: str) -> list[float]:
    vector = [0.0] * DIMS
    for token in tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = digest[0] % DIMS
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector))
    if not norm:
        return vector
    return [value / norm for value in vector]


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))
