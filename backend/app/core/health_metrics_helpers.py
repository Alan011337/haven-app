from __future__ import annotations

import re


def safe_numeric(value: object) -> float | int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    return None


def safe_queue_depth(value: object) -> int:
    numeric = safe_numeric(value)
    if numeric is not None:
        return max(0, int(numeric))
    if isinstance(value, dict):
        total = 0
        for sub_value in value.values():
            sub_numeric = safe_numeric(sub_value)
            if sub_numeric is None:
                continue
            total += max(0, int(sub_numeric))
        return max(0, total)
    return 0


def metric_name(prefix: str, raw_key: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_]", "_", str(raw_key)).strip("_").lower()
    if not normalized:
        normalized = "value"
    return f"{prefix}_{normalized}"


def append_counter_metrics(lines: list[str], *, prefix: str, counters: dict[str, object]) -> None:
    for key in sorted(counters.keys()):
        numeric = safe_numeric(counters.get(key))
        if numeric is None:
            continue
        lines.append(f"{metric_name(prefix, key)} {numeric}")

