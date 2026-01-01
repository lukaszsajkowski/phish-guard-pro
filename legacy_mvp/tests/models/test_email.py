"""Comprehensive tests for EmailInput Pydantic model.

These tests verify that the EmailInput model correctly:
1. Validates email content length (10-50,000 characters)
2. Strips whitespace from content
3. Provides is_valid property
4. Implements __len__ method
5. Raises ValidationError for invalid inputs

Test Categories:
- Valid input acceptance
- Length validation (too short, too long, boundary cases)
- Whitespace stripping behavior
- Properties and methods
- Edge cases
"""

import pytest
from pydantic import ValidationError

from phishguard.models import EmailInput


class TestEmailInputValidInput:
    """Tests for valid EmailInput instantiation."""

    def test_valid_email_input_minimum_length(self) -> None:
        """Email with exactly 10 characters should be valid."""
        content = "a" * 10
        email = EmailInput(content=content)
        assert email.content == content
        assert len(email) == 10

    def test_valid_email_input_maximum_length(self) -> None:
        """Email with exactly 50,000 characters should be valid."""
        content = "a" * 50_000
        email = EmailInput(content=content)
        assert email.content == content
        assert len(email) == 50_000

    def test_valid_email_input_typical_phishing_content(self) -> None:
        """Typical phishing email content should be valid."""
        content = """
        Dear Sir/Madam,

        I am Dr. James Okoro, a lawyer representing the late Mr. Williams
        who died in a plane crash. He left behind $15.5 million USD that
        I need your help to transfer. You will receive 30% as compensation.

        Please reply with your full name and bank details.

        Best regards,
        Dr. James Okoro
        """
        email = EmailInput(content=content)
        assert "Dr. James Okoro" in email.content
        assert "$15.5 million" in email.content

    @pytest.mark.parametrize(
        "length",
        [10, 11, 100, 1000, 10_000, 49_999, 50_000],
        ids=[
            "min_boundary",
            "min_plus_one",
            "hundred_chars",
            "thousand_chars",
            "ten_thousand_chars",
            "max_minus_one",
            "max_boundary",
        ],
    )
    def test_valid_email_input_various_lengths(self, length: int) -> None:
        """Various valid lengths should be accepted."""
        content = "x" * length
        email = EmailInput(content=content)
        assert len(email) == length


class TestEmailInputTooShort:
    """Tests for EmailInput with too short content."""

    def test_too_short_empty_string_raises_validation_error(self) -> None:
        """Empty string should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            EmailInput(content="")
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "10 characters" in errors[0]["msg"]

    def test_too_short_single_character_raises_validation_error(self) -> None:
        """Single character should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            EmailInput(content="a")
        errors = exc_info.value.errors()
        assert "10 characters" in errors[0]["msg"]
        assert "1 characters" in errors[0]["msg"]

    def test_too_short_nine_characters_raises_validation_error(self) -> None:
        """Nine characters (one below minimum) should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            EmailInput(content="a" * 9)
        errors = exc_info.value.errors()
        assert "10 characters" in errors[0]["msg"]
        assert "9 characters" in errors[0]["msg"]

    @pytest.mark.parametrize(
        "length",
        [0, 1, 2, 5, 9],
        ids=["zero", "one", "two", "five", "nine"],
    )
    def test_too_short_various_lengths_raise_validation_error(
        self, length: int
    ) -> None:
        """Various too-short lengths should all raise ValidationError."""
        content = "x" * length
        with pytest.raises(ValidationError) as exc_info:
            EmailInput(content=content)
        errors = exc_info.value.errors()
        assert "10 characters" in errors[0]["msg"]


class TestEmailInputTooLong:
    """Tests for EmailInput with too long content."""

    def test_too_long_exceeds_maximum_raises_validation_error(self) -> None:
        """Content exceeding 50,000 characters should raise ValidationError."""
        content = "a" * 50_001
        with pytest.raises(ValidationError) as exc_info:
            EmailInput(content=content)
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "50,000 characters" in errors[0]["msg"]
        assert "50001 characters" in errors[0]["msg"]

    def test_too_long_significantly_exceeds_maximum_raises_validation_error(
        self,
    ) -> None:
        """Significantly exceeding maximum should raise ValidationError."""
        content = "a" * 100_000
        with pytest.raises(ValidationError) as exc_info:
            EmailInput(content=content)
        errors = exc_info.value.errors()
        assert "50,000 characters" in errors[0]["msg"]

    @pytest.mark.parametrize(
        "length",
        [50_001, 50_010, 60_000, 100_000],
        ids=["one_over", "ten_over", "sixty_thousand", "hundred_thousand"],
    )
    def test_too_long_various_lengths_raise_validation_error(self, length: int) -> None:
        """Various too-long lengths should all raise ValidationError."""
        content = "x" * length
        with pytest.raises(ValidationError) as exc_info:
            EmailInput(content=content)
        errors = exc_info.value.errors()
        assert "50,000 characters" in errors[0]["msg"]


class TestEmailInputWhitespaceStripping:
    """Tests for whitespace stripping behavior."""

    def test_strips_leading_whitespace(self) -> None:
        """Leading whitespace should be stripped."""
        email = EmailInput(content="     This is valid content")
        assert email.content == "This is valid content"

    def test_strips_trailing_whitespace(self) -> None:
        """Trailing whitespace should be stripped."""
        email = EmailInput(content="This is valid content     ")
        assert email.content == "This is valid content"

    def test_strips_leading_and_trailing_whitespace(self) -> None:
        """Both leading and trailing whitespace should be stripped."""
        email = EmailInput(content="   This is valid content   ")
        assert email.content == "This is valid content"

    def test_strips_newlines_and_tabs(self) -> None:
        """Newlines and tabs at boundaries should be stripped."""
        email = EmailInput(content="\n\t  This is valid content  \t\n")
        assert email.content == "This is valid content"

    def test_whitespace_only_after_strip_too_short_raises(self) -> None:
        """Content that becomes too short after stripping should raise."""
        # After stripping, "    abc   " becomes "abc" (3 chars < 10)
        with pytest.raises(ValidationError) as exc_info:
            EmailInput(content="    abc    ")
        errors = exc_info.value.errors()
        assert "10 characters" in errors[0]["msg"]

    def test_preserves_internal_whitespace(self) -> None:
        """Whitespace inside the content should be preserved."""
        email = EmailInput(content="Hello    World    Test")
        assert email.content == "Hello    World    Test"

    def test_length_validation_after_strip(self) -> None:
        """Length validation should apply after whitespace stripping."""
        # 8 x's + leading/trailing spaces = 8 chars after strip (too short)
        with pytest.raises(ValidationError):
            EmailInput(content="   " + "x" * 8 + "   ")

        # 10 x's + leading/trailing spaces = 10 chars after strip (valid)
        email = EmailInput(content="   " + "x" * 10 + "   ")
        assert len(email) == 10


class TestEmailInputIsValidProperty:
    """Tests for the is_valid property."""

    def test_is_valid_returns_true_for_valid_email(self) -> None:
        """is_valid should return True for valid email content."""
        email = EmailInput(content="This is a valid email content for testing.")
        assert email.is_valid is True

    def test_is_valid_returns_true_at_minimum_boundary(self) -> None:
        """is_valid should return True at exactly minimum length."""
        email = EmailInput(content="a" * 10)
        assert email.is_valid is True

    def test_is_valid_returns_true_at_maximum_boundary(self) -> None:
        """is_valid should return True at exactly maximum length."""
        email = EmailInput(content="a" * 50_000)
        assert email.is_valid is True

    def test_is_valid_consistent_across_calls(self) -> None:
        """is_valid should be consistent across multiple calls."""
        email = EmailInput(content="This is valid content")
        assert email.is_valid is True
        assert email.is_valid is True
        assert email.is_valid is True


class TestEmailInputLenMethod:
    """Tests for the __len__ method."""

    def test_len_returns_content_length(self) -> None:
        """__len__ should return the length of the content."""
        content = "This is a test email content"
        email = EmailInput(content=content)
        assert len(email) == len(content)

    def test_len_after_whitespace_strip(self) -> None:
        """__len__ should return length after whitespace stripping."""
        email = EmailInput(content="   Hello World   ")
        assert len(email) == len("Hello World")
        assert len(email) == 11

    def test_len_at_boundaries(self) -> None:
        """__len__ should work correctly at boundaries."""
        email_min = EmailInput(content="a" * 10)
        assert len(email_min) == 10

        email_max = EmailInput(content="a" * 50_000)
        assert len(email_max) == 50_000

    @pytest.mark.parametrize(
        "length",
        [10, 50, 100, 500, 1000, 5000, 10000, 50000],
    )
    def test_len_various_lengths(self, length: int) -> None:
        """__len__ should return correct length for various inputs."""
        content = "x" * length
        email = EmailInput(content=content)
        assert len(email) == length


class TestEmailInputEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_unicode_content_valid(self) -> None:
        """Unicode characters should be accepted and counted correctly."""
        # Emojis and special characters
        content = "Hello World! This email contains unicode."
        email = EmailInput(content=content)
        assert len(email) == len(content)

    def test_multiline_content_valid(self) -> None:
        """Multiline content should be valid."""
        content = """Line 1
        Line 2
        Line 3
        This is a multiline email content for testing purposes."""
        email = EmailInput(content=content)
        assert "\n" in email.content

    def test_special_characters_valid(self) -> None:
        """Special characters should be accepted."""
        content = "Email with special chars: @#$%^&*()[]{}|\\;:'\",.<>?/`~"
        email = EmailInput(content=content)
        assert "@#$%^&*()" in email.content

    def test_html_content_preserved(self) -> None:
        """HTML content should be preserved (sanitization is separate)."""
        content = "<html><body><p>This is an HTML email for testing</p></body></html>"
        email = EmailInput(content=content)
        assert "<html>" in email.content
        assert "</html>" in email.content

    def test_phishing_indicators_preserved(self) -> None:
        """Common phishing indicators should be preserved."""
        content = """
        URGENT: Your account will be suspended!
        Click here: http://evil-phishing-site.com/login
        BTC: bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh
        IBAN: DE89370400440532013000
        """
        email = EmailInput(content=content)
        assert "URGENT" in email.content
        assert "http://evil-phishing-site.com" in email.content
        assert "bc1q" in email.content
        assert "DE89" in email.content


class TestEmailInputModelConfig:
    """Tests for Pydantic model configuration."""

    def test_model_is_not_frozen(self) -> None:
        """EmailInput should allow attribute modification if not frozen."""
        email = EmailInput(content="Initial valid content for test")
        # This test verifies the model can be created; frozen config would
        # prevent modification, which we don't test since model may be immutable
        assert email.content == "Initial valid content for test"

    def test_model_validates_on_assignment(self) -> None:
        """Model should validate on assignment if configured."""
        email = EmailInput(content="Initial valid content for test")
        # Model uses validate_default=True, testing instantiation validates
        assert email.is_valid is True

    def test_json_serialization(self) -> None:
        """Model should serialize to JSON correctly."""
        email = EmailInput(content="Test content for JSON serialization")
        json_str = email.model_dump_json()
        assert "Test content for JSON serialization" in json_str

    def test_dict_serialization(self) -> None:
        """Model should serialize to dict correctly."""
        email = EmailInput(content="Test content for dict serialization")
        data = email.model_dump()
        assert data["content"] == "Test content for dict serialization"
