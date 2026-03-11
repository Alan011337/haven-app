from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTEND_FLY_TOML = ROOT / "frontend" / "fly.toml"
FRONTEND_NEXT_CONFIG = ROOT / "frontend" / "next.config.ts"
FRONTEND_API_PROXY_ROUTE = ROOT / "frontend" / "src" / "app" / "api" / "[...path]" / "route.ts"
FRONTEND_HEALTH_PROXY_ROUTE = ROOT / "frontend" / "src" / "app" / "health" / "[...path]" / "route.ts"


class FrontendFlyDeployContractTests(unittest.TestCase):
    def test_frontend_fly_config_uses_same_origin_api_url_and_public_backend_proxy(self) -> None:
        config = tomllib.loads(FRONTEND_FLY_TOML.read_text(encoding="utf-8"))
        build_args = config["build"]["args"]
        env = config["env"]

        self.assertEqual(build_args["NEXT_PUBLIC_API_URL"], "https://haven-web-prod.fly.dev/api")
        self.assertEqual(env["NEXT_PUBLIC_API_URL"], "https://haven-web-prod.fly.dev/api")
        self.assertEqual(build_args["NEXT_PUBLIC_WS_URL"], "wss://haven-api-prod.fly.dev")
        self.assertEqual(env["NEXT_PUBLIC_WS_URL"], "wss://haven-api-prod.fly.dev")
        self.assertEqual(build_args["API_PROXY_TARGET"], "https://haven-api-prod.fly.dev/api")
        self.assertEqual(env["API_PROXY_TARGET"], "https://haven-api-prod.fly.dev/api")

    def test_frontend_fly_config_declares_explicit_dockerfile(self) -> None:
        config = tomllib.loads(FRONTEND_FLY_TOML.read_text(encoding="utf-8"))
        self.assertEqual(config["build"]["dockerfile"], "Dockerfile.fly")

    def test_frontend_uses_route_handlers_for_api_and_health_proxy(self) -> None:
        next_config = FRONTEND_NEXT_CONFIG.read_text(encoding="utf-8")
        api_route = FRONTEND_API_PROXY_ROUTE.read_text(encoding="utf-8")
        health_route = FRONTEND_HEALTH_PROXY_ROUTE.read_text(encoding="utf-8")

        self.assertNotIn("source: '/api/:path*'", next_config)
        self.assertNotIn("source: '/health/:path*'", next_config)
        self.assertIn("proxyApiRequest", api_route)
        self.assertIn("proxyHealthRequest", health_route)

    def test_frontend_dockerfile_installs_python_for_env_check(self) -> None:
        dockerfile = (ROOT / "frontend" / "Dockerfile.fly").read_text(encoding="utf-8")
        self.assertIn("apk add --no-cache python3", dockerfile)

    def test_frontend_dockerfile_skips_worktree_materialization_in_builder(self) -> None:
        dockerfile = (ROOT / "frontend" / "Dockerfile.fly").read_text(encoding="utf-8")
        self.assertIn("ENV SKIP_WORKTREE_MATERIALIZATION_CHECK=1", dockerfile)

    def test_frontend_dockerfile_sets_runtime_env_in_runner_stage(self) -> None:
        dockerfile = (ROOT / "frontend" / "Dockerfile.fly").read_text(encoding="utf-8")
        runner_stage = dockerfile.split("FROM node:22-alpine AS runner", maxsplit=1)[1]

        self.assertIn("ARG NEXT_PUBLIC_API_URL", runner_stage)
        self.assertIn("ARG NEXT_PUBLIC_WS_URL", runner_stage)
        self.assertIn("ARG API_PROXY_TARGET", runner_stage)
        self.assertIn("ENV SKIP_WORKTREE_MATERIALIZATION_CHECK=1", runner_stage)
        self.assertIn("ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}", runner_stage)
        self.assertIn("ENV NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL}", runner_stage)
        self.assertIn("ENV API_PROXY_TARGET=${API_PROXY_TARGET}", runner_stage)


if __name__ == "__main__":
    unittest.main()
