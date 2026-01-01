"""PhishGuard agent modules for phishing email analysis and engagement.

This package contains the specialized agents that power PhishGuard's
autonomous phishing defense system.
"""

from phishguard.agents.conversation import (
    ConversationAgent,
    ResponseGenerationError,
)
from phishguard.agents.intel_collector import (
    ExtractionResult,
    IntelCollector,
)
from phishguard.agents.persona_engine import PersonaEngine
from phishguard.agents.profiler import ClassificationError, ProfilerAgent
from phishguard.models.ioc import ExtractedIOC, IOCType

__all__ = [
    "ClassificationError",
    "ConversationAgent",
    "ExtractedIOC",
    "ExtractionResult",
    "IntelCollector",
    "IOCType",
    "PersonaEngine",
    "ProfilerAgent",
    "ResponseGenerationError",
]
