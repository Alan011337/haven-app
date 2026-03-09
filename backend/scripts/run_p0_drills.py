#!/usr/bin/env python3
"""Run P0-C/P0-D drills and write reproducible evidence files."""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.deps import get_current_user  # noqa: E402
from app.api.routers import billing, users  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models.analysis import Analysis  # noqa: E402
from app.models.audit_event import AuditEvent  # noqa: E402
from app.models.billing import BillingLedgerEntry, BillingWebhookReceipt  # noqa: E402
from app.models.billing import BillingCustomerBinding, BillingEntitlementState  # noqa: E402
from app.models.card import Card, CardCategory  # noqa: E402
from app.models.card_response import CardResponse, ResponseStatus  # noqa: E402
from app.models.card_session import CardSession, CardSessionMode, CardSessionStatus  # noqa: E402
from app.models.journal import Journal  # noqa: E402
from app.models.notification_event import (  # noqa: E402
    NotificationActionType,
    NotificationDeliveryStatus,
    NotificationEvent,
)
from app.models.user import User  # noqa: E402


@dataclass
class DrillResult:
    name: str
    ok: bool
    detail: str


P0_DRILL_SCHEMA_VERSION = "1.1.0"
P0_DRILL_ARTIFACT_KIND = "p0-drill"
P0_DRILL_GENERATED_BY = "backend/scripts/run_p0_drills.py"
P0_DRILL_CONTRACT_MODE = "strict"
P0_DRILL_REQUIRED_CHECKS: tuple[str, ...] = (
    "data_rights_export_scope",
    "data_rights_erase_integrity",
    "data_rights_audit_trail",
    "billing_state_change_idempotency",
    "billing_reconciliation_health",
    "billing_webhook_binding_resolution",
    "billing_webhook_identifier_conflict_guard",
    "billing_webhook_transition_guard",
    "billing_webhook_replay_safety",
)
DATA_RIGHTS_FIRE_DRILL_ARTIFACT_KIND = "data-rights-fire-drill"
DATA_RIGHTS_FIRE_DRILL_REQUIRED_CHECKS: tuple[str, ...] = (
    "data_rights_export_scope",
    "data_rights_erase_integrity",
    "data_rights_audit_trail",
)
BILLING_FIRE_DRILL_ARTIFACT_KIND = "billing-fire-drill"
BILLING_FIRE_DRILL_REQUIRED_CHECKS: tuple[str, ...] = (
    "billing_state_change_idempotency",
    "billing_reconciliation_health",
    "billing_webhook_binding_resolution",
    "billing_webhook_identifier_conflict_guard",
    "billing_webhook_transition_guard",
    "billing_webhook_replay_safety",
)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _stripe_signature(secret: str, payload_text: str, timestamp: int) -> str:
    signed_payload = f"{timestamp}.{payload_text}"
    digest = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


def _build_app(engine, state: dict[str, Any]) -> TestClient:
    app = FastAPI()
    app.include_router(users.router, prefix="/api/users")
    app.include_router(billing.router, prefix="/api/billing")

    def override_get_session() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    def override_get_current_user() -> User:
        current_user_id = state.get("current_user_id")
        if current_user_id is None:
            raise RuntimeError("current_user_id is not set")
        with Session(engine) as session:
            user = session.get(User, current_user_id)
            if not user:
                raise RuntimeError("user not found")
            return user

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app)


def _seed_data_rights_fixture(engine) -> dict[str, Any]:
    with Session(engine) as session:
        user_a = User(email="drill-a@example.com", full_name="Drill A", hashed_password="hashed")
        user_b = User(email="drill-b@example.com", full_name="Drill B", hashed_password="hashed")
        user_c = User(email="drill-c@example.com", full_name="Drill C", hashed_password="hashed")
        user_a.partner_id = user_b.id
        user_b.partner_id = user_a.id

        card = Card(
            category=CardCategory.DAILY_VIBE,
            title="Drill Card",
            description="drill",
            question="How are you feeling?",
            difficulty_level=1,
            is_ai_generated=False,
        )
        session.add(user_a)
        session.add(user_b)
        session.add(user_c)
        session.add(card)
        session.commit()
        session.refresh(user_a)
        session.refresh(user_b)
        session.refresh(user_c)
        session.refresh(card)

        journal_a = Journal(content="drill journal a", user_id=user_a.id)
        journal_b = Journal(content="drill journal b", user_id=user_b.id)
        session.add(journal_a)
        session.add(journal_b)
        session.commit()
        session.refresh(journal_a)
        session.refresh(journal_b)

        session.add(Analysis(journal_id=journal_a.id, mood_label="calm"))
        session.add(Analysis(journal_id=journal_b.id, mood_label="happy"))

        shared_session = CardSession(
            card_id=card.id,
            creator_id=user_a.id,
            partner_id=user_b.id,
            category=CardCategory.DAILY_VIBE.value,
            mode=CardSessionMode.DECK,
            status=CardSessionStatus.COMPLETED,
        )
        unrelated_session = CardSession(
            card_id=card.id,
            creator_id=user_b.id,
            partner_id=user_c.id,
            category=CardCategory.DAILY_VIBE.value,
            mode=CardSessionMode.DECK,
            status=CardSessionStatus.PENDING,
        )
        session.add(shared_session)
        session.add(unrelated_session)
        session.commit()
        session.refresh(shared_session)
        session.refresh(unrelated_session)

        session.add(
            CardResponse(
                card_id=card.id,
                user_id=user_a.id,
                content="a-shared",
                session_id=shared_session.id,
                status=ResponseStatus.REVEALED,
                is_initiator=True,
            )
        )
        session.add(
            CardResponse(
                card_id=card.id,
                user_id=user_b.id,
                content="b-shared",
                session_id=shared_session.id,
                status=ResponseStatus.REVEALED,
                is_initiator=False,
            )
        )
        session.add(
            CardResponse(
                card_id=card.id,
                user_id=user_b.id,
                content="b-unrelated",
                session_id=unrelated_session.id,
                status=ResponseStatus.PENDING,
                is_initiator=True,
            )
        )
        session.add(
            NotificationEvent(
                action_type=NotificationActionType.JOURNAL,
                status=NotificationDeliveryStatus.SENT,
                receiver_user_id=user_a.id,
                sender_user_id=user_b.id,
                receiver_email=user_a.email,
                dedupe_key="drill-a-recv",
            )
        )
        session.add(
            NotificationEvent(
                action_type=NotificationActionType.CARD,
                status=NotificationDeliveryStatus.SENT,
                receiver_user_id=user_c.id,
                sender_user_id=user_b.id,
                receiver_email=user_c.email,
                dedupe_key="drill-unrelated",
            )
        )
        session.commit()

        return {
            "user_a_id": user_a.id,
            "user_b_id": user_b.id,
            "user_c_id": user_c.id,
            "shared_session_id": shared_session.id,
            "unrelated_session_id": unrelated_session.id,
        }


def _run_data_rights_drill(client: TestClient, engine, state: dict[str, Any]) -> list[DrillResult]:
    results: list[DrillResult] = []

    state["current_user_id"] = state["user_a_id"]
    export_response = client.get("/api/users/me/data-export")
    export_ok = export_response.status_code == 200
    export_detail = f"status={export_response.status_code}"
    if export_ok:
        payload = export_response.json()
        export_ok = (
            payload.get("user", {}).get("id") == str(state["user_a_id"])
            and len(payload.get("journals", [])) == 1
            and len(payload.get("notification_events", [])) == 1
        )
        export_detail = (
            f"journals={len(payload.get('journals', []))}, "
            f"notifications={len(payload.get('notification_events', []))}"
        )
    results.append(DrillResult(name="data_rights_export_scope", ok=export_ok, detail=export_detail))

    erase_response = client.delete("/api/users/me/data")
    erase_ok = erase_response.status_code == 200
    erase_detail = f"status={erase_response.status_code}"
    if erase_ok:
        with Session(engine) as session:
            deleted_user = session.get(User, state["user_a_id"])
            partner_user = session.get(User, state["user_b_id"])
            shared_session = session.get(CardSession, state["shared_session_id"])
            unrelated_session = session.get(CardSession, state["unrelated_session_id"])
            erase_ok = (
                deleted_user is None
                and partner_user is not None
                and partner_user.partner_id is None
                and shared_session is None
                and unrelated_session is not None
            )
            erase_detail = (
                "deleted_user="
                f"{deleted_user is None},partner_unpaired={partner_user.partner_id is None if partner_user else False},"
                f"shared_deleted={shared_session is None},unrelated_preserved={unrelated_session is not None}"
            )
    results.append(DrillResult(name="data_rights_erase_integrity", ok=erase_ok, detail=erase_detail))

    with Session(engine) as session:
        export_audit = session.exec(
            select(AuditEvent).where(
                AuditEvent.action == "USER_DATA_EXPORT",
                AuditEvent.resource_id == state["user_a_id"],
            )
        ).first()
        erase_audit = session.exec(
            select(AuditEvent).where(
                AuditEvent.action == "USER_DATA_ERASE",
                AuditEvent.resource_id == state["user_a_id"],
            )
        ).first()
        audit_ok = export_audit is not None and erase_audit is not None
        audit_detail = (
            f"export={'yes' if export_audit else 'no'},"
            f"erase={'yes' if erase_audit else 'no'}"
        )
    results.append(DrillResult(name="data_rights_audit_trail", ok=audit_ok, detail=audit_detail))

    return results


def _run_billing_drill(client: TestClient, engine, state: dict[str, Any]) -> list[DrillResult]:
    results: list[DrillResult] = []
    state["current_user_id"] = state["user_b_id"]

    headers = {"Idempotency-Key": "drill-billing-key-1"}
    first = client.post(
        "/api/billing/state-change",
        headers=headers,
        json={"action": "UPGRADE", "target_plan": "PREMIUM"},
    )
    second = client.post(
        "/api/billing/state-change",
        headers=headers,
        json={"action": "UPGRADE", "target_plan": "PREMIUM"},
    )
    third = client.post(
        "/api/billing/state-change",
        headers=headers,
        json={"action": "DOWNGRADE", "target_plan": "FREE"},
    )

    idempotency_ok = (
        first.status_code == 200
        and second.status_code == 200
        and second.json().get("idempotency_replayed") is True
        and third.status_code == 409
    )
    idempotency_detail = (
        f"first={first.status_code},second={second.status_code},"
        f"second_replayed={second.json().get('idempotency_replayed') if second.status_code == 200 else None},"
        f"mismatch={third.status_code}"
    )
    results.append(
        DrillResult(
            name="billing_state_change_idempotency",
            ok=idempotency_ok,
            detail=idempotency_detail,
        )
    )

    reconciliation = client.get("/api/billing/reconciliation")
    reconciliation_ok = (
        reconciliation.status_code == 200
        and reconciliation.json().get("healthy") is True
        and reconciliation.json().get("command_count") == 1
        and reconciliation.json().get("missing_command_ledger_count") == 0
    )
    reconciliation_detail = (
        f"status={reconciliation.status_code},"
        f"healthy={reconciliation.json().get('healthy') if reconciliation.status_code == 200 else None},"
        f"command_count={reconciliation.json().get('command_count') if reconciliation.status_code == 200 else None},"
        "missing_command_ledger_count="
        f"{reconciliation.json().get('missing_command_ledger_count') if reconciliation.status_code == 200 else None}"
    )
    results.append(
        DrillResult(
            name="billing_reconciliation_health",
            ok=reconciliation_ok,
            detail=reconciliation_detail,
        )
    )

    original_secret = settings.BILLING_STRIPE_WEBHOOK_SECRET
    original_tolerance = settings.BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS
    settings.BILLING_STRIPE_WEBHOOK_SECRET = "whsec_drill"
    settings.BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS = 300
    try:
        bind_event = {
            "id": "evt_drill_binding_1",
            "type": "invoice.paid",
            "data": {
                "object": {
                    "customer": "cus_drill_binding_1",
                    "metadata": {"user_id": str(state["user_b_id"])},
                }
            },
        }
        bind_text = json.dumps(bind_event, separators=(",", ":"))
        bind_timestamp = int(time.time())
        bind_signature = _stripe_signature("whsec_drill", bind_text, bind_timestamp)
        bind_headers = {
            "Stripe-Signature": bind_signature,
            "Content-Type": "application/json",
        }
        bind_first = client.post(
            "/api/billing/webhooks/stripe",
            content=bind_text,
            headers=bind_headers,
        )

        follow_event = {
            "id": "evt_drill_binding_2",
            "type": "invoice.payment_failed",
            "data": {"object": {"customer": "cus_drill_binding_1"}},
        }
        follow_text = json.dumps(follow_event, separators=(",", ":"))
        follow_signature = _stripe_signature("whsec_drill", follow_text, bind_timestamp)
        follow_headers = {
            "Stripe-Signature": follow_signature,
            "Content-Type": "application/json",
        }
        bind_follow = client.post(
            "/api/billing/webhooks/stripe",
            content=follow_text,
            headers=follow_headers,
        )

        with Session(engine) as session:
            binding = session.exec(
                select(BillingCustomerBinding).where(
                    BillingCustomerBinding.provider == "STRIPE",
                    BillingCustomerBinding.provider_customer_id == "cus_drill_binding_1",
                )
            ).first()
            entitlement = session.exec(
                select(BillingEntitlementState).where(
                    BillingEntitlementState.user_id == state["user_b_id"]
                )
            ).first()
            binding_ok = (
                binding is not None
                and binding.user_id == state["user_b_id"]
                and entitlement is not None
                and entitlement.lifecycle_state == "PAST_DUE"
            )
            binding_detail = (
                f"first={bind_first.status_code},follow={bind_follow.status_code},"
                f"binding={'yes' if binding else 'no'},"
                f"entitlement_state={entitlement.lifecycle_state if entitlement else None}"
            )
        results.append(
            DrillResult(
                name="billing_webhook_binding_resolution",
                ok=binding_ok and bind_first.status_code == 200 and bind_follow.status_code == 200,
                detail=binding_detail,
            )
        )

        subscription_bind_event = {
            "id": "evt_drill_binding_3",
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_drill_conflict_1",
                    "metadata": {"user_id": str(state["user_c_id"])},
                }
            },
        }
        subscription_bind_text = json.dumps(subscription_bind_event, separators=(",", ":"))
        subscription_bind_signature = _stripe_signature(
            "whsec_drill", subscription_bind_text, bind_timestamp
        )
        subscription_bind_headers = {
            "Stripe-Signature": subscription_bind_signature,
            "Content-Type": "application/json",
        }
        subscription_bind_response = client.post(
            "/api/billing/webhooks/stripe",
            content=subscription_bind_text,
            headers=subscription_bind_headers,
        )

        identifier_conflict_event = {
            "id": "evt_drill_binding_4",
            "type": "invoice.paid",
            "data": {
                "object": {
                    "customer": "cus_drill_binding_1",
                    "subscription": "sub_drill_conflict_1",
                }
            },
        }
        identifier_conflict_text = json.dumps(identifier_conflict_event, separators=(",", ":"))
        identifier_conflict_signature = _stripe_signature(
            "whsec_drill", identifier_conflict_text, bind_timestamp
        )
        identifier_conflict_headers = {
            "Stripe-Signature": identifier_conflict_signature,
            "Content-Type": "application/json",
        }
        identifier_conflict_response = client.post(
            "/api/billing/webhooks/stripe",
            content=identifier_conflict_text,
            headers=identifier_conflict_headers,
        )

        identifier_conflict_ok = (
            subscription_bind_response.status_code == 200
            and identifier_conflict_response.status_code == 409
        )
        identifier_conflict_detail = (
            f"subscription_bind={subscription_bind_response.status_code},"
            f"conflict={identifier_conflict_response.status_code}"
        )
        results.append(
            DrillResult(
                name="billing_webhook_identifier_conflict_guard",
                ok=identifier_conflict_ok,
                detail=identifier_conflict_detail,
            )
        )

        transition_cancel_event = {
            "id": "evt_drill_transition_guard_1",
            "type": "customer.subscription.deleted",
            "data": {"object": {"customer": "cus_drill_binding_1"}},
        }
        transition_cancel_text = json.dumps(transition_cancel_event, separators=(",", ":"))
        transition_cancel_signature = _stripe_signature(
            "whsec_drill", transition_cancel_text, bind_timestamp
        )
        transition_cancel_headers = {
            "Stripe-Signature": transition_cancel_signature,
            "Content-Type": "application/json",
        }
        transition_cancel_response = client.post(
            "/api/billing/webhooks/stripe",
            content=transition_cancel_text,
            headers=transition_cancel_headers,
        )

        transition_invalid_paid_event = {
            "id": "evt_drill_transition_guard_2",
            "type": "invoice.paid",
            "data": {"object": {"customer": "cus_drill_binding_1"}},
        }
        transition_invalid_paid_text = json.dumps(
            transition_invalid_paid_event, separators=(",", ":")
        )
        transition_invalid_paid_signature = _stripe_signature(
            "whsec_drill", transition_invalid_paid_text, bind_timestamp
        )
        transition_invalid_paid_headers = {
            "Stripe-Signature": transition_invalid_paid_signature,
            "Content-Type": "application/json",
        }
        transition_invalid_paid_response = client.post(
            "/api/billing/webhooks/stripe",
            content=transition_invalid_paid_text,
            headers=transition_invalid_paid_headers,
        )

        with Session(engine) as session:
            transition_entitlement = session.exec(
                select(BillingEntitlementState).where(
                    BillingEntitlementState.user_id == state["user_b_id"]
                )
            ).first()
            transition_invalid_ledger = session.exec(
                select(BillingLedgerEntry).where(
                    BillingLedgerEntry.source_type == "WEBHOOK",
                    BillingLedgerEntry.source_key == "wh:stripe:evt_drill_transition_guard_2",
                )
            ).first()

        transition_guard_ok = (
            transition_cancel_response.status_code == 200
            and transition_invalid_paid_response.status_code == 409
            and transition_entitlement is not None
            and transition_entitlement.lifecycle_state == "CANCELED"
            and transition_invalid_ledger is None
        )
        transition_guard_detail = (
            f"cancel={transition_cancel_response.status_code},"
            f"invalid_paid={transition_invalid_paid_response.status_code},"
            f"entitlement_state={transition_entitlement.lifecycle_state if transition_entitlement else None},"
            f"invalid_ledger={'none' if transition_invalid_ledger is None else 'present'}"
        )
        results.append(
            DrillResult(
                name="billing_webhook_transition_guard",
                ok=transition_guard_ok,
                detail=transition_guard_detail,
            )
        )

        event = {
            "id": "evt_drill_replay_1",
            "type": "customer.subscription.deleted",
            "data": {"object": {"customer": "cus_drill_binding_1"}},
        }
        payload_text = json.dumps(event, separators=(",", ":"))
        timestamp = int(time.time())
        signature = _stripe_signature("whsec_drill", payload_text, timestamp)
        webhook_headers = {
            "Stripe-Signature": signature,
            "Content-Type": "application/json",
        }
        first_webhook = client.post(
            "/api/billing/webhooks/stripe",
            content=payload_text,
            headers=webhook_headers,
        )
        second_webhook = client.post(
            "/api/billing/webhooks/stripe",
            content=payload_text,
            headers=webhook_headers,
        )

        mismatch_event = {
            "id": "evt_drill_replay_1",
            "type": "invoice.payment_failed",
            "data": {"object": {"metadata": {"user_id": str(state["user_b_id"])}}},
        }
        mismatch_text = json.dumps(mismatch_event, separators=(",", ":"))
        mismatch_sig = _stripe_signature("whsec_drill", mismatch_text, timestamp)
        mismatch_headers = {
            "Stripe-Signature": mismatch_sig,
            "Content-Type": "application/json",
        }
        mismatch_webhook = client.post(
            "/api/billing/webhooks/stripe",
            content=mismatch_text,
            headers=mismatch_headers,
        )

        with Session(engine) as session:
            receipts = session.exec(
                select(BillingWebhookReceipt).where(
                    BillingWebhookReceipt.provider == "STRIPE",
                    BillingWebhookReceipt.provider_event_id == "evt_drill_replay_1",
                )
            ).all()
            receipt_count = len(receipts)
            webhook_ledgers = session.exec(
                select(BillingLedgerEntry).where(
                    BillingLedgerEntry.source_type == "WEBHOOK",
                    BillingLedgerEntry.source_key == "wh:stripe:evt_drill_replay_1",
                )
            ).all()
            webhook_ledger_count = len(webhook_ledgers)

        webhook_ok = (
            first_webhook.status_code == 200
            and second_webhook.status_code == 200
            and second_webhook.json().get("replayed") is True
            and mismatch_webhook.status_code == 409
            and receipt_count == 1
            and webhook_ledger_count == 1
        )
        webhook_detail = (
            f"first={first_webhook.status_code},second={second_webhook.status_code},"
            f"second_replayed={second_webhook.json().get('replayed') if second_webhook.status_code == 200 else None},"
            f"mismatch={mismatch_webhook.status_code},receipts={receipt_count},"
            f"webhook_ledgers={webhook_ledger_count}"
        )
    finally:
        settings.BILLING_STRIPE_WEBHOOK_SECRET = original_secret
        settings.BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS = original_tolerance

    results.append(DrillResult(name="billing_webhook_replay_safety", ok=webhook_ok, detail=webhook_detail))
    return results


def _write_evidence_artifact(
    *,
    evidence_dir: Path,
    stamp: str,
    generated_at_iso: str,
    artifact_kind: str,
    title: str,
    required_checks: tuple[str, ...],
    results: list[DrillResult],
) -> tuple[Path, Path]:
    result_names = {item.name for item in results}
    expected_names = set(required_checks)
    missing_required = sorted(expected_names - result_names)
    unexpected_checks = sorted(result_names - expected_names)
    if missing_required or unexpected_checks:
        raise RuntimeError(
            f"{artifact_kind} check contract mismatch: "
            f"missing={missing_required}, unexpected={unexpected_checks}"
        )

    checks_total = len(results)
    checks_passed = len([item for item in results if item.ok])
    checks_failed = checks_total - checks_passed

    payload = {
        "schema_version": P0_DRILL_SCHEMA_VERSION,
        "artifact_kind": artifact_kind,
        "generated_by": P0_DRILL_GENERATED_BY,
        "contract_mode": P0_DRILL_CONTRACT_MODE,
        "generated_at": generated_at_iso,
        "required_checks": sorted(required_checks),
        "checks_total": checks_total,
        "checks_passed": checks_passed,
        "checks_failed": checks_failed,
        "results": [asdict(item) for item in results],
        "all_passed": checks_failed == 0,
    }

    json_path = evidence_dir / f"{artifact_kind}-{stamp}.json"
    md_path = evidence_dir / f"{artifact_kind}-{stamp}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# {title}",
        "",
        f"- Schema version: {payload['schema_version']}",
        f"- Generated at (UTC): {payload['generated_at']}",
        f"- Overall: {'PASS' if payload['all_passed'] else 'FAIL'}",
        f"- Checks: total={payload['checks_total']} passed={payload['checks_passed']} failed={payload['checks_failed']}",
        "",
        "| Check | Result | Detail |",
        "| --- | --- | --- |",
    ]
    for item in results:
        lines.append(f"| `{item.name}` | {'PASS' if item.ok else 'FAIL'} | {item.detail} |")
    lines.append("")
    lines.append(f"- Raw JSON: `{json_path}`")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def _write_evidence(*, results: list[DrillResult]) -> dict[str, tuple[Path, Path]]:
    evidence_dir = REPO_ROOT / "docs" / "security" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    stamp = _utc_timestamp()
    generated_at_iso = datetime.now(timezone.utc).isoformat()
    results_by_name = {item.name: item for item in results}
    missing_data_rights = sorted(
        set(DATA_RIGHTS_FIRE_DRILL_REQUIRED_CHECKS) - set(results_by_name)
    )
    missing_billing = sorted(set(BILLING_FIRE_DRILL_REQUIRED_CHECKS) - set(results_by_name))
    if missing_data_rights or missing_billing:
        raise RuntimeError(
            "P0 drill subset check contract mismatch: "
            f"missing_data_rights={missing_data_rights}, missing_billing={missing_billing}"
        )

    data_rights_results = [results_by_name[name] for name in DATA_RIGHTS_FIRE_DRILL_REQUIRED_CHECKS]
    billing_results = [results_by_name[name] for name in BILLING_FIRE_DRILL_REQUIRED_CHECKS]

    outputs: dict[str, tuple[Path, Path]] = {}
    outputs[P0_DRILL_ARTIFACT_KIND] = _write_evidence_artifact(
        evidence_dir=evidence_dir,
        stamp=stamp,
        generated_at_iso=generated_at_iso,
        artifact_kind=P0_DRILL_ARTIFACT_KIND,
        title="P0 Drill Evidence",
        required_checks=P0_DRILL_REQUIRED_CHECKS,
        results=results,
    )
    outputs[DATA_RIGHTS_FIRE_DRILL_ARTIFACT_KIND] = _write_evidence_artifact(
        evidence_dir=evidence_dir,
        stamp=stamp,
        generated_at_iso=generated_at_iso,
        artifact_kind=DATA_RIGHTS_FIRE_DRILL_ARTIFACT_KIND,
        title="Data Rights Fire Drill Evidence",
        required_checks=DATA_RIGHTS_FIRE_DRILL_REQUIRED_CHECKS,
        results=data_rights_results,
    )
    outputs[BILLING_FIRE_DRILL_ARTIFACT_KIND] = _write_evidence_artifact(
        evidence_dir=evidence_dir,
        stamp=stamp,
        generated_at_iso=generated_at_iso,
        artifact_kind=BILLING_FIRE_DRILL_ARTIFACT_KIND,
        title="Billing Fire Drill Evidence",
        required_checks=BILLING_FIRE_DRILL_REQUIRED_CHECKS,
        results=billing_results,
    )
    return outputs


def main() -> int:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    state: dict[str, Any] = {"current_user_id": None}
    client = _build_app(engine, state)
    try:
        state.update(_seed_data_rights_fixture(engine))
        results = []
        results.extend(_run_data_rights_drill(client, engine, state))
        results.extend(_run_billing_drill(client, engine, state))
        evidence_paths = _write_evidence(results=results)

        print("[p0-drill]")
        for item in results:
            print(f"  - {item.name}: {'PASS' if item.ok else 'FAIL'} ({item.detail})")
        for artifact_kind in (
            P0_DRILL_ARTIFACT_KIND,
            DATA_RIGHTS_FIRE_DRILL_ARTIFACT_KIND,
            BILLING_FIRE_DRILL_ARTIFACT_KIND,
        ):
            json_path, md_path = evidence_paths[artifact_kind]
            print(f"  evidence_json[{artifact_kind}]: {json_path}")
            print(f"  evidence_md[{artifact_kind}]: {md_path}")

        if not all(item.ok for item in results):
            print("result: fail")
            return 1
        print("result: ok")
        return 0
    finally:
        client.close()
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
