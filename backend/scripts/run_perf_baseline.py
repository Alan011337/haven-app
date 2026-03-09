#!/usr/bin/env python3
"""Run backend synthetic performance baseline checks for key CUJ paths."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from statistics import median
from time import perf_counter

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.security import get_password_hash, verify_password  # noqa: E402
from app.models.analysis import Analysis  # noqa: E402
from app.models.card import Card, CardCategory, CardDeck  # noqa: E402
from app.models.card_response import CardResponse, ResponseStatus  # noqa: E402
from app.models.card_session import CardSession, CardSessionMode, CardSessionStatus  # noqa: E402
from app.models.journal import Journal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import memory_archive  # noqa: E402


def _percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    idx = int(round((len(values) - 1) * ratio))
    idx = max(0, min(idx, len(values) - 1))
    return round(float(values[idx]), 3)


def _run_benchmark(iterations: int, fn) -> dict[str, float]:  # noqa: ANN001
    samples: list[float] = []
    for _ in range(max(1, int(iterations))):
        started = perf_counter()
        fn()
        samples.append((perf_counter() - started) * 1000.0)
    samples.sort()
    return {
        "sample_count": len(samples),
        "p50_ms": _percentile(samples, 0.50),
        "p95_ms": _percentile(samples, 0.95),
        "p99_ms": _percentile(samples, 0.99),
        "avg_ms": round(sum(samples) / len(samples), 3),
        "median_ms": round(float(median(samples)), 3),
    }


def _collect_sqlite_query_plan_samples(engine, *, user_id, partner_id) -> dict[str, list[str]]:  # noqa: ANN001
    plans: dict[str, list[str]] = {}
    queries = {
        "timeline_journals": (
            "SELECT id, created_at FROM journals WHERE user_id = :user_id ORDER BY created_at DESC LIMIT 20",
            {"user_id": str(user_id)},
        ),
        "timeline_card_sessions": (
            (
                "SELECT id, created_at FROM card_sessions "
                "WHERE creator_id IN (:user_id, :partner_id) OR partner_id IN (:user_id, :partner_id) "
                "ORDER BY created_at DESC LIMIT 20"
            ),
            {"user_id": str(user_id), "partner_id": str(partner_id)},
        ),
    }
    with engine.connect() as connection:
        for query_name, (sql, params) in queries.items():
            rows = connection.exec_driver_sql(f"EXPLAIN QUERY PLAN {sql}", params).all()
            plans[query_name] = [
                " | ".join(str(part) for part in row if part is not None)
                for row in rows
            ]
    return plans


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run synthetic backend performance baseline")
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--auth-p95-budget-ms", type=float, default=120.0)
    parser.add_argument("--journal-write-p95-budget-ms", type=float, default=250.0)
    parser.add_argument("--card-write-p95-budget-ms", type=float, default=250.0)
    parser.add_argument("--timeline-query-p95-budget-ms", type=float, default=300.0)
    parser.add_argument(
        "--output",
        default="",
        help="Optional output JSON path.",
    )
    parser.add_argument(
        "--fail-on-budget-breach",
        action="store_true",
        help="Exit non-zero when any probe breaches budget.",
    )
    return parser


def _setup_fixture_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


def _seed_fixture(engine):  # noqa: ANN001
    with Session(engine) as session:
        user = User(
            email="perf-baseline@example.com",
            full_name="Perf Baseline",
            hashed_password="hashed",
        )
        partner = User(
            email="perf-baseline-partner@example.com",
            full_name="Perf Baseline Partner",
            hashed_password="hashed",
        )
        session.add(user)
        session.add(partner)
        session.flush()

        deck = CardDeck(name="Perf Deck", description="perf fixture")
        session.add(deck)
        session.flush()

        card = Card(
            category=CardCategory.DAILY_VIBE,
            title="Perf card",
            description="Perf desc",
            question="Perf question?",
            deck_id=deck.id,
        )
        session.add(card)
        session.flush()

        for idx in range(30):
            journal = Journal(
                user_id=user.id,
                content=f"journal fixture {idx}",
                mood="calm",
            )
            session.add(journal)
            session.flush()
            session.add(
                Analysis(
                    journal_id=journal.id,
                    mood_label="calm",
                    parse_success=True,
                )
            )

        for idx in range(20):
            card_session = CardSession(
                creator_id=user.id,
                partner_id=partner.id,
                card_id=card.id,
                category=CardCategory.DAILY_VIBE.value,
                mode=CardSessionMode.DECK,
                status=CardSessionStatus.COMPLETED,
            )
            session.add(card_session)
            session.flush()
            session.add(
                CardResponse(
                    card_id=card.id,
                    user_id=user.id,
                    session_id=card_session.id,
                    content=f"my answer {idx}",
                    status=ResponseStatus.REVEALED,
                )
            )
            session.add(
                CardResponse(
                    card_id=card.id,
                    user_id=partner.id,
                    session_id=card_session.id,
                    content=f"partner answer {idx}",
                    status=ResponseStatus.REVEALED,
                )
            )

        user_id = user.id
        partner_id = partner.id
        card_id = card.id
        session.commit()
    return user_id, partner_id, card_id


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    iterations = max(1, int(args.iterations))
    engine = _setup_fixture_engine()
    try:
        user_id, partner_id, card_id = _seed_fixture(engine)
        password_hash = get_password_hash("perf-password")

        def bench_auth_verify() -> None:
            assert verify_password("perf-password", password_hash)

        def bench_journal_write() -> None:
            with Session(engine) as session:
                session.add(
                    Journal(
                        user_id=user_id,
                        content=f"write-{uuid.uuid4().hex}",
                        mood="calm",
                    )
                )
                session.commit()

        def bench_card_write() -> None:
            with Session(engine) as session:
                session.add(
                    CardResponse(
                        card_id=card_id,
                        user_id=user_id,
                        session_id=None,
                        content=f"card-write-{uuid.uuid4().hex}",
                        status=ResponseStatus.PENDING,
                    )
                )
                session.commit()

        def bench_timeline_query() -> None:
            with Session(engine) as session:
                _items, _has_more, _cursor = memory_archive.get_unified_timeline(
                    session=session,
                    user_id=user_id,
                    partner_id=partner_id,
                    limit=20,
                )

        results = {
            "auth_verify": _run_benchmark(iterations, bench_auth_verify),
            "journal_write": _run_benchmark(iterations, bench_journal_write),
            "card_write": _run_benchmark(iterations, bench_card_write),
            "timeline_query": _run_benchmark(iterations, bench_timeline_query),
        }
        budgets = {
            "auth_verify": float(args.auth_p95_budget_ms),
            "journal_write": float(args.journal_write_p95_budget_ms),
            "card_write": float(args.card_write_p95_budget_ms),
            "timeline_query": float(args.timeline_query_p95_budget_ms),
        }
        evaluation = {
            name: ("pass" if values["p95_ms"] <= budgets[name] else "fail")
            for name, values in results.items()
        }
        failures = sorted(name for name, status in evaluation.items() if status != "pass")
        payload = {
            "artifact_kind": "backend-perf-baseline",
            "schema_version": "v1",
            "iterations": iterations,
            "budgets_p95_ms": budgets,
            "results": results,
            "evaluation": evaluation,
            "query_plan_samples": _collect_sqlite_query_plan_samples(
                engine,
                user_id=user_id,
                partner_id=partner_id,
            ),
            "status": "pass" if not failures else "fail",
            "failures": failures,
        }
        serialized = json.dumps(payload, ensure_ascii=True, indent=2) + "\n"
        if args.output:
            out_path = Path(args.output).resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(serialized, encoding="utf-8")
        print(serialized, end="")
        if args.fail_on_budget_breach and failures:
            return 1
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
