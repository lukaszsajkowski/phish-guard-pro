"""Response generation API endpoints for PhishGuard."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from phishguard.agents.conversation import ConversationAgent, ResponseGenerationError
from phishguard.api.dependencies import get_current_user_id
from phishguard.models.classification import AttackType
from phishguard.models.persona import PersonaProfile, PersonaType
from phishguard.models.thinking import AgentThinking
from phishguard.services import session_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/response", tags=["response"])


class ResponseGenerationRequest(BaseModel):
    """Request model for response generation."""

    session_id: str = Field(..., description="The session ID to generate a response for")


class ResponseGenerationResponse(BaseModel):
    """Response model for generated response."""

    content: str = Field(..., description="The generated response text")
    generation_time_ms: int = Field(..., description="Time to generate in milliseconds")
    safety_validated: bool = Field(True, description="Whether safety validation passed")
    regeneration_count: int = Field(0, description="Number of regeneration attempts")
    used_fallback_model: bool = Field(False, description="Whether fallback model was used")
    thinking: AgentThinking | None = Field(None, description="Agent thinking metadata")
    message_id: str = Field(..., description="The stored message ID")


@router.post(
    "/generate",
    response_model=ResponseGenerationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate victim persona response",
    description="Generates a believable response to scammer in the selected persona's style. Requires authentication.",
)
async def generate_response(
    request: ResponseGenerationRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> ResponseGenerationResponse:
    """
    Generate a victim persona response for a phishing email.

    Args:
        request: The request body containing session_id.
        user_id: The authenticated user's ID (from JWT).

    Returns:
        ResponseGenerationResponse with generated content and metadata.

    Raises:
        HTTPException: If session not found, not authorized, or generation fails.
    """
    # Load session data
    session = await session_service.get_session(request.session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Verify user owns this session
    if session.get("user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )

    # Get session data
    attack_type_str = session.get("attack_type")
    persona_data = session.get("persona")

    if not attack_type_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session has not been classified yet",
        )

    # Parse attack type
    try:
        attack_type = AttackType(attack_type_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invalid attack type stored: {attack_type_str}",
        )

    # Build persona profile
    if not persona_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session has no persona assigned",
        )

    try:
        persona = PersonaProfile(
            persona_type=PersonaType(persona_data["persona_type"]),
            name=persona_data["name"],
            age=persona_data["age"],
            style_description=persona_data["style_description"],
            background=persona_data["background"],
        )
    except (KeyError, ValueError) as e:
        logger.error("Failed to parse persona data: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse stored persona data",
        )

    # Get original email content
    email_content = await session_service.get_original_email(request.session_id)

    if not email_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No email content found for session",
        )

    # Generate response
    agent = ConversationAgent()

    try:
        result = await agent.generate_response(
            persona=persona,
            email_content=email_content,
            attack_type=attack_type,
            is_first_response=True,  # For now, always first response
        )

        # Persist the generated response
        thinking_dict = None
        if result.thinking:
            thinking_dict = {
                "turn_goal": result.thinking.turn_goal,
                "selected_tactic": result.thinking.selected_tactic,
                "reasoning": result.thinking.reasoning,
            }

        message_id = await session_service.add_bot_response(
            session_id=request.session_id,
            content=result.content,
            thinking=thinking_dict,
            generation_time_ms=result.generation_time_ms,
        )

        logger.info(
            "Generated response for session %s (user %s): %d chars in %dms",
            request.session_id,
            user_id,
            len(result.content),
            result.generation_time_ms,
        )

        return ResponseGenerationResponse(
            content=result.content,
            generation_time_ms=result.generation_time_ms,
            safety_validated=result.safety_validated,
            regeneration_count=result.regeneration_count,
            used_fallback_model=result.used_fallback_model,
            thinking=result.thinking,
            message_id=message_id,
        )

    except ResponseGenerationError as e:
        logger.error("Response generation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Unexpected error during response generation: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Response generation failed. Please try again.",
        )
