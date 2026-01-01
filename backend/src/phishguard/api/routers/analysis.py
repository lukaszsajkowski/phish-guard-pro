import uuid
from fastapi import APIRouter, HTTPException, status
from phishguard.models.email import EmailAnalysisInput, EmailAnalysisResponse

router = APIRouter(prefix="/analysis", tags=["analysis"])

@router.post(
    "/",
    response_model=EmailAnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit phishing email for analysis",
    description="Accepts text content of a suspicious email and initiates the analysis process."
)
async def analyze_email(email_input: EmailAnalysisInput):
    """
    Initiates analysis of a suspicious email.
    
    Args:
        email_input: The email content request body.

    Returns:
        EmailAnalysisResponse containing the analysis ID and status.
    """
    # TODO: Integrate with LangGraph orchestrator
    # For now, we simulate a successful submission
    
    analysis_id = uuid.uuid4()
    
    return EmailAnalysisResponse(
        analysis_id=analysis_id,
        content_preview=email_input.content[:100],
        status="processing"
    )
