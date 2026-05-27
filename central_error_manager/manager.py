"""ErrorManager — central error collection, grouping, and resolution tracking."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable

from .error import ErrorSeverity, ErrorStatus, ManagedError

if TYPE_CHECKING:
    pass


class ErrorManager:
    """Central registry for collecting, deduplicating, and tracking errors."""

    def __init__(self) -> None:
        self._errors: dict[str, ManagedError] = {}  # fingerprint -> canonical error
        self._history: list[ManagedError] = []  # all raw submissions for auditing
        self._hooks: dict[str, list[Callable[[ManagedError], None]]] = defaultdict(list)

    # -- Ingestion --

    def record(self, error: ManagedError) -> ManagedError:
        """Record an error. If a duplicate (same fingerprint) exists, merge."""
        self._history.append(error)

        fp = error.fingerprint
        if fp in self._errors:
            self._errors[fp].merge(error)
        else:
            self._errors[fp] = error

        self._fire("on_record", self._errors[fp])
        return self._errors[fp]

    def record_exception(
        self,
        exc: BaseException,
        *,
        source: str = "",
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: dict | None = None,
        tags: list[str] | None = None,
    ) -> ManagedError:
        """Convenience: create a ManagedError from an exception and record it."""
        err = ManagedError.from_exception(exc, source=source, severity=severity, context=context, tags=tags)
        return self.record(err)

    # -- Queries --

    def get(self, fingerprint: str) -> ManagedError | None:
        return self._errors.get(fingerprint)

    def get_by_id(self, error_id: str) -> ManagedError | None:
        for err in self._errors.values():
            if err.error_id == error_id:
                return err
        return None

    @property
    def errors(self) -> list[ManagedError]:
        return list(self._errors.values())

    def open_errors(self) -> list[ManagedError]:
        return [e for e in self._errors.values() if e.is_open]

    def by_severity(self, severity: ErrorSeverity) -> list[ManagedError]:
        return [e for e in self._errors.values() if e.severity == severity]

    def by_source(self, source: str) -> list[ManagedError]:
        return [e for e in self._errors.values() if e.source == source]

    def by_tag(self, tag: str) -> list[ManagedError]:
        return [e for e in self._errors.values() if tag in e.tags]

    def unique_count(self) -> int:
        return len(self._errors)

    def total_count(self) -> int:
        return sum(e.occurrences for e in self._errors.values())

    # -- Resolution --

    def resolve(self, fingerprint: str) -> ManagedError | None:
        err = self._errors.get(fingerprint)
        if err:
            err.resolve()
            self._fire("on_resolve", err)
        return err

    def resolve_all(self, source: str = "") -> int:
        count = 0
        for err in self._errors.values():
            if err.is_open and (not source or err.source == source):
                err.resolve()
                count += 1
        return count

    def acknowledge(self, fingerprint: str) -> ManagedError | None:
        err = self._errors.get(fingerprint)
        if err:
            err.acknowledge()
        return err

    def suppress(self, fingerprint: str) -> ManagedError | None:
        err = self._errors.get(fingerprint)
        if err:
            err.suppress()
        return err

    # -- Hooks --

    def on(self, event: str, callback: Callable[[ManagedError], None]) -> None:
        """Register a hook. Events: on_record, on_resolve."""
        self._hooks[event].append(callback)

    def _fire(self, event: str, error: ManagedError) -> None:
        for cb in self._hooks.get(event, []):
            cb(error)

    # -- Maintenance --

    def clear_resolved(self) -> int:
        """Remove resolved errors. Returns count removed."""
        to_remove = [fp for fp, e in self._errors.items() if e.is_resolved]
        for fp in to_remove:
            del self._errors[fp]
        return len(to_remove)

    def reset(self) -> None:
        """Clear everything."""
        self._errors.clear()
        self._history.clear()
