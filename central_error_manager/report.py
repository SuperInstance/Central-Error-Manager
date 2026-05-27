"""ErrorReport — summaries, trends, and MTTR statistics."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .error import ErrorSeverity, ErrorStatus, ManagedError
from .manager import ErrorManager
from .classifier import ErrorCategory, ErrorClassifier


@dataclass
class ErrorSummary:
    """Snapshot of current error state."""
    total_unique: int
    total_occurrences: int
    open_count: int
    resolved_count: int
    by_severity: dict[str, int] = field(default_factory=dict)
    by_category: dict[str, int] = field(default_factory=dict)
    by_source: dict[str, int] = field(default_factory=dict)


@dataclass
class MTTRStats:
    """Mean Time To Resolve statistics."""
    mttr_seconds: float
    resolved_count: int
    min_seconds: float
    max_seconds: float
    by_severity: dict[str, float] = field(default_factory=dict)
    by_category: dict[str, float] = field(default_factory=dict)


class ErrorReport:
    """Generate reports from an ErrorManager."""

    def __init__(self, manager: ErrorManager, classifier: ErrorClassifier | None = None) -> None:
        self.manager = manager
        self.classifier = classifier or ErrorClassifier()

    def summary(self) -> ErrorSummary:
        """Generate a summary of current error state."""
        errors = self.manager.errors
        by_sev: dict[str, int] = {}
        by_cat: dict[str, int] = {}
        by_src: dict[str, int] = {}

        for err in errors:
            sev = err.severity.value
            by_sev[sev] = by_sev.get(sev, 0) + err.occurrences

            cat = self.classifier.classify(err).value
            by_cat[cat] = by_cat.get(cat, 0) + err.occurrences

            if err.source:
                by_src[err.source] = by_src.get(err.source, 0) + err.occurrences

        return ErrorSummary(
            total_unique=len(errors),
            total_occurrences=sum(e.occurrences for e in errors),
            open_count=sum(1 for e in errors if e.is_open),
            resolved_count=sum(1 for e in errors if e.is_resolved),
            by_severity=by_sev,
            by_category=by_cat,
            by_source=by_src,
        )

    def mttr(self) -> MTTRStats:
        """Calculate Mean Time To Resolve across all resolved errors."""
        resolved = [e for e in self.manager.errors if e.is_resolved and e.resolved_at]
        if not resolved:
            return MTTRStats(
                mttr_seconds=0.0, resolved_count=0, min_seconds=0.0, max_seconds=0.0
            )

        durations: list[float] = []
        for err in resolved:
            dt = (err.resolved_at - err.timestamp).total_seconds()
            durations.append(max(dt, 0.0))

        # By severity
        by_sev: dict[str, list[float]] = {}
        by_cat: dict[str, list[float]] = {}
        for err, dur in zip(resolved, durations):
            by_sev.setdefault(err.severity.value, []).append(dur)
            cat = self.classifier.classify(err).value
            by_cat.setdefault(cat, []).append(dur)

        return MTTRStats(
            mttr_seconds=sum(durations) / len(durations),
            resolved_count=len(resolved),
            min_seconds=min(durations),
            max_seconds=max(durations),
            by_severity={k: sum(v) / len(v) for k, v in by_sev.items()},
            by_category={k: sum(v) / len(v) for k, v in by_cat.items()},
        )

    def trends(self, top_n: int = 10) -> dict[str, Any]:
        """Return trending errors by occurrence count."""
        errors = sorted(self.manager.errors, key=lambda e: e.occurrences, reverse=True)
        top = errors[:top_n]
        return {
            "top_errors": [
                {
                    "fingerprint": e.fingerprint,
                    "error_type": e.error_type,
                    "message": e.message,
                    "occurrences": e.occurrences,
                    "severity": e.severity.value,
                    "status": e.status.value,
                    "source": e.source,
                }
                for e in top
            ],
            "total_unique": len(errors),
            "total_occurrences": sum(e.occurrences for e in errors),
        }

    def full_report(self) -> dict[str, Any]:
        """Generate a complete report with summary, MTTR, and trends."""
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_unique": self.summary().total_unique,
                "total_occurrences": self.summary().total_occurrences,
                "open_count": self.summary().open_count,
                "resolved_count": self.summary().resolved_count,
                "by_severity": self.summary().by_severity,
                "by_category": self.summary().by_category,
                "by_source": self.summary().by_source,
            },
            "mttr": {
                "mean_seconds": self.mttr().mttr_seconds,
                "resolved_count": self.mttr().resolved_count,
                "min_seconds": self.mttr().min_seconds,
                "max_seconds": self.mttr().max_seconds,
            },
            "trends": self.trends(),
        }
