# P2-D: Conflict resolution — detect high-risk keywords in journal content.

from __future__ import annotations

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 高風險關鍵字：觸發調解模式（可依產品調整）
CONFLICT_RISK_KEYWORDS = [
    "分手", "討厭", "生氣", "恨", "離婚", "結束", "不想在一起",
    "受夠", "絕望", "放棄", "不愛了", "冷戰", "吵架", "爭吵",
]
_CONFLICT_PATTERN: Optional[re.Pattern[str]] = None


def _get_pattern() -> re.Pattern[str]:
    global _CONFLICT_PATTERN
    if _CONFLICT_PATTERN is None:
        escaped = [re.escape(k) for k in CONFLICT_RISK_KEYWORDS]
        _CONFLICT_PATTERN = re.compile("|".join(escaped), re.IGNORECASE)
    return _CONFLICT_PATTERN


def detect_conflict_risk(content: str) -> bool:
    """Return True if content contains any conflict-risk keyword (triggers mediation mode)."""
    if not content or not content.strip():
        return False
    return _get_pattern().search(content) is not None
