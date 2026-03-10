from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTEND_FLY_TOML = ROOT / "frontend" / "fly.toml"
FRONTEND_NEXT_CONFIG = ROOT / "frontend" / "next.config.ts"


class FrontendFlyDeployContractTests(unittest.TestCase):
    def test_frontend_fly_config_uses_same_origin_api_url(self) -> None:
        config = tomllib.loads(FRONTEND_FLY_TOML.read_text(encoding="utf-8"))
        build_args = config["build"]["args"]
        env = config["env"]

        self.assertEqual(build_args["NEXT_PUBLIC_API_URL"], "https://haven-web-prod.fly.dev/api")
        self.assertEqual(env["NEXT_PUBLIC_API_URL"], "https://haven-web-prod.fly.dev/api")
        self.assertEqual(build_args["API_PROXY_TARGET"], "https://haven-api-prod.fly.dev/api")
        self.assertEqual(env["API_PROXY_TARGET"], "https://haven-api-prod.fly.dev/api")

    def test_next_config_rewrites_api_to_proxy_target(self) -> None:
        text = FRONTEND_NEXT_CONFIG.read_text(encoding="utf-8")
        self.assertIn("resolveApiProxyTarget", text)
        self.assertIn("source: '/api/:path*'", text)
        self.assertIn("destination: `${apiProxyTarget}/:path*`", text)
        self.assertIn("process.env.API_PROXY_TARGET", text)

    def test_frontend_dockerfile_installs_python_for_env_check(self) -> None:
        dockerfile = (ROOT / "frontend" / "Dockerfile.fly").read_text(encoding="utf-8")
        self.assertIn("apk add --no-cache python3", dockerfile)


if __name__ == "__main__":
    unittest.main()
