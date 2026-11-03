"""Models for the Basal in-role check (US-050)."""

from pydantic import BaseModel, Field

IN_ROLE_WARNING_MESSAGE = (
    "This reply may break the persona's role. Review it before sending."
)


class InRoleWarning(BaseModel):
    """Advisory warning that a reply may break the persona's role.

    Attributes:
        message: Human-readable warning text.
        confidence: Basal confidence for the ``breaks_role`` answer (0-1).
    """

    message: str
    confidence: float = Field(..., ge=0.0, le=1.0)
