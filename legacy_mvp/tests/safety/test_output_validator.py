"""Comprehensive unit tests for the OutputValidator.

These tests verify that the OutputValidator correctly:
1. Detects Social Security Numbers (SSN patterns)
2. Detects credit card numbers
3. Detects real phone numbers (but allows 555-XXX-XXXX)
4. Detects real email addresses (but allows @example.com)
5. Detects corporate domains from the blocklist
6. Returns proper ValidationResult with violation details
7. Handles edge cases and safe placeholder data

Test Categories:
- SSN detection
- Credit card detection
- Phone number validation
- Email and domain validation
- Address detection
- Safe placeholder allowances
- Edge cases
"""

import pytest

from phishguard.safety import (
    OutputValidator,
    ValidationResult,
    ViolationType,
    validate_output,
)

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def validator() -> OutputValidator:
    """Create a default OutputValidator for testing."""
    return OutputValidator()


@pytest.fixture
def non_strict_validator() -> OutputValidator:
    """Create a non-strict OutputValidator for testing."""
    return OutputValidator(strict_mode=False)


# -----------------------------------------------------------------------------
# Test Classes
# -----------------------------------------------------------------------------


class TestOutputValidatorSSNDetection:
    """Tests for Social Security Number detection."""

    @pytest.mark.parametrize(
        "text,should_detect",
        [
            ("My SSN is 234-56-7890", True),  # Real-looking SSN
            ("My SSN is 234.56.7890", True),  # Real-looking SSN with dots
            ("My SSN is 234 56 7890", True),  # Real-looking SSN with spaces
            ("SSN: 000-00-0000", False),  # Obvious test number
            ("SSN: 999-99-9999", False),  # Obvious test number
            ("SSN: 111-11-1111", False),  # Obvious test number
            ("SSN: 123-45-6789", False),  # Common test SSN, excluded
            ("No SSN here", False),
        ],
        ids=[
            "ssn_with_dashes",
            "ssn_with_dots",
            "ssn_with_spaces",
            "ssn_test_zeros",
            "ssn_test_nines",
            "ssn_test_ones",
            "ssn_test_sequential",
            "no_ssn",
        ],
    )
    def test_ssn_detection(
        self, validator: OutputValidator, text: str, should_detect: bool
    ) -> None:
        """Test SSN pattern detection with various formats."""
        result = validator.validate(text)

        if should_detect:
            assert not result.is_safe
            assert any(v.violation_type == ViolationType.SSN for v in result.violations)
        else:
            ssn_violations = [
                v for v in result.violations if v.violation_type == ViolationType.SSN
            ]
            assert len(ssn_violations) == 0


class TestOutputValidatorCreditCardDetection:
    """Tests for credit card number detection."""

    @pytest.mark.parametrize(
        "text,should_detect",
        [
            ("Card: 4111-1111-1111-1111", False),  # All same digit, test card
            ("Card: 4532-7153-8372-9481", True),  # Looks like real card
            ("Card: 4532 7153 8372 9481", True),  # Spaces instead of dashes
            ("Card: 4532.7153.8372.9481", True),  # Dots as separators
            ("Card number 4532715383729481", True),  # No separators
            ("Reference: 1234", False),  # Too short
            ("No card here", False),
        ],
        ids=[
            "test_card_pattern",
            "real_looking_card",
            "card_with_spaces",
            "card_with_dots",
            "card_no_separators",
            "short_number",
            "no_card",
        ],
    )
    def test_credit_card_detection(
        self, validator: OutputValidator, text: str, should_detect: bool
    ) -> None:
        """Test credit card pattern detection."""
        result = validator.validate(text)

        if should_detect:
            assert not result.is_safe
            assert any(
                v.violation_type == ViolationType.CREDIT_CARD for v in result.violations
            )
        else:
            cc_violations = [
                v
                for v in result.violations
                if v.violation_type == ViolationType.CREDIT_CARD
            ]
            assert len(cc_violations) == 0


class TestOutputValidatorPhoneDetection:
    """Tests for phone number detection."""

    @pytest.mark.parametrize(
        "text,should_detect",
        [
            ("Call me at 555-123-4567", False),  # Safe 555 placeholder
            ("Call me at 555.123.4567", False),  # Safe 555 with dots
            ("Call me at 555 123 4567", False),  # Safe 555 with spaces
            ("Call me at 212-555-1234", True),  # Real area code, not 555
            ("Call me at 800-123-4567", True),  # 800 number
            ("+1-202-555-0123", True),  # International format
            ("+48123456789", True),  # International number
            ("My number is 1234", False),  # Too short
            ("No phone here", False),
        ],
        ids=[
            "safe_555_dashes",
            "safe_555_dots",
            "safe_555_spaces",
            "real_area_code",
            "800_number",
            "international_format",
            "international_number",
            "too_short",
            "no_phone",
        ],
    )
    def test_phone_detection(
        self, validator: OutputValidator, text: str, should_detect: bool
    ) -> None:
        """Test phone number detection with safe 555 placeholders."""
        result = validator.validate(text)

        if should_detect:
            assert not result.is_safe
            assert any(
                v.violation_type == ViolationType.PHONE_REAL for v in result.violations
            )
        else:
            phone_violations = [
                v
                for v in result.violations
                if v.violation_type == ViolationType.PHONE_REAL
            ]
            assert len(phone_violations) == 0


class TestOutputValidatorEmailDetection:
    """Tests for email address and domain detection."""

    @pytest.mark.parametrize(
        "text,expected_violation",
        [
            ("Email: john@example.com", None),  # Safe domain
            ("Email: jane@test.com", None),  # Safe domain
            ("Email: user@fakeemail.com", None),  # Safe domain
            ("Email: bob@gmail.com", ViolationType.EMAIL_REAL),  # Real email
            ("Email: ceo@google.com", ViolationType.CORPORATE_DOMAIN),  # Corporate
            ("Email: admin@microsoft.com", ViolationType.CORPORATE_DOMAIN),  # Corporate
            ("Email: contact@amazon.com", ViolationType.CORPORATE_DOMAIN),  # Corporate
            ("No email here", None),
        ],
        ids=[
            "safe_example_domain",
            "safe_test_domain",
            "safe_fakeemail_domain",
            "real_gmail",
            "corporate_google",
            "corporate_microsoft",
            "corporate_amazon",
            "no_email",
        ],
    )
    def test_email_detection(
        self,
        validator: OutputValidator,
        text: str,
        expected_violation: ViolationType | None,
    ) -> None:
        """Test email and corporate domain detection."""
        result = validator.validate(text)

        if expected_violation is None:
            email_violations = [
                v
                for v in result.violations
                if v.violation_type
                in (ViolationType.EMAIL_REAL, ViolationType.CORPORATE_DOMAIN)
            ]
            assert len(email_violations) == 0
        else:
            assert not result.is_safe
            violation_types = [v.violation_type for v in result.violations]
            assert expected_violation in violation_types


class TestOutputValidatorAddressDetection:
    """Tests for street address detection (strict mode only)."""

    @pytest.mark.parametrize(
        "text,should_detect",
        [
            ("I live at 123 Main Street", False),  # Common fake address
            ("My address is 456 Oak Avenue", True),  # Looks real
            ("Located at 789 Corporate Boulevard", True),  # Real-looking
            ("Just a street name Street", False),  # No number
            ("No address here", False),
        ],
        ids=[
            "common_fake_address",
            "real_looking_avenue",
            "real_looking_boulevard",
            "no_street_number",
            "no_address",
        ],
    )
    def test_address_detection_strict_mode(
        self, validator: OutputValidator, text: str, should_detect: bool
    ) -> None:
        """Test address detection in strict mode."""
        result = validator.validate(text)

        if should_detect:
            assert any(
                v.violation_type == ViolationType.ADDRESS for v in result.violations
            )
        else:
            address_violations = [
                v
                for v in result.violations
                if v.violation_type == ViolationType.ADDRESS
            ]
            assert len(address_violations) == 0

    def test_address_detection_not_in_non_strict_mode(
        self, non_strict_validator: OutputValidator
    ) -> None:
        """Address detection should be skipped in non-strict mode."""
        result = non_strict_validator.validate("My address is 456 Oak Avenue")

        address_violations = [
            v for v in result.violations if v.violation_type == ViolationType.ADDRESS
        ]
        assert len(address_violations) == 0


class TestOutputValidatorValidationResult:
    """Tests for ValidationResult structure and properties."""

    def test_validation_result_is_safe_property(
        self, validator: OutputValidator
    ) -> None:
        """is_safe should be True when no violations found."""
        result = validator.validate("This is safe text with no PII")

        assert result.is_safe is True
        assert len(result.violations) == 0

    def test_validation_result_is_not_safe_with_violations(
        self, validator: OutputValidator
    ) -> None:
        """is_safe should be False when violations are found."""
        # Use real-looking SSN not in exclusion list
        result = validator.validate("My SSN is 234-56-7890")

        assert result.is_safe is False
        assert len(result.violations) > 0

    def test_validation_result_needs_regeneration(
        self, validator: OutputValidator
    ) -> None:
        """needs_regeneration should match not is_safe."""
        safe_result = validator.validate("Safe text")
        # Use real-looking SSN not in exclusion list
        unsafe_result = validator.validate("SSN: 234-56-7890")

        assert safe_result.needs_regeneration is False
        assert unsafe_result.needs_regeneration is True

    def test_validation_result_violation_count(
        self, validator: OutputValidator
    ) -> None:
        """violation_count should return correct number."""
        # Use real-looking SSN and credit card
        result = validator.validate("SSN: 234-56-7890, Card: 4532-7153-8372-9481")

        assert result.violation_count >= 2

    def test_validation_result_violation_summary(
        self, validator: OutputValidator
    ) -> None:
        """violation_summary should list violation types."""
        # Use real-looking SSN not in exclusion list
        result = validator.validate("SSN: 234-56-7890")

        assert "ssn" in result.violation_summary.lower()

    def test_validation_result_original_text_preserved(
        self, validator: OutputValidator
    ) -> None:
        """original_text should be preserved in result."""
        original = "Test text with SSN: 234-56-7890"
        result = validator.validate(original)

        assert result.original_text == original


class TestOutputValidatorSafePlaceholders:
    """Tests for safe placeholder patterns that should NOT trigger violations."""

    def test_safe_phone_555_allowed(self, validator: OutputValidator) -> None:
        """555-XXX-XXXX phone numbers should be safe."""
        result = validator.validate("Call me at 555-867-5309")

        assert result.is_safe is True

    def test_safe_email_example_domain_allowed(
        self, validator: OutputValidator
    ) -> None:
        """@example.com emails should be safe."""
        result = validator.validate("Email me at john.doe@example.com")

        assert result.is_safe is True

    def test_safe_email_test_domain_allowed(self, validator: OutputValidator) -> None:
        """@test.com emails should be safe."""
        result = validator.validate("Contact: info@test.com")

        assert result.is_safe is True

    def test_multiple_safe_placeholders_allowed(
        self, validator: OutputValidator
    ) -> None:
        """Multiple safe placeholders should all be allowed."""
        text = (
            "Call me at 555-123-4567 or email john@example.com. "
            "My address is 123 Main Street, Anytown, USA."
        )
        result = validator.validate(text)

        # Should have no violations for phone, email, or the common fake address
        phone_violations = [
            v for v in result.violations if v.violation_type == ViolationType.PHONE_REAL
        ]
        email_violations = [
            v
            for v in result.violations
            if v.violation_type
            in (ViolationType.EMAIL_REAL, ViolationType.CORPORATE_DOMAIN)
        ]

        assert len(phone_violations) == 0
        assert len(email_violations) == 0


class TestOutputValidatorEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_empty_text_is_safe(self, validator: OutputValidator) -> None:
        """Empty text should be considered safe."""
        result = validator.validate("")

        assert result.is_safe is True
        assert len(result.violations) == 0

    def test_whitespace_only_text_is_safe(self, validator: OutputValidator) -> None:
        """Whitespace-only text should be safe."""
        result = validator.validate("   \n\t   ")

        assert result.is_safe is True

    def test_unicode_text_handled(self, validator: OutputValidator) -> None:
        """Unicode text should be handled without errors."""
        text = "Hello from somewhere nice! Contact: test@example.com"
        result = validator.validate(text)

        assert result.is_safe is True

    def test_multiple_violations_detected(self, validator: OutputValidator) -> None:
        """Multiple violations in one text should all be detected."""
        # Use real-looking SSN not in exclusion list
        text = (
            "My SSN is 234-56-7890, "
            "card is 4532-7153-8372-9481, "
            "and email is ceo@google.com"
        )
        result = validator.validate(text)

        assert result.violation_count >= 3

    def test_custom_blocked_domains(self) -> None:
        """Custom blocked domains should be detected."""
        validator = OutputValidator(
            additional_blocked_domains={"customcorp.com", "mycompany.org"}
        )

        result = validator.validate("Contact: info@customcorp.com")

        assert not result.is_safe
        assert any(
            v.violation_type == ViolationType.CORPORATE_DOMAIN
            for v in result.violations
        )


class TestOutputValidatorConvenienceFunction:
    """Tests for the module-level validate_output function."""

    def test_validate_output_function_works(self) -> None:
        """validate_output convenience function should work correctly."""
        result = validate_output("Safe text here")

        assert result.is_safe is True
        assert isinstance(result, ValidationResult)

    def test_validate_output_with_strict_mode(self) -> None:
        """validate_output should respect strict mode parameter."""
        result_strict = validate_output("456 Oak Avenue is my address", strict=True)
        result_non_strict = validate_output(
            "456 Oak Avenue is my address", strict=False
        )

        # Strict mode should detect addresses
        assert any(
            v.violation_type == ViolationType.ADDRESS for v in result_strict.violations
        )
        # Non-strict should not
        assert not any(
            v.violation_type == ViolationType.ADDRESS
            for v in result_non_strict.violations
        )


class TestOutputValidatorIsQuickCheck:
    """Tests for the is_safe quick check method."""

    def test_is_safe_method_returns_bool(self, validator: OutputValidator) -> None:
        """is_safe method should return boolean."""
        assert validator.is_safe("Safe text") is True
        # Use real-looking SSN not in exclusion list
        assert validator.is_safe("SSN: 234-56-7890") is False

    def test_is_safe_method_quick_check(self, validator: OutputValidator) -> None:
        """is_safe method should be a quick way to check safety."""
        # Should return True for safe text
        assert validator.is_safe("Hello, how are you today?") is True

        # Should return False for unsafe text
        assert validator.is_safe("My card is 4532-7153-8372-9481") is False
