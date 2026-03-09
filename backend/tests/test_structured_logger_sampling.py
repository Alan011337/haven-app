from __future__ import annotations

import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.structured_logger import should_sample_event  # noqa: E402


class StructuredLoggerSamplingTests(unittest.TestCase):
    def test_should_sample_event_honors_bounds(self) -> None:
        self.assertTrue(should_sample_event(sample_key="k", sample_rate=1.0))
        self.assertFalse(should_sample_event(sample_key="k", sample_rate=0.0))
        self.assertTrue(should_sample_event(sample_key="k", sample_rate=2.0))
        self.assertFalse(should_sample_event(sample_key="k", sample_rate=-1.0))

    def test_should_sample_event_is_deterministic_for_same_key(self) -> None:
        first = should_sample_event(sample_key="ws-send-failed:user-1", sample_rate=0.25)
        second = should_sample_event(sample_key="ws-send-failed:user-1", sample_rate=0.25)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
