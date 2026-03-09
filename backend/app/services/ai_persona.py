"""AI persona helpers for system-message composition (P1-H baseline)."""

from __future__ import annotations

import re
from typing import Any

from app.core.config import settings
from app.schemas.ai import JournalAnalysis

PERSONA_ID = "third_party_observer_v1"
PERSONA_CONTEXT_VERSION = "v1"
PERSONA_GUARDRAIL_VERSION = "v1"

_CONFLICT_KEYWORDS = (
    "吵架",
    "冷戰",
    "忽略",
    "被忽視",
    "生氣",
    "炸毛",
    "崩潰",
    "壓力",
    "衝突",
    "fight",
    "argument",
    "angry",
    "ignored",
)

_POSITIVE_KEYWORDS = (
    "感謝",
    "謝謝",
    "開心",
    "幸福",
    "欣賞",
    "被理解",
    "被支持",
    "喜悅",
    "love",
    "grateful",
    "appreciate",
)

_PERSONA_TEXT_FIELDS: tuple[str, ...] = (
    "mood_label",
    "emotional_needs",
    "advice_for_user",
    "action_for_user",
    "advice_for_partner",
    "action_for_partner",
)

_PERSONA_OUTPUT_RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "partner_identity_claim_zh",
        re.compile(r"我是你(?:的)?(?:男朋友|女朋友|伴侶|老公|老婆)", flags=re.IGNORECASE),
        "我是一位中立第三者觀察者",
    ),
    (
        "partner_identity_claim_en",
        re.compile(r"\bi\s*(?:am|'m)\s*your\s*(?:boyfriend|girlfriend|partner|husband|wife)\b", flags=re.IGNORECASE),
        "I am a neutral third-party observer",
    ),
    (
        "direct_love_phrase_zh",
        re.compile(r"(^|[。！？\n])\s*我愛你(?=[。！？，,\s\n]|$)", flags=re.IGNORECASE),
        r"\1看起來你的伴侶很在乎你",
    ),
    (
        "direct_love_phrase_en",
        re.compile(r"(^|[.!?\n])\s*i\s*love\s*you(?=[.!?,\s\n]|$)", flags=re.IGNORECASE),
        r"\1It looks like your partner deeply cares about you",
    ),
)


def infer_relationship_weather(content: str) -> str:
    text = (content or "").strip().lower()
    if not text:
        return "neutral"

    conflict_score = sum(1 for keyword in _CONFLICT_KEYWORDS if keyword in text)
    positive_score = sum(1 for keyword in _POSITIVE_KEYWORDS if keyword in text)

    if conflict_score <= 0 and positive_score <= 0:
        return "neutral"
    if conflict_score >= positive_score:
        return "conflict"
    return "repair"


def _normalize_weather_hint(weather_hint: str | None) -> str:
    normalized = (weather_hint or "").strip().lower()
    if normalized in {"conflict", "repair", "neutral"}:
        return normalized
    return "neutral"


def resolve_relationship_weather(
    *,
    content: str,
    relationship_weather_hint: str | None = None,
) -> str:
    current_weather = infer_relationship_weather(content)
    if current_weather in {"conflict", "repair"}:
        return current_weather

    hint_weather = _normalize_weather_hint(relationship_weather_hint)
    if hint_weather in {"conflict", "repair"}:
        return hint_weather
    return current_weather


def build_dynamic_context_injection(
    content: str,
    *,
    relationship_weather_hint: str | None = None,
) -> str:
    weather = resolve_relationship_weather(
        content=content,
        relationship_weather_hint=relationship_weather_hint,
    )
    if weather == "neutral":
        return ""
    if weather == "conflict":
        guidance = (
            "保持第三者觀察者語氣，先描述情緒與需求，再給低刺激、低命令的微行動建議。"
            "避免站隊與指責；若有升高風險，優先安全政策。"
        )
    else:
        guidance = (
            "保持第三者觀察者語氣，強化正向情緒見證與具體感謝行動，"
            "延長雙方的正向互動半衰期。"
        )

    return (
        f"[DYNAMIC_CONTEXT::{PERSONA_CONTEXT_VERSION}]\n"
        f"persona_id: {PERSONA_ID}\n"
        f"relationship_weather: {weather}\n"
        f"guidance: {guidance}"
    )


def build_analysis_messages(
    *,
    content: str,
    base_prompt: str,
    relationship_weather_hint: str | None = None,
    relationship_mode: str | None = None,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [{"role": "system", "content": base_prompt}]

    normalized_mode = (relationship_mode or "").strip().lower()
    if normalized_mode == "solo":
        messages.append(
            {
                "role": "system",
                "content": (
                    "[LIFECYCLE::solo_mode]\n"
                    "User is currently in solo mode. "
                    "Do not assume current partner context; provide individual-focused coaching."
                ),
            }
        )

    if settings.AI_DYNAMIC_CONTEXT_INJECTION_ENABLED:
        context = build_dynamic_context_injection(
            content,
            relationship_weather_hint=relationship_weather_hint,
        )
        if context:
            messages.append({"role": "system", "content": context})

    messages.append({"role": "user", "content": content})
    return messages


def apply_persona_output_guardrails(
    analysis: JournalAnalysis,
) -> tuple[JournalAnalysis, dict[str, Any]]:
    payload = analysis.model_dump()
    hit_fields: set[str] = set()
    hit_rules: set[str] = set()

    for field in _PERSONA_TEXT_FIELDS:
        original_text = str(payload.get(field) or "")
        sanitized_text = original_text
        for rule_id, pattern, replacement in _PERSONA_OUTPUT_RULES:
            if pattern.search(sanitized_text):
                hit_fields.add(field)
                hit_rules.add(rule_id)
                sanitized_text = pattern.sub(replacement, sanitized_text)

        if sanitized_text != original_text:
            payload[field] = sanitized_text

    if not hit_fields:
        return analysis, {
            "adjusted": False,
            "version": PERSONA_GUARDRAIL_VERSION,
            "rule_ids": [],
            "fields": [],
        }

    sanitized = JournalAnalysis.model_validate(payload)
    return sanitized, {
        "adjusted": True,
        "version": PERSONA_GUARDRAIL_VERSION,
        "rule_ids": sorted(hit_rules),
        "fields": sorted(hit_fields),
    }
