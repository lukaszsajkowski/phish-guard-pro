"""Urgency tactics analyzer for scammer messages.

Detects pressure keywords and urgency tactics used by scammers
to manipulate victims into quick action.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class UrgencyResult:
    """Result of urgency tactics analysis.

    Attributes:
        score: Urgency score (0-10 scale).
        detected_keywords: List of detected urgency keywords/phrases.
        explanation: Human-readable explanation of the score.
    """

    score: float
    detected_keywords: tuple[str, ...]
    explanation: str


class UrgencyAnalyzer:
    """Analyzer for detecting urgency tactics in scammer messages.

    Scammers frequently use urgency and pressure tactics to force
    victims into quick decisions without proper consideration.
    """

    # Urgency keyword patterns (case-insensitive, 0-10 scale)
    URGENCY_PATTERNS: list[tuple[str, float]] = [
        # High urgency (2.5 points each)
        (r"\bimmediately\b", 2.5),
        (r"\burgent\b", 2.5),
        (r"\basap\b", 2.5),
        (r"\bright now\b", 2.5),
        (r"\bact now\b", 2.5),
        (r"\bdon'?t delay\b", 2.5),
        (r"\btime is running out\b", 2.5),
        (r"\bexpires? today\b", 2.5),
        (r"\blast chance\b", 2.5),
        (r"\bfinal notice\b", 2.5),
        (r"\bfinal warning\b", 2.5),
        # Medium urgency (2.0 points each)
        (r"\bdeadline\b", 2.0),
        (r"\blimited time\b", 2.0),
        (r"\btoday only\b", 2.0),
        (r"\bwithin \d+ hours?\b", 2.0),
        (r"\bwithin \d+ days?\b", 1.5),
        (r"\bhurry\b", 2.0),
        (r"\bquickly\b", 1.5),
        (r"\btime.?sensitive\b", 2.0),
        (r"\brespond immediately\b", 2.5),
        (r"\breply urgently\b", 2.5),
        # Moderate urgency (1.5 points each)
        (r"\bas soon as possible\b", 1.5),
        (r"\bpromptly\b", 1.5),
        (r"\bwithout delay\b", 1.5),
        (r"\bdon'?t wait\b", 1.5),
        (r"\bsoon\b", 1.0),
        # Threat-based urgency (2.0 points each)
        (r"\bor else\b", 2.0),
        (r"\botherwise\b", 1.5),
        (r"\bconsequences\b", 1.5),
        (r"\blose this opportunity\b", 2.0),
        (r"\bmiss out\b", 1.5),
        (r"\bwon'?t wait\b", 2.0),
        (r"\bcan'?t wait\b", 1.5),
        (r"\baccount.{0,10}(suspend|block|close)\b", 2.0),
        (r"\b(suspend|block|close).{0,10}account\b", 2.0),
    ]

    def __init__(self) -> None:
        """Initialize the urgency analyzer with compiled patterns."""
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), weight)
            for pattern, weight in self.URGENCY_PATTERNS
        ]

    def analyze(self, messages: list[str]) -> UrgencyResult:
        """Analyze messages for urgency tactics.

        Args:
            messages: List of scammer message texts to analyze.

        Returns:
            UrgencyResult with score, detected keywords, and explanation.
        """
        if not messages:
            return UrgencyResult(
                score=0.0,
                detected_keywords=(),
                explanation="No messages to analyze.",
            )

        # Combine all messages for analysis
        combined_text = " ".join(messages)

        detected = []
        total_weight = 0.0

        for pattern, weight in self._compiled_patterns:
            matches = pattern.findall(combined_text)
            if matches:
                # Only count each pattern once per analysis
                detected.append(matches[0].lower().strip())
                total_weight += weight

        # Cap at 10 (0-10 scale)
        raw_score = min(total_weight, 10.0)

        # Generate explanation
        if raw_score == 0:
            explanation = "No urgency tactics detected."
        elif raw_score < 3:
            explanation = f"Minimal urgency: {len(detected)} indicator(s) found."
        elif raw_score < 5:
            explanation = f"Low urgency: {len(detected)} pressure tactic(s) detected."
        elif raw_score < 7:
            explanation = f"Moderate urgency: {len(detected)} tactics detected."
        else:
            count = len(detected)
            explanation = f"High urgency: {count} strong pressure indicators."

        return UrgencyResult(
            score=round(raw_score, 2),
            detected_keywords=tuple(sorted(set(detected))),
            explanation=explanation,
        )

    def analyze_single(self, message: str) -> UrgencyResult:
        """Analyze a single message for urgency tactics.

        Args:
            message: Single scammer message text.

        Returns:
            UrgencyResult with score, detected keywords, and explanation.
        """
        return self.analyze([message])
