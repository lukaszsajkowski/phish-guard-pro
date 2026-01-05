"""IOC (Indicators of Compromise) models for PhishGuard.

This module contains Pydantic models for representing IOCs extracted
from scammer messages during conversation.
"""

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class IOCType(str, Enum):
    """Types of Indicators of Compromise extracted from messages.

    Attributes:
        BTC_WALLET: Bitcoin wallet address.
        IBAN: International Bank Account Number.
        PHONE: Phone number in various formats.
        URL: Web URL (http/https).
    """

    BTC_WALLET = "btc_wallet"
    """Bitcoin wallet address (bc1, 1, 3 prefix)."""

    IBAN = "iban"
    """International Bank Account Number."""

    PHONE = "phone"
    """Phone number (international formats)."""

    URL = "url"
    """Web URL (http/https)."""

    @property
    def display_name(self) -> str:
        """Get human-readable name for the IOC type."""
        names = {
            IOCType.BTC_WALLET: "BTC Wallet",
            IOCType.IBAN: "IBAN",
            IOCType.PHONE: "Phone Number",
            IOCType.URL: "URL",
        }
        return names.get(self, self.value)

    @property
    def is_high_value(self) -> bool:
        """Check if this IOC type is high-value (financial).

        High-value IOCs are BTC wallets and IBANs.
        """
        return self in (IOCType.BTC_WALLET, IOCType.IBAN)


class ExtractedIOC(BaseModel):
    """A single extracted Indicator of Compromise.

    Attributes:
        ioc_type: The type of IOC (BTC, IBAN, phone, URL).
        value: The extracted value.
        timestamp: When the IOC was extracted.
        context: Surrounding text for context (optional).
        message_index: Index of the message where IOC was found.
    """

    model_config = ConfigDict(
        frozen=True,
        validate_assignment=True,
        use_enum_values=False,
    )

    ioc_type: IOCType = Field(
        ...,
        description="The type of IOC extracted.",
    )
    value: str = Field(
        ...,
        description="The extracted IOC value.",
        min_length=1,
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the IOC was extracted.",
    )
    context: str | None = Field(
        default=None,
        description="Surrounding text for context.",
    )
    message_index: int = Field(
        ...,
        description="Index of the message in conversation history.",
        ge=0,
    )

    @property
    def is_high_value(self) -> bool:
        """Check if this is a high-value IOC."""
        return self.ioc_type.is_high_value
