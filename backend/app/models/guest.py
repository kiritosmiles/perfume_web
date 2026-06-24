from pydantic import BaseModel, model_validator
from typing import Literal

VALID_CARD_IDS = {"joy", "sadness", "anxiety", "calm", "excitement", "nostalgia", "romance", "melancholy"}
VALID_INTENTS = {"self_use", "gift", "explore"}


class GuestSessionInput(BaseModel):
    emotion_card_ids: list[str]
    scene_tag: str | None = None
    browser_id: str | None = None
    user_text: str | None = None
    allergens: list[str] | None = None
    refine: str | None = None
    gate_answer: str | None = None
    intent: Literal["self_use", "gift", "explore"] = "self_use"
    # ── Environment perception (FR-2.8, all optional, backward-compatible) ──
    season: str | None = None  # spring|summer|autumn|winter
    time_of_day: str | None = None  # morning|afternoon|evening|night
    weather_code: int | None = None  # WMO weather code
    temperature: float | None = None  # Celsius
    diversity: float = 0.0  # FR-3.8: 0-1 diversity control

    @model_validator(mode="after")
    def validate_has_input(self):
        """At least one of emotion_card_ids or user_text must be provided."""
        has_cards = bool(self.emotion_card_ids)
        has_text = bool(self.user_text and self.user_text.strip())
        if not has_cards and not has_text:
            raise ValueError("At least one of emotion_card_ids or user_text is required")
        return self

    @model_validator(mode="after")
    def validate_card_ids(self):
        """If card IDs provided, validate them."""
        if self.emotion_card_ids:
            if len(self.emotion_card_ids) > 2:
                raise ValueError("emotion_card_ids must contain 1-2 card ids")
            invalid = [cid for cid in self.emotion_card_ids if cid not in VALID_CARD_IDS]
            if invalid:
                raise ValueError(f"Invalid card id(s): {', '.join(invalid)}. Valid: {', '.join(sorted(VALID_CARD_IDS))}")
            # If user_text also provided and cards empty, ensure cards are valid
            if len(self.emotion_card_ids) < 1 and not (self.user_text and self.user_text.strip()):
                raise ValueError("emotion_card_ids must contain at least 1 card id when no user_text")
        return self
