"""Response generation API endpoints for PhishGuard."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from phishguard.agents.conversation import ConversationAgent, ResponseGenerationError
from phishguard.agents.intel_collector import IntelCollector, ExtractionResult
from phishguard.api.dependencies import get_current_user_id
from phishguard.models.classification import AttackType
from phishguard.models.conversation import ConversationMessage, MessageSender
from phishguard.models.ioc import ExtractedIOC
from phishguard.models.persona import PersonaProfile, PersonaType
from phishguard.models.thinking import AgentThinking
from phishguard.safety import OutputValidator
from phishguard.services import session_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/response", tags=["response"])


class ResponseGenerationRequest(BaseModel):
    """Request model for response generation."""

    session_id: str = Field(..., description="The session ID to generate a response for")
    scammer_message: str | None = Field(
        default=None,
        min_length=1,
        max_length=50000,
        description="Optional scammer message to add before generating response",
    )


class ResponseGenerationResponse(BaseModel):
    """Response model for generated response."""

    content: str = Field(..., description="The generated response text")
    generation_time_ms: int = Field(..., description="Time to generate in milliseconds")
    safety_validated: bool = Field(True, description="Whether safety validation passed")
    regeneration_count: int = Field(0, description="Number of regeneration attempts")
    used_fallback_model: bool = Field(False, description="Whether fallback model was used")
    thinking: AgentThinking | None = Field(None, description="Agent thinking metadata")
    message_id: str = Field(..., description="The stored message ID")
    scammer_message_id: str | None = Field(None, description="The stored scammer message ID if provided")
    extracted_iocs: list[dict] = Field(default_factory=list, description="IOCs extracted from scammer message")


class ResponseValidationRequest(BaseModel):
    """Request model for response content validation."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="The edited response content to validate",
    )
    session_id: str = Field(..., description="The session ID for authorization context")
    message_id: str = Field(..., description="The message ID being edited")


class ResponseValidationResponse(BaseModel):
    """Response model for validation result."""

    is_safe: bool = Field(..., description="Whether the content passed safety checks")
    violations: list[str] = Field(
        default_factory=list, description="List of violation descriptions if unsafe"
    )


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

    # Handle scammer message if provided (multi-turn)
    scammer_message_id: str | None = None
    extracted_iocs: list[dict] = []

    if request.scammer_message:
        # Save the scammer message
        scammer_message_id = await session_service.add_scammer_message(
            session_id=request.session_id,
            content=request.scammer_message,
        )

        # Extract IOCs from scammer message
        intel_collector = IntelCollector()
        conversation_history = await session_service.get_conversation_history(request.session_id)
        message_index = len(conversation_history)
        extraction_result = intel_collector.extract(request.scammer_message, message_index)

        if extraction_result.has_iocs:
            extracted_iocs = [
                {
                    "type": ioc.ioc_type.value,
                    "value": ioc.value,
                    "context": ioc.context,
                    "is_high_value": ioc.is_high_value,
                }
                for ioc in extraction_result.iocs
            ]
            logger.info(
                "Extracted %d IOCs from scammer message in session %s",
                len(extracted_iocs),
                request.session_id,
            )

            # Persist IOCs to database
            await session_service.save_extracted_iocs(
                session_id=request.session_id,
                iocs=extracted_iocs,
            )

    # Fetch conversation history
    history_data = await session_service.get_conversation_history(request.session_id)
    conversation_history: list[ConversationMessage] = []

    for msg in history_data:
        sender_str = msg.get("sender", "")
        try:
            sender = MessageSender(sender_str)
            conversation_history.append(ConversationMessage(
                sender=sender,
                content=msg.get("content", ""),
            ))
        except ValueError:
            logger.warning("Unknown sender type: %s", sender_str)
            continue

    is_first_response = len(conversation_history) == 0

    # Generate response
    agent = ConversationAgent()

    try:
        result = await agent.generate_response(
            persona=persona,
            email_content=email_content,
            attack_type=attack_type,
            conversation_history=conversation_history if conversation_history else None,
            is_first_response=is_first_response,
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
            scammer_message_id=scammer_message_id,
            extracted_iocs=extracted_iocs,
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


@router.post(
    "/validate",
    response_model=ResponseValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate edited response content",
    description="Validates user-edited response content for safety violations. Used before saving edits.",
)
async def validate_response(
    request: ResponseValidationRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> ResponseValidationResponse:
    """
    Validate edited response content for safety violations.

    This endpoint is used when a user edits a generated response (US-008).
    The content is validated through the same safety layer used for
    generated responses to ensure no real PII is included.

    Args:
        request: The request body containing content to validate.
        user_id: The authenticated user's ID (from JWT).

    Returns:
        ResponseValidationResponse with safety status and any violations.

    Raises:
        HTTPException: If session not found or user not authorized.
    """
    # Load session to verify ownership
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

    # Validate the content through safety layer
    validator = OutputValidator()
    result = validator.validate(request.content)

    # Build violation descriptions for the frontend
    violation_descriptions = [
        f"{v.violation_type.value}: {v.description}" for v in result.violations
    ]

    # If content is safe, persist the changes to the database
    if result.is_safe:
        try:
            await session_service.update_message_content(
                message_id=request.message_id,
                new_content=request.content,
            )
            logger.info(
                "Saved edited message %s for session %s (user %s)",
                request.message_id,
                request.session_id,
                user_id,
            )
        except Exception as e:
            logger.error("Failed to save edited message: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save edited content",
            )
    else:
        logger.info(
            "Validated edited content for session %s (user %s): safe=%s, violations=%d",
            request.session_id,
            user_id,
            result.is_safe,
            len(result.violations),
        )

    return ResponseValidationResponse(
        is_safe=result.is_safe,
        violations=violation_descriptions,
    )
