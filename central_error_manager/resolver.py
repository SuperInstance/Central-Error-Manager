"""ErrorResolver — strategy-based error resolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from .error import ManagedError, ErrorSeverity
from .classifier import ErrorCategory


class ResolutionStrategy(Enum):
    """Built-in resolution strategies."""
    RETRY = "retry"
    FALLBACK = "fallback"
    ESCALATE = "escalate"
    IGNORE = "ignore"


@dataclass
class Resolution:
    """Outcome of a resolution attempt."""
    strategy: ResolutionStrategy
    success: bool
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Type for custom resolvers: (error, category) -> Resolution
ResolverFunc = Callable[[ManagedError, ErrorCategory], Resolution]


class ErrorResolver:
    """Resolve errors using configurable strategies by category and severity."""

    def __init__(self) -> None:
        self._strategies: dict[str, ResolutionStrategy] = {}
        self._custom_resolvers: list[ResolverFunc] = []
        self._history: list[tuple[ManagedError, Resolution]] = []
        self._set_defaults()

    def _set_defaults(self) -> None:
        """Default strategy mapping by category."""
        self._strategies = {
            ErrorCategory.NETWORK.value: ResolutionStrategy.RETRY,
            ErrorCategory.TIMEOUT.value: ResolutionStrategy.RETRY,
            ErrorCategory.AUTH.value: ResolutionStrategy.ESCALATE,
            ErrorCategory.RESOURCE.value: ResolutionStrategy.ESCALATE,
            ErrorCategory.LOGIC.value: ResolutionStrategy.FALLBACK,
            ErrorCategory.CONFIGURATION.value: ResolutionStrategy.ESCALATE,
            ErrorCategory.UNKNOWN.value: ResolutionStrategy.FALLBACK,
        }

    def set_strategy(self, category: ErrorCategory, strategy: ResolutionStrategy) -> None:
        self._strategies[category.value] = strategy

    def add_custom_resolver(self, resolver: ResolverFunc) -> None:
        self._custom_resolvers.append(resolver)

    def resolve(self, error: ManagedError, category: ErrorCategory) -> Resolution:
        """Attempt to resolve an error using matching strategy."""
        # Try custom resolvers first
        for resolver in self._custom_resolvers:
            result = resolver(error, category)
            if result.success:
                self._history.append((error, result))
                error.resolve()
                return result

        # Fall back to strategy-based resolution
        strategy = self._strategies.get(category.value, ResolutionStrategy.FALLBACK)
        resolution = self._apply_strategy(error, category, strategy)

        self._history.append((error, resolution))
        if resolution.success:
            error.resolve()
        return resolution

    def _apply_strategy(
        self, error: ManagedError, category: ErrorCategory, strategy: ResolutionStrategy
    ) -> Resolution:
        if strategy == ResolutionStrategy.RETRY:
            return self._retry(error, category)
        elif strategy == ResolutionStrategy.FALLBACK:
            return self._fallback(error, category)
        elif strategy == ResolutionStrategy.ESCALATE:
            return self._escalate(error, category)
        elif strategy == ResolutionStrategy.IGNORE:
            return Resolution(strategy=strategy, success=True, message="Error ignored per policy")
        return Resolution(strategy=strategy, success=False, message="Unknown strategy")

    def _retry(self, error: ManagedError, category: ErrorCategory) -> Resolution:
        max_retries = 3
        current = error.context.get("retry_count", 0)
        if current < max_retries:
            error.context["retry_count"] = current + 1
            return Resolution(
                strategy=ResolutionStrategy.RETRY,
                success=True,
                message=f"Retry {current + 1}/{max_retries}",
                details={"retry_count": current + 1},
            )
        return Resolution(
            strategy=ResolutionStrategy.RETRY,
            success=False,
            message=f"Max retries ({max_retries}) exceeded",
        )

    def _fallback(self, error: ManagedError, category: ErrorCategory) -> Resolution:
        fallback_available = error.context.get("fallback", False)
        if fallback_available:
            return Resolution(
                strategy=ResolutionStrategy.FALLBACK,
                success=True,
                message="Fallback path activated",
                details={"fallback": True},
            )
        return Resolution(
            strategy=ResolutionStrategy.FALLBACK,
            success=False,
            message="No fallback available",
        )

    def _escalate(self, error: ManagedError, category: ErrorCategory) -> Resolution:
        error.severity = ErrorSeverity.HIGH
        return Resolution(
            strategy=ResolutionStrategy.ESCALATE,
            success=False,
            message=f"Escalated: {category.value} error requires human attention",
            details={"escalated": True, "new_severity": "high"},
        )

    @property
    def history(self) -> list[tuple[ManagedError, Resolution]]:
        return list(self._history)
