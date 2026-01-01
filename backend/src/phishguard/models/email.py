from pydantic import BaseModel, Field, constr
from typing import Optional
from uuid import UUID

class EmailAnalysisInput(BaseModel):
    """Input model for analyzing a suspicious email."""
    content: constr(min_length=10, max_length=50000) = Field( # type: ignore
        ..., 
        description="The full content of the suspicious email to analyze.",
        examples=["Subject: Urgent Account Update\n\nDear User..."]
    )

class EmailAnalysisResponse(BaseModel):
    """Response model for the initial email analysis."""
    analysis_id: UUID = Field(..., description="Unique ID for this analysis session.")
    content_preview: str = Field(..., description="Preview of the analyzed content (first 100 chars).")
    status: str = Field(..., description="Current status of the analysis.", examples=["pending", "processing", "completed"])
