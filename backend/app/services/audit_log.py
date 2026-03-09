import json
import logging
import uuid
from typing import Any, Mapping, Optional

from sqlmodel import Session

from app.api.error_handling import commit_with_error_handling
from app.models.audit_event import AuditEvent, AuditEventOutcome

logger = logging.getLogger(__name__)


def _serialize_metadata(metadata: Optional[Mapping[str, Any]]) -> Optional[str]:
    if not metadata:
        return None
    return json.dumps(metadata, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def record_audit_event(
    *,
    session: Session,
    actor_user_id: Optional[uuid.UUID],
    action: str,
    resource_type: str,
    resource_id: Optional[uuid.UUID] = None,
    target_user_id: Optional[uuid.UUID] = None,
    outcome: AuditEventOutcome = AuditEventOutcome.SUCCESS,
    reason: Optional[str] = None,
    metadata: Optional[Mapping[str, Any]] = None,
) -> None:
    event = AuditEvent(
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=outcome,
        reason=reason,
        metadata_json=_serialize_metadata(metadata),
    )
    session.add(event)


def record_audit_event_best_effort(
    *,
    session: Session,
    actor_user_id: Optional[uuid.UUID],
    action: str,
    resource_type: str,
    resource_id: Optional[uuid.UUID] = None,
    target_user_id: Optional[uuid.UUID] = None,
    outcome: AuditEventOutcome = AuditEventOutcome.SUCCESS,
    reason: Optional[str] = None,
    metadata: Optional[Mapping[str, Any]] = None,
    commit: bool = False,
) -> None:
    try:
        record_audit_event(
            session=session,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            target_user_id=target_user_id,
            outcome=outcome,
            reason=reason,
            metadata=metadata,
        )
        if commit:
            try:
                commit_with_error_handling(
                    session,
                    logger=logger,
                    action="audit_event_best_effort",
                    conflict_detail="Audit event conflict.",
                    failure_detail="Audit event persist failed.",
                )
            except Exception as exc:
                session.rollback()
                logger.error(
                    "Failed to persist audit event action=%s reason=%s",
                    action,
                    type(exc).__name__,
                )
    except Exception as exc:
        if commit:
            session.rollback()
        logger.error(
            "Failed to persist audit event action=%s reason=%s",
            action,
            type(exc).__name__,
        )
