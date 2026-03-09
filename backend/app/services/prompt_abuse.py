from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class PromptAbuseMatch:
    pattern_id: str
    reason: str
    matched_text: str


@dataclass(frozen=True)
class PromptAbuseResult:
    flagged: bool
    matches: tuple[PromptAbuseMatch, ...]


# Minimal policy-backed regex baseline for prompt-abuse detection.
_PROMPT_ABUSE_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    (
        "ignore_system_prompt",
        "Attempts to override system instructions",
        re.compile(r"\b(ignore|bypass|override)\b.{0,40}\b(system|developer)\b.{0,40}\b(prompt|instruction)s?\b", re.IGNORECASE),
    ),
    (
        "reveal_hidden_prompt",
        "Attempts to exfiltrate hidden prompt/policy",
        re.compile(r"\b(reveal|show|print|dump|leak)\b.{0,40}\b(system prompt|hidden prompt|policy|guardrail)\b", re.IGNORECASE),
    ),
    (
        "jailbreak_roleplay",
        "Classic jailbreak roleplay markers",
        re.compile(r"\b(DAN|do anything now|jailbreak|developer mode)\b", re.IGNORECASE),
    ),
)


def detect_prompt_abuse(content: str) -> PromptAbuseResult:
    if not isinstance(content, str) or not content.strip():
        return PromptAbuseResult(flagged=False, matches=())

    matches: list[PromptAbuseMatch] = []
    for pattern_id, reason, regex in _PROMPT_ABUSE_PATTERNS:
        matched = regex.search(content)
        if matched:
            matches.append(
                PromptAbuseMatch(
                    pattern_id=pattern_id,
                    reason=reason,
                    matched_text=matched.group(0)[:120],
                )
            )

    return PromptAbuseResult(flagged=bool(matches), matches=tuple(matches))


def iter_prompt_abuse_pattern_ids() -> Iterable[str]:
    for pattern_id, _, _ in _PROMPT_ABUSE_PATTERNS:
        yield pattern_id
