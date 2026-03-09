# backend/app/services/ai.py
# AI Do/Don't contract: docs/ai-safety/ai-guardrails.md (tone rewrite, repair templates, no judgment/diagnosis/manipulation)

import asyncio
import json
import uuid
from collections.abc import Mapping
from pathlib import Path
import httpx
import logging
from app.core.config import settings
# 引入必要的 Schema 和 Enum
from app.schemas.ai import JournalAnalysis, CardRecommendation 
from app.core.prompts import HAVEN_SYSTEM_PROMPT, CURRENT_PROMPT_VERSION
from app.services.ai_safety import (
    ModerationSignal,
    derive_safety_tier_from_moderation,
    merge_safety_tier,
    normalize_category_bools,
    normalize_category_scores,
)
from app.services.prompt_abuse import detect_prompt_abuse
from app.services.ai_persona import apply_persona_output_guardrails, build_analysis_messages
from app.services.ai_errors import (
    HavenAIProviderError,
    HavenAISchemaError,
    HavenAITimeoutError,
)
from app.services.ai_router import (
    AIRouterRequestContext,
    AIProviderAdapter,
    AIProviderError,
    AIProviderFallbackExhaustedError,
    AIProviderIdempotencyRejectedError,
    ai_router_runtime_metrics,
    build_input_fingerprint,
    build_normalized_content_hash,
    run_provider_adapters,
    select_task_route,
)
from app.services.trace_span import trace_span
from app.middleware.request_context import request_id_var

# CURRENT_PROMPT_VERSION is now imported from app.core.prompts
ANALYSIS_MODEL = "gpt-4o-mini"
GEMINI_ANALYSIS_MODEL = settings.AI_ROUTER_GEMINI_MODEL
MODERATION_MODEL = "omni-moderation-latest"
logger = logging.getLogger(__name__)

_openai_async_client_cls = None
_openai_connection_error_type = None
_openai_status_error_type = None
_openai_import_reason: str | None = None
_openai_bootstrap_attempted = False
_openai_client = None
# Backward-compatible patch point for tests that monkeypatch `app.services.ai.client`.
client = None

# 🚀 Module-level Gemini httpx client — reuses TCP connections across requests
# instead of creating a new AsyncClient per-call (saves ~50-80ms per Gemini request).
_GEMINI_HTTP_TIMEOUT = httpx.Timeout(30.0, connect=5.0)
_gemini_http_client: httpx.AsyncClient | None = None


def _bootstrap_openai_support() -> None:
    global _openai_async_client_cls
    global _openai_connection_error_type
    global _openai_status_error_type
    global _openai_import_reason
    global _openai_bootstrap_attempted
    if _openai_bootstrap_attempted:
        return
    _openai_bootstrap_attempted = True
    try:
        from openai import APIConnectionError, APIStatusError, AsyncOpenAI
    except Exception as exc:  # pragma: no cover - env-specific import failure path
        _openai_import_reason = type(exc).__name__
        _openai_async_client_cls = None
        _openai_connection_error_type = None
        _openai_status_error_type = None
        return
    _openai_async_client_cls = AsyncOpenAI
    _openai_connection_error_type = APIConnectionError
    _openai_status_error_type = APIStatusError
    _openai_import_reason = None


def _get_openai_client():
    global _openai_client
    global client
    if client is not None:
        return client
    _bootstrap_openai_support()
    if _openai_async_client_cls is None:
        return None
    if _openai_client is None:
        _openai_client = _openai_async_client_cls(
            api_key=settings.OPENAI_API_KEY,
            timeout=httpx.Timeout(30.0, connect=5.0),
        )
        client = _openai_client
    return _openai_client


def _is_openai_connection_error(exc: Exception) -> bool:
    _bootstrap_openai_support()
    if _openai_connection_error_type is None:
        return False
    return isinstance(exc, _openai_connection_error_type)


def _is_openai_status_error(exc: Exception) -> bool:
    _bootstrap_openai_support()
    if _openai_status_error_type is None:
        return False
    return isinstance(exc, _openai_status_error_type)


def _get_openai_status_code(exc: Exception) -> int | None:
    if not _is_openai_status_error(exc):
        return None
    return getattr(exc, "status_code", None)


def _is_request_class_quality_gate_red(request_class: str) -> bool:
    safe_request_class = request_class.strip().lower() or "unknown"
    forced_gate_red_classes = {
        item.strip().lower()
        for item in str(
            getattr(settings, "AI_ROUTER_FORCE_QUALITY_GATE_RED_CLASSES", "")
            or ""
        ).split(",")
        if item.strip()
    }
    if safe_request_class in forced_gate_red_classes:
        ai_router_runtime_metrics.increment(
            f"ai_router_quality_gate_red_forced_total_{safe_request_class}"
        )
        ai_router_runtime_metrics.set_state(
            f"quality_gate_status_{safe_request_class}",
            "red_forced",
        )
        return True

    snapshot_path = Path(
        str(getattr(settings, "AI_QUALITY_GATE_SNAPSHOT_FILE", "") or "").strip()
    )
    if str(snapshot_path) in {"", "."}:
        ai_router_runtime_metrics.increment(
            f"ai_router_quality_gate_missing_snapshot_total_{safe_request_class}"
        )
        ai_router_runtime_metrics.set_state(
            f"quality_gate_status_{safe_request_class}",
            "green_missing_snapshot",
        )
        return False
    if not snapshot_path.exists():
        ai_router_runtime_metrics.increment(
            f"ai_router_quality_gate_missing_snapshot_total_{safe_request_class}"
        )
        ai_router_runtime_metrics.set_state(
            f"quality_gate_status_{safe_request_class}",
            "green_missing_snapshot",
        )
        return False

    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("AI quality gate snapshot parse failed: reason=%s", type(exc).__name__)
        ai_router_runtime_metrics.increment(
            f"ai_router_quality_gate_snapshot_parse_error_total_{safe_request_class}"
        )
        ai_router_runtime_metrics.set_state(
            f"quality_gate_status_{safe_request_class}",
            "green_snapshot_parse_error",
        )
        return False

    gate = payload.get("request_class_gate")
    if not isinstance(gate, Mapping):
        ai_router_runtime_metrics.increment(
            f"ai_router_quality_gate_missing_request_class_gate_total_{safe_request_class}"
        )
        ai_router_runtime_metrics.set_state(
            f"quality_gate_status_{safe_request_class}",
            "green_missing_request_class_gate",
        )
        return False
    status = str(gate.get(safe_request_class, "")).strip().lower()
    if status == "red":
        ai_router_runtime_metrics.increment(
            f"ai_router_quality_gate_red_total_{safe_request_class}"
        )
        ai_router_runtime_metrics.set_state(
            f"quality_gate_status_{safe_request_class}",
            "red",
        )
        return True
    ai_router_runtime_metrics.increment(
        f"ai_router_quality_gate_green_total_{safe_request_class}"
    )
    ai_router_runtime_metrics.set_state(
        f"quality_gate_status_{safe_request_class}",
        "green",
    )
    return False


def _get_gemini_http_client() -> httpx.AsyncClient:
    """Lazy-init reusable Gemini HTTP client with connection pooling."""
    global _gemini_http_client
    if _gemini_http_client is None or getattr(_gemini_http_client, "is_closed", False):
        _gemini_http_client = httpx.AsyncClient(
            timeout=_GEMINI_HTTP_TIMEOUT,
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5,
                keepalive_expiry=120,
            ),
        )
    return _gemini_http_client


async def analyze_journal(
    content: str,
    *,
    relationship_weather_hint: str | None = None,
    relationship_mode: str | None = None,
) -> dict:
    """
    使用「Moderation 前置檢查 + Structured Outputs」分析日記內容。
    回傳符合 JournalAnalysis Schema 的字典。
    """
    prompt_abuse = detect_prompt_abuse(content)
    if prompt_abuse.flagged:
        logger.warning(
            "[PROMPT ABUSE] blocked suspicious prompt payload pattern_ids=%s",
            [item.pattern_id for item in prompt_abuse.matches],
        )
        return _get_fallback_response(
            "系統偵測到可疑提示詞攻擊內容，已啟用保護模式。",
            safety_tier=2,
            parse_success=False,
            model_version="prompt_abuse_policy_v1",
        )

    moderation_signal, moderation_errored = await _run_moderation_precheck(content)

    # 極高風險內容先進入安全回應模式，避免進一步產生互動建議。
    if moderation_signal and moderation_signal.safety_tier >= 3:
        logger.warning(
            "[SAFETY ALERT] Moderation precheck blocked detailed analysis (tier=%s).",
            moderation_signal.safety_tier,
        )
        return _get_fallback_response(
            "系統偵測到高風險訊號，建議先確保安全並尋求即時協助。",
            safety_tier=moderation_signal.safety_tier,
            parse_success=False,
            model_version=MODERATION_MODEL,
        )

    try:
        route = select_task_route("l2_deep_reasoning")
        analysis_messages = build_analysis_messages(
            content=content,
            base_prompt=HAVEN_SYSTEM_PROMPT,
            relationship_weather_hint=relationship_weather_hint,
            relationship_mode=relationship_mode,
        )
        provider_adapters = _build_analysis_provider_adapters(
            analysis_messages=analysis_messages,
            temperature=0.7,
        )
        with trace_span(
            "ai.structured_parse",
            model=ANALYSIS_MODEL,
            provider=route.selected_provider,
            provider_chain=list(route.provider_chain),
            router_reason=route.reason,
        ):
            request_id = (request_id_var.get() or "").strip() or str(uuid.uuid4())
            fingerprint_payload = {
                "request_class": "journal_analysis",
                "schema_version": "journal_analysis_v1",
                "prompt_version": CURRENT_PROMPT_VERSION,
                "moderation_version": MODERATION_MODEL,
                "relationship_mode": relationship_mode or "",
                "strict_schema_mode": True,
                "normalized_content_hash": build_normalized_content_hash(content),
            }
            input_fingerprint = build_input_fingerprint(payload=fingerprint_payload)
            request_context = AIRouterRequestContext(
                request_class="journal_analysis",
                request_id=request_id,
                # Default idempotency identity follows request_id; caller can override upstream.
                idempotency_key=request_id,
                input_fingerprint=input_fingerprint,
                quality_gate_red=_is_request_class_quality_gate_red("journal_analysis"),
                strict_schema_mode=True,
                prompt_version=CURRENT_PROMPT_VERSION,
                schema_version="journal_analysis_v1",
                moderation_version=MODERATION_MODEL,
                relationship_mode=relationship_mode,
            )
            provider_result = await run_provider_adapters(
                route=route,
                adapters=provider_adapters,
                request_context=request_context,
            )

        # 取得解析後的 Pydantic 物件
        analysis_result = provider_result.parsed
        if isinstance(analysis_result, dict):
            analysis_result = JournalAnalysis.model_validate(analysis_result)

        if not analysis_result:
            raise ValueError("AI provider 回傳了空的解析結果")

        # 1) 先把 Moderation 的風險分級合併進結果
        analysis_result = _merge_moderation_safety_tier(analysis_result, moderation_signal)

        # 🛡️ STEP 1: 執行安全斷路器檢查 (Safety Circuit Breaker)
        # 這是新增的關鍵步驟，確保寫入 DB 前資料是安全的
        analysis_result = _apply_safety_circuit_breaker(analysis_result)

        # 🛡️ STEP 2: Persona Runtime Guardrail（避免 AI 冒充伴侶）
        if settings.AI_PERSONA_RUNTIME_GUARDRAIL_ENABLED:
            analysis_result, persona_guardrail_meta = apply_persona_output_guardrails(analysis_result)
            if persona_guardrail_meta.get("adjusted"):
                logger.warning(
                    "AI persona guardrail adjusted output: fields=%s rule_ids=%s version=%s",
                    persona_guardrail_meta.get("fields"),
                    persona_guardrail_meta.get("rule_ids"),
                    persona_guardrail_meta.get("version"),
                )

        # 3) 轉為 dict
        result_dict = analysis_result.model_dump()

        # 4) 注入版本/解析資訊
        result_dict["prompt_version"] = CURRENT_PROMPT_VERSION
        result_dict["model_version"] = provider_result.model_version
        result_dict["provider"] = provider_result.provider
        result_dict["parse_success"] = True
        result_dict["moderation_skipped"] = moderation_errored

        if provider_result.fallback_used:
            logger.warning(
                "AI router fallback succeeded: provider=%s failure_reasons=%s",
                provider_result.provider,
                [failure.reason for failure in provider_result.failures],
            )

        return result_dict

    except AIProviderFallbackExhaustedError as e:
        logger.warning(
            "AI provider fallback exhausted: reasons=%s",
            [f"{failure.provider}:{failure.reason}" for failure in e.failures],
        )
        typed_error = HavenAIProviderError(
            reason="provider_fallback_exhausted",
            retryable=True,
            provider="multi",
        )
        logger.warning("AI typed_error=%s retryable=%s", typed_error.reason, typed_error.retryable)
        return _get_fallback_response(
            "連線不穩定，正在努力恢復中...",
            safety_tier=moderation_signal.safety_tier if moderation_signal else 0,
            parse_success=False,
            model_version=ANALYSIS_MODEL,
            moderation_skipped=moderation_errored,
        )
    except AIProviderIdempotencyRejectedError:
        logger.warning("AI idempotency mismatch rejected by router")
        return _get_fallback_response(
            "請稍後重試，我們正在同步你的分析狀態。",
            safety_tier=moderation_signal.safety_tier if moderation_signal else 0,
            parse_success=False,
            model_version=ANALYSIS_MODEL,
            moderation_skipped=moderation_errored,
        )

    except (json.JSONDecodeError, ValueError, TypeError) as e:
        typed_error = HavenAISchemaError(
            reason="analysis_schema_error",
            retryable=False,
            provider="multi",
        )
        logger.warning(
            "AI schema parse error: reason=%s typed_error=%s",
            type(e).__name__,
            typed_error.reason,
        )
        return _get_fallback_response(
            "系統暫時無法解析分析結果，已回退到安全建議。",
            safety_tier=moderation_signal.safety_tier if moderation_signal else 0,
            parse_success=False,
            model_version=ANALYSIS_MODEL,
            moderation_skipped=moderation_errored,
        )

    except Exception as e:
        typed_error = HavenAIProviderError(
            reason="analysis_unexpected_error",
            retryable=True,
            provider="multi",
        )
        logger.error(
            "分析過程發生未預期錯誤: reason=%s typed_error=%s",
            type(e).__name__,
            typed_error.reason,
        )
        return _get_fallback_response(
            "系統暫時無法深入分析，但我們收到了你的心情。",
            safety_tier=moderation_signal.safety_tier if moderation_signal else 0,
            parse_success=False,
            model_version=ANALYSIS_MODEL,
            moderation_skipped=moderation_errored,
        )


def _build_analysis_provider_adapters(
    *,
    analysis_messages: list[dict[str, str]],
    temperature: float,
) -> dict[str, AIProviderAdapter]:
    return {
        "openai": AIProviderAdapter(
            provider="openai",
            run=lambda: _analyze_with_openai_provider(
                analysis_messages=analysis_messages,
                temperature=temperature,
            ),
        ),
        "gemini": AIProviderAdapter(
            provider="gemini",
            run=lambda: _analyze_with_gemini_provider(
                analysis_messages=analysis_messages,
                temperature=temperature,
            ),
        ),
    }


async def _analyze_with_openai_provider(
    *,
    analysis_messages: list[dict[str, str]],
    temperature: float,
) -> tuple[JournalAnalysis, str]:
    client = _get_openai_client()
    if client is None:
        raise AIProviderError(
            provider="openai",
            reason="provider_adapter_missing",
            retryable=False,
        )
    try:
        completion = await client.beta.chat.completions.parse(
            model=ANALYSIS_MODEL,
            messages=analysis_messages,
            response_format=JournalAnalysis,
            temperature=temperature,
        )
    except Exception as exc:
        if isinstance(exc, (asyncio.TimeoutError, TimeoutError)) or _is_openai_connection_error(exc):
            raise AIProviderError(provider="openai", reason="timeout", retryable=True) from exc
        if _is_openai_status_error(exc):
            status_code = _get_openai_status_code(exc)
            if status_code == 429:
                raise AIProviderError(
                    provider="openai",
                    reason="status_429",
                    retryable=True,
                    status_code=status_code,
                ) from exc
            if status_code is not None and status_code >= 500:
                raise AIProviderError(
                    provider="openai",
                    reason="status_5xx",
                    retryable=True,
                    status_code=status_code,
                ) from exc
            raise AIProviderError(
                provider="openai",
                reason="status_4xx",
                retryable=False,
                status_code=status_code,
            ) from exc
        raise AIProviderError(
            provider="openai",
            reason="unexpected_error",
            retryable=True,
        ) from exc

    parsed = completion.choices[0].message.parsed
    if not parsed:
        raise AIProviderError(
            provider="openai",
            reason="empty_parse_result",
            retryable=True,
        )

    return parsed, str(completion.model or ANALYSIS_MODEL)


async def _analyze_with_gemini_provider(
    *,
    analysis_messages: list[dict[str, str]],
    temperature: float,
) -> tuple[JournalAnalysis, str]:
    api_key = (settings.GEMINI_API_KEY or "").strip()
    if not api_key:
        raise AIProviderError(
            provider="gemini",
            reason="missing_api_key",
            retryable=False,
        )

    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_ANALYSIS_MODEL}:generateContent"
    payload = _build_gemini_payload(
        analysis_messages=analysis_messages,
        temperature=temperature,
    )

    try:
        # Use module-level reusable client for production, but allow tests to
        # patch `_gemini_http_client` directly for mock injection.
        http_client = _get_gemini_http_client()
        response = await http_client.post(
            endpoint,
            params={"key": api_key},
            json=payload,
        )
    except (httpx.TimeoutException, asyncio.TimeoutError, TimeoutError) as exc:
        raise AIProviderError(provider="gemini", reason="timeout", retryable=True) from exc
    except httpx.HTTPError as exc:
        raise AIProviderError(
            provider="gemini",
            reason="network_error",
            retryable=True,
        ) from exc

    status_code = response.status_code
    if status_code == 429:
        raise AIProviderError(
            provider="gemini",
            reason="status_429",
            retryable=True,
            status_code=status_code,
        )
    if status_code >= 500:
        raise AIProviderError(
            provider="gemini",
            reason="status_5xx",
            retryable=True,
            status_code=status_code,
        )
    if status_code >= 400:
        raise AIProviderError(
            provider="gemini",
            reason="status_4xx",
            retryable=False,
            status_code=status_code,
        )

    try:
        payload_json = response.json()
    except ValueError as exc:
        raise AIProviderError(
            provider="gemini",
            reason="invalid_json_response",
            retryable=True,
        ) from exc

    content_text = _extract_gemini_text(payload_json)
    if not content_text:
        raise AIProviderError(
            provider="gemini",
            reason="missing_content_text",
            retryable=True,
        )

    try:
        parsed_payload = _coerce_json_object(content_text)
        parsed = JournalAnalysis.model_validate(parsed_payload)
    except Exception as exc:
        raise AIProviderError(
            provider="gemini",
            reason="schema_validation_failed",
            retryable=True,
        ) from exc

    model_version = str(payload_json.get("modelVersion") or GEMINI_ANALYSIS_MODEL)
    return parsed, model_version


def _build_gemini_payload(
    *,
    analysis_messages: list[dict[str, str]],
    temperature: float,
) -> dict:
    system_segments: list[str] = []
    contents: list[dict[str, object]] = []

    for message in analysis_messages:
        role = str(message.get("role") or "").strip().lower()
        text = str(message.get("content") or "").strip()
        if not text:
            continue
        if role == "system":
            system_segments.append(text)
            continue
        normalized_role = "model" if role == "assistant" else "user"
        contents.append({"role": normalized_role, "parts": [{"text": text}]})

    if not contents:
        contents.append({"role": "user", "parts": [{"text": "請分析這段日記內容。"}]})

    contract_suffix = _json_contract_suffix()
    updated_contents: list[dict[str, object]] = []
    suffix_applied = False
    for entry in contents:
        role = str(entry.get("role") or "")
        parts_raw = entry.get("parts")
        if role == "user" and isinstance(parts_raw, list) and parts_raw and not suffix_applied:
            first_part = parts_raw[0]
            if isinstance(first_part, Mapping):
                user_text = str(first_part.get("text") or "")
                patched_entry = dict(entry)
                patched_entry["parts"] = [{"text": f"{user_text}\n\n{contract_suffix}"}]
                updated_contents.append(patched_entry)
                suffix_applied = True
                continue
        updated_contents.append(entry)
    if not suffix_applied:
        updated_contents.append({"role": "user", "parts": [{"text": contract_suffix}]})

    payload: dict[str, object] = {
        "contents": updated_contents,
        "generationConfig": {
            "temperature": temperature,
            "responseMimeType": "application/json",
        },
    }
    if system_segments:
        payload["systemInstruction"] = {
            "parts": [{"text": "\n\n".join(system_segments)}],
        }
    return payload


def _json_contract_suffix() -> str:
    return (
        "Return ONLY one JSON object with keys: "
        "mood_label, emotional_needs, advice_for_user, action_for_user, "
        "advice_for_partner, action_for_partner, card_recommendation, safety_tier. "
        "Do not output markdown, prose, or code fences."
    )


def _extract_gemini_text(payload: dict) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return ""
    first_candidate = candidates[0]
    if not isinstance(first_candidate, Mapping):
        return ""
    content = first_candidate.get("content")
    if not isinstance(content, Mapping):
        return ""
    parts = content.get("parts")
    if not isinstance(parts, list) or not parts:
        return ""
    first_part = parts[0]
    if not isinstance(first_part, Mapping):
        return ""
    return str(first_part.get("text") or "").strip()


def _coerce_json_object(raw_text: str) -> dict:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
            text = "\n".join(lines[1:-1]).strip()
            if text.lower().startswith("json"):
                text = text[4:].strip()

    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("provider response must be JSON object")
    return parsed


_moderation_failure_count = 0


def get_moderation_failure_count() -> int:
    """Return cumulative count of moderation precheck failures for health monitoring."""
    return _moderation_failure_count


async def _run_moderation_precheck(content: str) -> tuple[ModerationSignal | None, bool]:
    """Run OpenAI moderation precheck.

    Returns:
        (signal, was_error): signal is the ModerationSignal or None.
        was_error is True ONLY when moderation service failed (not when content is clean).
    """
    global _moderation_failure_count
    client = _get_openai_client()
    if client is None:
        _moderation_failure_count += 1
        logger.critical(
            "[SAFETY] Moderation precheck UNAVAILABLE: reason=%s failure_count=%d",
            _openai_import_reason or "openai_import_unavailable",
            _moderation_failure_count,
        )
        return None, True
    try:
        with trace_span("ai.moderation_precheck"):
            response = await client.moderations.create(
                model=MODERATION_MODEL,
                input=content,
            )
        if not response.results:
            return None, False  # normal: no signal, not an error

        result = response.results[0]
        categories = normalize_category_bools(getattr(result, "categories", None))
        category_scores = normalize_category_scores(getattr(result, "category_scores", None))
        flagged = bool(getattr(result, "flagged", False))
        tier = derive_safety_tier_from_moderation(flagged, categories, category_scores)

        return ModerationSignal(
            safety_tier=tier,
            flagged=flagged,
            categories=categories,
            category_scores=category_scores,
            model=MODERATION_MODEL,
        ), False
    except Exception as e:
        _moderation_failure_count += 1
        if _is_openai_connection_error(e) or _is_openai_status_error(e):
            # Only log exception type to prevent PII/secret leakage via exception message (P0-H).
            logger.critical(
                "[SAFETY] Moderation precheck UNAVAILABLE: reason=%s failure_count=%d",
                type(e).__name__,
                _moderation_failure_count,
            )
        elif isinstance(e, (RuntimeError, ValueError, TypeError)):
            typed_error = HavenAIProviderError(
                reason="moderation_runtime_error",
                retryable=True,
                provider="openai",
            )
            logger.critical(
                "[SAFETY] Moderation precheck FAILED: reason=%s typed_error=%s failure_count=%d",
                type(e).__name__,
                typed_error.reason,
                _moderation_failure_count,
            )
        else:
            logger.critical(
                "[SAFETY] Moderation precheck FAILED: reason=%s failure_count=%d",
                type(e).__name__,
                _moderation_failure_count,
            )
    return None, True  # moderation was unavailable


def _merge_moderation_safety_tier(
    result: JournalAnalysis,
    moderation_signal: ModerationSignal | None,
) -> JournalAnalysis:
    merged_tier = merge_safety_tier(result.safety_tier, moderation_signal)
    if merged_tier > result.safety_tier:
        logger.warning(
            "[SAFETY ALIGN] Elevated safety_tier from %s to %s by moderation precheck.",
            result.safety_tier,
            merged_tier,
        )
        result.safety_tier = merged_tier
    return result

def _apply_safety_circuit_breaker(result: JournalAnalysis) -> JournalAnalysis:
    """
    🔒 安全斷路器邏輯
    如果 AI 判定 safety_tier >= 2 (自傷/暴力風險)，
    強制覆寫傳給伴侶的建議，防止衝突升級。
    """
    if result.safety_tier >= 2:
        logger.warning(
            "[SAFETY ALERT] High Risk Detected (Tier %s). Overriding partner advice.",
            result.safety_tier,
        )
        
        # 強制覆寫給伴侶的建議
        result.advice_for_partner = (
            "⚠️ 安全提醒：系統偵測到目前情緒張力較高，或包含敏感內容。"
            "此刻最好的支持是給予空間，並優先確認對方的物理與心理安全。"
            "若有緊急狀況，請立即尋求專業協助 (如 1925 安心專線)。"
        )
        
        # 強制覆寫給伴侶的行動
        result.action_for_partner = "給予安靜的陪伴，確認安全，暫停深度溝通。"
        
        # 強制將推薦卡牌改為「安全氣囊 (Safe Zone)」，避免跳出刺激性卡片
        result.card_recommendation = CardRecommendation.SAFE_ZONE
        
        # (選用) 標記情緒標籤，讓前端 UI 可以識別並變色
        result.mood_label = f"🚨 {result.mood_label} (需關注)"

    return result

def _get_fallback_response(
    message: str,
    *,
    safety_tier: int = 0,
    parse_success: bool = False,
    model_version: str | None = None,
    moderation_skipped: bool = False,
) -> dict:
    """
    當 AI 服務掛掉時的優雅降級 (Graceful Degradation) 回應。
    """
    if safety_tier >= 2:
        return {
            "mood_label": "🚨 需安全關注",
            "emotional_needs": "目前先以身心安全為第一優先，待狀態穩定後再進行深度對話。",
            "advice_for_user": message,
            "action_for_user": "請先離開高壓情境，聯絡可信任的人，並考慮立即求助。",
            "advice_for_partner": (
                "⚠️ 安全提醒：請先確認對方是否安全，避免逼問或辯論。"
                "若有立即風險，請優先求助專業資源。"
            ),
            "action_for_partner": "先確認安全、給予空間與陪伴，必要時協助聯繫 1925 / 113。",
            "card_recommendation": CardRecommendation.SAFE_ZONE,
            "safety_tier": safety_tier,
            "prompt_version": CURRENT_PROMPT_VERSION,
            "model_version": model_version,
            "parse_success": parse_success,
            "moderation_skipped": moderation_skipped,
        }

    return {
        "mood_label": "🌿 平靜",
        "emotional_needs": "（暫時無法連接 AI 腦波，但你的感受是真實的）",
        "advice_for_user": message,
        "action_for_user": "深呼吸三次，給自己一分鐘的空白。",
        "advice_for_partner": "他現在可能需要一點安靜的陪伴。",
        "action_for_partner": "靜靜地陪在他身邊即可。",
        "card_recommendation": CardRecommendation.SAFE_ZONE,
        "safety_tier": safety_tier,
        "prompt_version": "fallback_v1",
        "model_version": model_version,
        "parse_success": parse_success,
        "moderation_skipped": moderation_skipped,
    }


# Cooldown rewriter: aggressive → "I feel" / "I need" style. See docs/ai-safety/ai-guardrails.md
COOLDOWN_REWRITER_SYSTEM = """You are a relationship communication helper. Your ONLY job is to rephrase the user's message into a calmer "I feel..." / "I need..." style. Rules (from Haven AI Guardrails):
- DO: Rephrase attacking or harsh language into I-statements. Keep the same meaning and concerns.
- DON'T: Judge who is right or wrong, diagnose, or use manipulative or guilt-tripping language.
- Output ONLY the rewritten sentence in the same language as the input. No explanation, no prefix."""


async def rewrite_aggressive_to_i_message(message: str) -> str:
    """
    Rewrite potentially aggressive message to I-statement style. No judgment/diagnosis/manipulation.
    Caller must ensure user is in active cooldown. No PII logged.
    """
    if not message or not message.strip():
        return (message or "").strip()
    content = message.strip()[:2000]
    client = _get_openai_client()
    if client is None:
        logger.warning("Cooldown rewriter skipped: openai client unavailable reason=%s", _openai_import_reason or "openai_import_unavailable")
        return content
    try:
        with trace_span("ai.rewrite_i_message"):
            completion = await client.chat.completions.create(
                model=ANALYSIS_MODEL,
                messages=[
                    {"role": "system", "content": COOLDOWN_REWRITER_SYSTEM},
                    {"role": "user", "content": content},
                ],
                temperature=0.3,
                max_tokens=500,
            )
        text = (completion.choices[0].message.content or "").strip()
        return text or content
    except Exception as e:
        if isinstance(e, (asyncio.TimeoutError, TimeoutError)) or _is_openai_connection_error(e) or _is_openai_status_error(e):
            typed_error = HavenAITimeoutError(
                reason="cooldown_rewriter_timeout",
                retryable=True,
                provider="openai",
            )
            logger.warning(
                "Cooldown rewriter failed: reason=%s typed_error=%s",
                type(e).__name__,
                typed_error.reason,
            )
            return content
        logger.warning("Cooldown rewriter failed: reason=%s", type(e).__name__)
        return content
