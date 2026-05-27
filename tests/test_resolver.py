"""Tests for ErrorResolver."""

import pytest

from central_error_manager.error import ManagedError, ErrorSeverity, ErrorStatus
from central_error_manager.classifier import ErrorCategory
from central_error_manager.resolver import ErrorResolver, ResolutionStrategy, Resolution


class TestErrorResolver:
    def setup_method(self):
        self.resolver = ErrorResolver()

    def test_retry_strategy_succeeds(self):
        err = ManagedError(message="conn refused", error_type="ConnectionError", source="svc")
        result = self.resolver.resolve(err, ErrorCategory.NETWORK)
        assert result.strategy == ResolutionStrategy.RETRY
        assert result.success
        assert result.details["retry_count"] == 1

    def test_retry_exhausts(self):
        err = ManagedError(message="conn refused", error_type="ConnectionError", source="svc")
        for _ in range(3):
            self.resolver.resolve(err, ErrorCategory.NETWORK)
        # 4th attempt should fail
        err.status = ErrorStatus.OPEN  # reopen for test
        result = self.resolver.resolve(err, ErrorCategory.NETWORK)
        assert not result.success

    def test_fallback_succeeds(self):
        err = ManagedError(
            message="not found",
            error_type="ValueError",
            source="svc",
            context={"fallback": True},
        )
        result = self.resolver.resolve(err, ErrorCategory.LOGIC)
        assert result.strategy == ResolutionStrategy.FALLBACK
        assert result.success

    def test_fallback_fails(self):
        err = ManagedError(message="not found", error_type="ValueError", source="svc")
        result = self.resolver.resolve(err, ErrorCategory.LOGIC)
        assert not result.success

    def test_escalate(self):
        err = ManagedError(message="unauthorized", error_type="AuthError", source="svc")
        result = self.resolver.resolve(err, ErrorCategory.AUTH)
        assert result.strategy == ResolutionStrategy.ESCALATE
        assert not result.success
        assert err.severity == ErrorSeverity.HIGH

    def test_ignore_strategy(self):
        self.resolver.set_strategy(ErrorCategory.UNKNOWN, ResolutionStrategy.IGNORE)
        err = ManagedError(message="weird", error_type="WeirdError", source="svc")
        result = self.resolver.resolve(err, ErrorCategory.UNKNOWN)
        assert result.success
        assert result.strategy == ResolutionStrategy.IGNORE

    def test_custom_resolver(self):
        def my_resolver(error, category):
            if "magic" in error.message:
                return Resolution(
                    strategy=ResolutionStrategy.FALLBACK,
                    success=True,
                    message="Magic resolver handled it",
                )
            return Resolution(strategy=ResolutionStrategy.FALLBACK, success=False)

        self.resolver.add_custom_resolver(my_resolver)
        err = ManagedError(message="magic failure", source="svc")
        result = self.resolver.resolve(err, ErrorCategory.LOGIC)
        assert result.success
        assert "Magic" in result.message

    def test_history(self):
        err = ManagedError(message="x", source="svc", context={"fallback": True})
        self.resolver.resolve(err, ErrorCategory.LOGIC)
        assert len(self.resolver.history) == 1

    def test_resolve_marks_error_resolved(self):
        err = ManagedError(message="x", source="svc", context={"fallback": True})
        assert err.is_open
        self.resolver.resolve(err, ErrorCategory.LOGIC)
        assert err.is_resolved
