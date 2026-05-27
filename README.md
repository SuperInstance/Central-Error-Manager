# Central Error Manager

Centralized error handling, tracking, and resolution management system. Aggregates errors from distributed services and provides intelligent error classification and remediation.

## Installation

```bash
pip install central-error-manager
```

## Quick Start

```python
from central_error_manager import ErrorManager, ErrorSeverity, ErrorClassifier, ErrorResolver, ErrorReport

# Set up the system
manager = ErrorManager()
classifier = ErrorClassifier()
resolver = ErrorResolver()
reporter = ErrorReport(manager, classifier)

# Record an error from a service
try:
    risky_operation()
except Exception as exc:
    manager.record_exception(exc, source="api-gateway", severity=ErrorSeverity.HIGH)

# Or create errors manually
from central_error_manager import ManagedError
err = ManagedError(
    message="Database connection pool exhausted",
    error_type="ResourceError",
    source="db-service",
    severity=ErrorSeverity.CRITICAL,
    context={"pool_size": 20, "active": 20},
    tags=["database", "production"],
)
manager.record(err)

# Classify errors
category = classifier.classify(err)  # ErrorCategory.RESOURCE

# Resolve errors with strategies
resolution = resolver.resolve(err, category)

# Generate reports
summary = reporter.summary()
print(f"{summary.open_count} open, {summary.resolved_count} resolved")
print(f"By severity: {summary.by_severity}")

mttr = reporter.mttr()
print(f"Mean time to resolve: {mttr.mttr_seconds:.1f}s")

trends = reporter.trends(top_n=5)
for err in trends["top_errors"]:
    print(f"  [{err['occurrences']}x] {err['error_type']}: {err['message']}")
```

## Features

- **Error aggregation** — Collect errors from multiple services with automatic deduplication via fingerprinting
- **Severity levels** — LOW, MEDIUM, HIGH, CRITICAL
- **Error classification** — Automatic categorization: network, auth, timeout, logic, resource, configuration
- **Resolution strategies** — Retry with configurable max, fallback paths, escalation, and ignore policies
- **Custom resolvers** — Register your own resolution logic
- **Reporting** — Summaries, MTTR statistics, trend analysis
- **Lifecycle hooks** — `on_record` and `on_resolve` callbacks
- **Zero dependencies** — Only requires Python 3.10+; pytest for testing

## Architecture

```
central_error_manager/
├── error.py         # ManagedError data model with fingerprinting
├── manager.py       # ErrorManager — central collection and dedup
├── classifier.py    # ErrorClassifier — pattern-based categorization
├── resolver.py      # ErrorResolver — strategy-based resolution
└── report.py        # ErrorReport — summaries, MTTR, trends
```

## Error Lifecycle

1. **Record** — Error captured with context, source, severity
2. **Deduplicate** — Same error (by fingerprint) merges occurrences
3. **Classify** — Automatically categorized by type/message patterns
4. **Resolve** — Strategy applied (retry, fallback, escalate, ignore)
5. **Report** — Summary stats, MTTR, and trends available anytime

## License

MIT
