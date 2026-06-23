"""Tests for Agent Gate (FR-5.11) — information completeness check."""

import pytest
from app.services.agent_gate import (
    _rule_based_verdict,
    _fallback_questions,
    agent_gate_check,
    GATE_TIMEOUT,
)


class TestRuleBasedVerdict:
    """Fast-path rule-based verdict logic (<1ms, no I/O)."""

    def test_self_use_sufficient_with_emotion_and_scene(self):
        verdict = _rule_based_verdict(
            intent="self_use",
            has_emotion=True,
            has_scene=True,
            graphrag_count=10,
            has_user_text=True,
            user_text_length=20,
        )
        assert verdict == "sufficient"

    def test_self_use_sufficient_with_emotion_and_long_text(self):
        verdict = _rule_based_verdict(
            intent="self_use",
            has_emotion=True,
            has_scene=False,
            graphrag_count=8,
            has_user_text=True,
            user_text_length=15,
        )
        assert verdict == "sufficient"

    def test_self_use_partial_with_emotion_only(self):
        verdict = _rule_based_verdict(
            intent="self_use",
            has_emotion=True,
            has_scene=False,
            graphrag_count=3,
            has_user_text=False,
            user_text_length=0,
        )
        assert verdict == "partial"

    def test_self_use_insufficient_without_emotion(self):
        verdict = _rule_based_verdict(
            intent="self_use",
            has_emotion=False,
            has_scene=False,
            graphrag_count=0,
            has_user_text=False,
            user_text_length=0,
        )
        assert verdict == "insufficient"

    def test_gift_sufficient_with_emotion_scene_and_candidates(self):
        verdict = _rule_based_verdict(
            intent="gift",
            has_emotion=True,
            has_scene=True,
            graphrag_count=10,
            has_user_text=True,
            user_text_length=30,
        )
        assert verdict == "sufficient"

    def test_gift_without_scene_is_insufficient(self):
        """Gift without scene tag is insufficient even with emotion + text."""
        verdict = _rule_based_verdict(
            intent="gift",
            has_emotion=True,
            has_scene=False,
            graphrag_count=10,
            has_user_text=True,
            user_text_length=20,
        )
        assert verdict == "insufficient"

    def test_gift_partial_with_scene_but_low_candidates(self):
        """Gift with emotion and scene but low candidate count is partial."""
        verdict = _rule_based_verdict(
            intent="gift",
            has_emotion=True,
            has_scene=True,
            graphrag_count=2,
            has_user_text=True,
            user_text_length=20,
        )
        assert verdict == "partial"

    def test_gift_insufficient_without_emotion(self):
        verdict = _rule_based_verdict(
            intent="gift",
            has_emotion=False,
            has_scene=False,
            graphrag_count=0,
            has_user_text=False,
            user_text_length=0,
        )
        assert verdict == "insufficient"

    def test_explore_always_sufficient(self):
        verdict = _rule_based_verdict(
            intent="explore",
            has_emotion=False,
            has_scene=False,
            graphrag_count=0,
            has_user_text=False,
            user_text_length=0,
        )
        assert verdict == "sufficient"

    def test_refine_skips_gate(self):
        verdict = _rule_based_verdict(
            intent="gift",
            has_emotion=False,
            has_scene=False,
            graphrag_count=0,
            has_user_text=False,
            refine_count=1,
        )
        assert verdict == "sufficient"

    def test_gate_answer_skips_gate(self):
        verdict = _rule_based_verdict(
            intent="gift",
            has_emotion=False,
            has_scene=False,
            graphrag_count=0,
            has_user_text=False,
            has_gate_answer=True,
        )
        assert verdict == "sufficient"

    def test_self_use_partial_low_graphrag(self):
        verdict = _rule_based_verdict(
            intent="self_use",
            has_emotion=True,
            has_scene=True,
            graphrag_count=2,  # below threshold
            has_user_text=True,
            user_text_length=20,
        )
        assert verdict == "partial"


class TestFallbackQuestions:
    """Fallback question generation when LLM is unavailable."""

    def test_gift_fallback_questions_count(self):
        questions = _fallback_questions("gift", "喜悦")
        assert 1 <= len(questions) <= 3

    def test_gift_fallback_questions_non_empty(self):
        questions = _fallback_questions("gift", "浪漫")
        for q in questions:
            assert len(q) > 0

    def test_self_use_fallback_questions(self):
        questions = _fallback_questions("self_use", "平静")
        assert len(questions) >= 1


class TestAgentGateCheck:
    """Integration-level gate check (fast path only; no LLM for tests)."""

    @pytest.mark.asyncio
    async def test_sufficient_returns_bypassed(self):
        result = await agent_gate_check(
            intent="self_use",
            emotion_cn="喜悦",
            has_scene=True,
            graphrag_candidates=10,
            user_text="今天心情很好，想找一款清新的香水",
            refine_count=0,
            gate_answer=None,
            api_key_override=None,  # No LLM key → fast path only
            base_url_override=None,
        )
        assert result["verdict"] == "sufficient"
        assert result["bypassed"] is True
        assert result["questions"] is None

    @pytest.mark.asyncio
    async def test_explore_always_sufficient(self):
        result = await agent_gate_check(
            intent="explore",
            emotion_cn="",
            has_scene=False,
            graphrag_candidates=0,
            user_text=None,
        )
        assert result["verdict"] == "sufficient"

    @pytest.mark.asyncio
    async def test_insufficient_returns_questions(self):
        result = await agent_gate_check(
            intent="gift",
            emotion_cn="",
            has_scene=False,
            graphrag_candidates=0,
            user_text=None,
            api_key_override=None,  # No LLM key → fallback questions
        )
        assert result["verdict"] == "insufficient"
        assert result["bypassed"] is False
        assert result["questions"] is not None
        assert 1 <= len(result["questions"]) <= 3
        assert result["hint"] is not None

    @pytest.mark.asyncio
    async def test_latency_reported(self):
        result = await agent_gate_check(
            intent="self_use",
            emotion_cn="喜悦",
            has_scene=True,
            graphrag_candidates=10,
        )
        assert "latency_ms" in result
        assert result["latency_ms"] >= 0
        # Should be well under 500ms for rule-based path (<5ms in practice)
        assert result["latency_ms"] < 500

    @pytest.mark.asyncio
    async def test_gate_answer_bypasses(self):
        result = await agent_gate_check(
            intent="gift",
            emotion_cn="",
            has_scene=False,
            graphrag_candidates=0,
            user_text=None,
            gate_answer="skip",
        )
        assert result["verdict"] == "sufficient"
        assert result["bypassed"] is True

    @pytest.mark.asyncio
    async def test_refine_bypasses(self):
        result = await agent_gate_check(
            intent="gift",
            emotion_cn="",
            has_scene=False,
            graphrag_candidates=0,
            user_text=None,
            refine_count=1,
        )
        assert result["verdict"] == "sufficient"
