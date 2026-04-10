"""Safety layer for PhishGuard.

This module provides output validation to prevent PII leakage
in AI-generated responses, and unmasking detection for session management.
"""

from phishguard.safety.output_validator import (
    OutputValidator,
    SafetyViolation,
    ValidationResult,
    ViolationType,
    validate_output,
)
from phishguard.safety.unmasking_detector import (
    UnmaskingDetector,
    UnmaskingPattern,
    UnmaskingResult,
    detect_unmasking,
)

__all__ = [
    # Output validation
    "OutputValidator",
    "SafetyViolation",
    "ValidationResult",
    "ViolationType",
    "validate_output",
    # Unmasking detection
    "UnmaskingDetector",
    "UnmaskingPattern",
    "UnmaskingResult",
    "detect_unmasking",
]
