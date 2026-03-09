import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

TIER3_KEYS = {"self_harm_instructions", "violence_graphic", "sexual_minors", "illicit_violent"}
TIER2_KEYS = {"self_harm", "self_harm_intent", "violence", "harassment_threatening", "hate_threatening"}


@dataclass(slots=True)
class ModerationSignal:
    safety_tier: int
    flagged: bool
    categories: dict[str, bool]
    category_scores: dict[str, float]
    model: str | None = None


def merge_safety_tier(base_tier: int, moderation_signal: ModerationSignal | None) -> int:
    if not moderation_signal:
        return base_tier
    return max(base_tier, moderation_signal.safety_tier)


def derive_safety_tier_from_moderation(
    flagged: bool,
    categories: dict[str, bool],
    category_scores: dict[str, float],
) -> int:
    tier3_score = max_category_score(category_scores, *TIER3_KEYS)
    tier2_score = max_category_score(category_scores, *TIER2_KEYS)
    any_score = max(category_scores.values(), default=0.0)

    if any(categories.get(key, False) for key in TIER3_KEYS) or tier3_score >= 0.70:
        return 3
    if any(categories.get(key, False) for key in TIER2_KEYS) or tier2_score >= 0.35:
        return 2
    if flagged or any_score >= 0.20:
        return 1
    return 0


def max_category_score(scores: dict[str, float], *keys: str) -> float:
    return max((scores.get(key, 0.0) for key in keys), default=0.0)


def normalize_category_bools(raw_categories: Any) -> dict[str, bool]:
    raw_dict = to_dict(raw_categories)
    normalized: dict[str, bool] = {}
    for key, value in raw_dict.items():
        normalized[normalize_category_key(str(key))] = bool(value)
    return normalized


def normalize_category_scores(raw_scores: Any) -> dict[str, float]:
    raw_dict = to_dict(raw_scores)
    normalized: dict[str, float] = {}
    for key, value in raw_dict.items():
        try:
            normalized[normalize_category_key(str(key))] = float(value)
        except (TypeError, ValueError):
            continue
    return normalized


def to_dict(payload: Any) -> dict[str, Any]:
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return payload
    if hasattr(payload, "model_dump"):
        dumped = payload.model_dump()
        if isinstance(dumped, dict):
            return dumped

    # openai typed objects expose fields as attributes; this fallback keeps us resilient.
    result: dict[str, Any] = {}
    for key in dir(payload):
        if key.startswith("_"):
            continue
        try:
            value = getattr(payload, key)
        except Exception:
            logger.debug("to_dict: skipped inaccessible attribute")
            continue
        if callable(value):
            continue
        result[key] = value
    return result


def normalize_category_key(key: str) -> str:
    return key.strip().lower().replace("/", "_").replace("-", "_").replace(" ", "_")
