# P2-E [AUTO-CONTENT]: Dynamic Content Injection — weekly 時事卡片 pipeline.

from __future__ import annotations

import asyncio
import json
import logging
from threading import Lock
from time import time
from typing import Any

from sqlmodel import Session, select

from app.core.config import settings
from app.core.log_redaction import redact_exception_reason
from app.core.settings_domains import get_dynamic_content_settings
from app.models.card import Card, CardCategory, CardDeck
from app.services.abuse_state_store_factory import create_abuse_state_store
from app.services.dynamic_content_runtime_metrics import dynamic_content_runtime_metrics
from app.services.retry_backoff import compute_exponential_backoff_seconds

logger = logging.getLogger(__name__)

TRENDING_DECK_NAME = "時事"
CARDS_PER_WEEK = 5

_COOLDOWN_LOCK = Lock()
_COOLDOWN_UNTIL_TS = 0.0
_COOLDOWN_STORE_DEGRADED = False
_COOLDOWN_STORE_RETRY_AT_TS = 0.0
_DEGRADED_MODE_UNTIL_TS = 0.0
_OPENAI_CLIENT: Any | None = None
_OPENAI_CLIENT_INIT_RETRY_AT_TS = 0.0
_COOLDOWN_STORE_KEY = "dynamic_content_pipeline:cooldown"
_DEGRADED_MODE_STORE_KEY = "dynamic_content_pipeline:degraded_mode"
_COOLDOWN_STORE = create_abuse_state_store(scope="dynamic-content-cooldown")

_STORE_ERROR_TIMEOUT = "timeout"
_STORE_ERROR_CONNECTION = "connection_error"
_STORE_ERROR_PAYLOAD = "payload_error"
_STORE_ERROR_RUNTIME = "runtime_error"
_STORE_ERROR_UNKNOWN = "unknown_error"


def _classify_store_exception(exc: Exception) -> str:
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return _STORE_ERROR_TIMEOUT
    if isinstance(exc, (ConnectionError, OSError)):
        return _STORE_ERROR_CONNECTION
    if isinstance(exc, (TypeError, ValueError)):
        return _STORE_ERROR_PAYLOAD
    if isinstance(exc, RuntimeError):
        return _STORE_ERROR_RUNTIME
    return _STORE_ERROR_UNKNOWN


def _record_store_exception(metric_prefix: str, exc: Exception) -> None:
    reason = _classify_store_exception(exc)
    dynamic_content_runtime_metrics.increment(f"{metric_prefix}_total")
    dynamic_content_runtime_metrics.increment(f"{metric_prefix}_{reason}_total")
    logger.warning(
        "Dynamic content store operation failed: metric=%s reason=%s detail=%s",
        metric_prefix,
        reason,
        redact_exception_reason(exc),
    )

def _runtime_settings():
    return get_dynamic_content_settings()


def _is_cooldown_active() -> bool:
    return _resolve_cooldown_until_ts() > time()


def _cooldown_remaining_seconds() -> int:
    remaining = _resolve_cooldown_until_ts() - time()
    return max(0, int(remaining))


def _cooldown_store_retry_seconds() -> float:
    return _runtime_settings().cooldown_store_retry_seconds


def _degraded_mode_threshold() -> float:
    return _runtime_settings().degraded_fallback_ratio_threshold


def _degraded_mode_min_attempts() -> int:
    return _runtime_settings().degraded_min_attempts


def _degraded_mode_duration_seconds() -> float:
    return _runtime_settings().degraded_duration_seconds


def _degraded_mode_recovery_threshold() -> float:
    return _runtime_settings().degraded_recovery_fallback_ratio_threshold


def _degraded_mode_recovery_min_attempts() -> int:
    return _runtime_settings().degraded_recovery_min_attempts


def _degraded_mode_extension_seconds() -> float:
    return _runtime_settings().degraded_extension_seconds


def _provider_init_retry_seconds() -> float:
    return _runtime_settings().provider_init_retry_seconds


def _provider_init_retry_remaining_seconds() -> int:
    remaining = _OPENAI_CLIENT_INIT_RETRY_AT_TS - time()
    return max(0, int(remaining))


def _get_openai_client() -> Any | None:
    global _OPENAI_CLIENT, _OPENAI_CLIENT_INIT_RETRY_AT_TS

    if _OPENAI_CLIENT is not None:
        return _OPENAI_CLIENT

    if _OPENAI_CLIENT_INIT_RETRY_AT_TS > time():
        dynamic_content_runtime_metrics.increment(
            "dynamic_content_provider_init_skipped_retry_window_total"
        )
        return None

    try:
        from openai import AsyncOpenAI

        _OPENAI_CLIENT = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        _OPENAI_CLIENT_INIT_RETRY_AT_TS = 0.0
        return _OPENAI_CLIENT
    except (ImportError, OSError, RuntimeError, ValueError, TypeError) as exc:
        _OPENAI_CLIENT = None
        _OPENAI_CLIENT_INIT_RETRY_AT_TS = time() + _provider_init_retry_seconds()
        logger.warning("OpenAI client unavailable: reason=%s", redact_exception_reason(exc))
        dynamic_content_runtime_metrics.increment("dynamic_content_provider_init_error_total")
        return None


def _degraded_mode_fallback_ratio() -> float:
    counters = dynamic_content_runtime_metrics.snapshot()
    attempts = int(counters.get("dynamic_content_generation_attempt_total", 0) or 0)
    if attempts <= 0:
        return 0.0
    fallback_total = 0
    for key, value in counters.items():
        if str(key).startswith("dynamic_content_fallback_"):
            if str(key) == "dynamic_content_fallback_degraded_mode_total":
                # Exclude degraded-mode self-fallback to prevent lock-in feedback loops.
                continue
            fallback_total += max(0, int(value or 0))
    return min(1.0, max(0.0, fallback_total / attempts))


def _degraded_mode_can_recover() -> bool:
    counters = dynamic_content_runtime_metrics.snapshot()
    attempts = int(counters.get("dynamic_content_generation_attempt_total", 0) or 0)
    if attempts < _degraded_mode_recovery_min_attempts():
        return False
    return _degraded_mode_fallback_ratio() <= _degraded_mode_recovery_threshold()


def _is_degraded_mode_active() -> bool:
    global _DEGRADED_MODE_UNTIL_TS
    now_ts = time()
    effective_until_ts = _resolve_degraded_until_ts()
    with _COOLDOWN_LOCK:
        _DEGRADED_MODE_UNTIL_TS = max(_DEGRADED_MODE_UNTIL_TS, effective_until_ts)
        if _DEGRADED_MODE_UNTIL_TS > now_ts:
            return True
        if _DEGRADED_MODE_UNTIL_TS > 0:
            if _degraded_mode_can_recover():
                _DEGRADED_MODE_UNTIL_TS = 0.0
                _write_degraded_until_to_store(0.0)
                dynamic_content_runtime_metrics.increment(
                    "dynamic_content_degraded_mode_recovered_total"
                )
            else:
                _DEGRADED_MODE_UNTIL_TS = now_ts + _degraded_mode_extension_seconds()
                _write_degraded_until_to_store(_DEGRADED_MODE_UNTIL_TS)
                dynamic_content_runtime_metrics.increment(
                    "dynamic_content_degraded_mode_extended_total"
                )
                return True
        return False


def _degraded_mode_remaining_seconds() -> int:
    with _COOLDOWN_LOCK:
        remaining = _DEGRADED_MODE_UNTIL_TS - time()
    return max(0, int(remaining))


def _activate_degraded_mode(*, reason: str, fallback_ratio: float) -> None:
    global _DEGRADED_MODE_UNTIL_TS
    with _COOLDOWN_LOCK:
        _DEGRADED_MODE_UNTIL_TS = max(
            _DEGRADED_MODE_UNTIL_TS,
            time() + _degraded_mode_duration_seconds(),
        )
        _write_degraded_until_to_store(_DEGRADED_MODE_UNTIL_TS)
    dynamic_content_runtime_metrics.increment("dynamic_content_degraded_mode_activated_total")
    logger.warning(
        "Dynamic content degraded mode activated: reason=%s fallback_ratio=%.3f threshold=%.3f min_attempts=%s",
        reason,
        fallback_ratio,
        _degraded_mode_threshold(),
        _degraded_mode_min_attempts(),
    )


def _maybe_activate_degraded_mode(*, reason: str) -> None:
    if _is_degraded_mode_active():
        return
    counters = dynamic_content_runtime_metrics.snapshot()
    attempts = int(counters.get("dynamic_content_generation_attempt_total", 0) or 0)
    if attempts < _degraded_mode_min_attempts():
        return
    fallback_ratio = _degraded_mode_fallback_ratio()
    if fallback_ratio < _degraded_mode_threshold():
        return
    _activate_degraded_mode(reason=reason, fallback_ratio=fallback_ratio)


def _cooldown_store_retry_remaining_seconds() -> int:
    if not _COOLDOWN_STORE_DEGRADED:
        return 0
    remaining = _COOLDOWN_STORE_RETRY_AT_TS - time()
    return max(0, int(remaining))


def _should_probe_cooldown_store() -> bool:
    if not _COOLDOWN_STORE_DEGRADED:
        return True
    return time() >= _COOLDOWN_STORE_RETRY_AT_TS


def _read_cooldown_until_from_store() -> float:
    global _COOLDOWN_STORE_DEGRADED, _COOLDOWN_STORE_RETRY_AT_TS
    if not _should_probe_cooldown_store():
        dynamic_content_runtime_metrics.increment(
            "dynamic_content_cooldown_store_read_skipped_degraded_total"
        )
        return 0.0

    try:
        payload = _COOLDOWN_STORE.load(_COOLDOWN_STORE_KEY)
    except Exception as exc:
        _COOLDOWN_STORE_DEGRADED = True
        _COOLDOWN_STORE_RETRY_AT_TS = time() + _cooldown_store_retry_seconds()
        _record_store_exception("dynamic_content_cooldown_store_read_error", exc)
        return 0.0

    if _COOLDOWN_STORE_DEGRADED:
        _COOLDOWN_STORE_DEGRADED = False
        _COOLDOWN_STORE_RETRY_AT_TS = 0.0
        dynamic_content_runtime_metrics.increment("dynamic_content_cooldown_store_recovered_total")
        logger.info("Dynamic content cooldown store recovered")

    if not isinstance(payload, dict):
        return 0.0
    raw_value = payload.get("until_ts")
    try:
        return float(raw_value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _write_cooldown_until_to_store(until_ts: float, *, cooldown_seconds: float) -> None:
    global _COOLDOWN_STORE_DEGRADED, _COOLDOWN_STORE_RETRY_AT_TS
    if not _should_probe_cooldown_store():
        dynamic_content_runtime_metrics.increment(
            "dynamic_content_cooldown_store_write_skipped_degraded_total"
        )
        return
    try:
        ttl_seconds = max(1, int(cooldown_seconds) + 60)
        _COOLDOWN_STORE.save(
            _COOLDOWN_STORE_KEY,
            {"until_ts": until_ts},
            ttl_seconds=ttl_seconds,
        )
        if _COOLDOWN_STORE_DEGRADED:
            _COOLDOWN_STORE_DEGRADED = False
            _COOLDOWN_STORE_RETRY_AT_TS = 0.0
            dynamic_content_runtime_metrics.increment("dynamic_content_cooldown_store_recovered_total")
            logger.info("Dynamic content cooldown store recovered")
    except Exception as exc:
        _COOLDOWN_STORE_DEGRADED = True
        _COOLDOWN_STORE_RETRY_AT_TS = time() + _cooldown_store_retry_seconds()
        _record_store_exception("dynamic_content_cooldown_store_write_error", exc)


def _clear_cooldown_store_for_test() -> None:
    global _COOLDOWN_STORE_DEGRADED, _COOLDOWN_STORE_RETRY_AT_TS
    _COOLDOWN_STORE_DEGRADED = False
    _COOLDOWN_STORE_RETRY_AT_TS = 0.0
    try:
        _COOLDOWN_STORE.delete(_COOLDOWN_STORE_KEY)
    except Exception:
        _COOLDOWN_STORE_DEGRADED = True
        _COOLDOWN_STORE_RETRY_AT_TS = time() + _cooldown_store_retry_seconds()


def _read_degraded_until_from_store() -> float:
    global _COOLDOWN_STORE_DEGRADED, _COOLDOWN_STORE_RETRY_AT_TS
    if not _should_probe_cooldown_store():
        dynamic_content_runtime_metrics.increment(
            "dynamic_content_degraded_store_read_skipped_degraded_total"
        )
        return 0.0

    try:
        payload = _COOLDOWN_STORE.load(_DEGRADED_MODE_STORE_KEY)
    except Exception as exc:
        _COOLDOWN_STORE_DEGRADED = True
        _COOLDOWN_STORE_RETRY_AT_TS = time() + _cooldown_store_retry_seconds()
        _record_store_exception("dynamic_content_degraded_store_read_error", exc)
        return 0.0

    if _COOLDOWN_STORE_DEGRADED:
        _COOLDOWN_STORE_DEGRADED = False
        _COOLDOWN_STORE_RETRY_AT_TS = 0.0
        dynamic_content_runtime_metrics.increment("dynamic_content_cooldown_store_recovered_total")
        logger.info("Dynamic content cooldown store recovered")

    if not isinstance(payload, dict):
        return 0.0
    raw_value = payload.get("until_ts")
    try:
        return float(raw_value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _write_degraded_until_to_store(until_ts: float) -> None:
    global _COOLDOWN_STORE_DEGRADED, _COOLDOWN_STORE_RETRY_AT_TS
    if not _should_probe_cooldown_store():
        dynamic_content_runtime_metrics.increment(
            "dynamic_content_degraded_store_write_skipped_degraded_total"
        )
        return
    try:
        if until_ts <= time():
            _COOLDOWN_STORE.delete(_DEGRADED_MODE_STORE_KEY)
        else:
            ttl_seconds = max(60, int(until_ts - time()) + 60)
            _COOLDOWN_STORE.save(
                _DEGRADED_MODE_STORE_KEY,
                {"until_ts": until_ts},
                ttl_seconds=ttl_seconds,
            )
        if _COOLDOWN_STORE_DEGRADED:
            _COOLDOWN_STORE_DEGRADED = False
            _COOLDOWN_STORE_RETRY_AT_TS = 0.0
            dynamic_content_runtime_metrics.increment("dynamic_content_cooldown_store_recovered_total")
            logger.info("Dynamic content cooldown store recovered")
    except Exception as exc:
        _COOLDOWN_STORE_DEGRADED = True
        _COOLDOWN_STORE_RETRY_AT_TS = time() + _cooldown_store_retry_seconds()
        _record_store_exception("dynamic_content_degraded_store_write_error", exc)


def _clear_degraded_store_for_test() -> None:
    global _COOLDOWN_STORE_DEGRADED, _COOLDOWN_STORE_RETRY_AT_TS
    _COOLDOWN_STORE_DEGRADED = False
    _COOLDOWN_STORE_RETRY_AT_TS = 0.0
    try:
        _COOLDOWN_STORE.delete(_DEGRADED_MODE_STORE_KEY)
    except Exception:
        _COOLDOWN_STORE_DEGRADED = True
        _COOLDOWN_STORE_RETRY_AT_TS = time() + _cooldown_store_retry_seconds()


def _resolve_cooldown_until_ts() -> float:
    store_until_ts = _read_cooldown_until_from_store()
    with _COOLDOWN_LOCK:
        return max(_COOLDOWN_UNTIL_TS, store_until_ts)


def _resolve_degraded_until_ts() -> float:
    store_until_ts = _read_degraded_until_from_store()
    with _COOLDOWN_LOCK:
        return max(_DEGRADED_MODE_UNTIL_TS, store_until_ts)


def _activate_cooldown(seconds: float) -> None:
    if seconds <= 0:
        return
    until_ts = time() + seconds
    with _COOLDOWN_LOCK:
        global _COOLDOWN_UNTIL_TS
        _COOLDOWN_UNTIL_TS = max(_COOLDOWN_UNTIL_TS, until_ts)
    _write_cooldown_until_to_store(until_ts, cooldown_seconds=seconds)
    dynamic_content_runtime_metrics.increment("dynamic_content_cooldown_activated_total")


def _reset_cooldown_for_test() -> None:
    with _COOLDOWN_LOCK:
        global _COOLDOWN_UNTIL_TS, _DEGRADED_MODE_UNTIL_TS, _OPENAI_CLIENT, _OPENAI_CLIENT_INIT_RETRY_AT_TS
        _COOLDOWN_UNTIL_TS = 0.0
        _DEGRADED_MODE_UNTIL_TS = 0.0
        _OPENAI_CLIENT = None
        _OPENAI_CLIENT_INIT_RETRY_AT_TS = 0.0
    _clear_cooldown_store_for_test()
    _clear_degraded_store_for_test()


def _ensure_trending_deck(session: Session) -> int:
    """Get or create the 時事 deck. Returns deck id."""
    deck = session.exec(select(CardDeck).where(CardDeck.name == TRENDING_DECK_NAME)).first()
    if deck:
        return deck.id
    deck = CardDeck(
        name=TRENDING_DECK_NAME,
        description="每週由 AI 生成的時事話題卡片，幫助伴侶輕鬆破冰與對話。",
    )
    session.add(deck)
    session.flush()
    logger.info("Created trending deck id=%s", deck.id)
    return deck.id


def _strip_markdown_fence(content: str) -> str:
    cleaned = content.strip()
    if not cleaned.startswith("```"):
        return cleaned
    lines = cleaned.splitlines()
    if len(lines) >= 3 and lines[-1].strip().startswith("```"):
        return "\n".join(lines[1:-1]).strip()
    if cleaned.startswith("```json"):
        return cleaned[7:].strip().rstrip("`").strip()
    return cleaned.strip("`").strip()


def _parse_generated_cards(content: str) -> list[dict[str, Any]]:
    payload = json.loads(_strip_markdown_fence(content))
    if not isinstance(payload, list):
        return []

    parsed: list[dict[str, Any]] = []
    for i, item in enumerate(payload[:CARDS_PER_WEEK]):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or f"時事話題 {i + 1}").strip()[:200]
        description = str(item.get("description") or "").strip()[:500]
        question = str(item.get("question") or "").strip()[:500]
        if not title or not question:
            continue
        parsed.append(
            {
                "title": title,
                "description": description or title,
                "question": question,
            }
        )
    return parsed[:CARDS_PER_WEEK]


async def _generate_trending_cards_via_ai() -> tuple[list[dict[str, Any]], str]:
    """
    Call AI to generate weekly cards.
    Returns tuple(cards, source) where source indicates ai/fallback reason.
    """
    dynamic_content_runtime_metrics.increment("dynamic_content_generation_attempt_total")

    if _is_cooldown_active():
        dynamic_content_runtime_metrics.increment("dynamic_content_fallback_cooldown_active_total")
        _maybe_activate_degraded_mode(reason="cooldown_active")
        return _fallback_trending_cards(), "fallback_cooldown_active"
    if _is_degraded_mode_active():
        dynamic_content_runtime_metrics.increment("dynamic_content_fallback_degraded_mode_total")
        return _fallback_trending_cards(), "fallback_degraded_mode"

    client = _get_openai_client()
    if client is None:
        dynamic_content_runtime_metrics.increment("dynamic_content_fallback_provider_unavailable_total")
        _maybe_activate_degraded_mode(reason="provider_unavailable")
        return _fallback_trending_cards(), "fallback_provider_unavailable"

    runtime_settings = _runtime_settings()
    timeout_seconds = runtime_settings.ai_timeout_seconds
    max_retries = runtime_settings.ai_max_retries
    backoff_base_seconds = runtime_settings.ai_backoff_base_seconds
    cooldown_seconds = runtime_settings.ai_failure_cooldown_seconds

    system = (
        "你是一位伴侶關係與對話設計師。請根據「本週時事、節令或普遍話題」生成 5 張「時事卡片」"
        "，每張卡片供情侶/伴侶一起討論。輸出必須是單一 JSON 陣列，每項含三個字串：title（卡片標題，簡短）、description（一句說明）、question（一個具體問題，讓兩人可以輪流回答）。"
        "不要輸出 markdown 或程式碼區塊，只輸出 JSON。"
    )
    user = (
        "請生成 5 張時事卡片的 JSON 陣列，每項格式："
        "{\"title\":\"...\", \"description\":\"...\", \"question\":\"...\"}。"
        "主題可包含本週新聞、節日、季節、生活趨勢等，適合伴侶輕鬆對話。"
    )

    for attempt in range(max_retries + 1):
        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=0.7,
                    max_tokens=1500,
                ),
                timeout=timeout_seconds,
            )

            content = (response.choices[0].message.content or "").strip()
            if not content:
                dynamic_content_runtime_metrics.increment("dynamic_content_fallback_empty_response_total")
                _maybe_activate_degraded_mode(reason="empty_response")
                return _fallback_trending_cards(), "fallback_empty_response"

            try:
                cards = _parse_generated_cards(content)
            except json.JSONDecodeError:
                logger.warning("Dynamic content parse failed: JSONDecodeError")
                dynamic_content_runtime_metrics.increment("dynamic_content_parse_error_total")
                _maybe_activate_degraded_mode(reason="parse_error")
                return _fallback_trending_cards(), "fallback_parse_error"

            if not cards:
                dynamic_content_runtime_metrics.increment("dynamic_content_fallback_invalid_payload_total")
                _maybe_activate_degraded_mode(reason="invalid_payload")
                return _fallback_trending_cards(), "fallback_invalid_payload"

            dynamic_content_runtime_metrics.increment("dynamic_content_generation_success_total")
            return cards, "ai"
        except asyncio.TimeoutError:
            dynamic_content_runtime_metrics.increment("dynamic_content_generation_timeout_total")
            logger.warning(
                "Dynamic content generation timeout: attempt=%s/%s timeout=%ss",
                attempt + 1,
                max_retries + 1,
                timeout_seconds,
            )
            if attempt < max_retries:
                await asyncio.sleep(
                    compute_exponential_backoff_seconds(
                        attempt=attempt,
                        base_seconds=backoff_base_seconds,
                        max_seconds=max(1.0, timeout_seconds),
                        jitter_ratio=0.0,
                    )
                )
                continue
            _activate_cooldown(cooldown_seconds)
            dynamic_content_runtime_metrics.increment("dynamic_content_fallback_timeout_total")
            _maybe_activate_degraded_mode(reason="timeout")
            return _fallback_trending_cards(), "fallback_timeout"
        except Exception as exc:
            dynamic_content_runtime_metrics.increment("dynamic_content_generation_error_total")
            logger.warning(
                "Dynamic content generation failed: reason=%s attempt=%s/%s",
                redact_exception_reason(exc),
                attempt + 1,
                max_retries + 1,
            )
            if attempt < max_retries:
                await asyncio.sleep(
                    compute_exponential_backoff_seconds(
                        attempt=attempt,
                        base_seconds=backoff_base_seconds,
                        max_seconds=max(1.0, timeout_seconds),
                        jitter_ratio=0.0,
                    )
                )
                continue
            _activate_cooldown(cooldown_seconds)
            dynamic_content_runtime_metrics.increment("dynamic_content_fallback_error_total")
            _maybe_activate_degraded_mode(reason="error")
            return _fallback_trending_cards(), "fallback_error"

    _activate_cooldown(cooldown_seconds)
    dynamic_content_runtime_metrics.increment("dynamic_content_fallback_unknown_total")
    _maybe_activate_degraded_mode(reason="unknown")
    return _fallback_trending_cards(), "fallback_unknown"


def _fallback_trending_cards() -> list[dict[str, Any]]:
    """Fallback when AI is unavailable: 5 fixed 時事-style prompts."""
    return [
        {"title": "本週最想分享的一件事", "description": "一起聊聊這週各自最有感的事。", "question": "這週你最想和對方分享的一件事是什麼？"},
        {"title": "最近的新聞或話題", "description": "選一個你們都注意到的時事。", "question": "最近有什麼新聞或話題讓你印象深刻？"},
        {"title": "季節與心情", "description": "隨著季節變化，心情也來交流一下。", "question": "這個季節讓你聯想到什麼？你的心情如何？"},
        {"title": "小確幸時刻", "description": "回想這週的小確幸。", "question": "這週有一個什麼樣的小確幸你想和對方說？"},
        {"title": "下週的小期待", "description": "一起期待下週。", "question": "下週你最期待的一件事是什麼？"},
    ]


async def run_weekly_injection(session: Session) -> int:
    """
    P2-E pipeline: ensure 時事 deck exists, generate cards via AI with safe fallback, insert into cards.
    Returns number of cards inserted.
    """
    dynamic_content_runtime_metrics.increment("dynamic_content_weekly_run_total")
    deck_id = _ensure_trending_deck(session)
    cards_data, source = await _generate_trending_cards_via_ai()
    dynamic_content_runtime_metrics.increment(f"dynamic_content_generation_source_{source}_total")

    if _runtime_settings().shadow_mode:
        dynamic_content_runtime_metrics.increment("dynamic_content_shadow_run_total")
        logger.info(
            "Dynamic content pipeline shadow run: generated=%s deck_id=%s source=%s",
            len(cards_data),
            deck_id,
            source,
        )
        return 0

    created = 0
    for item in cards_data:
        card = Card(
            category=CardCategory.DAILY_VIBE,
            title=item["title"],
            description=item.get("description") or item["title"],
            question=item["question"],
            difficulty_level=1,
            depth_level=1,
            tags=["時事", "動態"],
            is_ai_generated=True,
            deck_id=deck_id,
        )
        session.add(card)
        created += 1
    session.flush()

    dynamic_content_runtime_metrics.record_insert_count(created)
    if source != "ai":
        dynamic_content_runtime_metrics.increment("dynamic_content_weekly_run_fallback_total")

    logger.info(
        "Dynamic content pipeline run complete: inserted=%s deck_id=%s source=%s",
        created,
        deck_id,
        source,
    )
    return created


def get_dynamic_content_runtime_state() -> dict[str, int | float | bool]:
    return {
        "cooldown_active": _is_cooldown_active(),
        "cooldown_remaining_seconds": _cooldown_remaining_seconds(),
        "cooldown_store_degraded": bool(_COOLDOWN_STORE_DEGRADED),
        "cooldown_store_retry_remaining_seconds": _cooldown_store_retry_remaining_seconds(),
        "degraded_mode_active": _is_degraded_mode_active(),
        "degraded_mode_remaining_seconds": _degraded_mode_remaining_seconds(),
        "degraded_mode_store_degraded": bool(_COOLDOWN_STORE_DEGRADED),
        "degraded_mode_fallback_ratio": round(_degraded_mode_fallback_ratio(), 6),
        "degraded_mode_min_attempts": _degraded_mode_min_attempts(),
        "degraded_mode_threshold": _degraded_mode_threshold(),
        "degraded_mode_recovery_threshold": _degraded_mode_recovery_threshold(),
        "degraded_mode_recovery_min_attempts": _degraded_mode_recovery_min_attempts(),
        "provider_client_initialized": _OPENAI_CLIENT is not None,
        "provider_init_retry_remaining_seconds": _provider_init_retry_remaining_seconds(),
    }
