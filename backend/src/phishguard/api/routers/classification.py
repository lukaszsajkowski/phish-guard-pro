"""Classification API endpoints for phishing email analysis."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from phishguard.agents.profiler import ProfilerAgent, ClassificationError
from phishguard.agents.persona_engine import PersonaEngine
from phishguard.api.dependencies import get_current_user_id
from phishguard.models.classification import ClassificationResult
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
    Classify a phishing email and persist the session.

    Args:
        request: The request body containing email content.
        user_id: The authenticated user's ID (from JWT).

    Returns:
        ClassificationResult with attack type, confidence, persona, and session_id.

    Raises:
        HTTPException: If classification or persistence fails.
    """
    agent = ProfilerAgent()
    persona_engine = PersonaEngine(seed=None)  # No seed for random variety by default

    try:
        # Create session and store email content
        session_id = await session_service.create_session(
            user_id=user_id,
            email_content=request.email_content,
        )

        # Perform classification
        result = await agent.classify(request.email_content)

        # Select persona if phishing detected
        if result.is_phishing:
            persona = persona_engine.select_persona(result.attack_type)
            result = result.model_copy(update={"persona": persona})

        # Update session with classification results
        await session_service.update_session_classification(
            session_id=session_id,
            classification_result=result,
        )

        # Add session_id to result
        result = result.model_copy(update={"session_id": session_id})

        logger.info(
            "Classified email for user %s: attack_type=%s, session=%s",
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
    except Exception as e:
        logger.error("Classification failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Classification failed. Please try again.",
        )
