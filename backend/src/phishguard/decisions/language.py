"""Language gate: decide whether text may be sent to Basal (Polish/English only)."""

from fast_langdetect import detect

BASAL_LANGUAGES = {"pl", "en"}
LANGUAGE_MIN_SCORE = 0.5
# Shorter lines (code, labels, URLs, "Yes, 1") are too ambiguous to judge.
LANGUAGE_MIN_LETTERS = 20


def detect_pl_en(text: str) -> str | None:
    """Return ``"pl"`` or ``"en"`` for the text's top language, else ``None``."""
    top = detect(" ".join(text.split()), model="lite")[0]
    return top["lang"] if top["lang"] in BASAL_LANGUAGES else None


def is_basal_language(text: str) -> bool:
    """Return False when any line is confidently in a language Basal does not support.

    Checked per line because emails mix languages (e.g. a Polish body with an
    English signature). Short or ambiguous lines are let through.
    """
    for line in text.splitlines():
        if sum(ch.isalpha() for ch in line) < LANGUAGE_MIN_LETTERS:
            continue
        top = detect(line, model="lite")[0]
        if top["lang"] not in BASAL_LANGUAGES and top["score"] >= LANGUAGE_MIN_SCORE:
            return False
    return True
