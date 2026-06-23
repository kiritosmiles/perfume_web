"""Feedback Pydantic models for explicit and implicit feedback events."""

from pydantic import BaseModel, Field
from typing import Literal


class ExplicitFeedbackInput(BaseModel):
    generation_id: str
    card_rank: int = Field(ge=1, le=3, description="Card rank 1-3")
    reaction: Literal["like", "dislike"]
    reason: str | None = Field(default=None, max_length=200)


class ImplicitEvent(BaseModel):
    event_name: str = Field(min_length=1, max_length=64)
    payload: dict = Field(default_factory=dict)
    timestamp: str | None = None  # ISO 8601 client time


class ImplicitFeedbackInput(BaseModel):
    generation_id: str | None = None
    events: list[ImplicitEvent] = Field(min_length=1, max_length=50)
