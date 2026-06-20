from pydantic import BaseModel, model_validator

VALID_CARD_IDS = {"joy", "sadness", "anxiety", "calm", "excitement", "nostalgia", "romance", "melancholy"}


class GuestSessionInput(BaseModel):
    emotion_card_ids: list[str]
    scene_tag: str | None = None
    browser_id: str | None = None
    user_text: str | None = None

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
