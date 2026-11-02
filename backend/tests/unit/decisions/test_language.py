"""Tests for the Basal language gate."""

import pytest

from phishguard.decisions.language import is_basal_language

POLISH_419 = (
    "Szanowny Panie, nazywam się Adebayo Johnson i jestem adwokatem zmarłego klienta.\n"
    "Zmarły pozostawił fundusz w wysokości 12,5 miliona dolarów w banku w Lagos.\n"
    "Proszę o pilną odpowiedź, aby móc przekazać Panu szczegóły tej transakcji."
)
ENGLISH_SUPPORT = (
    "Dear customer, we detected unusual activity on your computer and need to fix it.\n"
    "Please call our technical support team immediately so we can remove the virus.\n"
    "Your account will be suspended within twenty four hours if you do not respond."
)
POLISH_WITH_ENGLISH_SIGNATURE = (
    "Szanowny Panie, nazywam się Adebayo Johnson i jestem adwokatem zmarłego klienta.\n"
    "Zmarły pozostawił fundusz w wysokości 12,5 miliona dolarów w banku w Lagos.\n"
    "Proszę o pilną odpowiedź, aby móc przekazać Panu szczegóły tej transakcji.\n"
    "Best regards, Barrister Adebayo Johnson\n"
    "https://secure-claims-portal.example.com/verify/account?id=48291"
)
GERMAN_INVOICE = (
    "Sehr geehrte Damen und Herren, anbei finden Sie die Rechnung für Ihre "
    "Bestellung.\n"
    "Bitte überweisen Sie den offenen Betrag innerhalb von vierzehn Tagen auf "
    "unser Konto.\n"
    "Bei Rückfragen stehen wir Ihnen jederzeit gerne zur Verfügung."
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (POLISH_419, True),
        (ENGLISH_SUPPORT, True),
        (POLISH_WITH_ENGLISH_SIGNATURE, True),
        (GERMAN_INVOICE, False),
        ("OK\n123", True),
        ("", True),
    ],
    ids=[
        "polish",
        "english",
        "polish_english_signature",
        "german",
        "short_lines",
        "empty",
    ],
)
def test_is_basal_language(text: str, expected: bool) -> None:
    assert is_basal_language(text) is expected
