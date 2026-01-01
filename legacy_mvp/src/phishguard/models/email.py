"""Email input models for PhishGuard.

This module contains Pydantic models for validating email content
pasted by users before analysis by the Profiler Agent.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EmailInput(BaseModel):
    """Validated email content input for phishing analysis.

    This model validates email content pasted by users in the UI
    before passing it to the Profiler Agent for classification.

    Attributes:
        content: The raw email content to analyze. Must be between
            10 and 50,000 characters.

    Example:
        >>> email = EmailInput(content="Dear Sir, I have a business proposal...")
        >>> email.is_valid
        True
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
    )

    content: str = Field(
        ...,
        description="Raw email content to analyze for phishing indicators",
        json_schema_extra={
            "minLength": 10,
            "maxLength": 50_000,
            "examples": [
                "Dear Sir, I am a Nigerian prince and I need your help...",
                "URGENT: Your account has been compromised. Click here to verify...",
            ],
        },
    )

    @field_validator("content", mode="after")
    @classmethod
    def validate_content_length(cls, value: str) -> str:
        """Validate content length with custom error messages.

        Args:
            value: The email content string after stripping whitespace.

        Returns:
            The validated content string.

        Raises:
            ValueError: If content is too short or too long.
        """
        if len(value) < 10:
            raise ValueError(
                f"Email content must be at least 10 characters long. "
                f"Provided content has only {len(value)} characters."
            )
        if len(value) > 50_000:
            raise ValueError(
                f"Email content must not exceed 50,000 characters. "
                f"Provided content has {len(value)} characters."
            )
        return value

    @property
    def is_valid(self) -> bool:
        """Check if the email content passes validation.

        This property provides a quick way to verify that the content
        meets all validation requirements without re-raising exceptions.

        Returns:
            True if the content is valid, False otherwise.
        """
        try:
            # Content has already been validated during instantiation,
            # but we check the constraints explicitly for clarity
            return 10 <= len(self.content) <= 50_000
        except Exception:
            return False

    def __len__(self) -> int:
        """Return the length of the email content.

        Returns:
            The number of characters in the content.
        """
        return len(self.content)
