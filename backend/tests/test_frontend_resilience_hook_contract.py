from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class FrontendResilienceHookContractTests(unittest.TestCase):
    def test_optimistic_sync_helper_exists_with_expected_api(self) -> None:
        helper_path = ROOT / "frontend/src/lib/optimistic-sync.ts"
        self.assertTrue(helper_path.exists())
        content = helper_path.read_text(encoding="utf-8")
        self.assertIn("enqueueOptimisticJournalFailure", content)
        self.assertIn("clearOptimisticSyncQueue", content)
        self.assertIn("getOptimisticSyncQueueSize", content)

    def test_journal_mutation_uses_optimistic_sync_fallback(self) -> None:
        hook_path = ROOT / "frontend/src/hooks/queries/useJournalMutations.ts"
        content = hook_path.read_text(encoding="utf-8")
        self.assertIn("enqueueOptimisticJournalFailure", content)
        self.assertIn("logClientError", content)
        self.assertIn("onError", content)

    def test_websocket_hook_contains_adaptive_reconnect_and_fallback_markers(self) -> None:
        hook_path = ROOT / "frontend/src/hooks/useSocket.ts"
        policy_path = ROOT / "frontend/src/hooks/socket-reconnect-policy.ts"
        hook_content = hook_path.read_text(encoding="utf-8")
        policy_content = policy_path.read_text(encoding="utf-8")
        self.assertIn("DEFAULT_RETRY_JITTER_RATIO", policy_content)
        self.assertIn("SERVER_PRESSURE_CLOSE_CODES", policy_content)
        self.assertIn("emitRealtimeFallback", hook_content)
        self.assertIn("ws_reconnect_attempted", hook_content)

    def test_posthog_loader_enforces_host_allowlist_and_optional_sri(self) -> None:
        lib_path = ROOT / "frontend/src/lib/posthog.ts"
        content = lib_path.read_text(encoding="utf-8")
        self.assertIn("ALLOWED_POSTHOG_SCRIPT_HOSTS", content)
        self.assertIn("NEXT_PUBLIC_POSTHOG_SCRIPT_SRC", content)
        self.assertIn("NEXT_PUBLIC_POSTHOG_SCRIPT_INTEGRITY", content)
        self.assertIn("script.integrity", content)
        self.assertIn("parsed.protocol !== 'https:'", content)

    def test_frontend_lint_script_supports_changed_scope(self) -> None:
        lint_path = ROOT / "frontend/scripts/lint.mjs"
        content = lint_path.read_text(encoding="utf-8")
        self.assertIn("LINT_SCOPE", content)
        self.assertIn("resolveChangedTargets", content)
        self.assertIn("spawnSync('git', args", content)
        self.assertIn("lintScope === 'changed'", content)


if __name__ == "__main__":
    unittest.main()
