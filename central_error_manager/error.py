"""ManagedError — the core error data model with severity, context, traceback, and fingerprinting."""

from __future__ import annotations

import hashlib
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ErrorSeverity(Enum):
    """How bad is it?"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorStatus(Enum):
    """Lifecycle state of a managed error."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


def _fingerprint(exc_type: str, message: str, source: str) -> str:
    """Deterministic fingerprint for deduplication."""
    raw = f"{exc_type}:{message}:{source}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class ManagedError:
    """A tracked, enriched error with full context for fleet-wide management."""

    message: str
    error_type: str = "Exception"
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    status: ErrorStatus = ErrorStatus.OPEN
    source: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    traceback_str: str = ""
    fingerprint: str = ""
    error_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None
    occurrences: int = 1
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.fingerprint:
            self.fingerprint = _fingerprint(self.error_type, self.message, self.source)
        if not self.traceback_str:
            self.traceback_str = traceback.format_exc() or ""

    @classmethod
    def from_exception(
        cls,
        exc: BaseException,
        *,
        source: str = "",
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> ManagedError:
        """Create a ManagedError from a live exception."""
        tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        return cls(
            message=str(exc),
            error_type=type(exc).__name__,
            severity=severity,
            source=source,
            context=context or {},
            traceback_str=tb_str,
            tags=tags or [],
        )

    def resolve(self) -> None:
        """Mark error as resolved."""
        self.status = ErrorStatus.RESOLVED
        self.resolved_at = datetime.now(timezone.utc)

    def acknowledge(self) -> None:
        """Acknowledge the error."""
        self.status = ErrorStatus.ACKNOWLEDGED

    def suppress(self) -> None:
        """Suppress future notifications for this error."""
        self.status = ErrorStatus.SUPPRESSED

    def merge(self, other: ManagedError) -> None:
        """Merge a duplicate error into this one (increment occurrences, update timestamp)."""
        if self.fingerprint != other.fingerprint:
            raise ValueError("Cannot merge errors with different fingerprints")
        self.occurrences += other.occurrences
        if other.timestamp > self.timestamp:
            self.timestamp = other.timestamp
            self.traceback_str = other.traceback_str

    @property
    def is_resolved(self) -> bool:
        return self.status == ErrorStatus.RESOLVED

    @property
    def is_open(self) -> bool:
        return self.status == ErrorStatus.OPEN
