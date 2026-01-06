"""Node functions for PhishGuard LangGraph workflow.

Each node represents a processing step in the workflow graph.
Nodes receive the current state, perform their operation, and return
state updates.
"""

import logging
import time
from typing import Any

from phishguard.agents.conversation import ConversationAgent
from phishguard.agents.intel_collector import IntelCollector
from phishguard.agents.persona_engine import PersonaEngine
from phishguard.agents.profiler import ProfilerAgent
from phishguard.models.classification import AttackType
from phishguard.models.conversation import ConversationMessage, MessageSender
from phishguard.models.persona import PersonaProfile, PersonaType
from phishguard.orchestrator.state import PhishGuardState
from phishguard.safety import OutputValidator

logger = logging.getLogger(__name__)


async def classify_email(state: PhishGuardState) -> dict[str, Any]:
    """Node: Classify email using ProfilerAgent.
    
    Args:
        state: Current workflow state with email_content.
        
    Returns:
        State update with classification result.
    """
    logger.info("Node: classify_email starting for session %s", state.get("session_id"))
    
    email_content = state.get("email_content", "")
    if not email_content:
        return {"error": "No email content provided"}
    
    profiler = ProfilerAgent()
    result = await profiler.classify(email_content)
    
    classification = {
        "attack_type": result.attack_type.value,
        "confidence": result.confidence,
        "reasoning": result.reasoning,
        "classification_time_ms": result.classification_time_ms,
    }
    
    logger.info(
        "Node: classify_email completed - attack_type=%s, confidence=%.1f",
        result.attack_type.value,
        result.confidence,
    )
    
    return {"classification": classification}


async def select_persona(state: PhishGuardState) -> dict[str, Any]:
    """Node: Select persona using PersonaEngine.
    
    Args:
        state: Current workflow state with classification.
        
    Returns:
        State update with selected persona.
    """
    logger.info("Node: select_persona starting for session %s", state.get("session_id"))
    
    classification = state.get("classification")
    if not classification:
        return {"error": "No classification available"}
    
    attack_type = AttackType(classification["attack_type"])
    engine = PersonaEngine()
    profile = engine.select_persona(attack_type)
    
    persona = {
        "persona_type": profile.persona_type.value,
        "name": profile.name,
        "age": profile.age,
        "style_description": profile.style_description,
        "background": profile.background,
    }
    
    logger.info(
        "Node: select_persona completed - persona=%s (%s)",
        profile.name,
        profile.persona_type.value,
    )
    
    return {"persona": persona}


async def generate_response(state: PhishGuardState) -> dict[str, Any]:
    """Node: Generate response using ConversationAgent.
    
    Args:
        state: Current workflow state with persona and history.
        
    Returns:
        State update with generated response.
    """
    logger.info("Node: generate_response starting for session %s", state.get("session_id"))
    start_time = time.perf_counter()
    
    persona_dict = state.get("persona")
    classification = state.get("classification")
    email_content = state.get("email_content", "")
    history = state.get("conversation_history", [])
    
    if not persona_dict:
        return {"error": "No persona available"}
    if not classification:
        return {"error": "No classification available"}
    
    # Reconstruct persona profile
    persona = PersonaProfile(
        persona_type=PersonaType(persona_dict["persona_type"]),
        name=persona_dict["name"],
        age=persona_dict["age"],
        style_description=persona_dict["style_description"],
        background=persona_dict["background"],
    )
    
    attack_type = AttackType(classification["attack_type"])
    
    # Convert history to ConversationMessage objects
    conversation_history = [
        ConversationMessage(
            sender=MessageSender(msg["sender"]),
            content=msg["content"],
        )
        for msg in history
    ]
    
    is_first = len(conversation_history) == 0
    
    agent = ConversationAgent()
    result = await agent.generate_response(
        persona=persona,
        email_content=email_content,
        attack_type=attack_type,
        conversation_history=conversation_history if not is_first else None,
        is_first_response=is_first,
    )
    
    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
    
    thinking = None
    if result.thinking:
        thinking = {
            "turn_goal": result.thinking.turn_goal,
            "selected_tactic": result.thinking.selected_tactic,
            "reasoning": result.thinking.reasoning,
        }
    
    logger.info(
        "Node: generate_response completed - %d chars, %dms",
        len(result.content),
        elapsed_ms,
    )
    
    return {
        "current_response": result.content,
        "current_thinking": thinking,
        "is_safe": result.safety_validated,
        "regeneration_count": result.regeneration_count,
        "generation_time_ms": elapsed_ms,
    }


async def extract_intel(state: PhishGuardState) -> dict[str, Any]:
    """Node: Extract IOCs using IntelCollector.
    
    Args:
        state: Current workflow state with scammer_message.
        
    Returns:
        State update with extracted IOCs.
    """
    logger.info("Node: extract_intel starting for session %s", state.get("session_id"))
    
    scammer_message = state.get("scammer_message")
    if not scammer_message:
        return {"extracted_iocs": []}
    
    history = state.get("conversation_history", [])
    message_index = len(history)
    
    collector = IntelCollector()
    result = collector.extract(scammer_message, message_index)
    
    iocs = []
    if result.has_iocs:
        iocs = [
            {
                "type": ioc.ioc_type.value,
                "value": ioc.value,
                "context": ioc.context,
                "is_high_value": ioc.is_high_value,
            }
            for ioc in result.iocs
        ]
    
    logger.info(
        "Node: extract_intel completed - %d IOCs extracted",
        len(iocs),
    )
    
    return {"extracted_iocs": iocs}


async def validate_safety(state: PhishGuardState) -> dict[str, Any]:
    """Node: Validate response safety.
    
    Args:
        state: Current workflow state with current_response.
        
    Returns:
        State update with safety validation result.
    """
    logger.info("Node: validate_safety starting for session %s", state.get("session_id"))
    
    response = state.get("current_response")
    if not response:
        return {"is_safe": False, "safety_violations": ["No response to validate"]}
    
    validator = OutputValidator()
    result = validator.validate(response)
    
    logger.info(
        "Node: validate_safety completed - is_safe=%s, violations=%d",
        result.is_safe,
        len(result.violations),
    )
    
    return {
        "is_safe": result.is_safe,
        "safety_violations": result.violations,
    }


async def add_scammer_message(state: PhishGuardState) -> dict[str, Any]:
    """Node: Add scammer message to conversation history.
    
    Args:
        state: Current workflow state with scammer_message.
        
    Returns:
        State update with scammer message added to history.
    """
    scammer_message = state.get("scammer_message")
    if not scammer_message:
        return {}
    
    logger.info("Node: add_scammer_message - adding message to history")
    
    return {
        "conversation_history": [{"sender": "scammer", "content": scammer_message}],
    }


async def add_bot_response(state: PhishGuardState) -> dict[str, Any]:
    """Node: Add bot response to conversation history.
    
    Args:
        state: Current workflow state with current_response.
        
    Returns:
        State update with bot response added to history.
    """
    response = state.get("current_response")
    if not response:
        return {}
    
    logger.info("Node: add_bot_response - adding response to history")
    
    return {
        "conversation_history": [{"sender": "bot", "content": response}],
    }
