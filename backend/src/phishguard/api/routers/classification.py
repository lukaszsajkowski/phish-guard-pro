from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from phishguard.agents.profiler import ProfilerAgent, ClassificationError
from phishguard.models.classification import ClassificationResult

router = APIRouter(prefix="/classification", tags=["classification"])

class ClassificationRequest(BaseModel):
    email_content: str

@router.post(
    "/analyze",
    response_model=ClassificationResult,
    status_code=status.HTTP_200_OK,
    summary="Classify phishing email attack type",
    description="Analyzes email content and returns the detected attack type with confidence score."
)
async def classify_email(request: ClassificationRequest) -> ClassificationResult:
    """
    Classify a phishing email.

    Args:
        request: The request body containing email content.

    Returns:
        ClassificationResult with attack type and confidence.
    
    Raises:
        HTTPException: If classification fails.
    """
    agent = ProfilerAgent()
    try:
        result = await agent.classify(request.email_content)
        return result
    except ClassificationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
