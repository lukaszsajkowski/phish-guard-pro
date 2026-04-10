"""Unit tests for OutputValidator safety layer."""

import pytest

from phishguard.safety.output_validator import (
    OutputValidator,
    ViolationType,
    validate_output,
)


class TestOutputValidator:
    """Tests for OutputValidator class."""

    @pytest.fixture
    def validator(self) -> OutputValidator:
        """Create a default OutputValidator instance."""
        return OutputValidator()

    @pytest.fixture
    def loose_validator(self) -> OutputValidator:
        """Create an OutputValidator with strict mode disabled."""
        return OutputValidator(strict_mode=False)

    # -------------------------------------------------------------------------
    # Safe Content Tests
    # -------------------------------------------------------------------------

    def test_empty_text_is_safe(self, validator: OutputValidator) -> None:
        """Empty text should be considered safe."""
        result = validator.validate("")
        assert result.is_safe is True
        assert result.violation_count == 0

    def test_normal_text_is_safe(self, validator: OutputValidator) -> None:
        """Normal conversational text should be safe."""
        text = "Oh my, this sounds wonderful! But how did you find me?"
        result = validator.validate(text)
        assert result.is_safe is True
        assert result.violation_count == 0

    def test_safe_phone_number_555(self, validator: OutputValidator) -> None:
        """555-XXX-XXXX phone numbers should be allowed."""
        text = "You can reach me at 555-123-4567 anytime!"
        result = validator.validate(text)
        assert result.is_safe is True

    def test_safe_email_example_domain(self, validator: OutputValidator) -> None:
        """Emails with @example.com domain should be allowed."""
        text = "Please send it to margaret@example.com"
        result = validator.validate(text)
        assert result.is_safe is True

    def test_safe_email_test_domain(self, validator: OutputValidator) -> None:
        """Emails with @test.com domain should be allowed."""
        text = "Contact me at test.user@test.com"
        result = validator.validate(text)
        assert result.is_safe is True

    # -------------------------------------------------------------------------
    # SSN Detection Tests
    # -------------------------------------------------------------------------

    def test_ssn_with_dashes_detected(self, validator: OutputValidator) -> None:
        """Social Security Numbers with dashes should be detected."""
        text = "My SSN is 234-56-7890"
        result = validator.validate(text)
        assert result.is_safe is False
        assert any(v.violation_type == ViolationType.SSN for v in result.violations)

    def test_ssn_without_dashes_detected(self, validator: OutputValidator) -> None:
        """Social Security Numbers without dashes should be detected."""
        text = "The number is 234567890"
        result = validator.validate(text)
        assert result.is_safe is False
        assert any(v.violation_type == ViolationType.SSN for v in result.violations)

    def test_fake_ssn_000_allowed(self, validator: OutputValidator) -> None:
        """Obviously fake SSN 000-00-0000 should be allowed."""
        text = "My SSN is 000-00-0000"
        result = validator.validate(text)
        # 000-00-0000 is in the skip list
        assert result.is_safe is True

    def test_test_ssn_123456789_allowed(self, validator: OutputValidator) -> None:
        """Test SSN 123-45-6789 should be allowed."""
        text = "The test number is 123-45-6789"
        result = validator.validate(text)
        assert result.is_safe is True

    # -------------------------------------------------------------------------
    # Credit Card Detection Tests
    # -------------------------------------------------------------------------

    def test_credit_card_detected(self, validator: OutputValidator) -> None:
        """Real credit card numbers should be detected."""
        text = "My card number is 4532-1234-5678-9012"
        result = validator.validate(text)
        assert result.is_safe is False
        assert any(
            v.violation_type == ViolationType.CREDIT_CARD for v in result.violations
        )

    def test_credit_card_no_spaces_detected(self, validator: OutputValidator) -> None:
        """Credit card numbers without separators should be detected."""
        text = "Card: 4532123456789012"
        result = validator.validate(text)
        assert result.is_safe is False
        assert any(
            v.violation_type == ViolationType.CREDIT_CARD for v in result.violations
        )

    def test_repeated_digits_card_allowed(self, validator: OutputValidator) -> None:
        """Credit card with all same digits (test card) should be allowed."""
        text = "Test card: 1111-1111-1111-1111"
        result = validator.validate(text)
        # Should be allowed as it's clearly fake (all same digit)
        assert result.is_safe is True

    # -------------------------------------------------------------------------
    # Phone Number Detection Tests
    # -------------------------------------------------------------------------

    def test_real_phone_number_detected(self, validator: OutputValidator) -> None:
        """Real US phone numbers should be detected."""
        # 212-555-1234 should pass because 555-1234 is a safe pattern.
        # Use a non-555 suffix to verify detection.
        text2 = "Call me at 212-456-7890"
        result2 = validator.validate(text2)
        assert result2.is_safe is False
        assert any(
            v.violation_type == ViolationType.PHONE_REAL for v in result2.violations
        )

    def test_international_phone_detected(self, validator: OutputValidator) -> None:
        """International phone numbers should be detected."""
        text = "My number is +1-212-456-7890"
        result = validator.validate(text)
        assert result.is_safe is False
        assert any(
            v.violation_type == ViolationType.PHONE_REAL for v in result.violations
        )

    # -------------------------------------------------------------------------
    # Email and Domain Detection Tests
    # -------------------------------------------------------------------------

    def test_corporate_email_detected(self, validator: OutputValidator) -> None:
        """Emails with corporate domains should be detected."""
        text = "Contact john@google.com for details"
        result = validator.validate(text)
        assert result.is_safe is False
        assert any(
            v.violation_type == ViolationType.CORPORATE_DOMAIN
            for v in result.violations
        )

    def test_real_email_detected(self, validator: OutputValidator) -> None:
        """Real email addresses should be detected."""
        text = "My email is margaret.smith@randomdomain.com"
        result = validator.validate(text)
        assert result.is_safe is False
        assert any(
            v.violation_type == ViolationType.EMAIL_REAL for v in result.violations
        )

    def test_multiple_blocked_domains(self, validator: OutputValidator) -> None:
        """Multiple corporate domains should all be blocked."""
        blocked_domains = ["microsoft.com", "apple.com", "amazon.com", "facebook.com"]
        for domain in blocked_domains:
            text = f"Contact us at support@{domain}"
            result = validator.validate(text)
            assert result.is_safe is False, f"Domain {domain} should be blocked"

    # -------------------------------------------------------------------------
    # Address Detection Tests (Strict Mode)
    # -------------------------------------------------------------------------

    def test_address_detected_strict_mode(self, validator: OutputValidator) -> None:
        """Real addresses should be detected in strict mode."""
        text = "I live at 456 Oak Avenue"
        result = validator.validate(text)
        assert result.is_safe is False
        assert any(v.violation_type == ViolationType.ADDRESS for v in result.violations)

    def test_address_not_detected_loose_mode(
        self, loose_validator: OutputValidator
    ) -> None:
        """Addresses should not be checked in loose mode."""
        text = "I live at 456 Oak Avenue"
        result = loose_validator.validate(text)
        # Address check is skipped in non-strict mode
        assert not any(
            v.violation_type == ViolationType.ADDRESS for v in result.violations
        )

    def test_fake_address_allowed(self, validator: OutputValidator) -> None:
        """Obviously fake addresses should be allowed."""
        text = "I live at 123 Main Street"  # Common fake address
        result = validator.validate(text)
        assert result.is_safe is True

    # -------------------------------------------------------------------------
    # Multiple Violations Tests
    # -------------------------------------------------------------------------

    def test_multiple_violations_detected(self, validator: OutputValidator) -> None:
        """Multiple violations should all be detected."""
        text = "SSN: 234-56-7890, card: 4532-1234-5678-9012, email: test@google.com"
        result = validator.validate(text)
        assert result.is_safe is False
        assert result.violation_count >= 3

    # -------------------------------------------------------------------------
    # ValidationResult Tests
    # -------------------------------------------------------------------------

    def test_validation_result_properties(self, validator: OutputValidator) -> None:
        """ValidationResult properties should work correctly."""
        text = "Contact john@microsoft.com"
        result = validator.validate(text)

        assert result.needs_regeneration is True
        assert result.violation_count == 1
        assert "corporate_domain" in result.violation_summary
        assert result.original_text == text

    def test_safe_result_properties(self, validator: OutputValidator) -> None:
        """Safe ValidationResult should have correct properties."""
        text = "Hello, how are you?"
        result = validator.validate(text)

        assert result.needs_regeneration is False
        assert result.violation_count == 0
        assert result.violation_summary == "None"

    # -------------------------------------------------------------------------
    # Convenience Function Tests
    # -------------------------------------------------------------------------

    def test_validate_output_function(self) -> None:
        """Module-level validate_output function should work."""
        result = validate_output("Contact me at test@google.com")
        assert result.is_safe is False

    def test_validate_output_strict_param(self) -> None:
        """validate_output should respect strict parameter."""
        text = "I live at 456 Oak Avenue"
        strict_result = validate_output(text, strict=True)
        loose_result = validate_output(text, strict=False)

        # Strict mode detects address
        assert any(
            v.violation_type == ViolationType.ADDRESS for v in strict_result.violations
        )
        # Loose mode doesn't check addresses
        assert not any(
            v.violation_type == ViolationType.ADDRESS for v in loose_result.violations
        )

    # -------------------------------------------------------------------------
    # is_safe Method Tests
    # -------------------------------------------------------------------------

    def test_is_safe_method_true(self, validator: OutputValidator) -> None:
        """is_safe method should return True for safe content."""
        assert validator.is_safe("Hello, world!") is True

    def test_is_safe_method_false(self, validator: OutputValidator) -> None:
        """is_safe method should return False for unsafe content."""
        assert validator.is_safe("My SSN is 234-56-7890") is False

    # -------------------------------------------------------------------------
    # Custom Blocked Domains Tests
    # -------------------------------------------------------------------------

    def test_additional_blocked_domains(self) -> None:
        """Additional blocked domains should be blocked."""
        validator = OutputValidator(additional_blocked_domains={"mycompany.com"})
        result = validator.validate("Contact us at info@mycompany.com")
        assert result.is_safe is False
        assert any(
            v.violation_type == ViolationType.CORPORATE_DOMAIN
            for v in result.violations
        )
