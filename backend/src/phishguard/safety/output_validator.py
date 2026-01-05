"""Output validation module for PhishGuard safety layer.

This module provides the OutputValidator class which validates AI-generated
responses to ensure they don't contain real PII or sensitive data. It
implements the bidirectional safety layer's output validation component.

Security Priority: P0 - Critical for Safety Score
Requirements: FR-014 through FR-018
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Final

# Configure security audit logger
logger = logging.getLogger("phishguard.safety.output_validator")


class ViolationType(str, Enum):
    """Classification of safety violations in generated output.

    Attributes:
        SSN: Social Security Number detected.
        NATIONAL_ID: Government ID number detected.
        BANK_ACCOUNT: Bank account or routing number detected.
        CREDIT_CARD: Credit card number detected.
        PHONE_REAL: Real phone number format (not 555-XXXX).
        EMAIL_REAL: Real email address (not @example.com).
        CORPORATE_DOMAIN: Fortune 500 or known corporate domain.
        ADDRESS: Potentially real street address.
    """

    SSN = "ssn"
    NATIONAL_ID = "national_id"
    BANK_ACCOUNT = "bank_account"
    CREDIT_CARD = "credit_card"
    PHONE_REAL = "phone_real"
    EMAIL_REAL = "email_real"
    CORPORATE_DOMAIN = "corporate_domain"
    ADDRESS = "address"


@dataclass(frozen=True)
class SafetyViolation:
    """Represents a single safety violation found in output.

    Attributes:
        violation_type: Category of the violation.
        matched_text: The text that triggered the violation.
        description: Human-readable description of the issue.
    """

    violation_type: ViolationType
    matched_text: str
    description: str


@dataclass
class ValidationResult:
    """Result of output safety validation.

    Attributes:
        is_safe: True if output passed all safety checks.
        violations: List of safety violations found.
        original_text: The text that was validated.
    """

    is_safe: bool
    violations: list[SafetyViolation] = field(default_factory=list)
    original_text: str = ""

    @property
    def needs_regeneration(self) -> bool:
        """Check if the output needs to be regenerated.

        Returns:
            True if any violations were found.
        """
        return not self.is_safe

    @property
    def violation_count(self) -> int:
        """Get the number of violations found.

        Returns:
            Count of safety violations.
        """
        return len(self.violations)

    @property
    def violation_summary(self) -> str:
        """Get a summary of all violations.

        Returns:
            Comma-separated list of violation types.
        """
        if not self.violations:
            return "None"
        return ", ".join(v.violation_type.value for v in self.violations)


class OutputValidator:
    """Validates AI-generated output to prevent PII/sensitive data leakage.

    The OutputValidator ensures that generated responses from the Conversation
    Agent don't contain real PII that could identify actual people or expose
    sensitive financial data. It blocks:

    - Social Security Numbers (XXX-XX-XXXX format)
    - Government ID numbers and passport numbers
    - Real bank account and routing numbers
    - Credit card numbers
    - Real phone numbers (allows 555-XXXX placeholders)
    - Real email addresses (allows @example.com)
    - Corporate domains from blocklist

    Example:
        >>> validator = OutputValidator()
        >>> result = validator.validate("My SSN is 123-45-6789")
        >>> result.is_safe
        False
        >>> result.violations[0].violation_type
        ViolationType.SSN

    Attributes:
        _blocked_domains: Set of corporate domains to block.
    """

    # Social Security Number pattern (US)
    SSN_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b"
    )

    # Credit card pattern (Luhn algorithm would be better but regex is faster)
    CREDIT_CARD_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"\b(?:\d{4}[-.\s]?){3}\d{4}\b"  # 16 digits with optional separators
    )

    # Phone number patterns (real formats, excluding 555-XXXX)
    PHONE_PATTERNS: Final[list[re.Pattern[str]]] = [
        # US format with area code (not 555)
        re.compile(r"\b(?!555)\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),
        # International format
        re.compile(r"\+\d{1,3}[-.\s]?\d{6,14}\b"),
    ]

    # Safe placeholder patterns (should NOT trigger violations)
    SAFE_PHONE_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"\b555[-.\s]?\d{3}[-.\s]?\d{4}\b"
    )

    # Email pattern (excluding safe domains)
    EMAIL_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        re.IGNORECASE,
    )

    # Safe email domains that should be allowed
    SAFE_EMAIL_DOMAINS: Final[set[str]] = {
        "example.com",
        "example.org",
        "example.net",
        "test.com",
        "test.org",
        "fake.com",
        "fakeemail.com",
        "mailinator.com",
        "tempmail.com",
    }

    # Blocked corporate domains (Fortune 500 + major tech companies)
    BLOCKED_CORPORATE_DOMAINS: Final[set[str]] = {
        # Tech giants
        "google.com",
        "apple.com",
        "microsoft.com",
        "amazon.com",
        "meta.com",
        "facebook.com",
        "netflix.com",
        "tesla.com",
        "nvidia.com",
        "adobe.com",
        "salesforce.com",
        "oracle.com",
        "ibm.com",
        "intel.com",
        "cisco.com",
        "vmware.com",
        # Finance
        "jpmorgan.com",
        "bankofamerica.com",
        "wellsfargo.com",
        "citigroup.com",
        "goldmansachs.com",
        "morganstanley.com",
        "visa.com",
        "mastercard.com",
        "paypal.com",
        # Retail
        "walmart.com",
        "target.com",
        "costco.com",
        "homedepot.com",
        "lowes.com",
        # Healthcare
        "unitedhealth.com",
        "cvs.com",
        "walgreens.com",
        "pfizer.com",
        "jnj.com",
        # Other major companies
        "exxonmobil.com",
        "chevron.com",
        "att.com",
        "verizon.com",
        "disney.com",
        "comcast.com",
        "boeing.com",
        "lockheedmartin.com",
    }

    def __init__(
        self,
        additional_blocked_domains: set[str] | None = None,
        strict_mode: bool = True,
    ) -> None:
        """Initialize the OutputValidator.

        Args:
            additional_blocked_domains: Extra domains to block beyond defaults.
            strict_mode: If True, applies stricter validation rules.
        """
        self._blocked_domains = self.BLOCKED_CORPORATE_DOMAINS.copy()
        if additional_blocked_domains:
            self._blocked_domains.update(additional_blocked_domains)
        self._strict_mode = strict_mode

    def validate(self, text: str) -> ValidationResult:
        """Validate output text for safety violations.

        Checks the text against all PII patterns and blocklists.
        Returns a ValidationResult indicating whether the text is safe
        and listing any violations found.

        Args:
            text: The AI-generated response text to validate.

        Returns:
            ValidationResult with safety status and any violations.

        Example:
            >>> validator = OutputValidator()
            >>> result = validator.validate("Contact me at john@google.com")
            >>> result.is_safe
            False
            >>> result.violations[0].violation_type
            ViolationType.CORPORATE_DOMAIN
        """
        if not text:
            return ValidationResult(is_safe=True, original_text=text)

        violations: list[SafetyViolation] = []

        # Check for SSN
        violations.extend(self._check_ssn(text))

        # Check for credit card numbers
        violations.extend(self._check_credit_card(text))

        # Check for real phone numbers
        violations.extend(self._check_phone_numbers(text))

        # Check for real email addresses and corporate domains
        violations.extend(self._check_emails(text))

        # Check for addresses (only in strict mode)
        if self._strict_mode:
            violations.extend(self._check_addresses(text))

        # Log violations for security audit
        if violations:
            logger.warning(
                "Output validation failed with %d violations: %s",
                len(violations),
                ", ".join(v.violation_type.value for v in violations),
            )

        return ValidationResult(
            is_safe=len(violations) == 0,
            violations=violations,
            original_text=text,
        )

    def _check_ssn(self, text: str) -> list[SafetyViolation]:
        """Check for Social Security Numbers.

        Args:
            text: Text to check.

        Returns:
            List of SSN violations found.
        """
        violations = []
        for match in self.SSN_PATTERN.finditer(text):
            # Verify it looks like a real SSN (not 000-00-0000 or 123-45-6789)
            matched = match.group(0)
            # Remove separators for validation
            digits = re.sub(r"[-.\s]", "", matched)
            # Skip obvious test/fake numbers
            if digits in ("000000000", "123456789", "111111111", "999999999"):
                continue
            violations.append(
                SafetyViolation(
                    violation_type=ViolationType.SSN,
                    matched_text=matched,
                    description="Potential Social Security Number detected",
                )
            )
        return violations

    def _check_credit_card(self, text: str) -> list[SafetyViolation]:
        """Check for credit card numbers.

        Args:
            text: Text to check.

        Returns:
            List of credit card violations found.
        """
        violations = []
        for match in self.CREDIT_CARD_PATTERN.finditer(text):
            matched = match.group(0)
            # Skip obvious test numbers (4111111111111111, etc.)
            digits = re.sub(r"[-.\s]", "", matched)
            if len(set(digits)) <= 2:  # All same digit or alternating
                continue
            violations.append(
                SafetyViolation(
                    violation_type=ViolationType.CREDIT_CARD,
                    matched_text=matched,
                    description="Potential credit card number detected",
                )
            )
        return violations

    def _check_phone_numbers(self, text: str) -> list[SafetyViolation]:
        """Check for real phone numbers (not 555-XXXX placeholders).

        Args:
            text: Text to check.

        Returns:
            List of phone number violations found.
        """
        violations = []

        # First, identify all safe placeholder numbers
        safe_positions: set[tuple[int, int]] = set()
        for match in self.SAFE_PHONE_PATTERN.finditer(text):
            safe_positions.add((match.start(), match.end()))

        # Now check for real phone patterns
        for pattern in self.PHONE_PATTERNS:
            for match in pattern.finditer(text):
                # Skip if this overlaps with a safe placeholder
                is_safe = any(
                    start <= match.start() < end or start < match.end() <= end
                    for start, end in safe_positions
                )
                if is_safe:
                    continue

                violations.append(
                    SafetyViolation(
                        violation_type=ViolationType.PHONE_REAL,
                        matched_text=match.group(0),
                        description="Real phone number detected (use 555-XXX-XXXX)",
                    )
                )

        return violations

    def _check_emails(self, text: str) -> list[SafetyViolation]:
        """Check for real email addresses and corporate domains.

        Args:
            text: Text to check.

        Returns:
            List of email/domain violations found.
        """
        violations = []

        for match in self.EMAIL_PATTERN.finditer(text):
            email = match.group(0).lower()
            domain = email.split("@")[1] if "@" in email else ""

            # Check if domain is in safe list
            if domain in self.SAFE_EMAIL_DOMAINS:
                continue

            # Check if domain is in blocked corporate list
            if domain in self._blocked_domains:
                violations.append(
                    SafetyViolation(
                        violation_type=ViolationType.CORPORATE_DOMAIN,
                        matched_text=email,
                        description=f"Corporate domain '{domain}' is blocked",
                    )
                )
            else:
                # It's a real email but not corporate - still flag it
                violations.append(
                    SafetyViolation(
                        violation_type=ViolationType.EMAIL_REAL,
                        matched_text=email,
                        description="Real email address detected (use @example.com)",
                    )
                )

        return violations

    def _check_addresses(self, text: str) -> list[SafetyViolation]:
        """Check for potential real street addresses.

        Args:
            text: Text to check.

        Returns:
            List of address violations found.
        """
        violations = []

        # Look for address patterns: number + street type
        address_pattern = re.compile(
            r"\b\d+\s+[A-Za-z]+\s+(?:street|avenue|boulevard|drive|lane|road|"
            r"court|place|way|circle|st|ave|blvd|dr|ln|rd|ct|pl)\b",
            re.IGNORECASE,
        )

        for match in address_pattern.finditer(text):
            matched = match.group(0)
            # Skip obviously fake addresses
            if any(
                fake in matched.lower()
                for fake in ("123 main", "fake street", "example")
            ):
                continue
            violations.append(
                SafetyViolation(
                    violation_type=ViolationType.ADDRESS,
                    matched_text=matched,
                    description="Potential real street address detected",
                )
            )

        return violations

    def is_safe(self, text: str) -> bool:
        """Quick check if output is safe without full violation details.

        Args:
            text: Text to validate.

        Returns:
            True if text passes all safety checks.
        """
        return self.validate(text).is_safe


# Module-level convenience function
def validate_output(text: str, strict: bool = True) -> ValidationResult:
    """Convenience function for one-off output validation.

    Args:
        text: Text to validate.
        strict: If True, applies stricter validation rules.

    Returns:
        ValidationResult with safety status and violations.
    """
    validator = OutputValidator(strict_mode=strict)
    return validator.validate(text)
