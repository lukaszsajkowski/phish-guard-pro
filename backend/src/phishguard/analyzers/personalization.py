"""Personalization analyzer for scammer messages.

Detects when scammers use victim's name or reference
specific context to appear more legitimate.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PersonalizationResult:
    """Result of personalization analysis.

    Attributes:
        score: Personalization score (0-10 scale).
        name_usage_count: Number of times victim's name was used.
        context_references: Detected context-specific references.
        explanation: Human-readable explanation of the score.
    """

    score: float
    name_usage_count: int
    context_references: tuple[str, ...]
    explanation: str


class PersonalizationAnalyzer:
    """Analyzer for detecting personalization in scammer messages.

    Scammers who personalize their messages (using victim's name,
    referencing specific details) are often more sophisticated.
    """

    # Context reference patterns (generic references scammers use, 0-10 scale)
    CONTEXT_PATTERNS: list[tuple[str, float]] = [
        # Direct references to prior interaction (1.5 points each)
        (r"\bas (?:we|you) discussed\b", 1.5),
        (r"\bas (?:we|you) mentioned\b", 1.5),
        (r"\byour (?:recent |last )?(?:email|message|reply)\b", 1.5),
        (r"\bfollowing up on\b", 1.5),
        (r"\bin (?:our|your) (?:previous|last) (?:conversation|exchange)\b", 1.5),
        # References to victim's situation (1.0 points each)
        (r"\byour (?:account|profile|application)\b", 1.0),
        (r"\byour (?:company|business|organization)\b", 1.2),
        (r"\byour (?:request|order|transaction)\b", 1.0),
        (r"\byou (?:asked|requested|inquired)\b", 1.2),
        # References to shared details (1.0-1.5 points each)
        (r"\bthe amount (?:of|you)\b", 1.0),
        (r"\bthe (?:money|funds|payment) you\b", 1.2),
        (r"\byour (?:bank|financial)\b", 1.2),
        (r"\bthe documents? you (?:sent|provided)\b", 1.5),
        # Temporal context (1.0 points each)
        (r"\blast (?:week|month|time)\b", 1.0),
        (r"\byesterday\b", 1.0),
        (r"\bour (?:meeting|call)\b", 1.2),
    ]

    def __init__(self) -> None:
        """Initialize the personalization analyzer with compiled patterns."""
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), weight)
            for pattern, weight in self.CONTEXT_PATTERNS
        ]

    def analyze(
        self,
        messages: list[str],
        victim_name: str | None = None,
        victim_first_name: str | None = None,
    ) -> PersonalizationResult:
        """Analyze messages for personalization.

        Args:
            messages: List of scammer message texts to analyze.
            victim_name: Full name of the victim persona (optional).
            victim_first_name: First name of the victim persona (optional).

        Returns:
            PersonalizationResult with score and detected indicators.
        """
        if not messages:
            return PersonalizationResult(
                score=0.0,
                name_usage_count=0,
                context_references=(),
                explanation="No messages to analyze.",
            )

        combined_text = " ".join(messages)
        total_score = 0.0
        name_count = 0
        context_refs = []

        # Check for name usage
        if victim_name:
            name_pattern = re.compile(re.escape(victim_name), re.IGNORECASE)
            name_matches = name_pattern.findall(combined_text)
            name_count += len(name_matches)

        if victim_first_name and victim_first_name != victim_name:
            first_name_pattern = re.compile(
                r"\b" + re.escape(victim_first_name) + r"\b",
                re.IGNORECASE,
            )
            first_name_matches = first_name_pattern.findall(combined_text)
            name_count += len(first_name_matches)

        # Score for name usage (up to 5 points)
        # First usage = 3 points, subsequent = 0.5 each, max 5 total
        if name_count > 0:
            name_score = min(3.0 + (name_count - 1) * 0.5, 5.0)
            total_score += name_score

        # Check for context references
        for pattern, weight in self._compiled_patterns:
            matches = pattern.findall(combined_text)
            if matches:
                context_refs.append(matches[0].lower().strip())
                total_score += weight

        # Cap total score at 10
        final_score = min(total_score, 10.0)

        # Generate explanation
        if final_score == 0:
            explanation = "No personalization detected."
        else:
            parts = []
            if name_count > 0:
                parts.append(f"name used {name_count}x")
            if context_refs:
                parts.append(f"{len(context_refs)} context ref(s)")
            detail = ", ".join(parts)

            if final_score < 3:
                explanation = f"Minimal personalization: {detail}."
            elif final_score < 5:
                explanation = f"Some personalization: {detail}."
            elif final_score < 7:
                explanation = f"Moderate personalization: {detail}."
            else:
                explanation = f"High personalization: {detail}."

        return PersonalizationResult(
            score=round(final_score, 2),
            name_usage_count=name_count,
            context_references=tuple(sorted(set(context_refs))),
            explanation=explanation,
        )

    def analyze_single(
        self,
        message: str,
        victim_name: str | None = None,
        victim_first_name: str | None = None,
    ) -> PersonalizationResult:
        """Analyze a single message for personalization.

        Args:
            message: Single scammer message text.
            victim_name: Full name of the victim persona (optional).
            victim_first_name: First name of the victim persona (optional).

        Returns:
            PersonalizationResult with score and detected indicators.
        """
        return self.analyze([message], victim_name, victim_first_name)
