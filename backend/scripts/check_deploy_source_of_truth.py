#!/usr/bin/env python3
"""Check deployment source-of-truth contract (Fly active, Render archived)."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_FLY = REPO_ROOT / "backend" / "fly.toml"
FRONTEND_FLY = REPO_ROOT / "frontend" / "fly.toml"
RENDER_BLUEPRINT = REPO_ROOT / "render.yaml"
DEPLOY_FLY_SCRIPT = REPO_ROOT / "scripts" / "deploy-fly-backend.sh"
MAKEFILE = REPO_ROOT / "Makefile"
BACKEND_FLY_REQUIRED_MARKERS = (
    'AI_ROUTER_SHARED_STATE_BACKEND = "redis"',
)
RENDER_REQUIRED_MARKERS = (
    "ARCHIVED DEPLOY BLUEPRINT",
    "Fly.io",
    "historical reference",
    "- key: AI_ROUTER_SHARED_STATE_BACKEND",
    "- key: AI_ROUTER_REDIS_URL",
)


def collect_violations() -> list[str]:
    violations: list[str] = []
    if not BACKEND_FLY.exists():
        violations.append("missing_backend_fly_toml")
    if not FRONTEND_FLY.exists():
        violations.append("missing_frontend_fly_toml")
    if not DEPLOY_FLY_SCRIPT.exists():
        violations.append("missing_deploy_fly_backend_script")
    if not MAKEFILE.exists():
        violations.append("missing_makefile")
    else:
        makefile_text = MAKEFILE.read_text(encoding="utf-8")
        for marker in ("release-check", "release-check-full", "security-gate-fast"):
            if marker not in makefile_text:
                violations.append(f"makefile_missing_target_marker:{marker}")
    if not RENDER_BLUEPRINT.exists():
        violations.append("missing_render_yaml")
    else:
        text = RENDER_BLUEPRINT.read_text(encoding="utf-8")
        for marker in RENDER_REQUIRED_MARKERS:
            if marker not in text:
                violations.append(f"render_yaml_missing_marker:{marker}")
    if BACKEND_FLY.exists():
        backend_fly_text = BACKEND_FLY.read_text(encoding="utf-8")
        for marker in BACKEND_FLY_REQUIRED_MARKERS:
            if marker not in backend_fly_text:
                violations.append(f"backend_fly_missing_marker:{marker}")
    return violations


def main() -> int:
    violations = collect_violations()
    if violations:
        print("[deploy-sot-contract] fail")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print("[deploy-sot-contract] pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
