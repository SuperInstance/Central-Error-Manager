"""Tests for ErrorManager."""

import pytest
from datetime import datetime, timezone

from central_error_manager.error import ManagedError, ErrorSeverity, ErrorStatus
from central_error_manager.manager import ErrorManager


class TestErrorManager:
    def setup_method(self):
        self.mgr = ErrorManager()

    def test_record_new_error(self):
        err = ManagedError(message="fail", error_type="ValueError", source="svc")
        result = self.mgr.record(err)
        assert result.fingerprint == err.fingerprint
        assert self.mgr.unique_count() == 1

    def test_dedup_merges(self):
        e1 = ManagedError(message="fail", error_type="ValueError", source="svc")
        e2 = ManagedError(message="fail", error_type="ValueError", source="svc")
        self.mgr.record(e1)
        self.mgr.record(e2)
        assert self.mgr.unique_count() == 1
        assert self.mgr.total_count() == 2

    def test_different_errors_not_merged(self):
        e1 = ManagedError(message="fail A", source="svc")
        e2 = ManagedError(message="fail B", source="svc")
        self.mgr.record(e1)
        self.mgr.record(e2)
        assert self.mgr.unique_count() == 2

    def test_record_exception(self):
        try:
            raise RuntimeError("boom")
        except RuntimeError as exc:
            err = self.mgr.record_exception(exc, source="test", severity=ErrorSeverity.HIGH)
        assert err.message == "boom"
        assert err.error_type == "RuntimeError"

    def test_get_by_fingerprint(self):
        err = ManagedError(message="x", error_type="E", source="s")
        self.mgr.record(err)
        assert self.mgr.get(err.fingerprint) is not None

    def test_get_by_id(self):
        err = ManagedError(message="x", error_type="E", source="s")
        self.mgr.record(err)
        assert self.mgr.get_by_id(err.error_id) is not None

    def test_open_errors(self):
        e1 = ManagedError(message="open", source="s")
        e2 = ManagedError(message="closed", source="s")
        e2.resolve()
        self.mgr.record(e1)
        self.mgr.record(e2)
        assert len(self.mgr.open_errors()) == 1

    def test_by_severity(self):
        e1 = ManagedError(message="a", source="s", severity=ErrorSeverity.CRITICAL)
        e2 = ManagedError(message="b", source="s", severity=ErrorSeverity.LOW)
        self.mgr.record(e1)
        self.mgr.record(e2)
        assert len(self.mgr.by_severity(ErrorSeverity.CRITICAL)) == 1
        assert len(self.mgr.by_severity(ErrorSeverity.LOW)) == 1

    def test_by_source(self):
        e1 = ManagedError(message="a", source="svc-a")
        e2 = ManagedError(message="b", source="svc-b")
        self.mgr.record(e1)
        self.mgr.record(e2)
        assert len(self.mgr.by_source("svc-a")) == 1

    def test_by_tag(self):
        e1 = ManagedError(message="a", source="s", tags=["api"])
        e2 = ManagedError(message="b", source="s", tags=["cron"])
        self.mgr.record(e1)
        self.mgr.record(e2)
        assert len(self.mgr.by_tag("api")) == 1

    def test_resolve(self):
        err = ManagedError(message="x", source="s")
        self.mgr.record(err)
        result = self.mgr.resolve(err.fingerprint)
        assert result.is_resolved

    def test_resolve_all(self):
        e1 = ManagedError(message="a", source="svc")
        e2 = ManagedError(message="b", source="svc")
        e3 = ManagedError(message="c", source="other")
        self.mgr.record(e1)
        self.mgr.record(e2)
        self.mgr.record(e3)
        count = self.mgr.resolve_all(source="svc")
        assert count == 2

    def test_clear_resolved(self):
        e1 = ManagedError(message="a", source="s")
        e2 = ManagedError(message="b", source="s")
        self.mgr.record(e1)
        self.mgr.record(e2)
        self.mgr.resolve(e1.fingerprint)
        removed = self.mgr.clear_resolved()
        assert removed == 1
        assert self.mgr.unique_count() == 1

    def test_hooks(self):
        recorded = []
        self.mgr.on("on_record", lambda e: recorded.append(e))
        err = ManagedError(message="x", source="s")
        self.mgr.record(err)
        assert len(recorded) == 1

    def test_resolve_hook(self):
        resolved = []
        self.mgr.on("on_resolve", lambda e: resolved.append(e))
        err = ManagedError(message="x", source="s")
        self.mgr.record(err)
        self.mgr.resolve(err.fingerprint)
        assert len(resolved) == 1

    def test_reset(self):
        self.mgr.record(ManagedError(message="a", source="s"))
        self.mgr.reset()
        assert self.mgr.unique_count() == 0
