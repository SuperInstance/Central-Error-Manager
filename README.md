# Central-Error-Manager

**Centralized error handling for distributed agent fleets** — aggregate, classify, resolve, and report errors across services.

## What This Gives You

- **Error recording** — capture exceptions with source, severity, context, and tags
- **Intelligent classification** — auto-categorize errors (resource, timeout, auth, etc.)
- **Resolution strategies** — automated remediation with configurable strategies
- **Error reports** — open/resolved counts, severity breakdowns, trend analysis
- **Zero external dependencies** — stdlib only, pytest for tests

## Installation

```bash
pip install central-error-manager
```

## Quick Start

```python
from central_error_manager import ErrorManager, ErrorSeverity, ErrorClassifier, ErrorResolver, ErrorReport

manager = ErrorManager()
classifier = ErrorClassifier()
resolver = ErrorResolver()
reporter = ErrorReport(manager, classifier)

try:
    risky_operation()
except Exception as exc:
    manager.record_exception(exc, source="api-gateway", severity=ErrorSeverity.HIGH)

# Classify and resolve
errors = manager.get_open_errors()
for err in errors:
    category = classifier.classify(err)
    resolution = resolver.resolve(err, category)

# Generate report
summary = reporter.summary()
print(f"{summary.open_count} open, {summary.resolved_count} resolved")
```

## Testing

```bash
pip install -e .
pytest
```

## License

MIT
