"""Tests for ManagedError data model."""

import pytest
from datetime import datetime, timezone, timedelta

from central_error_manager.error import (
    ManagedError,
    ErrorSeverity,
    ErrorStatus,
    _fingerprint,
)


class TestManagedError:
    def test_basic_creation(self):
        err = ManagedError(message="something broke")
        assert err.message == "something broke"
        assert err.error_type == "Exception"
        assert err.severity == ErrorSeverity.MEDIUM
        assert err.status == ErrorStatus.OPEN
        assert err.occurrences == 1
        assert err.fingerprint
        assert err.error_id

    def test_fingerprint_deterministic(self):
        e1 = ManagedError(message="fail", error_type="ValueError", source="svc")
        e2 = ManagedError(message="fail", error_type="ValueError", source="svc")
        assert e1.fingerprint == e2.fingerprint

    def test_fingerprint_differs_for_different_errors(self):
        e1 = ManagedError(message="fail A", error_type="ValueError", source="svc")
        e2 = ManagedError(message="fail B", error_type="TypeError", source="svc")
        assert e1.fingerprint != e2.fingerprint

    def test_from_exception(self):
        try:
            raise ValueError("bad value")
        except ValueError as exc:
            err = ManagedError.from_exception(exc, source="test", severity=ErrorSeverity.HIGH)
        assert err.message == "bad value"
        assert err.error_type == "ValueError"
        assert err.severity == ErrorSeverity.HIGH
        assert err.source == "test"
        assert "ValueError" in err.traceback_str

    def test_resolve(self):
        err = ManagedError(message="x")
        assert err.is_open
        err.resolve()
        assert err.is_resolved
        assert err.resolved_at is not None

    def test_acknowledge(self):
        err = ManagedError(message="x")
        err.acknowledge()
        assert err.status == ErrorStatus.ACKNOWLEDGED

    def test_suppress(self):
        err = ManagedError(message="x")
        err.suppress()
        assert err.status == ErrorStatus.SUPPRESSED

    def test_merge_same_fingerprint(self):
        e1 = ManagedError(message="fail", error_type="Err", source="s")
        e2 = ManagedError(message="fail", error_type="Err", source="s")
        e1.merge(e2)
        assert e1.occurrences == 2

    def test_merge_different_fingerprint_raises(self):
        e1 = ManagedError(message="a", error_type="Err", source="s")
        e2 = ManagedError(message="b", error_type="Err", source="s")
        with pytest.raises(ValueError, match="different fingerprints"):
            e1.merge(e2)

    def test_custom_fingerprint_preserved(self):
        err = ManagedError(message="x", fingerprint="custom-fp")
        assert err.fingerprint == "custom-fp"

    def test_tags_and_context(self):
        err = ManagedError(
            message="x",
            context={"user": "alice", "request_id": "abc"},
            tags=["api", "v2"],
        )
        assert err.context["user"] == "alice"
        assert "api" in err.tags
