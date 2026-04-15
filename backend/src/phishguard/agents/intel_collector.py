"""Intel Collector for extracting IOCs from scammer messages.

This module implements the IntelCollector, which extracts Indicators of
Compromise (IOCs) from scammer messages using regex patterns. It runs
without LLM calls for performance.

Ported from legacy MVP - Requirements: FR-019, FR-020, FR-021, FR-022
"""

import logging
import re
import time
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
    """

    # Bitcoin wallet address patterns
    BTC_BECH32_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"\bbc1[ac-hj-np-z02-9]{39,59}\b",
        re.IGNORECASE,
    )
    BTC_LEGACY_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b",
    )

    # IBAN pattern: 2 letters + 2 digits + up to 30 alphanumeric
    IBAN_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"\b[A-Z]{2}[0-9]{2}[A-Z0-9]{4,30}\b",
        re.IGNORECASE,
    )

    # Phone number patterns (international formats)
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
        (?:/[^\s<>\"\')\]]*)?              # Optional path
        """,
        re.VERBOSE | re.IGNORECASE,
    )

    # IPv4: standard dotted-quad, not inside larger numbers
    IPV4_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"(?<!\d)(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
        r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)(?!\d)",
    )

    # IPv6: compact heuristic covering full and compressed forms
    IPV6_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"(?<![:\w])(?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{0,4}(?![:\w])",
    )

    # Private/loopback/link-local IPv4 ranges to exclude (not useful as IOCs)
    PRIVATE_IPV4_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"^(?:127\.|10\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.|169\.254\.)",
    )

    # Context extraction: characters before/after IOC
    CONTEXT_CHARS: Final[int] = 30

    # Valid IBAN country codes
    VALID_IBAN_COUNTRIES: Final[set[str]] = {
        "AD",
        "AE",
        "AL",
        "AT",
        "AZ",
        "BA",
        "BE",
        "BG",
        "BH",
        "BR",
        "CH",
        "CR",
        "CY",
        "CZ",
        "DE",
        "DK",
        "DO",
        "EE",
        "ES",
        "FI",
        "FO",
        "FR",
        "GB",
        "GE",
        "GI",
        "GL",
        "GR",
        "GT",
        "HR",
        "HU",
        "IE",
        "IL",
        "IS",
        "IT",
        "JO",
        "KW",
        "KZ",
        "LB",
        "LI",
        "LT",
        "LU",
        "LV",
        "MC",
        "MD",
        "ME",
        "MK",
        "MR",
        "MT",
        "MU",
        "NG",
        "NL",
        "NO",
        "PK",
        "PL",
        "PS",
        "PT",
        "QA",
        "RO",
        "RS",
        "SA",
        "SE",
        "SI",
        "SK",
        "SM",
        "TN",
        "TR",
        "UA",
        "VG",
        "XK",
    }

    # Patterns indicating a bank account context (to exclude from phone detection)
    BANK_ACCOUNT_CONTEXT: Final[re.Pattern[str]] = re.compile(
        r"(?:account|acct|a/c|routing|sort\s*code)\s*(?:no\.?|number|#|:)?\s*$",
        re.IGNORECASE,
    )

    def extract(self, text: str, message_index: int) -> ExtractionResult:
        """Extract IOCs from a message.

        Scans the text for BTC wallets, IBANs, phone numbers, and URLs.
        Returns all found IOCs with timestamps and context.

        Args:
            text: The message text to scan.
            message_index: Index of the message in conversation history.

        Returns:
            ExtractionResult with all found IOCs.
        """
        start_time = time.perf_counter()
        iocs: list[ExtractedIOC] = []
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

        # Extract phone numbers (skip if inside excluded ranges or bank context)
        for match in self.PHONE_PATTERN.finditer(text):
            if self._overlaps_excluded(match.start(), match.end(), excluded_ranges):
                continue
            value = match.group(0)
            if self._is_valid_phone(value) and not self._in_bank_context(
                text, match.start()
            ):
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
            excluded_ranges.append((match.start(), match.end()))
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

        # Extract IPv4 addresses (skip private/loopback and ranges inside URLs)
        for match in self.IPV4_PATTERN.finditer(text):
            if self._overlaps_excluded(match.start(), match.end(), excluded_ranges):
                continue
            value = match.group(0)
            if not self.PRIVATE_IPV4_PATTERN.match(value):
                iocs.append(
                    self._create_ioc(
                        IOCType.IP,
                        value,
                        text,
                        match.start(),
                        match.end(),
                        message_index,
                    )
                )

        # Extract IPv6 addresses (skip ranges inside URLs)
        for match in self.IPV6_PATTERN.finditer(text):
            if self._overlaps_excluded(match.start(), match.end(), excluded_ranges):
                continue
            iocs.append(
                self._create_ioc(
                    IOCType.IP,
                    match.group(0),
                    text,
                    match.start(),
                    match.end(),
                    message_index,
                )
            )

        # Deduplicate by value
        seen_values: set[str] = set()
        unique_iocs: list[ExtractedIOC] = []
        for ioc in iocs:
            normalized = ioc.value.lower()
            if normalized not in seen_values:
                seen_values.add(normalized)
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
        """Create an ExtractedIOC with context."""
        context_start = max(0, start - self.CONTEXT_CHARS)
        context_end = min(len(text), end + self.CONTEXT_CHARS)
        context = text[context_start:context_end]

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
        """Check if a range overlaps with any excluded range."""
        for exc_start, exc_end in excluded_ranges:
            if start < exc_end and end > exc_start:
                return True
        return False

    def _looks_like_iban(self, value: str) -> bool:
        """Check if a string looks like an IBAN (to avoid BTC false positives)."""
        if len(value) < 4:
            return False
        return value[:2].isalpha() and value[2:4].isdigit()

    def _is_valid_iban(self, value: str) -> bool:
        """Validate IBAN format (basic validation)."""
        if not (15 <= len(value) <= 34):
            return False
        if not value[:2].isalpha() or not value[2:4].isdigit():
            return False
        return value[:2].upper() in self.VALID_IBAN_COUNTRIES

    def _is_valid_phone(self, value: str) -> bool:
        """Validate phone number format."""
        digits = re.sub(r"\D", "", value)
        return 7 <= len(digits) <= 15

    def _in_bank_context(self, text: str, match_start: int) -> bool:
        """Check if match position is preceded by bank account context."""
        # Look at the 30 characters before the match
        context_start = max(0, match_start - 30)
        preceding_text = text[context_start:match_start]
        return bool(self.BANK_ACCOUNT_CONTEXT.search(preceding_text))
