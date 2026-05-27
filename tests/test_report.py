"""Tests for ErrorReport."""

import pytest
from datetime import datetime, timezone, timedelta

from central_error_manager.error import ManagedError, ErrorSeverity, ErrorStatus
from central_error_manager.manager import ErrorManager
from central_error_manager.classifier import ErrorClassifier, ErrorCategory
from central_error_manager.report import ErrorReport


class TestErrorReport:
    def setup_method(self):
        self.mgr = ErrorManager()
        self.clf = ErrorClassifier()
        self.report = ErrorReport(self.mgr, self.clf)

    def _make_resolved(self, message: str, source: str, minutes_ago: float = 5) -> ManagedError:
        ts = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
        err = ManagedError(message=message, source=source, timestamp=ts)
        err.resolve()
        return err

    def test_empty_summary(self):
        s = self.report.summary()
        assert s.total_unique == 0
        assert s.total_occurrences == 0
        assert s.open_count == 0

    def test_summary_counts(self):
        self.mgr.record(ManagedError(message="a", source="svc-a"))
        self.mgr.record(ManagedError(message="b", source="svc-b"))
        e3 = ManagedError(message="c", source="svc-c")
        e3.resolve()
        self.mgr.record(e3)

        s = self.report.summary()
        assert s.total_unique == 3
        assert s.open_count == 2
        assert s.resolved_count == 1

    def test_summary_by_severity(self):
        self.mgr.record(ManagedError(message="a", source="s", severity=ErrorSeverity.HIGH))
        self.mgr.record(ManagedError(message="b", source="s", severity=ErrorSeverity.LOW))
        s = self.report.summary()
        assert s.by_severity.get("high") == 1
        assert s.by_severity.get("low") == 1

    def test_summary_by_category(self):
        self.mgr.record(ManagedError(message="conn refused", error_type="ConnectionError", source="s"))
        self.mgr.record(ManagedError(message="invalid token", error_type="AuthError", source="s"))
        s = self.report.summary()
        assert s.by_category.get("network") == 1
        assert s.by_category.get("auth") == 1

    def test_summary_by_source(self):
        self.mgr.record(ManagedError(message="a", source="svc-a"))
        self.mgr.record(ManagedError(message="b", source="svc-b"))
        self.mgr.record(ManagedError(message="c", source="svc-a"))
        s = self.report.summary()
        assert s.by_source.get("svc-a") == 2
        assert s.by_source.get("svc-b") == 1

    def test_mttr_no_resolved(self):
        stats = self.report.mttr()
        assert stats.mttr_seconds == 0.0
        assert stats.resolved_count == 0

    def test_mttr_calculation(self):
        resolved = self._make_resolved("a", "s", minutes_ago=10)
        self.mgr.record(resolved)

        stats = self.report.mttr()
        assert stats.resolved_count == 1
        assert stats.mttr_seconds > 0
        assert stats.mttr_seconds >= 500  # ~10 min = 600s

    def test_mttr_multiple(self):
        self.mgr.record(self._make_resolved("a", "s", minutes_ago=10))
        self.mgr.record(self._make_resolved("b", "s", minutes_ago=20))
        stats = self.report.mttr()
        assert stats.resolved_count == 2
        assert stats.min_seconds < stats.max_seconds

    def test_trends(self):
        for i in range(5):
            err = ManagedError(message="frequent", error_type="E", source="svc")
            self.mgr.record(err)
        self.mgr.record(ManagedError(message="once", error_type="E2", source="svc"))

        t = self.report.trends(top_n=5)
        assert t["total_unique"] == 2  # deduped: "frequent" (1 unique) + "once"
        assert t["total_occurrences"] == 6
        assert len(t["top_errors"]) == 2
        assert t["top_errors"][0]["occurrences"] == 5

    def test_full_report(self):
        self.mgr.record(ManagedError(message="a", source="s"))
        report = self.report.full_report()
        assert "summary" in report
        assert "mttr" in report
        assert "trends" in report
        assert "generated_at" in report
