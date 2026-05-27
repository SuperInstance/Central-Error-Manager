"""Tests for ErrorClassifier."""

import re
import pytest

from central_error_manager.error import ManagedError, ErrorSeverity
from central_error_manager.classifier import ErrorClassifier, ErrorCategory


class TestErrorClassifier:
    def setup_method(self):
        self.clf = ErrorClassifier()

    def test_network_type(self):
        err = ManagedError(message="failed", error_type="ConnectionError")
        assert self.clf.classify(err) == ErrorCategory.NETWORK

    def test_timeout_message(self):
        err = ManagedError(message="request timed out", error_type="RuntimeError")
        assert self.clf.classify(err) == ErrorCategory.TIMEOUT

    def test_auth_type(self):
        err = ManagedError(message="denied", error_type="AuthenticationError")
        assert self.clf.classify(err) == ErrorCategory.AUTH

    def test_resource_message(self):
        err = ManagedError(message="out of memory", error_type="RuntimeError")
        assert self.clf.classify(err) == ErrorCategory.RESOURCE

    def test_logic_message(self):
        err = ManagedError(message="not found", error_type="RuntimeError")
        assert self.clf.classify(err) == ErrorCategory.LOGIC

    def test_config_type(self):
        err = ManagedError(message="missing key", error_type="ConfigError")
        assert self.clf.classify(err) == ErrorCategory.CONFIGURATION

    def test_unknown(self):
        err = ManagedError(message="something weird happened", error_type="WeirdError")
        assert self.clf.classify(err) == ErrorCategory.UNKNOWN

    def test_custom_rules_override(self):
        clf = ErrorClassifier(
            custom_rules=[(re.compile(r"(?i)fizzbuzz"), ErrorCategory.LOGIC)]
        )
        err = ManagedError(message="fizzbuzz failure", error_type="Custom")
        assert clf.classify(err) == ErrorCategory.LOGIC

    def test_classify_batch(self):
        errors = [
            ManagedError(message="conn refused", error_type="ConnectionError"),
            ManagedError(message="invalid token", error_type="AuthError"),
            ManagedError(message="not found", error_type="ValueError"),
        ]
        groups = self.clf.classify_batch(errors)
        assert "network" in groups
        assert "auth" in groups
        assert "logic" in groups
