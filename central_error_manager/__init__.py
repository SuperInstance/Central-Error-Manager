"""Central Error Manager — centralized error handling, tracking, and resolution."""

from .error import ManagedError, ErrorSeverity, ErrorStatus
from .manager import ErrorManager
from .classifier import ErrorClassifier, ErrorCategory
from .resolver import ErrorResolver, ResolutionStrategy, Resolution
from .report import ErrorReport

__all__ = [
    "ManagedError",
    "ErrorSeverity",
    "ErrorStatus",
    "ErrorManager",
    "ErrorClassifier",
    "ErrorCategory",
    "ErrorResolver",
    "ResolutionStrategy",
    "Resolution",
    "ErrorReport",
]
__version__ = "0.1.0"
