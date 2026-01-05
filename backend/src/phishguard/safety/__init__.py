"""Safety layer for PhishGuard.

This module provides output validation to prevent PII leakage
in AI-generated responses.
"""

from phishguard.safety.output_validator import (
    OutputValidator,
    SafetyViolation,
    ValidationResult,
    ViolationType,
    validate_output,
)

__all__ = [
    "OutputValidator",
    "SafetyViolation",
    "ValidationResult",
    "ViolationType",
    "validate_output",
]
