"""PhishGuard LangGraph workflow graph definition.

This module creates the StateGraph that orchestrates the entire
PhishGuard workflow from email classification to response generation.
"""

import logging
from typing import Literal

from langgraph.graph import END, StateGraph

from phishguard.orchestrator.nodes import (
    add_bot_response,
    add_scammer_message,
    classify_email,
    extract_intel,
    extract_intel_from_email,
    generate_response,
    select_persona,
    validate_safety,
)
from phishguard.orchestrator.state import PhishGuardState

logger = logging.getLogger(__name__)


def should_continue_after_classification(
    state: PhishGuardState,
) -> Literal["extract_intel_from_email", "end"]:
    """Route after classification: continue if phishing, end if not.

    Args:
        state: Current workflow state.

    Returns:
        Next node name or END.
    """
    classification = state.get("classification")
    if not classification:
        return "end"

    attack_type = classification.get("attack_type", "not_phishing")
    if attack_type == "not_phishing":
        logger.info("Routing: Email is not phishing, ending workflow")
        return "end"

    logger.info("Routing: Email is phishing, extracting IOCs from initial email")
    return "extract_intel_from_email"


def should_regenerate(
    state: PhishGuardState,
) -> Literal["generate_response", "add_bot_response"]:
    """Route after safety validation: regenerate if unsafe.
    
    Args:
        state: Current workflow state.
        
    Returns:
        Next node name.
    """
    is_safe = state.get("is_safe", False)
    regeneration_count = state.get("regeneration_count", 0)
    max_regenerations = 3
    
    if is_safe:
        logger.info("Routing: Response is safe, adding to history")
        return "add_bot_response"
    
    if regeneration_count >= max_regenerations:
        logger.warning(
            "Routing: Max regenerations reached (%d), accepting response",
            regeneration_count,
        )
        return "add_bot_response"
    
    logger.info(
        "Routing: Response unsafe, regenerating (attempt %d)",
        regeneration_count + 1,
    )
    return "generate_response"


def create_phishguard_graph() -> StateGraph:
    """Create the PhishGuard workflow graph.

    The graph implements the following workflow:

    1. classify_email: Classify the email content
    2. (conditional) If not phishing -> END
    3. extract_intel_from_email: Extract IOCs from initial email
    4. select_persona: Select appropriate victim persona
    5. generate_response: Generate response in persona style
    6. validate_safety: Check response safety
    7. (conditional) If unsafe -> regenerate
    8. add_bot_response: Add response to conversation history
    9. END (wait for scammer message)

    For continuation (when scammer_message is provided):
    1. add_scammer_message: Add to history
    2. extract_intel: Extract IOCs from message
    3. generate_response: Generate next response
    4. (continue from step 6)

    Returns:
        Compiled StateGraph ready for execution.
    """
    # Create the graph with our state schema
    graph = StateGraph(PhishGuardState)
    
    # Add all nodes
    graph.add_node("classify_email", classify_email)
    graph.add_node("extract_intel_from_email", extract_intel_from_email)
    graph.add_node("select_persona", select_persona)
    graph.add_node("generate_response", generate_response)
    graph.add_node("extract_intel", extract_intel)
    graph.add_node("validate_safety", validate_safety)
    graph.add_node("add_scammer_message", add_scammer_message)
    graph.add_node("add_bot_response", add_bot_response)
    
    # Set entry point
    graph.set_entry_point("classify_email")
    
    # Add edges for initial classification flow
    graph.add_conditional_edges(
        "classify_email",
        should_continue_after_classification,
        {
            "extract_intel_from_email": "extract_intel_from_email",
            "end": END,
        },
    )

    # Extract IOCs from email -> Persona selection
    graph.add_edge("extract_intel_from_email", "select_persona")

    # Persona -> Generate response
    graph.add_edge("select_persona", "generate_response")
    
    # Generate -> Validate safety
    graph.add_edge("generate_response", "validate_safety")
    
    # Safety validation -> conditional regeneration or continue
    graph.add_conditional_edges(
        "validate_safety",
        should_regenerate,
        {
            "generate_response": "generate_response",
            "add_bot_response": "add_bot_response",
        },
    )
    
    # Add bot response -> END (wait for user/scammer)
    graph.add_edge("add_bot_response", END)
    
    # Scammer message continuation flow
    graph.add_edge("add_scammer_message", "extract_intel")
    graph.add_edge("extract_intel", "generate_response")
    
    logger.info("PhishGuard workflow graph created successfully")
    
    return graph.compile()


def create_continuation_graph() -> StateGraph:
    """Create a graph for continuing conversations with scammer messages.
    
    This is a separate entry point for when we're resuming a conversation
    with a new scammer message.
    
    Returns:
        Compiled StateGraph for conversation continuation.
    """
    graph = StateGraph(PhishGuardState)
    
    # Add nodes for continuation
    graph.add_node("add_scammer_message", add_scammer_message)
    graph.add_node("extract_intel", extract_intel)
    graph.add_node("generate_response", generate_response)
    graph.add_node("validate_safety", validate_safety)
    graph.add_node("add_bot_response", add_bot_response)
    
    # Set entry point for continuation
    graph.set_entry_point("add_scammer_message")
    
    # Build the continuation flow
    graph.add_edge("add_scammer_message", "extract_intel")
    graph.add_edge("extract_intel", "generate_response")
    graph.add_edge("generate_response", "validate_safety")
    
    graph.add_conditional_edges(
        "validate_safety",
        should_regenerate,
        {
            "generate_response": "generate_response",
            "add_bot_response": "add_bot_response",
        },
    )
    
    graph.add_edge("add_bot_response", END)
    
    logger.info("PhishGuard continuation graph created successfully")
    
    return graph.compile()
