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


def resolve_effective_depth_cap(
    answered_count: int,
    preferred_depth: int | None = None,
) -> int:
    """Return the starting depth cap, honouring an optional user preference.

    When *preferred_depth* is provided (1-3), it is used directly (clamped).
    Otherwise the progressive policy decides based on *answered_count*.
    """
    if preferred_depth is not None:
        return max(1, min(3, int(preferred_depth)))
    return resolve_depth_cap(answered_count)


def iter_depth_caps(start_cap: int) -> tuple[int, ...]:
    normalized = max(1, min(3, int(start_cap)))
    return tuple(range(normalized, 4))
