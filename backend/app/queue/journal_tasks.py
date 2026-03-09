# P2-B QUEUE-01: Async journal analysis and partner notification via Redis list queue.
# When REDIS_URL and ASYNC_JOURNAL_ANALYSIS are set, journal create returns after DB write and
# analysis/notify run in background workers. Fallback: no Redis or ASYNC_JOURNAL_ANALYSIS=False
# keeps synchronous behavior in the API.

import asyncio
import json
import logging
import uuid
from typing import Any

from app.core.config import settings
from app.db.session import engine
from app.models.journal import Journal
from app.models.analysis import Analysis
from app.models.user import User
from app.core.datetime_utils import utcnow
from app.services.retry_backoff import compute_exponential_backoff_seconds
from sqlmodel import Session

logger = logging.getLogger(__name__)

QUEUE_KEY_ANALYSIS = "haven:queue:journal_analysis"
QUEUE_KEY_NOTIFY = "haven:queue:journal_notify"
QUEUE_KEY_ANALYSIS_DLQ = "haven:queue:journal_analysis_dlq"
QUEUE_KEY_NOTIFY_DLQ = "haven:queue:journal_notify_dlq"
_BLOCK_TIMEOUT = 5
_worker_task: asyncio.Task[None] | None = None
_queue_client: Any = None

# Worker resilience constants
_MAX_WORKER_RESTARTS = 5
_RESTART_BASE_DELAY = 5.0
_JOB_TIMEOUT_SECONDS = 120  # 2 minutes max per analysis job


def _classify_job_exception(exc: Exception) -> str:
    if isinstance(exc, asyncio.TimeoutError):
        return "timeout"
    if isinstance(exc, (json.JSONDecodeError, ValueError, TypeError)):
        return "payload_error"
    if isinstance(exc, OSError):
        return "transport_error"
    return "unexpected_error"


def _enqueue_dead_letter(
    *,
    client: Any,
    queue_key: str,
    job_type: str,
    reason: str,
    payload_str: str,
) -> None:
    if client is None:
        return
    dead_letter = {
        "job_type": job_type,
        "reason": reason,
        "failed_at": utcnow().isoformat(),
        "payload": str(payload_str)[:2000],
    }
    try:
        client.rpush(queue_key, json.dumps(dead_letter, ensure_ascii=True, sort_keys=True))
    except Exception as exc:
        logger.warning(
            "Dead-letter enqueue failed: queue=%s reason=%s error=%s",
            queue_key,
            reason,
            type(exc).__name__,
        )


def _get_queue_client():  # sync Redis for rpush/blpop (singleton with ping check)
    global _queue_client
    if not (settings.REDIS_URL and (settings.REDIS_URL or "").strip()):
        return None
    if not getattr(settings, "ASYNC_JOURNAL_ANALYSIS", True):
        return None
    if _queue_client is not None:
        try:
            _queue_client.ping()
            return _queue_client
        except Exception:
            _queue_client = None
    try:
        import redis
        _queue_client = redis.Redis.from_url(
            (settings.REDIS_URL or "").strip(),
            decode_responses=True,
        )
        return _queue_client
    except Exception as e:
        logger.warning("Queue Redis client unavailable: %s", type(e).__name__)
        return None


def is_async_journal_analysis_enabled() -> bool:
    """True when journal create should enqueue analysis (non-blocking)."""
    return _get_queue_client() is not None


def enqueue_journal_analysis(
    *,
    journal_id: uuid.UUID,
    user_id: uuid.UUID,
    relationship_weather_hint: str | None = None,
    relationship_mode: str | None = None,
) -> bool:
    """Push a journal analysis job. Returns True if enqueued, False if queue unavailable."""
    client = _get_queue_client()
    if not client:
        return False
    payload = {
        "journal_id": str(journal_id),
        "user_id": str(user_id),
        "relationship_weather_hint": relationship_weather_hint,
        "relationship_mode": relationship_mode,
    }
    try:
        client.rpush(QUEUE_KEY_ANALYSIS, json.dumps(payload))
        return True
    except Exception as e:
        logger.warning("Enqueue journal analysis failed: %s", type(e).__name__)
        return False


def enqueue_journal_notification(journal_id: uuid.UUID) -> bool:
    """Push a partner notification job for a journal. Returns True if enqueued."""
    client = _get_queue_client()
    if not client:
        return False
    payload = {"journal_id": str(journal_id)}
    try:
        client.rpush(QUEUE_KEY_NOTIFY, json.dumps(payload))
        return True
    except Exception as e:
        logger.warning("Enqueue journal notification failed: %s", type(e).__name__)
        return False


async def run_analysis_job(payload_str: str) -> None:
    """Load journal, run AI analysis, persist Analysis and score, then enqueue notify."""
    try:
        payload = json.loads(payload_str)
        journal_id = uuid.UUID(payload["journal_id"])
        user_id = uuid.UUID(payload["user_id"])
        relationship_weather_hint = payload.get("relationship_weather_hint") or None
        relationship_mode = payload.get("relationship_mode") or None
    except (KeyError, ValueError, TypeError) as e:
        logger.warning("Invalid analysis job payload: %s", type(e).__name__)
        return

    from app.services.ai import analyze_journal
    from app.services.gamification import apply_journal_score_once, compute_journal_score_delta
    from app.services.audit_log import record_audit_event
    from app.services.conflict_detection import detect_conflict_risk
    from app.services.mediation_runtime import trigger_mediation

    conflict_triggered_for_partner: uuid.UUID | None = None  # partner_id to notify after commit

    with Session(engine) as session:
        journal = session.get(Journal, journal_id)
        if not journal:
            logger.warning("Analysis job: journal not found id=%s", journal_id)
            return
        user = session.get(User, user_id)
        if not user:
            logger.warning("Analysis job: user not found id=%s", user_id)
            return

        try:
            ai_result = await analyze_journal(
                journal.content or "",
                relationship_weather_hint=relationship_weather_hint,
                relationship_mode=relationship_mode,
            )
        except Exception as e:
            logger.error("Analysis job AI failed: %s", type(e).__name__)
            ai_result = {}

        if ai_result:
            conflict_risk = detect_conflict_risk(journal.content or "")
            new_analysis = Analysis(
                journal_id=journal.id,
                mood_label=ai_result.get("mood_label"),
                emotional_needs=ai_result.get("emotional_needs"),
                advice_for_user=ai_result.get("advice_for_user"),
                action_for_user=ai_result.get("action_for_user"),
                advice_for_partner=ai_result.get("advice_for_partner"),
                action_for_partner=ai_result.get("action_for_partner"),
                card_recommendation=ai_result.get("card_recommendation"),
                safety_tier=ai_result.get("safety_tier", 0),
                conflict_risk_detected=conflict_risk,
                prompt_version=ai_result.get("prompt_version", "unknown"),
                model_version=ai_result.get("model_version"),
                parse_success=bool(ai_result.get("parse_success", False)),
            )
            session.add(new_analysis)
            session.flush()
            if conflict_risk and user.partner_id:
                partner = session.get(User, user.partner_id)
                if partner and partner.partner_id == user.id:
                    trigger_mediation(
                        session=session,
                        user_id_1=user.id,
                        user_id_2=partner.id,
                        triggered_by_journal_id=journal.id,
                    )
                    conflict_triggered_for_partner = partner.id
            score_candidate = compute_journal_score_delta(ai_result)
            if score_candidate > 0:
                apply_journal_score_once(
                    session=session,
                    current_user=user,
                    journal_id=journal.id,
                    journal_content=journal.content or "",
                    event_at=journal.created_at,
                    candidate_delta=score_candidate,
                )
            record_audit_event(
                session=session,
                actor_user_id=user.id,
                action="JOURNAL_ANALYSIS_ASYNC",
                resource_type="journal",
                resource_id=journal.id,
                metadata={"has_analysis": True},
            )
        else:
            record_audit_event(
                session=session,
                actor_user_id=user.id,
                action="JOURNAL_ANALYSIS_ASYNC",
                resource_type="journal",
                resource_id=journal.id,
                metadata={"has_analysis": False},
            )
        session.commit()

    if conflict_triggered_for_partner:
        from app.services.notification_payloads import build_partner_notification_payload
        from app.services.notification import queue_partner_notification
        with Session(engine) as session:
            journal = session.get(Journal, journal_id)
            user = session.get(User, user_id) if journal else None
            partner = session.get(User, conflict_triggered_for_partner) if user else None
            if user and partner:
                for sender, receiver in ((user, partner), (partner, user)):
                    payload = build_partner_notification_payload(
                        session=session,
                        sender_user=sender,
                        event_type="mediation_invite",
                        scope_id=journal_id,
                        source_session_id=journal_id,
                        partner_user_id=receiver.id,
                    )
                    if payload:
                        queue_partner_notification(action_type="mediation_invite", event_type="mediation_invite", **payload)

    enqueue_journal_notification(journal_id)
    logger.info("Analysis job completed journal_id=%s", journal_id)


def run_notification_job(payload_str: str) -> None:
    """Load journal and user, build partner payload, call queue_partner_notification."""
    try:
        payload = json.loads(payload_str)
        journal_id = uuid.UUID(payload["journal_id"])
    except (KeyError, ValueError, TypeError) as e:
        logger.warning("Invalid notify job payload: %s", type(e).__name__)
        return

    from app.services.notification_payloads import build_partner_notification_payload
    from app.services.notification import queue_partner_notification

    with Session(engine) as session:
        journal = session.get(Journal, journal_id)
        if not journal:
            logger.warning("Notify job: journal not found id=%s", journal_id)
            return
        user = session.get(User, journal.user_id)
        if not user:
            logger.warning("Notify job: user not found for journal_id=%s", journal_id)
            return
        payload_out = build_partner_notification_payload(
            session=session,
            sender_user=user,
            event_type="journal",
            scope_id=journal_id,
            source_session_id=journal_id,
        )
        if not payload_out:
            return
        queue_partner_notification(
            action_type="journal",
            **payload_out,
        )
    logger.debug("Notify job completed journal_id=%s", journal_id)


def _blpop_analysis(client: Any) -> tuple[str | None, str | None] | None:
    """Sync: block on analysis queue. Returns (key, value) or None."""
    result = client.blpop(QUEUE_KEY_ANALYSIS, timeout=_BLOCK_TIMEOUT)
    return result

def _blpop_notify(client: Any) -> tuple[str | None, str | None] | None:
    """Sync: block on notify queue. Returns (key, value) or None."""
    result = client.blpop(QUEUE_KEY_NOTIFY, timeout=1)
    return result


async def _run_analysis_with_timeout(*, client: Any, payload_str: str) -> bool:
    """Run a single analysis job with timeout. Isolates failures from the worker loop."""
    try:
        await asyncio.wait_for(run_analysis_job(payload_str), timeout=_JOB_TIMEOUT_SECONDS)
        return True
    except asyncio.CancelledError:
        raise  # propagate for graceful shutdown
    except asyncio.TimeoutError:
        logger.error(
            "Analysis job timed out after %ds: %s",
            _JOB_TIMEOUT_SECONDS,
            payload_str[:200],
        )
        _enqueue_dead_letter(
            client=client,
            queue_key=QUEUE_KEY_ANALYSIS_DLQ,
            job_type="analysis",
            reason="timeout",
            payload_str=payload_str,
        )
        return False
    except (RuntimeError, ValueError, TypeError, OSError) as e:
        logger.error(
            "Analysis job failed: %s payload=%s",
            type(e).__name__,
            payload_str[:200],
        )
        _enqueue_dead_letter(
            client=client,
            queue_key=QUEUE_KEY_ANALYSIS_DLQ,
            job_type="analysis",
            reason=_classify_job_exception(e),
            payload_str=payload_str,
        )
        return False
    except Exception as e:
        logger.error(
            "Analysis job failed (unclassified): %s payload=%s",
            type(e).__name__,
            payload_str[:200],
        )
        _enqueue_dead_letter(
            client=client,
            queue_key=QUEUE_KEY_ANALYSIS_DLQ,
            job_type="analysis",
            reason="unexpected_error",
            payload_str=payload_str,
        )
        return False


def get_journal_queue_depth() -> dict[str, int]:
    """Return current queue depth for health monitoring. -1 if unavailable."""
    client = _get_queue_client()
    if not client:
        return {"analysis": -1, "notify": -1, "analysis_dlq": -1, "notify_dlq": -1}
    try:
        return {
            "analysis": client.llen(QUEUE_KEY_ANALYSIS),
            "notify": client.llen(QUEUE_KEY_NOTIFY),
            "analysis_dlq": client.llen(QUEUE_KEY_ANALYSIS_DLQ),
            "notify_dlq": client.llen(QUEUE_KEY_NOTIFY_DLQ),
        }
    except (RuntimeError, OSError, ValueError, TypeError):
        return {"analysis": -1, "notify": -1, "analysis_dlq": -1, "notify_dlq": -1}


async def _worker_loop() -> None:
    """Run analysis and notification workers with auto-restart on crash.

    Uses executor for blocking Redis blpop. On unhandled exception, the worker
    restarts with exponential backoff up to _MAX_WORKER_RESTARTS times.
    """
    for restart in range(_MAX_WORKER_RESTARTS):
        client = _get_queue_client()
        if not client:
            logger.info("Journal queue workers skipped: no Redis queue client")
            return
        try:
            if restart > 0:
                delay = compute_exponential_backoff_seconds(
                    attempt=min(restart - 1, 3),
                    base_seconds=_RESTART_BASE_DELAY,
                    max_seconds=40.0,
                    jitter_ratio=0.0,
                )
                logger.warning(
                    "Queue worker restarting (%d/%d) after %.0fs",
                    restart + 1,
                    _MAX_WORKER_RESTARTS,
                    delay,
                )
                await asyncio.sleep(delay)
            loop = asyncio.get_event_loop()
            logger.info("Journal queue workers started (attempt %d/%d)", restart + 1, _MAX_WORKER_RESTARTS)
            while True:
                # Block in thread to avoid blocking event loop
                result = await loop.run_in_executor(None, _blpop_analysis, client)
                if result and result[1]:
                    await _run_analysis_with_timeout(client=client, payload_str=result[1])
                # Drain notify queue (non-blocking then process)
                while True:
                    nr = await loop.run_in_executor(None, _blpop_notify, client)
                    if not nr or not nr[1]:
                        break
                    try:
                        run_notification_job(nr[1])
                    except (RuntimeError, ValueError, TypeError, OSError) as exc:
                        logger.error(
                            "Notify job failed: %s payload=%s",
                            type(exc).__name__,
                            str(nr[1])[:200],
                        )
                        _enqueue_dead_letter(
                            client=client,
                            queue_key=QUEUE_KEY_NOTIFY_DLQ,
                            job_type="notify",
                            reason=_classify_job_exception(exc),
                            payload_str=nr[1],
                        )
                    except Exception as exc:
                        logger.error(
                            "Notify job failed (unclassified): %s payload=%s",
                            type(exc).__name__,
                            str(nr[1])[:200],
                        )
                        _enqueue_dead_letter(
                            client=client,
                            queue_key=QUEUE_KEY_NOTIFY_DLQ,
                            job_type="notify",
                            reason="unexpected_error",
                            payload_str=nr[1],
                        )
        except asyncio.CancelledError:
            logger.info("Journal queue workers cancelled")
            return  # graceful shutdown — do not restart
        except Exception as e:
            logger.error(
                "Queue worker crashed (%d/%d): %s",
                restart + 1,
                _MAX_WORKER_RESTARTS,
                type(e).__name__,
                exc_info=True,
            )
    logger.critical("Queue worker exhausted all %d restarts, stopping permanently", _MAX_WORKER_RESTARTS)


def start_journal_queue_workers() -> None:
    """Start background asyncio task for analysis/notify queue. Idempotent."""
    global _worker_task
    if not (settings.REDIS_URL and (settings.REDIS_URL or "").strip()):
        return
    if not getattr(settings, "ASYNC_JOURNAL_ANALYSIS", True):
        return
    if _worker_task is not None and not _worker_task.done():
        return
    _worker_task = asyncio.create_task(_worker_loop())
    logger.info("Journal queue workers task created")


async def stop_journal_queue_workers() -> None:
    """Cancel background queue workers. Call on app shutdown (await from lifespan)."""
    global _worker_task
    if _worker_task is None:
        return
    _worker_task.cancel()
    try:
        await _worker_task
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.warning("Stop journal queue workers: %s", type(e).__name__)
    _worker_task = None
    logger.info("Journal queue workers stopped")
