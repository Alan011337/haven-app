from __future__ import annotations

import ast
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SESSION_PATH = BACKEND_ROOT / "app" / "db" / "session.py"


class DbPoolRuntimeSnapshotContractTests(unittest.TestCase):
    def test_query_runtime_snapshot_contract_keys_present(self) -> None:
        text = SESSION_PATH.read_text(encoding="utf-8")
        self.assertIn('"slow_query_threshold_ms"', text)
        self.assertIn('"query_total"', text)
        self.assertIn('"slow_query_total"', text)
        self.assertIn('"last_slow_query_fingerprint"', text)
        self.assertIn('"last_slow_query_duration_ms"', text)

    def test_runtime_counter_keys_include_query_and_slow_query(self) -> None:
        tree = ast.parse(SESSION_PATH.read_text(encoding="utf-8"))
        assign_nodes: list[ast.AST] = [
            node
            for node in tree.body
            if (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(t, ast.Name) and t.id == "_DB_RUNTIME_COUNTERS"
                    for t in node.targets
                )
            )
            or (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == "_DB_RUNTIME_COUNTERS"
            )
        ]
        self.assertTrue(assign_nodes, "_DB_RUNTIME_COUNTERS assignment not found")
        first = assign_nodes[0]
        counters_node = first.value if isinstance(first, (ast.Assign, ast.AnnAssign)) else None
        self.assertIsInstance(counters_node, ast.Dict)
        keys = {
            k.value
            for k in counters_node.keys
            if isinstance(k, ast.Constant) and isinstance(k.value, str)
        }
        self.assertIn("query_total", keys)
        self.assertIn("slow_query_total", keys)


if __name__ == "__main__":
    unittest.main()
