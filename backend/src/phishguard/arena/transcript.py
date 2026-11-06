"""Transcript message type for Arena conversations."""

from typing import Literal

from pydantic import BaseModel


class Message(BaseModel):
    """One message in an Arena transcript.

    Turn 0 is the victim's first reply to the email; turn n >= 1 holds scammer
    message n and the victim reply n.
    """

    sender: Literal["scammer", "victim"]
    content: str
    turn: int
