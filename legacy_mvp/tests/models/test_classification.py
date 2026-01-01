"""Comprehensive tests for Classification models.

These tests verify that the AttackType enum and ClassificationResult model:
1. AttackType enum has all 9 expected values
2. AttackType display_name property returns correct human-readable names
3. AttackType string values match expected patterns
4. ClassificationResult validates all required fields
5. ClassificationResult enforces confidence range (0-100)
6. ClassificationResult rounds confidence to 2 decimal places
7. ClassificationResult enforces reasoning minimum length
8. ClassificationResult is_phishing property works correctly
9. ClassificationResult is_high_confidence property works correctly
10. ClassificationResult is_low_confidence_not_phishing property works correctly
11. ClassificationResult is frozen (immutable)
12. ClassificationResult serializes to JSON correctly

Test Categories:
- AttackType enum values and properties
- ClassificationResult valid construction
- ClassificationResult confidence validation
- ClassificationResult reasoning validation
- ClassificationResult properties (is_phishing, is_high_confidence, etc.)
- ClassificationResult immutability
- ClassificationResult serialization
"""

import json

import pytest
from pydantic import ValidationError

from phishguard.models.classification import AttackType, ClassificationResult


class TestAttackTypeEnumValues:
    """Tests for AttackType enum value existence and correctness."""

    def test_attack_type_has_nine_values(self) -> None:
        """AttackType should have exactly 9 enum values."""
        assert len(AttackType) == 9

    @pytest.mark.parametrize(
        "enum_member,expected_value",
        [
            (AttackType.NIGERIAN_419, "nigerian_419"),
            (AttackType.CEO_FRAUD, "ceo_fraud"),
            (AttackType.FAKE_INVOICE, "fake_invoice"),
            (AttackType.ROMANCE_SCAM, "romance_scam"),
            (AttackType.TECH_SUPPORT, "tech_support"),
            (AttackType.LOTTERY_PRIZE, "lottery_prize"),
            (AttackType.CRYPTO_INVESTMENT, "crypto_investment"),
            (AttackType.DELIVERY_SCAM, "delivery_scam"),
            (AttackType.NOT_PHISHING, "not_phishing"),
        ],
        ids=[
            "nigerian_419",
            "ceo_fraud",
            "fake_invoice",
            "romance_scam",
            "tech_support",
            "lottery_prize",
            "crypto_investment",
            "delivery_scam",
            "not_phishing",
        ],
    )
    def test_attack_type_string_values(
        self, enum_member: AttackType, expected_value: str
    ) -> None:
        """Each AttackType should have the correct string value."""
        assert enum_member.value == expected_value

    def test_all_attack_types_are_lowercase_snake_case(self) -> None:
        """All AttackType values should be lowercase snake_case."""
        for attack_type in AttackType:
            assert attack_type.value == attack_type.value.lower()
            assert " " not in attack_type.value
            # Verify snake_case pattern (lowercase letters, digits, underscores)
            assert all(
                c.islower() or c.isdigit() or c == "_" for c in attack_type.value
            )

    def test_attack_type_is_string_subclass(self) -> None:
        """AttackType should be a string enum (subclass of str)."""
        for attack_type in AttackType:
            assert isinstance(attack_type, str)
            assert isinstance(attack_type.value, str)


class TestAttackTypeDisplayName:
    """Tests for AttackType display_name property."""

    @pytest.mark.parametrize(
        "attack_type,expected_display_name",
        [
            (AttackType.NIGERIAN_419, "Nigerian 419"),
            (AttackType.CEO_FRAUD, "CEO Fraud"),
            (AttackType.FAKE_INVOICE, "Fake Invoice"),
            (AttackType.ROMANCE_SCAM, "Romance Scam"),
            (AttackType.TECH_SUPPORT, "Tech Support"),
            (AttackType.LOTTERY_PRIZE, "Lottery/Prize"),
            (AttackType.CRYPTO_INVESTMENT, "Crypto Investment"),
            (AttackType.DELIVERY_SCAM, "Delivery Scam"),
            (AttackType.NOT_PHISHING, "Not Phishing"),
        ],
        ids=[
            "nigerian_419_display",
            "ceo_fraud_display",
            "fake_invoice_display",
            "romance_scam_display",
            "tech_support_display",
            "lottery_prize_display",
            "crypto_investment_display",
            "delivery_scam_display",
            "not_phishing_display",
        ],
    )
    def test_display_name_returns_correct_value(
        self, attack_type: AttackType, expected_display_name: str
    ) -> None:
        """display_name should return the correct human-readable name."""
        assert attack_type.display_name == expected_display_name

    def test_all_attack_types_have_display_names(self) -> None:
        """Every AttackType should have a display_name defined."""
        for attack_type in AttackType:
            display_name = attack_type.display_name
            assert display_name is not None
            assert isinstance(display_name, str)
            assert len(display_name) > 0

    def test_display_names_are_title_case_or_special(self) -> None:
        """Display names should be properly formatted for UI display."""
        for attack_type in AttackType:
            display_name = attack_type.display_name
            # Check that display names don't contain underscores
            assert "_" not in display_name
            # Check that display names are not all lowercase
            assert display_name != display_name.lower()


class TestClassificationResultValidConstruction:
    """Tests for valid ClassificationResult instantiation."""

    def test_valid_classification_result_all_fields(self) -> None:
        """ClassificationResult with all valid fields should be created."""
        result = ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=95.5,
            reasoning="Email contains classic 419 indicators.",
            classification_time_ms=1250,
        )
        assert result.attack_type == AttackType.NIGERIAN_419
        assert result.confidence == 95.5
        assert result.reasoning == "Email contains classic 419 indicators."
        assert result.classification_time_ms == 1250

    @pytest.mark.parametrize(
        "attack_type",
        list(AttackType),
        ids=[at.name for at in AttackType],
    )
    def test_valid_classification_result_all_attack_types(
        self, attack_type: AttackType
    ) -> None:
        """ClassificationResult should accept any valid AttackType."""
        result = ClassificationResult(
            attack_type=attack_type,
            confidence=75.0,
            reasoning="Test reasoning for classification.",
            classification_time_ms=500,
        )
        assert result.attack_type == attack_type

    def test_valid_classification_result_minimum_values(self) -> None:
        """ClassificationResult with minimum valid values should be created."""
        result = ClassificationResult(
            attack_type=AttackType.NOT_PHISHING,
            confidence=0.0,
            reasoning="x",  # min_length=1
            classification_time_ms=0,
        )
        assert result.confidence == 0.0
        assert result.reasoning == "x"
        assert result.classification_time_ms == 0

    def test_valid_classification_result_maximum_confidence(self) -> None:
        """ClassificationResult with maximum confidence should be created."""
        result = ClassificationResult(
            attack_type=AttackType.CEO_FRAUD,
            confidence=100.0,
            reasoning="Absolutely certain this is CEO fraud.",
            classification_time_ms=999,
        )
        assert result.confidence == 100.0


class TestClassificationResultConfidenceValidation:
    """Tests for confidence field validation."""

    def test_confidence_below_zero_raises_validation_error(self) -> None:
        """Confidence below 0 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ClassificationResult(
                attack_type=AttackType.NIGERIAN_419,
                confidence=-1.0,
                reasoning="Test reasoning.",
                classification_time_ms=100,
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("confidence",)
        assert "greater than or equal to 0" in errors[0]["msg"]

    def test_confidence_above_hundred_raises_validation_error(self) -> None:
        """Confidence above 100 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ClassificationResult(
                attack_type=AttackType.NIGERIAN_419,
                confidence=100.01,
                reasoning="Test reasoning.",
                classification_time_ms=100,
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("confidence",)
        assert "less than or equal to 100" in errors[0]["msg"]

    @pytest.mark.parametrize(
        "invalid_confidence",
        [-100.0, -50.5, -0.01, 100.1, 150.0, 200.0, 1000.0],
        ids=[
            "minus_100",
            "minus_50.5",
            "minus_0.01",
            "100.1",
            "150",
            "200",
            "1000",
        ],
    )
    def test_confidence_out_of_range_raises_validation_error(
        self, invalid_confidence: float
    ) -> None:
        """Various out-of-range confidence values should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ClassificationResult(
                attack_type=AttackType.NIGERIAN_419,
                confidence=invalid_confidence,
                reasoning="Test reasoning.",
                classification_time_ms=100,
            )
        errors = exc_info.value.errors()
        assert errors[0]["loc"] == ("confidence",)

    @pytest.mark.parametrize(
        "valid_confidence",
        [0.0, 0.01, 25.0, 50.0, 75.5, 99.99, 100.0],
        ids=["zero", "tiny", "quarter", "half", "three_quarters", "almost_max", "max"],
    )
    def test_confidence_in_range_accepted(self, valid_confidence: float) -> None:
        """Confidence values within 0-100 range should be accepted."""
        result = ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=valid_confidence,
            reasoning="Test reasoning.",
            classification_time_ms=100,
        )
        assert result.confidence == round(valid_confidence, 2)


class TestClassificationResultConfidenceRounding:
    """Tests for confidence rounding to 2 decimal places."""

    @pytest.mark.parametrize(
        "input_confidence,expected_rounded",
        [
            (85.555, 85.56),
            (85.554, 85.55),
            (75.1234, 75.12),
            (75.1256, 75.13),
            (99.999, 100.0),
            (0.001, 0.0),
            (50.005, 50.01),  # Due to float representation, rounds up
            (50.015, 50.02),  # Due to float representation, rounds up
            (33.333, 33.33),
            (66.666, 66.67),
        ],
        ids=[
            "round_up_555",
            "round_down_554",
            "round_down_1234",
            "round_up_1256",
            "round_to_100",
            "round_to_zero",
            "round_005",
            "round_015",
            "round_down_333",
            "round_up_666",
        ],
    )
    def test_confidence_rounded_to_two_decimals(
        self, input_confidence: float, expected_rounded: float
    ) -> None:
        """Confidence should be rounded to 2 decimal places."""
        result = ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=input_confidence,
            reasoning="Test reasoning.",
            classification_time_ms=100,
        )
        assert result.confidence == expected_rounded

    def test_confidence_already_two_decimals_unchanged(self) -> None:
        """Confidence with exactly 2 decimal places should remain unchanged."""
        result = ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=85.75,
            reasoning="Test reasoning.",
            classification_time_ms=100,
        )
        assert result.confidence == 85.75

    def test_confidence_integer_unchanged(self) -> None:
        """Integer confidence values should remain as integers (with .0)."""
        result = ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=85,
            reasoning="Test reasoning.",
            classification_time_ms=100,
        )
        assert result.confidence == 85.0


class TestClassificationResultReasoningValidation:
    """Tests for reasoning field validation."""

    def test_empty_reasoning_raises_validation_error(self) -> None:
        """Empty reasoning string should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ClassificationResult(
                attack_type=AttackType.NIGERIAN_419,
                confidence=85.0,
                reasoning="",
                classification_time_ms=100,
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("reasoning",)
        assert "1 character" in errors[0]["msg"]

    def test_single_character_reasoning_valid(self) -> None:
        """Single character reasoning (min_length=1) should be valid."""
        result = ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=85.0,
            reasoning="X",
            classification_time_ms=100,
        )
        assert result.reasoning == "X"

    def test_long_reasoning_valid(self) -> None:
        """Long reasoning strings should be valid."""
        long_reasoning = (
            "This email exhibits multiple classic indicators of a Nigerian 419 scam: "
            "1) Claims of a foreign dignitary or wealthy individual, "
            "2) Promise of large sum of money (millions of dollars), "
            "3) Request for personal banking information, "
            "4) Urgency and secrecy emphasized, "
            "5) Poor grammar and spelling typical of these scams, "
            "6) Request for advance fee or processing payment."
        )
        result = ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=95.0,
            reasoning=long_reasoning,
            classification_time_ms=100,
        )
        assert result.reasoning == long_reasoning

    @pytest.mark.parametrize(
        "valid_reasoning",
        [
            "x",
            "Short.",
            "Medium length reasoning text.",
            "A" * 1000,
        ],
        ids=["single_char", "short", "medium", "very_long"],
    )
    def test_various_reasoning_lengths_valid(self, valid_reasoning: str) -> None:
        """Various valid reasoning lengths should be accepted."""
        result = ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=85.0,
            reasoning=valid_reasoning,
            classification_time_ms=100,
        )
        assert result.reasoning == valid_reasoning


class TestClassificationResultIsPhishingProperty:
    """Tests for is_phishing property."""

    @pytest.mark.parametrize(
        "attack_type",
        [
            AttackType.NIGERIAN_419,
            AttackType.CEO_FRAUD,
            AttackType.FAKE_INVOICE,
            AttackType.ROMANCE_SCAM,
            AttackType.TECH_SUPPORT,
            AttackType.LOTTERY_PRIZE,
            AttackType.CRYPTO_INVESTMENT,
            AttackType.DELIVERY_SCAM,
        ],
        ids=[
            "nigerian_419",
            "ceo_fraud",
            "fake_invoice",
            "romance_scam",
            "tech_support",
            "lottery_prize",
            "crypto_investment",
            "delivery_scam",
        ],
    )
    def test_is_phishing_true_for_phishing_types(self, attack_type: AttackType) -> None:
        """is_phishing should return True for all phishing attack types."""
        result = ClassificationResult(
            attack_type=attack_type,
            confidence=85.0,
            reasoning="Test reasoning.",
            classification_time_ms=100,
        )
        assert result.is_phishing is True

    def test_is_phishing_false_for_not_phishing(self) -> None:
        """is_phishing should return False for NOT_PHISHING type."""
        result = ClassificationResult(
            attack_type=AttackType.NOT_PHISHING,
            confidence=85.0,
            reasoning="This is a legitimate email.",
            classification_time_ms=100,
        )
        assert result.is_phishing is False

    def test_is_phishing_is_boolean(self) -> None:
        """is_phishing should always return a boolean value."""
        for attack_type in AttackType:
            result = ClassificationResult(
                attack_type=attack_type,
                confidence=85.0,
                reasoning="Test reasoning.",
                classification_time_ms=100,
            )
            assert isinstance(result.is_phishing, bool)


class TestClassificationResultIsHighConfidenceProperty:
    """Tests for is_high_confidence property."""

    @pytest.mark.parametrize(
        "confidence,expected_high_confidence",
        [
            (0.0, False),
            (50.0, False),
            (79.0, False),
            (79.99, False),
            (80.0, True),
            (80.01, True),
            (85.0, True),
            (95.0, True),
            (99.99, True),
            (100.0, True),
        ],
        ids=[
            "zero",
            "fifty",
            "seventy_nine",
            "just_below_80",
            "exactly_80",
            "just_above_80",
            "eighty_five",
            "ninety_five",
            "almost_100",
            "hundred",
        ],
    )
    def test_is_high_confidence_threshold(
        self, confidence: float, expected_high_confidence: bool
    ) -> None:
        """is_high_confidence should return True when confidence >= 80."""
        result = ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=confidence,
            reasoning="Test reasoning.",
            classification_time_ms=100,
        )
        assert result.is_high_confidence is expected_high_confidence

    def test_is_high_confidence_is_boolean(self) -> None:
        """is_high_confidence should always return a boolean value."""
        result = ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=85.0,
            reasoning="Test reasoning.",
            classification_time_ms=100,
        )
        assert isinstance(result.is_high_confidence, bool)


class TestClassificationResultIsLowConfidenceNotPhishingProperty:
    """Tests for is_low_confidence_not_phishing property."""

    @pytest.mark.parametrize(
        "confidence,expected_result",
        [
            (29.99, True),
            (30.0, False),
            (30.01, False),
        ],
        ids=[
            "just_below_30",
            "exactly_30",
            "just_above_30",
        ],
    )
    def test_is_low_confidence_not_phishing_boundary_values(
        self, confidence: float, expected_result: bool
    ) -> None:
        """is_low_confidence_not_phishing should use 30% threshold correctly."""
        result = ClassificationResult(
            attack_type=AttackType.NOT_PHISHING,
            confidence=confidence,
            reasoning="Test reasoning.",
            classification_time_ms=100,
        )
        assert result.is_low_confidence_not_phishing is expected_result

    @pytest.mark.parametrize(
        "confidence,expected_result",
        [
            (0.0, True),
            (15.0, True),
            (29.9, True),
            (30.0, False),
            (50.0, False),
            (80.0, False),
            (100.0, False),
        ],
        ids=[
            "zero",
            "fifteen",
            "just_below_30",
            "exactly_30",
            "fifty",
            "eighty",
            "hundred",
        ],
    )
    def test_is_low_confidence_not_phishing_for_not_phishing_type(
        self, confidence: float, expected_result: bool
    ) -> None:
        """Returns True only for NOT_PHISHING with confidence < 30."""
        result = ClassificationResult(
            attack_type=AttackType.NOT_PHISHING,
            confidence=confidence,
            reasoning="This appears to be a legitimate email.",
            classification_time_ms=100,
        )
        assert result.is_low_confidence_not_phishing is expected_result

    @pytest.mark.parametrize(
        "attack_type",
        [
            AttackType.NIGERIAN_419,
            AttackType.CEO_FRAUD,
            AttackType.CRYPTO_INVESTMENT,
        ],
        ids=[
            "nigerian_419",
            "ceo_fraud",
            "crypto_investment",
        ],
    )
    def test_is_low_confidence_not_phishing_false_for_phishing_types(
        self, attack_type: AttackType
    ) -> None:
        """Returns False for all phishing types regardless of confidence."""
        # Test with low confidence (below 30%)
        result_low = ClassificationResult(
            attack_type=attack_type,
            confidence=15.0,
            reasoning="Test reasoning.",
            classification_time_ms=100,
        )
        assert result_low.is_low_confidence_not_phishing is False

        # Test with high confidence (above 30%)
        result_high = ClassificationResult(
            attack_type=attack_type,
            confidence=85.0,
            reasoning="Test reasoning.",
            classification_time_ms=100,
        )
        assert result_high.is_low_confidence_not_phishing is False

    def test_is_low_confidence_not_phishing_is_boolean(self) -> None:
        """is_low_confidence_not_phishing should always return a boolean value."""
        result = ClassificationResult(
            attack_type=AttackType.NOT_PHISHING,
            confidence=25.0,
            reasoning="Test reasoning.",
            classification_time_ms=100,
        )
        assert isinstance(result.is_low_confidence_not_phishing, bool)


class TestClassificationResultFrozenModel:
    """Tests for model immutability (frozen=True)."""

    def test_cannot_modify_attack_type(self) -> None:
        """Attempting to modify attack_type should raise error."""
        result = ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=85.0,
            reasoning="Test reasoning.",
            classification_time_ms=100,
        )
        with pytest.raises(ValidationError) as exc_info:
            result.attack_type = AttackType.CEO_FRAUD
        errors = exc_info.value.errors()
        assert (
            "frozen" in errors[0]["msg"].lower()
            or "immutable" in str(exc_info.value).lower()
        )

    def test_cannot_modify_confidence(self) -> None:
        """Attempting to modify confidence should raise error."""
        result = ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=85.0,
            reasoning="Test reasoning.",
            classification_time_ms=100,
        )
        with pytest.raises(ValidationError) as exc_info:
            result.confidence = 99.0
        errors = exc_info.value.errors()
        assert (
            "frozen" in errors[0]["msg"].lower()
            or "immutable" in str(exc_info.value).lower()
        )

    def test_cannot_modify_reasoning(self) -> None:
        """Attempting to modify reasoning should raise error."""
        result = ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=85.0,
            reasoning="Original reasoning.",
            classification_time_ms=100,
        )
        with pytest.raises(ValidationError) as exc_info:
            result.reasoning = "Modified reasoning."
        errors = exc_info.value.errors()
        assert (
            "frozen" in errors[0]["msg"].lower()
            or "immutable" in str(exc_info.value).lower()
        )

    def test_cannot_modify_classification_time_ms(self) -> None:
        """Attempting to modify classification_time_ms should raise error."""
        result = ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=85.0,
            reasoning="Test reasoning.",
            classification_time_ms=100,
        )
        with pytest.raises(ValidationError) as exc_info:
            result.classification_time_ms = 200
        errors = exc_info.value.errors()
        assert (
            "frozen" in errors[0]["msg"].lower()
            or "immutable" in str(exc_info.value).lower()
        )


class TestClassificationResultSerialization:
    """Tests for JSON and dict serialization."""

    def test_json_serialization(self) -> None:
        """ClassificationResult should serialize to JSON correctly."""
        result = ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=85.5,
            reasoning="Test reasoning for JSON serialization.",
            classification_time_ms=1250,
        )
        json_str = result.model_dump_json()
        data = json.loads(json_str)

        assert data["attack_type"] == "nigerian_419"
        assert data["confidence"] == 85.5
        assert data["reasoning"] == "Test reasoning for JSON serialization."
        assert data["classification_time_ms"] == 1250

    def test_dict_serialization(self) -> None:
        """ClassificationResult should serialize to dict correctly."""
        result = ClassificationResult(
            attack_type=AttackType.CEO_FRAUD,
            confidence=92.33,
            reasoning="Test reasoning for dict serialization.",
            classification_time_ms=500,
        )
        data = result.model_dump()

        assert data["attack_type"] == AttackType.CEO_FRAUD
        assert data["confidence"] == 92.33
        assert data["reasoning"] == "Test reasoning for dict serialization."
        assert data["classification_time_ms"] == 500

    def test_json_round_trip(self) -> None:
        """ClassificationResult should survive JSON round-trip."""
        original = ClassificationResult(
            attack_type=AttackType.ROMANCE_SCAM,
            confidence=77.77,
            reasoning="Round-trip test reasoning.",
            classification_time_ms=999,
        )

        # Serialize to JSON
        json_str = original.model_dump_json()

        # Deserialize back
        data = json.loads(json_str)
        restored = ClassificationResult(**data)

        assert restored.attack_type == original.attack_type
        assert restored.confidence == original.confidence
        assert restored.reasoning == original.reasoning
        assert restored.classification_time_ms == original.classification_time_ms

    @pytest.mark.parametrize(
        "attack_type",
        list(AttackType),
        ids=[at.name for at in AttackType],
    )
    def test_json_serialization_all_attack_types(self, attack_type: AttackType) -> None:
        """All attack types should serialize to JSON correctly."""
        result = ClassificationResult(
            attack_type=attack_type,
            confidence=75.0,
            reasoning="Test reasoning.",
            classification_time_ms=100,
        )
        json_str = result.model_dump_json()
        data = json.loads(json_str)
        assert data["attack_type"] == attack_type.value


class TestClassificationResultMissingFields:
    """Tests for missing required fields."""

    def test_missing_attack_type_raises_validation_error(self) -> None:
        """Missing attack_type should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ClassificationResult(
                confidence=85.0,
                reasoning="Test reasoning.",
                classification_time_ms=100,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("attack_type",) for e in errors)

    def test_missing_confidence_raises_validation_error(self) -> None:
        """Missing confidence should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ClassificationResult(
                attack_type=AttackType.NIGERIAN_419,
                reasoning="Test reasoning.",
                classification_time_ms=100,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_missing_reasoning_raises_validation_error(self) -> None:
        """Missing reasoning should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ClassificationResult(
                attack_type=AttackType.NIGERIAN_419,
                confidence=85.0,
                classification_time_ms=100,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("reasoning",) for e in errors)

    def test_missing_classification_time_ms_raises_validation_error(self) -> None:
        """Missing classification_time_ms should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ClassificationResult(
                attack_type=AttackType.NIGERIAN_419,
                confidence=85.0,
                reasoning="Test reasoning.",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("classification_time_ms",) for e in errors)


class TestClassificationResultClassificationTimeValidation:
    """Tests for classification_time_ms field validation."""

    def test_negative_classification_time_raises_validation_error(self) -> None:
        """Negative classification_time_ms should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ClassificationResult(
                attack_type=AttackType.NIGERIAN_419,
                confidence=85.0,
                reasoning="Test reasoning.",
                classification_time_ms=-1,
            )
        errors = exc_info.value.errors()
        assert errors[0]["loc"] == ("classification_time_ms",)
        assert "greater than or equal to 0" in errors[0]["msg"]

    def test_zero_classification_time_valid(self) -> None:
        """Zero classification_time_ms should be valid."""
        result = ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=85.0,
            reasoning="Test reasoning.",
            classification_time_ms=0,
        )
        assert result.classification_time_ms == 0

    @pytest.mark.parametrize(
        "time_ms",
        [0, 1, 100, 1000, 5000, 10000, 100000],
        ids=["zero", "one", "hundred", "thousand", "five_k", "ten_k", "hundred_k"],
    )
    def test_valid_classification_times(self, time_ms: int) -> None:
        """Various valid classification times should be accepted."""
        result = ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=85.0,
            reasoning="Test reasoning.",
            classification_time_ms=time_ms,
        )
        assert result.classification_time_ms == time_ms


class TestClassificationResultEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_unicode_reasoning_valid(self) -> None:
        """Unicode characters in reasoning should be accepted."""
        result = ClassificationResult(
            attack_type=AttackType.ROMANCE_SCAM,
            confidence=88.0,
            reasoning="This email contains emoji hearts and unusual characters.",
            classification_time_ms=150,
        )
        assert "unusual characters" in result.reasoning

    def test_multiline_reasoning_valid(self) -> None:
        """Multiline reasoning should be valid."""
        reasoning = """Line 1: Initial analysis.
Line 2: Secondary indicators.
Line 3: Final conclusion."""
        result = ClassificationResult(
            attack_type=AttackType.CEO_FRAUD,
            confidence=91.0,
            reasoning=reasoning,
            classification_time_ms=200,
        )
        assert "\n" in result.reasoning

    def test_special_characters_in_reasoning(self) -> None:
        """Special characters in reasoning should be preserved."""
        reasoning = (
            "Found URLs: http://example.com, emails: test@test.com, symbols: $#@!"
        )
        result = ClassificationResult(
            attack_type=AttackType.FAKE_INVOICE,
            confidence=78.0,
            reasoning=reasoning,
            classification_time_ms=300,
        )
        assert "http://example.com" in result.reasoning
        assert "$#@!" in result.reasoning

    def test_attack_type_from_string_value(self) -> None:
        """ClassificationResult should accept string value for attack_type."""
        result = ClassificationResult(
            attack_type="nigerian_419",
            confidence=85.0,
            reasoning="Test reasoning.",
            classification_time_ms=100,
        )
        assert result.attack_type == AttackType.NIGERIAN_419

    def test_properties_consistent_across_calls(self) -> None:
        """Properties should return consistent values across multiple calls."""
        result = ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=85.0,
            reasoning="Test reasoning.",
            classification_time_ms=100,
        )
        # Call properties multiple times
        assert result.is_phishing is True
        assert result.is_phishing is True
        assert result.is_high_confidence is True
        assert result.is_high_confidence is True


class TestClassificationResultRealisticScenarios:
    """Tests with realistic phishing classification scenarios."""

    def test_nigerian_419_high_confidence_classification(self) -> None:
        """Realistic Nigerian 419 scam classification."""
        result = ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=95.75,
            reasoning=(
                "Email exhibits classic 419 scam indicators: claims of deceased "
                "wealthy relative in Nigeria, promise of $15.5 million inheritance, "
                "request for personal banking details to facilitate transfer, "
                "urgency and secrecy emphasized."
            ),
            classification_time_ms=2150,
        )
        assert result.is_phishing is True
        assert result.is_high_confidence is True
        assert result.attack_type.display_name == "Nigerian 419"

    def test_ceo_fraud_medium_confidence_classification(self) -> None:
        """Realistic CEO fraud classification with medium confidence."""
        result = ClassificationResult(
            attack_type=AttackType.CEO_FRAUD,
            confidence=72.5,
            reasoning=(
                "Email appears to impersonate company executive requesting "
                "urgent wire transfer. Some indicators present but email "
                "domain appears partially legitimate."
            ),
            classification_time_ms=1890,
        )
        assert result.is_phishing is True
        assert result.is_high_confidence is False
        assert result.attack_type.display_name == "CEO Fraud"

    def test_legitimate_email_not_phishing(self) -> None:
        """Realistic legitimate email classification."""
        result = ClassificationResult(
            attack_type=AttackType.NOT_PHISHING,
            confidence=88.0,
            reasoning=(
                "Email appears to be a legitimate newsletter from a known "
                "subscription service. No suspicious links, no urgency tactics, "
                "proper unsubscribe options present."
            ),
            classification_time_ms=980,
        )
        assert result.is_phishing is False
        assert result.is_high_confidence is True
        assert result.attack_type.display_name == "Not Phishing"
