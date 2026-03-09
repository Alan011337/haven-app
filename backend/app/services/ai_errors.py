from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HavenAIError(Exception):
    reason: str
    retryable: bool = False
    provider: str | None = None

    def __str__(self) -> str:
        return f"{self.reason}:{self.provider or 'generic'}"


class HavenAITimeoutError(HavenAIError):
    pass


class HavenAIProviderError(HavenAIError):
    pass


class HavenAISchemaError(HavenAIError):
    pass


class HavenAIPolicyError(HavenAIError):
    pass
