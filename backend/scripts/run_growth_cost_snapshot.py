#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _iso_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _load_optional_json(path_value: str) -> dict:
    if not path_value:
        return {}
    path = Path(path_value)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate combined growth + unit economics snapshot.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--core-loop-summary", default="")
    parser.add_argument("--outbox-summary", default="")
    parser.add_argument("--active-couples", type=int, default=0)
    parser.add_argument("--ai-cost-usd", type=float, default=0.0)
    parser.add_argument("--push-cost-usd", type=float, default=0.0)
    parser.add_argument("--db-cost-usd", type=float, default=0.0)
    parser.add_argument("--ws-cost-usd", type=float, default=0.0)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    core_loop = _load_optional_json(args.core_loop_summary)
    outbox = _load_optional_json(args.outbox_summary)

    active_couples = max(0, int(args.active_couples))
    total_cost = float(args.ai_cost_usd) + float(args.push_cost_usd) + float(args.db_cost_usd) + float(args.ws_cost_usd)
    per_active_couple = (total_cost / active_couples) if active_couples > 0 else None

    payload = {
        "schema_version": "v1",
        "recorded_at": _iso_now(),
        "growth": {
            "core_loop": core_loop,
            "outbox": outbox,
        },
        "cost": {
            "ai_cost_usd": float(args.ai_cost_usd),
            "push_cost_usd": float(args.push_cost_usd),
            "db_cost_usd": float(args.db_cost_usd),
            "ws_cost_usd": float(args.ws_cost_usd),
            "total_cost_usd": total_cost,
            "active_couples": active_couples,
            "per_active_couple_cost_usd": per_active_couple,
        },
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")

    print("[growth-cost-snapshot] result")
    print(f"  output: {output_path}")
    print(f"  total_cost_usd: {total_cost}")
    print(f"  active_couples: {active_couples}")
    print(f"  per_active_couple_cost_usd: {per_active_couple if per_active_couple is not None else 'n/a'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
