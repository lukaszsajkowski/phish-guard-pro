"""Bot unmasking detection module for PhishGuard safety layer.

This module provides the UnmaskingDetector class which detects when a scammer
appears to have realized they are talking to a bot, not a real person. This
enables the system to automatically propose ending the session.

Security Priority: P1 - Important for Session Management
Requirements: FR-028, FR-029, US-016
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Final

logger = logging.getLogger("phishguard.safety.unmasking_detector")


@dataclass(frozen=True)
class UnmaskingResult:
    """Result of unmasking detection analysis.

    Attributes:
        is_unmasked: True if unmasking phrases were detected.
        matched_phrases: List of phrases that triggered detection.
        confidence: Confidence level of detection (0.0-1.0).
    """

    is_unmasked: bool
    matched_phrases: list[str] = field(default_factory=list)
    confidence: float = 0.0

    @property
    def phrase_count(self) -> int:
        """Get the number of matched phrases."""
        return len(self.matched_phrases)


@dataclass(frozen=True)
class UnmaskingPattern:
    """Defines a pattern for detecting bot unmasking.

    Attributes:
        pattern: Compiled regex pattern for detection.
        description: Human-readable description of what this pattern detects.
        weight: Weight for confidence calculation (higher = more certain).
    """

    pattern: re.Pattern[str]
    description: str
    weight: float = 1.0


class UnmaskingDetector:
    """Detects when a scammer has unmasked the bot.

    This detector analyzes scammer messages for phrases that indicate
    they have realized they are talking to a bot or automated system,
    not a real person. Detection triggers include:

    - Direct accusations ("you're a bot", "this is fake")
    - Frustration phrases ("stop wasting my time", "I know what you're doing")
    - Conversation termination ("I'm done", "goodbye scammer")
    - No-response indicators (handled separately by the UI)

    Example:
        >>> detector = UnmaskingDetector()
        >>> result = detector.detect("You're just a bot, stop messaging me")
        >>> result.is_unmasked
        True
        >>> result.matched_phrases
        ["you're just a bot", "stop messaging me"]
    """

    # Minimum confidence threshold to consider unmasking detected
    CONFIDENCE_THRESHOLD: Final[float] = 0.3

    def __init__(self) -> None:
        """Initialize the UnmaskingDetector with detection patterns."""
        self._patterns = self._build_patterns()

    def _build_patterns(self) -> list[UnmaskingPattern]:
        """Build the list of unmasking detection patterns.

        Returns:
            List of UnmaskingPattern objects for detection.
        """
        patterns: list[UnmaskingPattern] = []

        # =================================================================
        # HIGH CONFIDENCE PATTERNS - Direct bot/fake accusations
        # =================================================================

        high_confidence = [
            # Direct bot accusations
            (
                r"(?:you(?:'re| are)|this is)\s+(?:a\s+)?"
                r"(?:bot|robot|automated|AI|artificial)",
                "Direct bot accusation",
                1.0,
            ),
            (
                r"(?:you(?:'re| are)|this is)\s+(?:just\s+)?"
                r"(?:a\s+)?(?:scam|fake|fraud)",
                "Fake/scam accusation",
                1.0,
            ),
            (
                r"i\s+know\s+(?:you(?:'re| are)|this is)\s+"
                r"(?:a\s+)?(?:bot|fake|scam|automated)",
                "Explicit unmasking",
                1.0,
            ),
            # Conversation termination
            (
                r"(?:i(?:'m| am)|we(?:'re| are))\s+(?:done|finished)\s+"
                r"(?:with\s+)?(?:you|this|talking)",
                "Conversation termination",
                0.9,
            ),
            (
                r"stop\s+(?:messaging|contacting|emailing|texting|bothering)\s+me",
                "Stop contact demand",
                0.9,
            ),
            (
                r"(?:don(?:'t|ot)|do not)\s+(?:contact|message|email|text)\s+me\s+"
                r"(?:again|anymore)",
                "No further contact demand",
                0.9,
            ),
        ]

        for pattern_str, description, weight in high_confidence:
            patterns.append(
                UnmaskingPattern(
                    pattern=re.compile(pattern_str, re.IGNORECASE),
                    description=description,
                    weight=weight,
                )
            )

        # =================================================================
        # MEDIUM CONFIDENCE PATTERNS - Frustration/suspicion
        # =================================================================

        medium_confidence = [
            # Time wasting accusations
            (
                r"(?:you(?:'re| are)|this is)\s+(?:just\s+)?"
                r"wasting\s+(?:my\s+)?time",
                "Time wasting accusation",
                0.7,
            ),
            (
                r"stop\s+(?:wasting|playing|messing)\s+"
                r"(?:my\s+)?(?:time|around|with me)",
                "Stop wasting time demand",
                0.7,
            ),
            # Suspicion phrases
            (
                r"i\s+(?:think|believe|suspect)\s+(?:you(?:'re| are)|this is)\s+"
                r"(?:a\s+)?(?:scam|fake|bot)",
                "Suspicion expressed",
                0.6,
            ),
            (
                r"(?:something|this)\s+(?:is(?:n't| not)?|seems?)\s+"
                r"(?:right|real|legitimate)",
                "Legitimacy questioning",
                0.5,
            ),
            # Reporting threats
            (
                r"(?:i(?:'ll| will)|going to)\s+(?:report|block|flag)\s+(?:you|this)",
                "Report/block threat",
                0.7,
            ),
            (
                r"(?:reported|blocked|flagged)\s+(?:you|this|your)",
                "Already reported",
                0.8,
            ),
        ]

        for pattern_str, description, weight in medium_confidence:
            patterns.append(
                UnmaskingPattern(
                    pattern=re.compile(pattern_str, re.IGNORECASE),
                    description=description,
                    weight=weight,
                )
            )

        # =================================================================
        # LOWER CONFIDENCE PATTERNS - May indicate end but not certain
        # =================================================================

        lower_confidence = [
            # Goodbye phrases (alone not conclusive, but supporting)
            (
                r"\b(?:goodbye|bye|farewell)\b.*(?:scammer|bot|fake)?",
                "Goodbye with possible accusation",
                0.4,
            ),
            # Generic termination
            (
                r"(?:this|our)\s+(?:conversation|discussion|chat)\s+is\s+(?:over|done|finished)",
                "Conversation over statement",
                0.5,
            ),
            # Profanity with termination (common when frustrated)
            (
                r"(?:f\*+|f[-*]ck|screw)\s+(?:off|you|this)",
                "Profane dismissal",
                0.6,
            ),
        ]

        for pattern_str, description, weight in lower_confidence:
            patterns.append(
                UnmaskingPattern(
                    pattern=re.compile(pattern_str, re.IGNORECASE),
                    description=description,
                    weight=weight,
                )
            )

        return patterns

    def detect(self, message: str) -> UnmaskingResult:
        """Analyze a scammer message for unmasking indicators.

        Args:
            message: The scammer's message text to analyze.

        Returns:
            UnmaskingResult with detection status and matched phrases.
        """
        if not message or not message.strip():
            return UnmaskingResult(is_unmasked=False)

        matched_phrases: list[str] = []
        total_weight = 0.0

        for pattern in self._patterns:
            match = pattern.pattern.search(message)
            if match:
                matched_text = match.group(0)
                matched_phrases.append(matched_text.lower().strip())
                total_weight += pattern.weight
                logger.debug(
                    "Unmasking pattern matched: %s -> '%s'",
                    pattern.description,
                    matched_text,
                )

        # Calculate confidence as ratio of matched weight
        # More matches = higher confidence, but single strong match is enough
        if matched_phrases:
            confidence = min(1.0, total_weight / 2.0)  # Divide by 2 to normalize
        else:
            confidence = 0.0

        is_unmasked = confidence >= self.CONFIDENCE_THRESHOLD

        if is_unmasked:
            logger.info(
                "Bot unmasking detected (confidence: %.2f): %s",
                confidence,
                matched_phrases,
            )

        return UnmaskingResult(
            is_unmasked=is_unmasked,
            matched_phrases=matched_phrases,
            confidence=confidence,
        )


# Module-level convenience function
def detect_unmasking(message: str) -> UnmaskingResult:
    """Convenience function for one-off unmasking detection.

    Args:
        message: The scammer's message to analyze.

    Returns:
        UnmaskingResult with detection status and matched phrases.
    """
    detector = UnmaskingDetector()
    return detector.detect(message)
