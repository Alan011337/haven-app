from __future__ import annotations


def resolve_depth_cap(answered_count: int) -> int:
    """
    Progressive depth policy:
    - 0~2 answered cards: only depth <= 1
    - 3~11 answered cards: depth <= 2
    - 12+ answered cards: depth <= 3
    """
    if answered_count < 3:
        return 1
    if answered_count < 12:
        return 2
    return 3


def iter_depth_caps(start_cap: int) -> tuple[int, ...]:
    normalized = max(1, min(3, int(start_cap)))
    return tuple(range(normalized, 4))
