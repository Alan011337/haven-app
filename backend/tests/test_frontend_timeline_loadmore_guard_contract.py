from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
TIMELINE_HOOK_PATH = REPO_ROOT / "frontend" / "src" / "features" / "memory" / "useMemoryData.ts"


def test_timeline_loadmore_guard_contract_present() -> None:
    text = TIMELINE_HOOK_PATH.read_text(encoding="utf-8")
    assert "LOAD_MORE_MIN_INTERVAL_MS" in text
    assert "loadMoreLockedRef" in text
    assert "lastLoadMoreAtRef" in text
    assert "if (timelineQuery.isFetching) return;" in text
    assert "if (nextCursor === timelineCursor) return;" in text
