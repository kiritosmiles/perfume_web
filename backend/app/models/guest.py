from pydantic import BaseModel


class GuestSessionInput(BaseModel):
    emotion_card_ids: list[str]  # 1-2 card ids
    scene_tag: str | None = None
    browser_id: str | None = None
