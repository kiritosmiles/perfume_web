"""Tests for intent detection service."""

import pytest
from app.services.intent import detect_intent, _keyword_detect, is_guest_intent_allowed


class TestKeywordDetect:
    def test_gift_keyword_detected(self):
        result = _keyword_detect("送给女朋友的礼物")
        assert result is not None
        assert result["intent"] == "gift"
        assert result["confidence"] == 1.0
        assert result["source"] == "keyword"

    def test_self_use_keyword_detected(self):
        result = _keyword_detect("给自己买一瓶香水")
        assert result is not None
        assert result["intent"] == "self_use"
        assert result["confidence"] == 1.0

    def test_explore_keyword_detected(self):
        result = _keyword_detect("我就随便看看有什么好闻的")
        assert result is not None
        assert result["intent"] == "explore"
        assert result["confidence"] == 1.0

    def test_no_keyword_match_returns_none(self):
        result = _keyword_detect("今天天气不错")
        assert result is None

    def test_gift_keyword_prioritized(self):
        result = _keyword_detect("给自己买个礼物送人")  # "礼物" comes before "给自己" in keyword list
        assert result is not None
        assert result["intent"] == "gift"


class TestDetectIntent:
    @pytest.mark.asyncio
    async def test_defaults_to_self_use_without_text(self):
        result = await detect_intent(user_text=None, user_toggle="self_use")
        assert result["intent"] == "self_use"
        assert result["source"] == "default"

    @pytest.mark.asyncio
    async def test_user_toggle_overrides(self):
        result = await detect_intent(user_text="随便看看", user_toggle="gift")
        assert result["intent"] == "gift"
        assert result["source"] == "user_toggle"
        assert result["confidence"] == 1.0

    @pytest.mark.asyncio
    async def test_keyword_from_text(self):
        result = await detect_intent(user_text="想送给朋友的礼物", user_toggle="self_use")
        assert result["intent"] == "gift"
        assert result["source"] == "keyword"

    @pytest.mark.asyncio
    async def test_no_text_no_toggle_defaults_self(self):
        result = await detect_intent(user_text="", user_toggle="self_use")
        assert result["intent"] == "self_use"
        assert result["source"] == "default"


class TestGuestIntent:
    def test_guest_self_use_allowed(self):
        assert is_guest_intent_allowed("self_use") is True

    def test_guest_gift_not_allowed(self):
        assert is_guest_intent_allowed("gift") is False

    def test_guest_explore_not_allowed(self):
        assert is_guest_intent_allowed("explore") is False
