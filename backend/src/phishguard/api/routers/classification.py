"""Classification API endpoints for phishing email analysis."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from phishguard.agents.profiler import ClassificationError
from phishguard.api.dependencies import get_current_user_id
from phishguard.models.classification import AttackType, ClassificationResult
from phishguard.models.persona import PersonaProfile, PersonaType
from phishguard.orchestrator import create_phishguard_graph, get_checkpointer
from phishguard.services import session_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/classification", tags=["classification"])


class ClassificationRequest(BaseModel):
    """Request model for email classification."""

    email_content: str


@router.post(
    "/analyze",
    response_model=ClassificationResult,
    status_code=status.HTTP_200_OK,
    summary="Classify phishing email attack type",
    description="Analyzes email content and returns the detected attack type with confidence score. Requires authentication.",
)
async def classify_email(
    request: ClassificationRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> ClassificationResult:
    """
    Classify a phishing email using LangGraph orchestration.

    Args:
        request: The request body containing email content.
        user_id: The authenticated user's ID (from JWT).

    Returns:
        ClassificationResult with attack type, confidence, persona, and session_id.

    Raises:
        HTTPException: If classification or persistence fails.
    """
    try:
        # Create session and store email content
        session_id = await session_service.create_session(
            user_id=user_id,
            email_content=request.email_content,
        )

        # Create and execute the LangGraph workflow
        graph = create_phishguard_graph()
        
        # Initial state for the graph
        initial_state = {
            "email_content": request.email_content,
            "session_id": session_id,
            "user_id": user_id,
        }
        
        # Execute graph with PostgreSQL checkpointer for persistence
        async with get_checkpointer() as checkpointer:
            result_state = await graph.ainvoke(
                initial_state,
                config={
                    "configurable": {"thread_id": session_id},
                    "checkpointer": checkpointer,
                },
            )

        # Check for errors
        if result_state.get("error"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result_state["error"],
            )

        # Build ClassificationResult from graph state
        classification = result_state.get("classification", {})
        persona_data = result_state.get("persona")
        
        # Reconstruct persona if available
        persona = None
        if persona_data:
            persona = PersonaProfile(
                persona_type=PersonaType(persona_data["persona_type"]),
                name=persona_data["name"],
                age=persona_data["age"],
                style_description=persona_data["style_description"],
                background=persona_data["background"],
            )

        # Get extracted IOCs from graph state
        extracted_iocs = result_state.get("extracted_iocs", [])

        result = ClassificationResult(
            attack_type=AttackType(classification.get("attack_type", "not_phishing")),
            confidence=classification.get("confidence", 0.0),
            reasoning=classification.get("reasoning", ""),
            classification_time_ms=classification.get("classification_time_ms", 0),
            persona=persona,
            session_id=session_id,
            extracted_iocs=extracted_iocs,
        )

        # Update session with classification results
        await session_service.update_session_classification(
            session_id=session_id,
            classification_result=result,
        )

        logger.info(
            "Classified email via LangGraph for user %s: attack_type=%s, session=%s",
            user_id,
            result.attack_type.value,
            session_id,
        )

        return result

    except ClassificationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Classification failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Classification failed. Please try again.",
        )
