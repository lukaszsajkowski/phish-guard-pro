"""Persona Engine for victim profile generation.

This module implements the PersonaEngine, which selects and generates
believable victim personas based on the classified attack type.
"""

import random
from typing import Final

from faker import Faker

from phishguard.models import AttackType
from phishguard.models.persona import PersonaProfile, PersonaType

# Attack type to persona type mapping
# Each attack type is mapped to the most vulnerable persona type
ATTACK_PERSONA_MAPPING: Final[dict[AttackType, PersonaType]] = {
    AttackType.NIGERIAN_419: PersonaType.NAIVE_RETIREE,
    AttackType.CEO_FRAUD: PersonaType.STRESSED_MANAGER,
    AttackType.FAKE_INVOICE: PersonaType.STRESSED_MANAGER,
    AttackType.ROMANCE_SCAM: PersonaType.NAIVE_RETIREE,
    AttackType.TECH_SUPPORT: PersonaType.CONFUSED_STUDENT,
    AttackType.LOTTERY_PRIZE: PersonaType.GREEDY_INVESTOR,
    AttackType.CRYPTO_INVESTMENT: PersonaType.GREEDY_INVESTOR,
    AttackType.DELIVERY_SCAM: PersonaType.CONFUSED_STUDENT,
    AttackType.NOT_PHISHING: PersonaType.CONFUSED_STUDENT,  # Fallback
}

# Age ranges for each persona type (min, max)
PERSONA_AGE_RANGES: Final[dict[PersonaType, tuple[int, int]]] = {
    PersonaType.NAIVE_RETIREE: (65, 82),
    PersonaType.STRESSED_MANAGER: (35, 55),
    PersonaType.GREEDY_INVESTOR: (28, 50),
    PersonaType.CONFUSED_STUDENT: (19, 26),
}

# Style descriptions for each persona type
PERSONA_STYLES: Final[dict[PersonaType, str]] = {
    PersonaType.NAIVE_RETIREE: (
        "Trusting and polite, uses formal language. "
        "Easily confused by technology and modern terms. "
        "Eager to help and quick to believe in good intentions."
    ),
    PersonaType.STRESSED_MANAGER: (
        "Impatient and busy, prefers brief responses. "
        "Easily annoyed by delays, may overlook details due to time pressure. "
        "Speaks in direct, businesslike manner."
    ),
    PersonaType.GREEDY_INVESTOR: (
        "Enthusiastic about financial opportunities. "
        "Asks many questions about returns and profits. "
        "Can be skeptical but gets excited by high-yield promises."
    ),
    PersonaType.CONFUSED_STUDENT: (
        "Uncertain and easily intimidated by authority figures. "
        "Asks clarifying questions, apologizes frequently. "
        "Nervous about making mistakes or getting in trouble."
    ),
}

# Background stories for each persona type
PERSONA_BACKGROUNDS: Final[dict[PersonaType, list[str]]] = {
    PersonaType.NAIVE_RETIREE: [
        "Retired teacher, recently widowed, lives alone with two cats",
        "Former factory worker, enjoys gardening and church activities",
        "Retired nurse, has grandchildren in another state, lonely at times",
    ],
    PersonaType.STRESSED_MANAGER: [
        "Marketing director at a mid-size company, managing multiple projects",
        "Operations manager, dealing with supply chain issues and deadlines",
        "Sales team lead, under pressure to hit quarterly targets",
    ],
    PersonaType.GREEDY_INVESTOR: [
        "Amateur day trader, looking for the next big opportunity",
        "Small business owner wanting to grow retirement savings quickly",
        "Tech worker who missed out on Bitcoin, seeking new investments",
    ],
    PersonaType.CONFUSED_STUDENT: [
        "First-year college student, first time living away from home",
        "Graduate student, overwhelmed with thesis deadlines",
        "International student, still adjusting to new country and systems",
    ],
}


class PersonaEngine:
    """Engine for selecting and generating victim personas.

    The PersonaEngine selects an appropriate victim persona based on
    the attack type and generates consistent identity details using
    the Faker library with a seeded random generator.

    Attributes:
        _faker: Faker instance for generating persona details.
        _random: Seeded random instance for consistent selections.

    Example:
        >>> engine = PersonaEngine(seed=12345)
        >>> profile = engine.select_persona(AttackType.NIGERIAN_419)
        >>> print(profile.persona_type)
        PersonaType.NAIVE_RETIREE
        >>> print(profile.name)
        'Margaret Thompson'  # Consistent with seed
    """

    def __init__(self, seed: int | None = None) -> None:
        """Initialize the PersonaEngine with an optional seed.

        Args:
            seed: Optional seed for reproducible persona generation.
                Using the same seed will always produce the same
                persona details (name, age, background selection).
        """
        self._seed = seed
        self._faker = Faker()
        self._random = random.Random()

        if seed is not None:
            self._faker.seed_instance(seed)
            self._random.seed(seed)

    def select_persona(self, attack_type: AttackType) -> PersonaProfile:
        """Select and generate a persona based on the attack type.

        Maps the attack type to an appropriate persona type, then
        generates consistent identity details using the seeded
        Faker instance.

        Args:
            attack_type: The classified type of phishing attack.

        Returns:
            A complete PersonaProfile with generated details.

        Example:
            >>> engine = PersonaEngine(seed=42)
            >>> profile = engine.select_persona(AttackType.CEO_FRAUD)
            >>> print(profile.summary)
            'David Chen, 45 - Stressed Manager'
        """
        persona_type = self._get_persona_type(attack_type)
        name = self._generate_name()
        age = self._generate_age(persona_type)
        style = self._get_style_description(persona_type)
        background = self._select_background(persona_type)

        return PersonaProfile(
            persona_type=persona_type,
            name=name,
            age=age,
            style_description=style,
            background=background,
        )

    def _get_persona_type(self, attack_type: AttackType) -> PersonaType:
        """Get the persona type for an attack type.

        Args:
            attack_type: The classified attack type.

        Returns:
            The corresponding PersonaType.
        """
        return ATTACK_PERSONA_MAPPING.get(attack_type, PersonaType.CONFUSED_STUDENT)

    def _generate_name(self) -> str:
        """Generate a full name using Faker.

        Returns:
            A generated full name string.
        """
        return self._faker.name()

    def _generate_age(self, persona_type: PersonaType) -> int:
        """Generate an age appropriate for the persona type.

        Args:
            persona_type: The type of persona.

        Returns:
            An age within the persona's appropriate range.
        """
        min_age, max_age = PERSONA_AGE_RANGES[persona_type]
        return self._random.randint(min_age, max_age)

    def _get_style_description(self, persona_type: PersonaType) -> str:
        """Get the communication style description for a persona type.

        Args:
            persona_type: The type of persona.

        Returns:
            The style description string.
        """
        return PERSONA_STYLES[persona_type]

    def _select_background(self, persona_type: PersonaType) -> str:
        """Select a background story for the persona.

        Args:
            persona_type: The type of persona.

        Returns:
            A randomly selected background story.
        """
        backgrounds = PERSONA_BACKGROUNDS[persona_type]
        return self._random.choice(backgrounds)
