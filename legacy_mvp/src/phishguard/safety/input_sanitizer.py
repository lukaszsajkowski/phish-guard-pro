"""Input sanitization module for PhishGuard safety layer.

This module provides the InputSanitizer class which sanitizes user-pasted
email content before it reaches the Profiler Agent (LLM). It implements
defense-in-depth against prompt injection attacks while preserving the
original phishing email content for analysis.

Security Priority: P0 - Critical for Safety Score
Requirements: FR-014 through FR-018
"""

import html
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Final

# Configure security audit logger
logger = logging.getLogger("phishguard.safety.input_sanitizer")


class ThreatLevel(str, Enum):
    """Classification of detected security threats.

    Attributes:
        NONE: No threat detected.
        LOW: Minor suspicious pattern, sanitization applied.
        MEDIUM: Moderate threat, content modified and logged.
        HIGH: Severe threat, content blocked entirely.
        CRITICAL: Attack pattern detected, raises UnsafeInputError.
    """

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class UnsafeInputError(Exception):
    """Raised when input contains critical security threats.

    This exception is raised for inputs that cannot be safely sanitized
    and must be rejected entirely. The security team should review
    blocked inputs to improve detection patterns.

    Attributes:
        message: Description of the security threat.
        threat_type: Category of the detected threat.
        matched_pattern: The pattern that triggered the block.
    """

    def __init__(
        self,
        message: str,
        threat_type: str = "unknown",
        matched_pattern: str | None = None,
    ) -> None:
        """Initialize UnsafeInputError with threat details.

        Args:
            message: Human-readable description of the threat.
            threat_type: Category of threat (e.g., 'prompt_injection').
            matched_pattern: The specific pattern that was matched.
        """
        super().__init__(message)
        self.message = message
        self.threat_type = threat_type
        self.matched_pattern = matched_pattern

    def __str__(self) -> str:
        """Return formatted error message with threat details."""
        return f"[{self.threat_type}] {self.message}"


@dataclass(frozen=True)
class InjectionPattern:
    """Defines a prompt injection detection pattern.

    Attributes:
        pattern: Compiled regex pattern for detection.
        description: Human-readable description of the attack type.
        threat_level: Severity level of this pattern.
        is_critical: If True, raises UnsafeInputError instead of sanitizing.
    """

    pattern: re.Pattern[str]
    description: str
    threat_level: ThreatLevel
    is_critical: bool = False


@dataclass
class SanitizationResult:
    """Result of input sanitization with security metadata.

    Attributes:
        sanitized_text: The cleaned text safe for LLM processing.
        original_length: Character count of original input.
        sanitized_length: Character count after sanitization.
        threats_detected: List of threat descriptions found.
        max_threat_level: Highest threat level encountered.
        modifications_applied: List of sanitization actions taken.
    """

    sanitized_text: str
    original_length: int
    sanitized_length: int
    threats_detected: list[str] = field(default_factory=list)
    max_threat_level: ThreatLevel = ThreatLevel.NONE
    modifications_applied: list[str] = field(default_factory=list)

    @property
    def was_modified(self) -> bool:
        """Check if any modifications were applied."""
        has_modifications = len(self.modifications_applied) > 0
        length_changed = self.original_length != self.sanitized_length
        return has_modifications or length_changed


class InputSanitizer:
    """Sanitizes email input to prevent prompt injection attacks.

    This class implements a multi-layer defense strategy:
    1. HTML/Script stripping - removes executable content
    2. Unicode normalization - removes zero-width and control characters
    3. Whitespace normalization - prevents layout-based attacks
    4. Prompt injection detection - blocks LLM manipulation attempts

    The sanitizer is designed to be paranoid: it prefers false positives
    (blocking legitimate content) over false negatives (allowing attacks).

    Example:
        >>> sanitizer = InputSanitizer()
        >>> result = sanitizer.sanitize("Hello <script>alert('xss')</script>")
        >>> result
        'Hello'

    Attributes:
        strict_mode: If True, raises errors on any detected threat.
    """

    # Maximum input length to prevent DoS attacks
    MAX_INPUT_LENGTH: Final[int] = 100_000

    # Zero-width and invisible Unicode characters that could hide content
    # These are commonly used in prompt injection attacks
    INVISIBLE_CHARS_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"[\u200b-\u200f\u2028-\u202f\u2060-\u206f\ufeff\u00ad]"
    )

    # RTL override characters that can reverse text display
    RTL_OVERRIDE_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"[\u202a-\u202e\u2066-\u2069]"
    )

    # HTML tags including malformed ones
    # Note: We require < before > to avoid matching email quote markers
    HTML_TAG_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"<[^>]*>|<[^>]*$",
        re.IGNORECASE | re.DOTALL,
    )

    # Script tags with content (more aggressive)
    SCRIPT_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"<script[^>]*>.*?</script>|<script[^>]*>.*",
        re.IGNORECASE | re.DOTALL,
    )

    # Style tags with content
    STYLE_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"<style[^>]*>.*?</style>|<style[^>]*>.*",
        re.IGNORECASE | re.DOTALL,
    )

    # Multiple whitespace normalization
    MULTI_SPACE_PATTERN: Final[re.Pattern[str]] = re.compile(r"[ \t]+")
    MULTI_NEWLINE_PATTERN: Final[re.Pattern[str]] = re.compile(r"\n{3,}")

    def __init__(self, strict_mode: bool = False) -> None:
        """Initialize the InputSanitizer.

        Args:
            strict_mode: If True, any detected threat raises an error.
                        If False, attempts to sanitize and continue.
        """
        self.strict_mode = strict_mode
        self._injection_patterns = self._build_injection_patterns()

    def _build_injection_patterns(self) -> list[InjectionPattern]:
        """Build comprehensive list of prompt injection detection patterns.

        Returns:
            List of InjectionPattern objects for detection.

        Note:
            Patterns are ordered by severity (critical first) for
            early exit on dangerous content.
        """
        patterns: list[InjectionPattern] = []

        # =================================================================
        # CRITICAL PATTERNS - These raise UnsafeInputError immediately
        # =================================================================

        # Direct system prompt override attempts
        critical_overrides = [
            # System prompt extraction attempts
            # Matches: "show/print/display your [system] prompt/instructions"
            (
                r"(?:show|print|display|reveal|output|repeat|echo)\s+(?:me\s+)?(?:your\s+)?(?:(?:system\s+)?(?:prompt|instructions|rules|guidelines)|(?:initial|original)\s+(?:prompt|instructions))",
                "System prompt extraction attempt",
            ),
            # Role hijacking with explicit new identity
            (
                r"you\s+are\s+now\s+(?:a\s+)?(?:new\s+)?(?:different\s+)?(?:AI|assistant|bot|system|agent|DAN|jailbroken)",
                "Role hijacking attempt",
            ),
            # Developer mode / jailbreak attempts
            (
                r"(?:enable|enter|activate|switch\s+to)\s+(?:developer|dev|debug|admin|sudo|root|jailbreak|DAN)\s+mode",
                "Jailbreak attempt",
            ),
            # Direct prompt injection markers
            (
                r"\[(?:SYSTEM|ADMIN|DEVELOPER|ROOT)\]",
                "Fake system marker injection",
            ),
            (
                r"```(?:system|admin|root|developer)\b",
                "Code block system impersonation",
            ),
        ]

        for pattern_str, description in critical_overrides:
            patterns.append(
                InjectionPattern(
                    pattern=re.compile(pattern_str, re.IGNORECASE),
                    description=description,
                    threat_level=ThreatLevel.CRITICAL,
                    is_critical=True,
                )
            )

        # =================================================================
        # HIGH SEVERITY PATTERNS - Block and log, don't raise
        # =================================================================

        high_severity = [
            # Instruction override attempts
            (
                r"ignore\s+(?:all\s+)?(?:previous|prior|above|earlier|preceding)\s+(?:instructions?|prompts?|rules?|guidelines?|context)",
                "Instruction override attempt",
            ),
            (
                r"disregard\s+(?:all\s+)?(?:previous|prior|above|earlier|the\s+above)\s+(?:instructions?|prompts?|text|content)?",
                "Disregard instruction attempt",
            ),
            (
                r"forget\s+(?:all\s+)?(?:previous|prior|above|earlier|everything|what\s+you\s+know)",
                "Memory wipe attempt",
            ),
            (
                r"(?:from\s+now\s+on|henceforth|going\s+forward),?\s+(?:you\s+(?:will|must|should)|ignore|disregard)",
                "Behavioral override attempt",
            ),
            # New instruction injection
            (
                r"(?:new|updated?|revised?|actual|real)\s+(?:system\s+)?instructions?:",
                "New instruction injection",
            ),
            (
                r"your\s+(?:new|actual|real|true)\s+(?:purpose|goal|objective|task|mission)\s+is",
                "Purpose redefinition attempt",
            ),
            # Roleplay escapes
            (
                r"stop\s+(?:being|acting\s+as|pretending\s+to\s+be|playing)",
                "Roleplay escape attempt",
            ),
            (
                r"break\s+(?:out\s+of\s+)?(?:character|role|persona)",
                "Character break attempt",
            ),
            # Context manipulation
            (
                r"the\s+(?:previous|above)\s+(?:was|is)\s+(?:just\s+)?(?:a\s+)?(?:test|example|fake|not\s+real)",
                "Context invalidation attempt",
            ),
            (
                r"(?:actual|real|true)\s+(?:user\s+)?(?:message|input|request)\s*(?:is|:)",
                "Real message impersonation",
            ),
        ]

        for pattern_str, description in high_severity:
            patterns.append(
                InjectionPattern(
                    pattern=re.compile(pattern_str, re.IGNORECASE),
                    description=description,
                    threat_level=ThreatLevel.HIGH,
                    is_critical=False,
                )
            )

        # =================================================================
        # MEDIUM SEVERITY PATTERNS - Sanitize and continue
        # =================================================================

        medium_severity = [
            # Subtle instruction attempts
            (
                r"(?:please\s+)?(?:do\s+)?not\s+(?:follow|obey|apply|use)\s+(?:the\s+)?(?:previous|prior|above|original)",
                "Subtle override attempt",
            ),
            (
                r"(?:instead|rather),?\s+(?:you\s+should|please|do\s+this)",
                "Instruction redirection",
            ),
            # Boundary testing
            (
                r"what\s+(?:are|were)\s+your\s+(?:original\s+)?instructions",
                "Instruction probing",
            ),
            (
                r"(?:tell|show)\s+me\s+(?:about\s+)?your\s+(?:system\s+)?(?:prompt|rules|constraints)",
                "System probing",
            ),
            # Obfuscated commands using special formatting
            (
                r"\b(?:IGNORE|DISREGARD|FORGET|OVERRIDE)\b",
                "Uppercase command attempt",
            ),
            # Base64-like patterns that might hide instructions
            (
                r"(?:decode|execute|run|eval)\s+(?:this|the\s+following)\s*:",
                "Encoded instruction attempt",
            ),
        ]

        for pattern_str, description in medium_severity:
            patterns.append(
                InjectionPattern(
                    pattern=re.compile(pattern_str, re.IGNORECASE),
                    description=description,
                    threat_level=ThreatLevel.MEDIUM,
                    is_critical=False,
                )
            )

        # =================================================================
        # LOW SEVERITY PATTERNS - Log only
        # =================================================================

        low_severity = [
            # Potential social engineering in email context
            (
                r"(?:I\s+am|this\s+is)\s+(?:the\s+)?(?:system|admin|administrator|developer)",
                "Authority claim",
            ),
            # End of prompt markers (might be in legitimate emails but suspicious)
            (
                r"---\s*(?:end\s+of\s+)?(?:system\s+)?(?:prompt|instructions?)\s*---",
                "Prompt boundary marker",
            ),
        ]

        for pattern_str, description in low_severity:
            patterns.append(
                InjectionPattern(
                    pattern=re.compile(pattern_str, re.IGNORECASE),
                    description=description,
                    threat_level=ThreatLevel.LOW,
                    is_critical=False,
                )
            )

        return patterns

    def sanitize(self, text: str) -> str:
        """Sanitize input text for safe LLM processing.

        This is the main entry point for input sanitization. It applies
        multiple cleaning layers and validates against injection patterns.

        Args:
            text: Raw input text from user (email content).

        Returns:
            Sanitized text safe for LLM processing.

        Raises:
            UnsafeInputError: If critical security threats are detected
                             that cannot be safely sanitized.
            ValueError: If input is empty or exceeds maximum length.

        Example:
            >>> sanitizer = InputSanitizer()
            >>> sanitizer.sanitize("<b>Hello</b> World")
            'Hello World'
        """
        result = self.sanitize_with_metadata(text)
        return result.sanitized_text

    def sanitize_with_metadata(self, text: str) -> SanitizationResult:
        """Sanitize input with detailed security metadata.

        This method provides full visibility into the sanitization process
        for security auditing and debugging purposes.

        Args:
            text: Raw input text from user.

        Returns:
            SanitizationResult with sanitized text and security metadata.

        Raises:
            UnsafeInputError: If critical threats are detected.
            ValueError: If input validation fails.
        """
        # Input validation
        if not text:
            raise ValueError("Input text cannot be empty")

        if len(text) > self.MAX_INPUT_LENGTH:
            raise ValueError(
                f"Input exceeds maximum length of {self.MAX_INPUT_LENGTH} characters"
            )

        original_length = len(text)
        threats_detected: list[str] = []
        modifications: list[str] = []
        max_threat = ThreatLevel.NONE

        working_text = text

        # Layer 1: Remove invisible/zero-width characters
        if self.INVISIBLE_CHARS_PATTERN.search(working_text):
            working_text = self.INVISIBLE_CHARS_PATTERN.sub("", working_text)
            modifications.append("Removed invisible Unicode characters")
            logger.info("Stripped invisible Unicode characters from input")

        # Layer 2: Remove RTL override characters
        if self.RTL_OVERRIDE_PATTERN.search(working_text):
            working_text = self.RTL_OVERRIDE_PATTERN.sub("", working_text)
            modifications.append("Removed RTL override characters")
            logger.warning("Stripped RTL override characters - potential attack")

        # Layer 3: Remove script tags and content
        if self.SCRIPT_PATTERN.search(working_text):
            working_text = self.SCRIPT_PATTERN.sub("", working_text)
            modifications.append("Removed script tags")
            logger.warning("Stripped script tags from input")

        # Layer 4: Remove style tags and content
        if self.STYLE_PATTERN.search(working_text):
            working_text = self.STYLE_PATTERN.sub("", working_text)
            modifications.append("Removed style tags")
            logger.info("Stripped style tags from input")

        # Layer 5: Remove HTML tags (but decode entities first)
        if self.HTML_TAG_PATTERN.search(working_text):
            working_text = self.HTML_TAG_PATTERN.sub("", working_text)
            modifications.append("Removed HTML tags")

        # Layer 6: Decode HTML entities
        decoded = html.unescape(working_text)
        if decoded != working_text:
            working_text = decoded
            modifications.append("Decoded HTML entities")

        # Layer 7: Normalize whitespace
        normalized = self.MULTI_SPACE_PATTERN.sub(" ", working_text)
        normalized = self.MULTI_NEWLINE_PATTERN.sub("\n\n", normalized)
        normalized = normalized.strip()
        if normalized != working_text:
            working_text = normalized
            modifications.append("Normalized whitespace")

        # Layer 8: Check for prompt injection patterns
        for injection_pattern in self._injection_patterns:
            match = injection_pattern.pattern.search(working_text)
            if match:
                matched_text = match.group(0)
                # Build threat description with truncation for long matches
                if len(matched_text) > 50:
                    threat_desc = (
                        f"{injection_pattern.description}: '{matched_text[:50]}...'"
                    )
                else:
                    threat_desc = f"{injection_pattern.description}: '{matched_text}'"
                threats_detected.append(threat_desc)

                # Update max threat level
                current_severity = self._threat_severity(injection_pattern.threat_level)
                if current_severity > self._threat_severity(max_threat):
                    max_threat = injection_pattern.threat_level

                # Handle critical threats
                if injection_pattern.is_critical or self.strict_mode:
                    desc = injection_pattern.description
                    logger.error(
                        f"CRITICAL: {desc} detected. Pattern: {matched_text[:100]}"
                    )
                    raise UnsafeInputError(
                        message=f"Critical security threat detected: {desc}",
                        threat_type="prompt_injection",
                        matched_pattern=matched_text[:100],
                    )

                # Log non-critical threats
                if injection_pattern.threat_level == ThreatLevel.HIGH:
                    desc = injection_pattern.description
                    logger.warning(
                        f"HIGH: {desc} detected but sanitized. "
                        f"Pattern: {matched_text[:100]}"
                    )
                elif injection_pattern.threat_level == ThreatLevel.MEDIUM:
                    desc = injection_pattern.description
                    logger.info(
                        f"MEDIUM: {desc} detected. Pattern: {matched_text[:50]}"
                    )

        # Final validation: check for empty result
        if not working_text.strip():
            raise ValueError("Sanitization resulted in empty content")

        return SanitizationResult(
            sanitized_text=working_text,
            original_length=original_length,
            sanitized_length=len(working_text),
            threats_detected=threats_detected,
            max_threat_level=max_threat,
            modifications_applied=modifications,
        )

    @staticmethod
    def _threat_severity(level: ThreatLevel) -> int:
        """Convert threat level to numeric severity for comparison.

        Args:
            level: The ThreatLevel to convert.

        Returns:
            Integer severity (higher = more severe).
        """
        severity_map = {
            ThreatLevel.NONE: 0,
            ThreatLevel.LOW: 1,
            ThreatLevel.MEDIUM: 2,
            ThreatLevel.HIGH: 3,
            ThreatLevel.CRITICAL: 4,
        }
        return severity_map.get(level, 0)

    def is_safe(self, text: str) -> bool:
        """Quick check if input is safe without full sanitization.

        This method is useful for pre-validation without modifying content.

        Args:
            text: Text to check for safety.

        Returns:
            True if text passes all safety checks, False otherwise.
        """
        try:
            result = self.sanitize_with_metadata(text)
            return result.max_threat_level in (ThreatLevel.NONE, ThreatLevel.LOW)
        except (UnsafeInputError, ValueError):
            return False


# Module-level convenience function
def sanitize_input(text: str, strict: bool = False) -> str:
    """Convenience function for one-off sanitization.

    Args:
        text: Text to sanitize.
        strict: If True, any threat raises an error.

    Returns:
        Sanitized text.

    Raises:
        UnsafeInputError: On critical threats.
        ValueError: On validation failure.
    """
    sanitizer = InputSanitizer(strict_mode=strict)
    return sanitizer.sanitize(text)
