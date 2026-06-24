"""User profile API — get/update profile, submit onboarding (FR-1.1, FR-1.2, FR-4.8)."""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.services.emotion import compute_value_dimensions
from app.services.profile import (
    get_user_profile,
    ensure_profile_exists,
    submit_onboarding,
    increment_conversation_count,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class OnboardingAnswer(BaseModel):
    question: int
    option: str
    mapped_vector: dict[str, float] | None = None
    mapped_tags: list[str] | None = None


class OnboardingInput(BaseModel):
    answers: list[OnboardingAnswer]


@router.get("/profile")
async def api_get_profile(current_user: dict = Depends(get_current_user)):
    """Return the current user's profile or a 200 with null for new users."""
    user_id = current_user["id"]
    await ensure_profile_exists(user_id)
    profile = await get_user_profile(user_id)
    profile_data = profile["profile_data"] if profile else None

    # Compute value dimensions from stored emotion tendency (FR-2.5)
    value_dimensions = None
    if profile_data and profile_data.get("emotion_tendency"):
        value_dimensions = compute_value_dimensions(profile_data["emotion_tendency"])

    return {
        "user_id": user_id,
        "profile": profile_data,
        "conversation_count": profile["conversation_count"] if profile else 0,
        "updated_at": profile["updated_at"] if profile else None,
        "value_dimensions": value_dimensions,
    }


@router.post("/profile/onboarding")
async def api_submit_onboarding(
    body: OnboardingInput,
    current_user: dict = Depends(get_current_user),
):
    """Process onboarding questionnaire answers, build initial profile."""
    user_id = current_user["id"]
    answers = [a.model_dump() for a in body.answers]
    profile = await submit_onboarding(user_id, answers)
    return {
        "user_id": user_id,
        "profile": profile,
    }
