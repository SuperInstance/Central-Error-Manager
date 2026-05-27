"""ErrorClassifier — automatic error categorization."""

from __future__ import annotations

import re
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .error import ManagedError


class ErrorCategory(Enum):
    """Broad error categories for routing and reporting."""
    NETWORK = "network"
    AUTH = "auth"
    TIMEOUT = "timeout"
    LOGIC = "logic"
    RESOURCE = "resource"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


# Pattern tables: (compiled_regex, category)
_TYPE_PATTERNS: list[tuple[re.Pattern[str], ErrorCategory]] = [
    (re.compile(r"(?i)(connection|socket|network|dns|host)"), ErrorCategory.NETWORK),
    (re.compile(r"(?i)(timeout|timed?\s*out)"), ErrorCategory.TIMEOUT),
    (re.compile(r"(?i)(auth|unauthorized|forbidden|credential|token|permission)"), ErrorCategory.AUTH),
    (re.compile(r"(?i)(oom|memory|resource|disk|space|quota|limit)"), ErrorCategory.RESOURCE),
    (re.compile(r"(?i)(config|setting|env|missing\s+key|misconfig)"), ErrorCategory.CONFIGURATION),
]

_MSG_PATTERNS: list[tuple[re.Pattern[str], ErrorCategory]] = [
    (re.compile(r"(?i)(refused|reset|unreachable|no route|name resolution)"), ErrorCategory.NETWORK),
    (re.compile(r"(?i)(timed?\s*out|deadline exceeded)"), ErrorCategory.TIMEOUT),
    (re.compile(r"(?i)(invalid\s+token|expired|access denied|login|forbidden)"), ErrorCategory.AUTH),
    (re.compile(r"(?i)(out of memory|no space|too many open)"), ErrorCategory.RESOURCE),
    (re.compile(r"(?i)(not found|key error|index error|value error|type error)"), ErrorCategory.LOGIC),
    (re.compile(r"(?i)(missing\s+\w+|not configured|invalid\s+config)"), ErrorCategory.CONFIGURATION),
]


class ErrorClassifier:
    """Classify errors into categories based on type name and message patterns."""

    def __init__(
        self,
        custom_rules: list[tuple[re.Pattern[str], ErrorCategory]] | None = None,
    ) -> None:
        self._custom: list[tuple[re.Pattern[str], ErrorCategory]] = custom_rules or []

    def classify(self, error: ManagedError) -> ErrorCategory:
        """Return the best-matching category for an error."""
        # Custom rules first
        for pattern, category in self._custom:
            if pattern.search(error.error_type) or pattern.search(error.message):
                return category

        # Type name patterns
        for pattern, category in _TYPE_PATTERNS:
            if pattern.search(error.error_type):
                return category

        # Message patterns
        for pattern, category in _MSG_PATTERNS:
            if pattern.search(error.message):
                return category

        return ErrorCategory.UNKNOWN

    def classify_batch(self, errors: list[ManagedError]) -> dict[str, list[ManagedError]]:
        """Classify a batch and group by category name."""
        groups: dict[str, list[ManagedError]] = {}
        for err in errors:
            cat = self.classify(err)
            groups.setdefault(cat.value, []).append(err)
        return groups
