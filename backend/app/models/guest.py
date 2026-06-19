from pydantic import BaseModel, field_validator

VALID_CARD_IDS = {"joy", "sadness", "anxiety", "calm", "excitement", "nostalgia", "romance", "melancholy"}


class GuestSessionInput(BaseModel):
    emotion_card_ids: list[str]
    scene_tag: str | None = None
    browser_id: str | None = None

    @field_validator("emotion_card_ids")
    @classmethod
    def validate_card_ids(cls, v: list[str]) -> list[str]:
        if len(v) < 1 or len(v) > 2:
            raise ValueError("emotion_card_ids must contain 1-2 card ids")
        invalid = [cid for cid in v if cid not in VALID_CARD_IDS]
        if invalid:
            raise ValueError(f"Invalid card id(s): {', '.join(invalid)}. Valid: {', '.join(sorted(VALID_CARD_IDS))}")
        return v
