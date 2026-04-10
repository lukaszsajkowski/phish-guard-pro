"""Comprehensive tests for Persona models.

These tests verify that the PersonaType enum and PersonaProfile model:
1. PersonaType enum has all 4 expected values
2. PersonaType display_name property returns correct human-readable names
3. PersonaType string values match expected patterns
4. PersonaProfile validates all required fields
5. PersonaProfile enforces age range (18-95)
6. PersonaProfile enforces name and field length constraints
7. PersonaProfile summary property works correctly
8. PersonaProfile is frozen (immutable)
9. PersonaProfile serializes to JSON correctly
"""

import json

import pytest
from pydantic import ValidationError

from phishguard.models.persona import PersonaProfile, PersonaType


class TestPersonaTypeEnumValues:
    """Tests for PersonaType enum value existence and correctness."""

    def test_persona_type_has_four_values(self) -> None:
        """PersonaType should have exactly 4 enum values."""
        assert len(PersonaType) == 4

    @pytest.mark.parametrize(
        "enum_member,expected_value",
        [
            (PersonaType.NAIVE_RETIREE, "naive_retiree"),
            (PersonaType.STRESSED_MANAGER, "stressed_manager"),
            (PersonaType.GREEDY_INVESTOR, "greedy_investor"),
            (PersonaType.CONFUSED_STUDENT, "confused_student"),
        ],
        ids=[
            "naive_retiree",
            "stressed_manager",
            "greedy_investor",
            "confused_student",
        ],
    )
    def test_persona_type_string_values(
        self, enum_member: PersonaType, expected_value: str
    ) -> None:
        """Each PersonaType should have the correct string value."""
        assert enum_member.value == expected_value

    def test_all_persona_types_are_lowercase_snake_case(self) -> None:
        """All PersonaType values should be lowercase snake_case."""
        for persona_type in PersonaType:
            assert persona_type.value == persona_type.value.lower()
            assert " " not in persona_type.value
            # Verify snake_case pattern (lowercase letters, digits, underscores)
            assert all(
                c.islower() or c.isdigit() or c == "_" for c in persona_type.value
            )

    def test_persona_type_is_string_subclass(self) -> None:
        """PersonaType should be a string enum (subclass of str)."""
        for persona_type in PersonaType:
            assert isinstance(persona_type, str)
            assert isinstance(persona_type.value, str)


class TestPersonaTypeDisplayName:
    """Tests for PersonaType display_name property."""

    @pytest.mark.parametrize(
        "persona_type,expected_display_name",
        [
            (PersonaType.NAIVE_RETIREE, "Naive Retiree"),
            (PersonaType.STRESSED_MANAGER, "Stressed Manager"),
            (PersonaType.GREEDY_INVESTOR, "Greedy Investor"),
            (PersonaType.CONFUSED_STUDENT, "Confused Student"),
        ],
        ids=[
            "naive_retiree_display",
            "stressed_manager_display",
            "greedy_investor_display",
            "confused_student_display",
        ],
    )
    def test_display_name_returns_correct_value(
        self, persona_type: PersonaType, expected_display_name: str
    ) -> None:
        """display_name should return the correct human-readable name."""
        assert persona_type.display_name == expected_display_name

    def test_all_persona_types_have_display_names(self) -> None:
        """Every PersonaType should have a display_name defined."""
        for persona_type in PersonaType:
            display_name = persona_type.display_name
            assert display_name is not None
            assert isinstance(display_name, str)
            assert len(display_name) > 0

    def test_display_names_are_title_case(self) -> None:
        """Display names should be properly formatted for UI display."""
        for persona_type in PersonaType:
            display_name = persona_type.display_name
            # Check that display names don't contain underscores
            assert "_" not in display_name
            # Check that display names are not all lowercase
            assert display_name != display_name.lower()


class TestPersonaProfileValidConstruction:
    """Tests for valid PersonaProfile instantiation."""

    def test_valid_persona_profile_all_fields(self) -> None:
        """PersonaProfile with all valid fields should be created."""
        profile = PersonaProfile(
            persona_type=PersonaType.NAIVE_RETIREE,
            name="Margaret Thompson",
            age=72,
            style_description="Trusting and polite, uses formal language.",
            background="Retired teacher, recently widowed.",
        )
        assert profile.persona_type == PersonaType.NAIVE_RETIREE
        assert profile.name == "Margaret Thompson"
        assert profile.age == 72
        assert profile.style_description == "Trusting and polite, uses formal language."
        assert profile.background == "Retired teacher, recently widowed."

    @pytest.mark.parametrize(
        "persona_type",
        list(PersonaType),
        ids=[pt.name for pt in PersonaType],
    )
    def test_valid_persona_profile_all_persona_types(
        self, persona_type: PersonaType
    ) -> None:
        """PersonaProfile should accept any valid PersonaType."""
        profile = PersonaProfile(
            persona_type=persona_type,
            name="Test User",
            age=45,
            style_description="Test style description.",
            background="Test background.",
        )
        assert profile.persona_type == persona_type

    def test_valid_persona_profile_minimum_age(self) -> None:
        """PersonaProfile with minimum age (18) should be created."""
        profile = PersonaProfile(
            persona_type=PersonaType.CONFUSED_STUDENT,
            name="Young Student",
            age=18,
            style_description="Uncertain.",
            background="First-year student.",
        )
        assert profile.age == 18

    def test_valid_persona_profile_maximum_age(self) -> None:
        """PersonaProfile with maximum age (95) should be created."""
        profile = PersonaProfile(
            persona_type=PersonaType.NAIVE_RETIREE,
            name="Elder Person",
            age=95,
            style_description="Wise.",
            background="Long retired.",
        )
        assert profile.age == 95


class TestPersonaProfileAgeValidation:
    """Tests for age field validation."""

    def test_age_below_minimum_raises_validation_error(self) -> None:
        """Age below 18 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PersonaProfile(
                persona_type=PersonaType.CONFUSED_STUDENT,
                name="Too Young",
                age=17,
                style_description="Style.",
                background="Background.",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("age",)
        assert "greater than or equal to 18" in errors[0]["msg"]

    def test_age_above_maximum_raises_validation_error(self) -> None:
        """Age above 95 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PersonaProfile(
                persona_type=PersonaType.NAIVE_RETIREE,
                name="Too Old",
                age=96,
                style_description="Style.",
                background="Background.",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("age",)
        assert "less than or equal to 95" in errors[0]["msg"]

    @pytest.mark.parametrize(
        "invalid_age",
        [0, 1, 10, 17, 96, 100, 150],
        ids=["zero", "one", "ten", "seventeen", "ninety_six", "hundred", "one_fifty"],
    )
    def test_age_out_of_range_raises_validation_error(self, invalid_age: int) -> None:
        """Various out-of-range age values should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PersonaProfile(
                persona_type=PersonaType.NAIVE_RETIREE,
                name="Invalid Age",
                age=invalid_age,
                style_description="Style.",
                background="Background.",
            )
        errors = exc_info.value.errors()
        assert errors[0]["loc"] == ("age",)

    @pytest.mark.parametrize(
        "valid_age",
        [18, 19, 25, 45, 65, 80, 94, 95],
        ids=[
            "min",
            "nineteen",
            "mid_twenties",
            "mid_forties",
            "retired",
            "elderly",
            "almost_max",
            "max",
        ],
    )
    def test_age_in_range_accepted(self, valid_age: int) -> None:
        """Age values within 18-95 range should be accepted."""
        profile = PersonaProfile(
            persona_type=PersonaType.NAIVE_RETIREE,
            name="Valid Age",
            age=valid_age,
            style_description="Style.",
            background="Background.",
        )
        assert profile.age == valid_age


class TestPersonaProfileNameValidation:
    """Tests for name field validation."""

    def test_empty_name_raises_validation_error(self) -> None:
        """Empty name string should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PersonaProfile(
                persona_type=PersonaType.NAIVE_RETIREE,
                name="",
                age=70,
                style_description="Style.",
                background="Background.",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("name",)

    def test_single_character_name_valid(self) -> None:
        """Single character name (min_length=1) should be valid."""
        profile = PersonaProfile(
            persona_type=PersonaType.NAIVE_RETIREE,
            name="X",
            age=70,
            style_description="Style.",
            background="Background.",
        )
        assert profile.name == "X"

    def test_long_name_at_max_length_valid(self) -> None:
        """Name at maximum length (100) should be valid."""
        long_name = "A" * 100
        profile = PersonaProfile(
            persona_type=PersonaType.NAIVE_RETIREE,
            name=long_name,
            age=70,
            style_description="Style.",
            background="Background.",
        )
        assert profile.name == long_name
        assert len(profile.name) == 100

    def test_name_exceeds_max_length_raises_validation_error(self) -> None:
        """Name exceeding 100 characters should raise ValidationError."""
        too_long_name = "A" * 101
        with pytest.raises(ValidationError) as exc_info:
            PersonaProfile(
                persona_type=PersonaType.NAIVE_RETIREE,
                name=too_long_name,
                age=70,
                style_description="Style.",
                background="Background.",
            )
        errors = exc_info.value.errors()
        assert errors[0]["loc"] == ("name",)


class TestPersonaProfileStyleValidation:
    """Tests for style_description field validation."""

    def test_empty_style_description_raises_validation_error(self) -> None:
        """Empty style_description string should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PersonaProfile(
                persona_type=PersonaType.NAIVE_RETIREE,
                name="Test User",
                age=70,
                style_description="",
                background="Background.",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("style_description",)

    def test_single_character_style_valid(self) -> None:
        """Single character style_description (min_length=1) should be valid."""
        profile = PersonaProfile(
            persona_type=PersonaType.NAIVE_RETIREE,
            name="Test User",
            age=70,
            style_description="X",
            background="Background.",
        )
        assert profile.style_description == "X"


class TestPersonaProfileBackgroundValidation:
    """Tests for background field validation."""

    def test_empty_background_raises_validation_error(self) -> None:
        """Empty background string should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PersonaProfile(
                persona_type=PersonaType.NAIVE_RETIREE,
                name="Test User",
                age=70,
                style_description="Style.",
                background="",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("background",)

    def test_single_character_background_valid(self) -> None:
        """Single character background (min_length=1) should be valid."""
        profile = PersonaProfile(
            persona_type=PersonaType.NAIVE_RETIREE,
            name="Test User",
            age=70,
            style_description="Style.",
            background="X",
        )
        assert profile.background == "X"


class TestPersonaProfileSummaryProperty:
    """Tests for summary property."""

    def test_summary_format(self) -> None:
        """summary should return correctly formatted string."""
        profile = PersonaProfile(
            persona_type=PersonaType.NAIVE_RETIREE,
            name="Margaret Thompson",
            age=72,
            style_description="Trusting and polite.",
            background="Retired teacher.",
        )
        assert profile.summary == "Margaret Thompson, 72 - Naive Retiree"

    @pytest.mark.parametrize(
        "persona_type,expected_suffix",
        [
            (PersonaType.NAIVE_RETIREE, "Naive Retiree"),
            (PersonaType.STRESSED_MANAGER, "Stressed Manager"),
            (PersonaType.GREEDY_INVESTOR, "Greedy Investor"),
            (PersonaType.CONFUSED_STUDENT, "Confused Student"),
        ],
        ids=["retiree", "manager", "investor", "student"],
    )
    def test_summary_includes_display_name(
        self, persona_type: PersonaType, expected_suffix: str
    ) -> None:
        """summary should include the persona type display name."""
        profile = PersonaProfile(
            persona_type=persona_type,
            name="Test User",
            age=45,
            style_description="Style.",
            background="Background.",
        )
        assert profile.summary.endswith(expected_suffix)

    def test_summary_includes_name_and_age(self) -> None:
        """summary should include the name and age."""
        profile = PersonaProfile(
            persona_type=PersonaType.GREEDY_INVESTOR,
            name="John Smith",
            age=35,
            style_description="Style.",
            background="Background.",
        )
        assert "John Smith" in profile.summary
        assert "35" in profile.summary


class TestPersonaProfileFrozenModel:
    """Tests for model immutability (frozen=True)."""

    def test_cannot_modify_persona_type(self) -> None:
        """Attempting to modify persona_type should raise error."""
        profile = PersonaProfile(
            persona_type=PersonaType.NAIVE_RETIREE,
            name="Test User",
            age=70,
            style_description="Style.",
            background="Background.",
        )
        with pytest.raises(ValidationError) as exc_info:
            profile.persona_type = PersonaType.STRESSED_MANAGER
        errors = exc_info.value.errors()
        # Pydantic v2 message check may vary; mostly verify it raises
        assert errors

    def test_cannot_modify_name(self) -> None:
        """Attempting to modify name should raise error."""
        profile = PersonaProfile(
            persona_type=PersonaType.NAIVE_RETIREE,
            name="Original Name",
            age=70,
            style_description="Style.",
            background="Background.",
        )
        with pytest.raises(ValidationError) as exc_info:
            profile.name = "New Name"
        errors = exc_info.value.errors()
        assert errors

    def test_cannot_modify_age(self) -> None:
        """Attempting to modify age should raise error."""
        profile = PersonaProfile(
            persona_type=PersonaType.NAIVE_RETIREE,
            name="Test User",
            age=70,
            style_description="Style.",
            background="Background.",
        )
        with pytest.raises(ValidationError) as exc_info:
            profile.age = 80
        errors = exc_info.value.errors()
        assert errors


class TestPersonaProfileSerialization:
    """Tests for JSON and dict serialization."""

    def test_json_serialization(self) -> None:
        """PersonaProfile should serialize to JSON correctly."""
        profile = PersonaProfile(
            persona_type=PersonaType.NAIVE_RETIREE,
            name="Margaret Thompson",
            age=72,
            style_description="Trusting and polite.",
            background="Retired teacher.",
        )
        json_str = profile.model_dump_json()
        data = json.loads(json_str)

        assert data["persona_type"] == "naive_retiree"
        assert data["name"] == "Margaret Thompson"
        assert data["age"] == 72
        assert data["style_description"] == "Trusting and polite."
        assert data["background"] == "Retired teacher."

    def test_dict_serialization(self) -> None:
        """PersonaProfile should serialize to dict correctly."""
        profile = PersonaProfile(
            persona_type=PersonaType.STRESSED_MANAGER,
            name="David Chen",
            age=45,
            style_description="Impatient and busy.",
            background="Marketing director.",
        )
        data = profile.model_dump()

        assert data["persona_type"] == PersonaType.STRESSED_MANAGER
        assert data["name"] == "David Chen"
        assert data["age"] == 45

    def test_json_round_trip(self) -> None:
        """PersonaProfile should survive JSON round-trip."""
        original = PersonaProfile(
            persona_type=PersonaType.GREEDY_INVESTOR,
            name="Robert Williams",
            age=38,
            style_description="Enthusiastic about returns.",
            background="Day trader.",
        )

        # Serialize to JSON
        json_str = original.model_dump_json()

        # Deserialize back
        data = json.loads(json_str)
        restored = PersonaProfile(**data)

        assert restored.persona_type == original.persona_type
        assert restored.name == original.name
        assert restored.age == original.age
        assert restored.style_description == original.style_description
        assert restored.background == original.background

    @pytest.mark.parametrize(
        "persona_type",
        list(PersonaType),
        ids=[pt.name for pt in PersonaType],
    )
    def test_json_serialization_all_persona_types(
        self, persona_type: PersonaType
    ) -> None:
        """All persona types should serialize to JSON correctly."""
        profile = PersonaProfile(
            persona_type=persona_type,
            name="Test User",
            age=45,
            style_description="Style.",
            background="Background.",
        )
        json_str = profile.model_dump_json()
        data = json.loads(json_str)
        assert data["persona_type"] == persona_type.value


class TestPersonaProfileMissingFields:
    """Tests for missing required fields."""

    def test_missing_persona_type_raises_validation_error(self) -> None:
        """Missing persona_type should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PersonaProfile(
                name="Test User",
                age=70,
                style_description="Style.",
                background="Background.",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("persona_type",) for e in errors)

    def test_missing_name_raises_validation_error(self) -> None:
        """Missing name should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PersonaProfile(
                persona_type=PersonaType.NAIVE_RETIREE,
                age=70,
                style_description="Style.",
                background="Background.",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_missing_age_raises_validation_error(self) -> None:
        """Missing age should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PersonaProfile(
                persona_type=PersonaType.NAIVE_RETIREE,
                name="Test User",
                style_description="Style.",
                background="Background.",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("age",) for e in errors)

    def test_missing_style_description_raises_validation_error(self) -> None:
        """Missing style_description should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PersonaProfile(
                persona_type=PersonaType.NAIVE_RETIREE,
                name="Test User",
                age=70,
                background="Background.",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("style_description",) for e in errors)

    def test_missing_background_raises_validation_error(self) -> None:
        """Missing background should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PersonaProfile(
                persona_type=PersonaType.NAIVE_RETIREE,
                name="Test User",
                age=70,
                style_description="Style.",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("background",) for e in errors)


class TestPersonaProfileRealisticScenarios:
    """Tests with realistic persona profile scenarios."""

    def test_naive_retiree_profile(self) -> None:
        """Realistic Naive Retiree persona."""
        profile = PersonaProfile(
            persona_type=PersonaType.NAIVE_RETIREE,
            name="Margaret Thompson",
            age=72,
            style_description=(
                "Trusting and polite, uses formal language. "
                "Easily confused by technology and modern terms."
            ),
            background="Retired teacher, recently widowed, lives alone with two cats.",
        )
        assert profile.persona_type.display_name == "Naive Retiree"
        assert profile.age >= 65
        assert "Margaret Thompson" in profile.summary

    def test_stressed_manager_profile(self) -> None:
        """Realistic Stressed Manager persona."""
        profile = PersonaProfile(
            persona_type=PersonaType.STRESSED_MANAGER,
            name="David Chen",
            age=45,
            style_description=(
                "Impatient and busy, prefers brief responses. Easily annoyed by delays."
            ),
            background="Marketing director at mid-size company, managing projects.",
        )
        assert profile.persona_type.display_name == "Stressed Manager"
        assert 35 <= profile.age <= 55
        assert "David Chen" in profile.summary

    def test_greedy_investor_profile(self) -> None:
        """Realistic Greedy Investor persona."""
        profile = PersonaProfile(
            persona_type=PersonaType.GREEDY_INVESTOR,
            name="Robert Williams",
            age=38,
            style_description=(
                "Enthusiastic about financial opportunities. "
                "Asks many questions about returns and profits."
            ),
            background="Amateur day trader, looking for the next big opportunity.",
        )
        assert profile.persona_type.display_name == "Greedy Investor"
        assert "Robert Williams" in profile.summary

    def test_confused_student_profile(self) -> None:
        """Realistic Confused Student persona."""
        profile = PersonaProfile(
            persona_type=PersonaType.CONFUSED_STUDENT,
            name="Emily Johnson",
            age=21,
            style_description=(
                "Uncertain and easily intimidated by authority figures. "
                "Asks clarifying questions, apologizes frequently."
            ),
            background="First-year college student, first time living away from home.",
        )
        assert profile.persona_type.display_name == "Confused Student"
        assert 18 <= profile.age <= 26
        assert "Emily Johnson" in profile.summary
