"""User configuration endpoints — LLM API key management."""

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.redis import store_llm_key, get_llm_key

logger = logging.getLogger(__name__)
router = APIRouter()


class LLMKeyInput(BaseModel):
    browser_id: str = Field(..., min_length=1, max_length=128)
    api_key: str = Field(..., min_length=1, max_length=256)
    base_url: str | None = Field(default=None, max_length=512)


@router.post("/config/llm-key")
async def save_llm_key(input_data: LLMKeyInput):
    """Store user-provided LLM API key in Redis (24h TTL)."""
    try:
        await store_llm_key(
            input_data.browser_id,
            input_data.api_key,
            input_data.base_url,
        )
        logger.info("LLM key stored for browser %s", input_data.browser_id[:8])
        return {"status": "ok", "message": "API key saved. Valid for 24 hours."}
    except Exception as e:
        logger.error("Failed to store LLM key: %s", e)
        raise HTTPException(status_code=500, detail="Failed to save API key")


@router.get("/config/llm-key/status")
async def check_llm_key_status(browser_id: str = Query(..., min_length=1)):
    """Check if a user has configured their LLM API key."""
    key_data = await get_llm_key(browser_id)
    return {"configured": key_data is not None}
