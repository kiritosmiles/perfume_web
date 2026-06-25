"""Tests for Deep Mode Trigger Evaluation (Phase 4 optimization)."""

import pytest
from app.services.deep_trigger import (
    evaluate_deep_triggers,
    get_deep_trigger_description,
    TRIGGER_REFINEMENT_EXHAUSTED,
    TRIGGER_CROSS_STYLE,
    TRIGGER_COMPLEX_GIFT,
    TRIGGER_EMOTION_SCENE_CONFLICT,
    TRIGGER_USER_EXPLICIT,
)


# ── TestDeepTriggers ──────────────────────────────────────────────────────────

class TestDeepTriggers:
    """Test evaluate_deep_triggers() for all 5 trigger conditions."""

    def test_no_trigger_normal_case(self):
        """Normal self_use with no special conditions → no deep trigger."""
        should, reason = evaluate_deep_triggers(
            intent="self_use",
            diversity=0.0,
            refine_count=0,
        )
        assert should is False
        assert reason is None

    def test_refinement_exhausted_triggers_deep(self):
        """3+ refinements → deep trigger."""
        should, reason = evaluate_deep_triggers(refine_count=3)
        assert should is True
        assert reason == TRIGGER_REFINEMENT_EXHAUSTED

    def test_refinement_exhausted_at_4(self):
        """4 refinements should also trigger deep."""
        should, reason = evaluate_deep_triggers(refine_count=4)
        assert should is True
        assert reason == TRIGGER_REFINEMENT_EXHAUSTED

    def test_cross_style_jump_triggers_deep(self):
        """diversity >= 0.5 → cross-style exploration trigger."""
        should, reason = evaluate_deep_triggers(diversity=0.5)
        assert should is True
        assert reason == TRIGGER_CROSS_STYLE

    def test_cross_style_at_0_6(self):
        """diversity = 0.6 also triggers cross-style."""
        should, reason = evaluate_deep_triggers(diversity=0.6)
        assert should is True
        assert reason == TRIGGER_CROSS_STYLE

    def test_diversity_below_threshold_no_trigger(self):
        """diversity = 0.4 should not trigger cross-style."""
        should, reason = evaluate_deep_triggers(diversity=0.4)
        assert should is False or reason != TRIGGER_CROSS_STYLE

    def test_complex_gift_no_recipient_info(self):
        """Gift intent with no recipient info → deep trigger."""
        should, reason = evaluate_deep_triggers(
            intent="gift",
            recipient_info=None,
        )
        assert should is True
        assert reason == TRIGGER_COMPLEX_GIFT

    def test_complex_gift_sparse_tags(self):
        """Gift intent with < 1 recipient tag → deep trigger."""
        should, reason = evaluate_deep_triggers(
            intent="gift",
            recipient_info={"age_range": None, "relationship": None, "gender_pref": None},
        )
        assert should is True
        assert reason == TRIGGER_COMPLEX_GIFT

    def test_gift_with_sufficient_info_no_trigger(self):
        """Gift with 1+ recipient tag → no deep trigger from gift."""
        should, reason = evaluate_deep_triggers(
            intent="gift",
            recipient_info={"age_range": "25-35", "relationship": None, "gender_pref": None},
        )
        # age_range counts as 1 tag → should NOT trigger complex_gift
        assert not (should and reason == TRIGGER_COMPLEX_GIFT)

    def test_emotion_scene_conflict_anxiety_party(self):
        """Anxiety + party scene → deep trigger."""
        should, reason = evaluate_deep_triggers(
            emotion_vector={"anxiety": 0.6, "calm": 0.2, "joy": 0.1, "sadness": 0.05,
                            "excitement": 0.03, "nostalgia": 0.01, "romance": 0.01, "melancholy": 0.0},
            scene_tag="party",
        )
        assert should is True
        assert reason == TRIGGER_EMOTION_SCENE_CONFLICT

    def test_anxiety_work_is_conflict(self):
        """Anxiety + work scene → no conflict (work not in anxiety conflicts)."""
        should, reason = evaluate_deep_triggers(
            emotion_vector={"anxiety": 0.5, "calm": 0.3, "joy": 0.1, "sadness": 0.05,
                            "excitement": 0.03, "nostalgia": 0.01, "romance": 0.01, "melancholy": 0.0},
            scene_tag="work",
        )
        # work is NOT in EMOTION_SCENE_CONFLICTS["anxiety"] — only party/date
        assert should is False

    def test_anxiety_home_no_conflict(self):
        """Anxiety + home scene → no conflict (home not in anxiety conflicts)."""
        should, reason = evaluate_deep_triggers(
            emotion_vector={"anxiety": 0.5, "calm": 0.3, "joy": 0.1, "sadness": 0.05,
                            "excitement": 0.03, "nostalgia": 0.01, "romance": 0.01, "melancholy": 0.0},
            scene_tag="home",
        )
        assert should is False

    def test_no_emotion_vector_no_conflict(self):
        """No emotion vector → no conflict trigger (safe default)."""
        should, reason = evaluate_deep_triggers(
            emotion_vector=None,
            scene_tag="party",
        )
        assert should is False or reason != TRIGGER_EMOTION_SCENE_CONFLICT

    def test_user_explicit_triggers_deep(self):
        """User explicit request → deep trigger."""
        should, reason = evaluate_deep_triggers(user_requested_deep=True)
        assert should is True
        assert reason == TRIGGER_USER_EXPLICIT

    def test_user_explicit_overrides_other_triggers(self):
        """User explicit takes priority over all other triggers."""
        should, reason = evaluate_deep_triggers(
            user_requested_deep=True,
            diversity=0.5,
        )
        assert should is True
        assert reason == TRIGGER_USER_EXPLICIT


# ── TestTriggerDescriptions ───────────────────────────────────────────────────

class TestTriggerDescriptions:
    """Test get_deep_trigger_description() returns Chinese strings."""

    def test_all_descriptions_non_empty(self):
        """All known triggers have descriptions."""
        for trigger in [
            TRIGGER_REFINEMENT_EXHAUSTED,
            TRIGGER_CROSS_STYLE,
            TRIGGER_COMPLEX_GIFT,
            TRIGGER_EMOTION_SCENE_CONFLICT,
            TRIGGER_USER_EXPLICIT,
        ]:
            desc = get_deep_trigger_description(trigger)
            assert isinstance(desc, str)
            assert len(desc) > 0

    def test_unknown_trigger_returns_raw(self):
        """Unknown trigger returns the input string."""
        assert get_deep_trigger_description("unknown_xyz") == "unknown_xyz"
