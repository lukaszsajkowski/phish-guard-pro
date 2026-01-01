"""Safety layer for PhishGuard input/output validation.

This module provides security-critical components for:
- Input sanitization (preventing prompt injection)
- Output validation (preventing PII leakage)

All components are designed with a "fail secure" philosophy:
when in doubt, block the content and log for review.

Example:
    >>> from phishguard.safety import InputSanitizer, UnsafeInputError
    >>> sanitizer = InputSanitizer()
    >>> sanitizer.sanitize("<script>alert('xss')</script>Hello")
    'Hello'

    >>> from phishguard.safety import OutputValidator
    >>> validator = OutputValidator()
    >>> result = validator.validate("My SSN is 123-45-6789")
    >>> result.is_safe
    False
"""

from phishguard.safety.input_sanitizer import (
    InjectionPattern,
    InputSanitizer,
    SanitizationResult,
    ThreatLevel,
    UnsafeInputError,
    sanitize_input,
)
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
    # Input sanitization
    "InputSanitizer",
    "UnsafeInputError",
    "InjectionPattern",
    "SanitizationResult",
    "ThreatLevel",
    "sanitize_input",
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
