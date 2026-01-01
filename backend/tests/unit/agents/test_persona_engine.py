"""Comprehensive tests for PersonaEngine agent.

These tests verify that the PersonaEngine:
1. Maps all attack types to appropriate persona types
2. Generates consistent names with the same seed
3. Generates different names with different seeds
4. Generates ages within appropriate ranges for each persona
5. Returns complete PersonaProfile objects
6. Handles all edge cases correctly
"""

import pytest

from phishguard.agents.persona_engine import (
    ATTACK_PERSONA_MAPPING,
    PERSONA_AGE_RANGES,
    PERSONA_BACKGROUNDS,
    PERSONA_STYLES,
    PersonaEngine,
)
from phishguard.models.classification import AttackType
from phishguard.models.persona import PersonaProfile, PersonaType


class TestAttackTypeToPersonaMapping:
    """Tests for attack type to persona type mapping."""

    def test_all_attack_types_have_mapping(self) -> None:
        """Every AttackType should have a corresponding PersonaType mapping."""
        for attack_type in AttackType:
            assert attack_type in ATTACK_PERSONA_MAPPING

    @pytest.mark.parametrize(
        "attack_type,expected_persona",
        [
            (AttackType.NIGERIAN_419, PersonaType.NAIVE_RETIREE),
            (AttackType.CEO_FRAUD, PersonaType.STRESSED_MANAGER),
            (AttackType.FAKE_INVOICE, PersonaType.STRESSED_MANAGER),
            (AttackType.ROMANCE_SCAM, PersonaType.NAIVE_RETIREE),
            (AttackType.TECH_SUPPORT, PersonaType.CONFUSED_STUDENT),
            (AttackType.LOTTERY_PRIZE, PersonaType.GREEDY_INVESTOR),
            (AttackType.CRYPTO_INVESTMENT, PersonaType.GREEDY_INVESTOR),
            (AttackType.DELIVERY_SCAM, PersonaType.CONFUSED_STUDENT),
            (AttackType.NOT_PHISHING, PersonaType.CONFUSED_STUDENT),
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
    def test_attack_type_maps_to_expected_persona(
        self, attack_type: AttackType, expected_persona: PersonaType
    ) -> None:
        """Each attack type should map to the expected persona type."""
        engine = PersonaEngine(seed=12345)
        profile = engine.select_persona(attack_type)
        assert profile.persona_type == expected_persona

    def test_mapping_returns_correct_persona_for_419_scam(self) -> None:
        """Nigerian 419 scam should target Naive Retiree persona."""
        engine = PersonaEngine()
        profile = engine.select_persona(AttackType.NIGERIAN_419)
        assert profile.persona_type == PersonaType.NAIVE_RETIREE

    def test_mapping_returns_correct_persona_for_ceo_fraud(self) -> None:
        """CEO Fraud should target Stressed Manager persona."""
        engine = PersonaEngine()
        profile = engine.select_persona(AttackType.CEO_FRAUD)
        assert profile.persona_type == PersonaType.STRESSED_MANAGER


class TestFakerSeedingConsistency:
    """Tests for Faker seeding and name generation consistency."""

    def test_same_seed_produces_same_name(self) -> None:
        """Same seed should produce identical names."""
        seed = 42
        engine1 = PersonaEngine(seed=seed)
        engine2 = PersonaEngine(seed=seed)

        profile1 = engine1.select_persona(AttackType.NIGERIAN_419)
        profile2 = engine2.select_persona(AttackType.NIGERIAN_419)

        assert profile1.name == profile2.name

    def test_different_seeds_produce_different_names(self) -> None:
        """Different seeds should typically produce different names."""
        engine1 = PersonaEngine(seed=42)
        engine2 = PersonaEngine(seed=9999)

        profile1 = engine1.select_persona(AttackType.NIGERIAN_419)
        profile2 = engine2.select_persona(AttackType.NIGERIAN_419)

        # While not guaranteed, different seeds should produce different names
        # This test may rarely fail if by chance both seeds produce same name
        assert profile1.name != profile2.name

    def test_no_seed_produces_random_names(self) -> None:
        """No seed should produce varying names across instances."""
        # Create multiple engines without seed
        names = set()
        for _ in range(5):
            engine = PersonaEngine()
            profile = engine.select_persona(AttackType.NIGERIAN_419)
            names.add(profile.name)

        # With random seeds, we expect at least some variation
        # (not all 5 names being identical)
        assert len(names) >= 2

    def test_seed_produces_valid_name_format(self) -> None:
        """Generated names should have valid format."""
        engine = PersonaEngine(seed=12345)
        profile = engine.select_persona(AttackType.NIGERIAN_419)

        assert profile.name is not None
        assert isinstance(profile.name, str)
        assert len(profile.name) > 0
        assert len(profile.name) <= 100  # Max name length constraint

    @pytest.mark.parametrize("seed", [0, 1, 100, 999999, 2**30])
    def test_various_seeds_produce_valid_names(self, seed: int) -> None:
        """Various seed values should all produce valid names."""
        engine = PersonaEngine(seed=seed)
        profile = engine.select_persona(AttackType.CEO_FRAUD)

        assert profile.name is not None
        assert len(profile.name) > 0


class TestAgeRangeValidation:
    """Tests for age generation within appropriate ranges."""

    def test_naive_retiree_age_in_range(self) -> None:
        """Naive Retiree age should be within 65-82 range."""
        engine = PersonaEngine(seed=12345)
        for _ in range(10):
            profile = engine.select_persona(AttackType.NIGERIAN_419)
            min_age, max_age = PERSONA_AGE_RANGES[PersonaType.NAIVE_RETIREE]
            assert min_age <= profile.age <= max_age

    def test_stressed_manager_age_in_range(self) -> None:
        """Stressed Manager age should be within 35-55 range."""
        engine = PersonaEngine(seed=12345)
        for _ in range(10):
            profile = engine.select_persona(AttackType.CEO_FRAUD)
            min_age, max_age = PERSONA_AGE_RANGES[PersonaType.STRESSED_MANAGER]
            assert min_age <= profile.age <= max_age

    def test_greedy_investor_age_in_range(self) -> None:
        """Greedy Investor age should be within 28-50 range."""
        engine = PersonaEngine(seed=12345)
        for _ in range(10):
            profile = engine.select_persona(AttackType.CRYPTO_INVESTMENT)
            min_age, max_age = PERSONA_AGE_RANGES[PersonaType.GREEDY_INVESTOR]
            assert min_age <= profile.age <= max_age

    def test_confused_student_age_in_range(self) -> None:
        """Confused Student age should be within 19-26 range."""
        engine = PersonaEngine(seed=12345)
        for _ in range(10):
            profile = engine.select_persona(AttackType.TECH_SUPPORT)
            min_age, max_age = PERSONA_AGE_RANGES[PersonaType.CONFUSED_STUDENT]
            assert min_age <= profile.age <= max_age

    @pytest.mark.parametrize(
        "persona_type",
        list(PersonaType),
        ids=[pt.name for pt in PersonaType],
    )
    def test_all_persona_types_have_age_ranges(self, persona_type: PersonaType) -> None:
        """Every PersonaType should have a defined age range."""
        assert persona_type in PERSONA_AGE_RANGES
        min_age, max_age = PERSONA_AGE_RANGES[persona_type]
        assert 18 <= min_age < max_age <= 95


class TestCompleteProfileGeneration:
    """Tests for complete PersonaProfile object generation."""

    def test_select_persona_returns_persona_profile(self) -> None:
        """select_persona should return a PersonaProfile instance."""
        engine = PersonaEngine(seed=12345)
        profile = engine.select_persona(AttackType.NIGERIAN_419)

        assert isinstance(profile, PersonaProfile)

    def test_profile_has_all_required_fields(self) -> None:
        """Generated profile should have all required fields populated."""
        engine = PersonaEngine(seed=12345)
        profile = engine.select_persona(AttackType.CEO_FRAUD)

        assert profile.persona_type is not None
        assert profile.name is not None
        assert profile.age is not None
        assert profile.style_description is not None
        assert profile.background is not None

    def test_profile_style_matches_persona_type(self) -> None:
        """Profile style_description should match the persona type's style."""
        engine = PersonaEngine(seed=12345)

        for attack_type in AttackType:
            profile = engine.select_persona(attack_type)
            expected_style = PERSONA_STYLES[profile.persona_type]
            assert profile.style_description == expected_style

    def test_profile_summary_property_works(self) -> None:
        """Generated profile should have working summary property."""
        engine = PersonaEngine(seed=12345)
        profile = engine.select_persona(AttackType.ROMANCE_SCAM)

        summary = profile.summary
        assert profile.name in summary
        assert str(profile.age) in summary
        assert profile.persona_type.display_name in summary


class TestBackgroundSelection:
    """Tests for background story selection."""

    @pytest.mark.parametrize(
        "persona_type",
        list(PersonaType),
        ids=[pt.name for pt in PersonaType],
    )
    def test_all_persona_types_have_backgrounds(
        self, persona_type: PersonaType
    ) -> None:
        """Every PersonaType should have background options defined."""
        assert persona_type in PERSONA_BACKGROUNDS
        backgrounds = PERSONA_BACKGROUNDS[persona_type]
        assert len(backgrounds) >= 1

    def test_background_is_from_defined_options(self) -> None:
        """Selected background should be from the defined options."""
        engine = PersonaEngine(seed=12345)

        for attack_type in AttackType:
            profile = engine.select_persona(attack_type)
            valid_backgrounds = PERSONA_BACKGROUNDS[profile.persona_type]
            assert profile.background in valid_backgrounds

    def test_same_seed_produces_same_background(self) -> None:
        """Same seed should produce same background selection."""
        seed = 42
        engine1 = PersonaEngine(seed=seed)
        engine2 = PersonaEngine(seed=seed)

        profile1 = engine1.select_persona(AttackType.LOTTERY_PRIZE)
        profile2 = engine2.select_persona(AttackType.LOTTERY_PRIZE)

        assert profile1.background == profile2.background


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_not_phishing_attack_type_handled(self) -> None:
        """NOT_PHISHING attack type should still generate valid persona."""
        engine = PersonaEngine(seed=12345)
        profile = engine.select_persona(AttackType.NOT_PHISHING)

        assert isinstance(profile, PersonaProfile)
        assert profile.persona_type == PersonaType.CONFUSED_STUDENT

    def test_multiple_calls_with_same_engine(self) -> None:
        """Multiple calls to same engine should produce different results."""
        engine = PersonaEngine()

        profiles = [engine.select_persona(AttackType.NIGERIAN_419) for _ in range(3)]

        # Different calls to same engine produce different names
        # (unless by rare chance)
        names = {p.name for p in profiles}
        assert len(names) >= 2

    def test_engine_without_seed_is_random(self) -> None:
        """Engine without seed should produce random results."""
        engine = PersonaEngine()
        profile1 = engine.select_persona(AttackType.CEO_FRAUD)

        # Create new engine without seed
        engine2 = PersonaEngine()
        profile2 = engine2.select_persona(AttackType.CEO_FRAUD)

        # Results should likely differ (not guaranteed but highly probable)
        # We check that at least one of name or age differs
        assert (profile1.name != profile2.name) or (profile1.age != profile2.age)

    def test_style_descriptions_are_non_empty(self) -> None:
        """All persona types should have non-empty style descriptions."""
        for persona_type in PersonaType:
            style = PERSONA_STYLES[persona_type]
            assert style is not None
            assert len(style) > 0

    def test_age_ranges_are_valid_tuples(self) -> None:
        """All age ranges should be valid (min, max) tuples."""
        for persona_type in PersonaType:
            age_range = PERSONA_AGE_RANGES[persona_type]
            assert isinstance(age_range, tuple)
            assert len(age_range) == 2
            min_age, max_age = age_range
            assert isinstance(min_age, int)
            assert isinstance(max_age, int)
            assert min_age < max_age


class TestRealisticScenarios:
    """Tests with realistic usage scenarios."""

    def test_session_consistency_simulation(self) -> None:
        """Simulate session where same seed produces consistent persona."""
        session_seed = 12345

        # First classification
        engine1 = PersonaEngine(seed=session_seed)
        profile1 = engine1.select_persona(AttackType.CRYPTO_INVESTMENT)

        # Simulated page reload with same session seed
        engine2 = PersonaEngine(seed=session_seed)
        profile2 = engine2.select_persona(AttackType.CRYPTO_INVESTMENT)

        # Should be identical
        assert profile1.name == profile2.name
        assert profile1.age == profile2.age
        assert profile1.background == profile2.background
        assert profile1.persona_type == profile2.persona_type

    def test_different_sessions_different_personas(self) -> None:
        """Different sessions (different seeds) should produce different personas."""
        session1_seed = 11111
        session2_seed = 22222

        engine1 = PersonaEngine(seed=session1_seed)
        engine2 = PersonaEngine(seed=session2_seed)

        profile1 = engine1.select_persona(AttackType.ROMANCE_SCAM)
        profile2 = engine2.select_persona(AttackType.ROMANCE_SCAM)

        # Same attack type, different seeds -> different personas
        assert profile1.name != profile2.name

    def test_full_workflow_nigerian_419(self) -> None:
        """Full workflow test for Nigerian 419 scam."""
        engine = PersonaEngine(seed=99999)
        profile = engine.select_persona(AttackType.NIGERIAN_419)

        # Should be a Naive Retiree
        assert profile.persona_type == PersonaType.NAIVE_RETIREE
        assert profile.persona_type.display_name == "Naive Retiree"

        # Should have elderly age
        assert 65 <= profile.age <= 82

        # Should have appropriate style
        assert "trusting" in profile.style_description.lower()

    def test_full_workflow_ceo_fraud(self) -> None:
        """Full workflow test for CEO Fraud scam."""
        engine = PersonaEngine(seed=88888)
        profile = engine.select_persona(AttackType.CEO_FRAUD)

        # Should be a Stressed Manager
        assert profile.persona_type == PersonaType.STRESSED_MANAGER
        assert profile.persona_type.display_name == "Stressed Manager"

        # Should have mid-career age
        assert 35 <= profile.age <= 55

        # Should have business-like style
        assert "busy" in profile.style_description.lower()
