"""Emotion Journal API — trend data and weekly journals (FR-4.9)."""

import logging

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.services.journal import get_emotion_trend, get_weekly_journal

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/journal/trend")
async def api_get_emotion_trend(
    days: int = Query(default=30, ge=7, le=90),
    current_user: dict = Depends(get_current_user),
):
    """Return daily emotion trend data from L3 memory for the last N days.

    Each entry: {date, primary_emotion, emotion_scores, keywords, summary_text}
    """
    user_id = current_user["id"]
    trend = await get_emotion_trend(user_id, days=days)
    return {
        "user_id": user_id,
        "days": days,
        "count": len(trend),
        "data": trend,
    }


@router.get("/journal/weekly")
async def api_get_weekly_journal(
    week_start: str = Query(default=""),
    current_user: dict = Depends(get_current_user),
):
    """Return a weekly journal for the given week (or most recent completed week).

    Query params:
        week_start: ISO date (YYYY-MM-DD) for Monday of the target week.
                    If empty, defaults to the most recent completed week.
    """
    user_id = current_user["id"]
    ws = week_start if week_start else None
    journal = await get_weekly_journal(user_id, week_start=ws)
    return {
        "user_id": user_id,
        **journal,
    }
