"""Intel Collector for extracting IOCs from scammer messages.

This module implements the IntelCollector, which extracts Indicators of
Compromise (IOCs) from scammer messages using regex patterns. It runs
without LLM calls for performance.

Requirements: FR-019, FR-020, FR-021, FR-022
"""

import logging
import re
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from phishguard.models.ioc import ExtractedIOC, IOCType

logger = logging.getLogger(__name__)


class ExtractionResult(BaseModel):
    """Result of IOC extraction from a message.

    Attributes:
        iocs: List of extracted IOCs.
        extraction_time_ms: Time taken for extraction in milliseconds.
        message_index: Index of the processed message.
    """

    model_config = ConfigDict(
        frozen=True,
        validate_assignment=True,
    )

    iocs: tuple[ExtractedIOC, ...] = Field(
        default_factory=tuple,
        description="List of extracted IOCs.",
    )
    extraction_time_ms: int = Field(
        ...,
        description="Time taken for extraction in milliseconds.",
        ge=0,
    )
    message_index: int = Field(
        ...,
        description="Index of the processed message.",
        ge=0,
    )

    @property
    def has_iocs(self) -> bool:
        """Check if any IOCs were extracted."""
        return len(self.iocs) > 0

    @property
    def high_value_count(self) -> int:
        """Count of high-value IOCs (BTC, IBAN)."""
        return sum(1 for ioc in self.iocs if ioc.is_high_value)


class IntelCollector:
    """Extracts Indicators of Compromise from scammer messages.

    The IntelCollector uses regex patterns to extract IOCs from text
    without making LLM calls. It runs in parallel with conversation
    generation for performance.

    Supported IOC types:
    - BTC wallet addresses (bc1/1/3 prefix)
    - IBAN numbers (2 letters + 2 digits + up to 30 alphanumeric)
    - Phone numbers (international formats)
    - URLs (http/https)

    Example:
        >>> collector = IntelCollector()
        >>> result = collector.extract(
        ...     "Send money to bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
        ...     message_index=1
        ... )
        >>> len(result.iocs)
        1
        >>> result.iocs[0].ioc_type
        <IOCType.BTC_WALLET: 'btc_wallet'>
    """

    # Bitcoin wallet address patterns
    # bc1 (bech32): bc1 + 39-59 chars (lowercase alphanumeric, no 1/b/i/o)
    # Legacy (1/3): 1 or 3 followed by 25-34 base58 characters
    BTC_BECH32_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"\bbc1[ac-hj-np-z02-9]{39,59}\b",
        re.IGNORECASE,
    )
    BTC_LEGACY_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b",
    )

    # IBAN pattern: 2 letters + 2 digits + up to 30 alphanumeric
    # Examples: GB82WEST12345698765432, DE89370400440532013000
    IBAN_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"\b[A-Z]{2}[0-9]{2}[A-Z0-9]{4,30}\b",
        re.IGNORECASE,
    )

    # Phone number patterns (international formats)
    # Matches: +1-234-567-8900, +44 20 7123 4567, (123) 456-7890, etc.
    PHONE_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"""
        (?:
            # International format with + prefix
            \+[1-9]\d{0,2}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}
            |
            # US format: (123) 456-7890 or 123-456-7890
            \(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}
            |
            # Generic international: country code + number
            \+[1-9]\d{6,14}
        )
        """,
        re.VERBOSE,
    )

    # URL pattern: http/https with domain and optional path
    URL_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"""
        https?://                           # Protocol
        (?:[\w-]+\.)+[\w-]+                 # Domain
        (?:/[^\s<>\"\'\)\]]*)?              # Optional path
        """,
        re.VERBOSE | re.IGNORECASE,
    )

    # Context extraction: characters before/after IOC
    CONTEXT_CHARS: Final[int] = 30

    def __init__(self) -> None:
        """Initialize the IntelCollector."""
        pass

    def extract(self, text: str, message_index: int) -> ExtractionResult:
        """Extract IOCs from a message.

        Scans the text for BTC wallets, IBANs, phone numbers, and URLs.
        Returns all found IOCs with timestamps and context.

        Args:
            text: The message text to scan.
            message_index: Index of the message in conversation history.

        Returns:
            ExtractionResult with all found IOCs.

        Example:
            >>> collector = IntelCollector()
            >>> result = collector.extract(
            ...     "Contact me at +1-555-123-4567 or visit https://scam.com",
            ...     message_index=0
            ... )
            >>> len(result.iocs)
            2
        """
        import time

        start_time = time.perf_counter()
        iocs: list[ExtractedIOC] = []

        # Track ranges of text that belong to other IOC types
        # to avoid false positives (e.g., phone numbers inside IBANs)
        excluded_ranges: list[tuple[int, int]] = []

        # Extract BTC wallets (bech32)
        for match in self.BTC_BECH32_PATTERN.finditer(text):
            excluded_ranges.append((match.start(), match.end()))
            iocs.append(
                self._create_ioc(
                    IOCType.BTC_WALLET,
                    match.group(0),
                    text,
                    match.start(),
                    match.end(),
                    message_index,
                )
            )

        # Extract BTC wallets (legacy)
        for match in self.BTC_LEGACY_PATTERN.finditer(text):
            value = match.group(0)
            # Avoid false positives from IBAN pattern overlap
            if not self._looks_like_iban(value):
                excluded_ranges.append((match.start(), match.end()))
                iocs.append(
                    self._create_ioc(
                        IOCType.BTC_WALLET,
                        value,
                        text,
                        match.start(),
                        match.end(),
                        message_index,
                    )
                )

        # Extract IBANs
        for match in self.IBAN_PATTERN.finditer(text):
            value = match.group(0).upper()
            if self._is_valid_iban(value):
                excluded_ranges.append((match.start(), match.end()))
                iocs.append(
                    self._create_ioc(
                        IOCType.IBAN,
                        value,
                        text,
                        match.start(),
                        match.end(),
                        message_index,
                    )
                )

        # Extract phone numbers (skip if inside excluded ranges)
        for match in self.PHONE_PATTERN.finditer(text):
            # Check if this match overlaps with any excluded range
            if self._overlaps_excluded(match.start(), match.end(), excluded_ranges):
                continue
            value = match.group(0)
            # Clean up and validate
            if self._is_valid_phone(value):
                iocs.append(
                    self._create_ioc(
                        IOCType.PHONE,
                        value,
                        text,
                        match.start(),
                        match.end(),
                        message_index,
                    )
                )

        # Extract URLs
        for match in self.URL_PATTERN.finditer(text):
            iocs.append(
                self._create_ioc(
                    IOCType.URL,
                    match.group(0),
                    text,
                    match.start(),
                    match.end(),
                    message_index,
                )
            )

        # Deduplicate IOCs by value (keep first occurrence)
        seen_values: set[str] = set()
        unique_iocs: list[ExtractedIOC] = []
        for ioc in iocs:
            normalized_value = ioc.value.lower()
            if normalized_value not in seen_values:
                seen_values.add(normalized_value)
                unique_iocs.append(ioc)

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        if unique_iocs:
            logger.info(
                "Extracted %d IOCs from message %d in %dms",
                len(unique_iocs),
                message_index,
                elapsed_ms,
            )

        return ExtractionResult(
            iocs=tuple(unique_iocs),
            extraction_time_ms=elapsed_ms,
            message_index=message_index,
        )

    def _create_ioc(
        self,
        ioc_type: IOCType,
        value: str,
        text: str,
        start: int,
        end: int,
        message_index: int,
    ) -> ExtractedIOC:
        """Create an ExtractedIOC with context.

        Args:
            ioc_type: Type of IOC.
            value: The extracted value.
            text: Full message text.
            start: Start index of match.
            end: End index of match.
            message_index: Message index in conversation.

        Returns:
            ExtractedIOC with surrounding context.
        """
        # Extract context around the IOC
        context_start = max(0, start - self.CONTEXT_CHARS)
        context_end = min(len(text), end + self.CONTEXT_CHARS)
        context = text[context_start:context_end]

        # Add ellipsis if truncated
        if context_start > 0:
            context = "..." + context
        if context_end < len(text):
            context = context + "..."

        return ExtractedIOC(
            ioc_type=ioc_type,
            value=value,
            context=context,
            message_index=message_index,
        )

    def _overlaps_excluded(
        self, start: int, end: int, excluded_ranges: list[tuple[int, int]]
    ) -> bool:
        """Check if a range overlaps with any excluded range.

        Args:
            start: Start index of match.
            end: End index of match.
            excluded_ranges: List of (start, end) tuples to exclude.

        Returns:
            True if the range overlaps with any excluded range.
        """
        for exc_start, exc_end in excluded_ranges:
            # Check for overlap
            if start < exc_end and end > exc_start:
                return True
        return False

    def _looks_like_iban(self, value: str) -> bool:
        """Check if a string looks like an IBAN (to avoid BTC false positives).

        Args:
            value: String to check.

        Returns:
            True if it looks like an IBAN.
        """
        # IBANs start with 2 letters followed by 2 digits
        if len(value) < 4:
            return False
        return value[:2].isalpha() and value[2:4].isdigit()

    def _is_valid_iban(self, value: str) -> bool:
        """Validate IBAN format (basic validation).

        Args:
            value: Uppercase IBAN string.

        Returns:
            True if format is valid.
        """
        # Must be 15-34 characters
        if not (15 <= len(value) <= 34):
            return False

        # First 2 chars must be letters, next 2 must be digits
        if not value[:2].isalpha() or not value[2:4].isdigit():
            return False

        # Known country codes with IBAN support (subset)
        valid_country_codes = {
            "AD", "AE", "AL", "AT", "AZ", "BA", "BE", "BG", "BH", "BR",
            "CH", "CR", "CY", "CZ", "DE", "DK", "DO", "EE", "ES", "FI",
            "FO", "FR", "GB", "GE", "GI", "GL", "GR", "GT", "HR", "HU",
            "IE", "IL", "IS", "IT", "JO", "KW", "KZ", "LB", "LI", "LT",
            "LU", "LV", "MC", "MD", "ME", "MK", "MR", "MT", "MU", "NL",
            "NO", "PK", "PL", "PS", "PT", "QA", "RO", "RS", "SA", "SE",
            "SI", "SK", "SM", "TN", "TR", "UA", "VG", "XK",
        }

        country_code = value[:2].upper()
        if country_code not in valid_country_codes:
            return False

        return True

    def _is_valid_phone(self, value: str) -> bool:
        """Validate phone number format.

        Args:
            value: Phone number string.

        Returns:
            True if format is valid.
        """
        # Extract just digits
        digits = re.sub(r"\D", "", value)

        # Must have at least 7 digits (local) and at most 15 (E.164 max)
        if not (7 <= len(digits) <= 15):
            return False

        return True
