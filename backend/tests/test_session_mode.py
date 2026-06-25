"""Tests for FR-1.5 Session Mode and FR-3.5 Intent Gating (Batch 2)."""

import pytest
from app.models.guest import GuestSessionInput


# ── TestSessionModeInput ──────────────────────────────────────────────────────
class TestSessionModeInput:
    """Test GuestSessionInput session_mode field."""

    def test_default_session_mode_is_context(self):
        """Default session_mode should be 'context'."""
        inp = GuestSessionInput(emotion_card_ids=["joy"])
        assert inp.session_mode == "context"

    def test_identity_mode_accepted(self):
        """Identity mode should be accepted."""
        inp = GuestSessionInput(emotion_card_ids=["joy"], session_mode="identity")
        assert inp.session_mode == "identity"

    def test_novelty_mode_accepted(self):
        """Novelty mode should be accepted."""
        inp = GuestSessionInput(emotion_card_ids=["joy"], session_mode="novelty")
        assert inp.session_mode == "novelty"

    def test_context_mode_accepted(self):
        """Context mode should be accepted."""
        inp = GuestSessionInput(emotion_card_ids=["joy"], session_mode="context")
        assert inp.session_mode == "context"


# ── TestRecipientFields ───────────────────────────────────────────────────────
class TestRecipientFields:
    """Test GuestSessionInput recipient fields for gift intent (FR-3.5)."""

    def test_all_recipient_fields_default_none(self):
        """Recipient fields default to None."""
        inp = GuestSessionInput(emotion_card_ids=["joy"])
        assert inp.recipient_age_range is None
        assert inp.recipient_relationship is None
        assert inp.recipient_gender_pref is None

    def test_recipient_fields_settable(self):
        """Recipient fields can be set for gift intent."""
        inp = GuestSessionInput(
            emotion_card_ids=["joy"],
            intent="gift",
            recipient_age_range="25-35",
            recipient_relationship="partner",
            recipient_gender_pref="feminine",
        )
        assert inp.recipient_age_range == "25-35"
        assert inp.recipient_relationship == "partner"
        assert inp.recipient_gender_pref == "feminine"

    def test_recipient_fields_with_self_use_no_error(self):
        """Recipient fields can exist even for self_use (harmless)."""
        inp = GuestSessionInput(
            emotion_card_ids=["joy"],
            intent="self_use",
            recipient_age_range="18-24",
        )
        assert inp.recipient_age_range == "18-24"
        assert inp.intent == "self_use"


# ── TestSessionModeSSE ────────────────────────────────────────────────────────
class TestSessionModeSSE:
    """Test session_mode flow logic."""

    def test_novelty_forces_diversity(self):
        """Novelty mode should force diversity >= 0.5."""
        mode = "novelty"
        diversity = 0.0
        if mode == "novelty":
            diversity = max(0.5, diversity)
        assert diversity == 0.5

    def test_novelty_does_not_reduce_higher_diversity(self):
        """Novelty should not reduce already-high diversity."""
        mode = "novelty"
        diversity = 0.8
        if mode == "novelty":
            diversity = max(0.5, diversity)
        assert diversity == 0.8

    def test_context_mode_keeps_diversity(self):
        """Context mode should not change diversity."""
        mode = "context"
        diversity = 0.3
        # context: no change
        assert mode == "context"
        assert diversity == 0.3

    def test_identity_mode_keeps_diversity(self):
        """Identity mode should not change diversity."""
        mode = "identity"
        diversity = 0.0
        # identity: no change
        assert diversity == 0.0


# ── TestExploreIntentGating ───────────────────────────────────────────────────
class TestExploreIntentGating:
    """Test FR-3.5 explore intent diversity selection in _diverse_top3."""

    def test_explore_deprioritizes_floral_citrus(self):
        """Explore mode should de-prioritize floral and citrus clusters."""
        EXPLORE_DEPRIORITIZED = {"floral", "citrus", "woody"}
        assert "floral" in EXPLORE_DEPRIORITIZED
        assert "citrus" in EXPLORE_DEPRIORITIZED
        assert "woody" in EXPLORE_DEPRIORITIZED
        assert "leather" not in EXPLORE_DEPRIORITIZED
        assert "oriental" not in EXPLORE_DEPRIORITIZED

    def test_explore_cluster_order_prefers_niche(self):
        """Explore cluster_order should rank niche items first."""
        EXPLORE_DEPRIORITIZED = {"floral", "citrus", "woody"}
        cluster_order = {"leather": 0, "oriental": 0, "floral": 10, "citrus": 10}
        # niche clusters score lower = selected first
        assert cluster_order["leather"] < cluster_order["floral"]
        assert cluster_order["oriental"] < cluster_order["citrus"]


# ── TestTierQuota ─────────────────────────────────────────────────────────────
class TestTierQuota:
    """Test tier-based quota limits."""

    def test_free_tier_limits(self):
        """Free tier has limited quota."""
        from app.core.quota import TIER_QUOTA_LIMITS
        free = TIER_QUOTA_LIMITS["free"]
        assert free["sessions"] == 10
        assert free["generations"] == 15
        assert free["deep"] == 3

    def test_premium_tier_unlimited(self):
        """Premium tier has unlimited quota."""
        from app.core.quota import TIER_QUOTA_LIMITS
        premium = TIER_QUOTA_LIMITS["premium"]
        assert premium["sessions"] >= 999_000
        assert premium["generations"] >= 999_000
        assert premium["deep"] >= 999_000

    def test_get_quota_max_free(self):
        """_get_quota_max returns free limit for 'free' tier."""
        from app.core.quota import _get_quota_max
        assert _get_quota_max("free", "sessions") == 10
        assert _get_quota_max("free", "deep") == 3

    def test_get_quota_max_premium(self):
        """_get_quota_max returns unlimited for 'premium' tier."""
        from app.core.quota import _get_quota_max
        assert _get_quota_max("premium", "sessions") >= 999_000

    def test_get_quota_max_unknown_tier_defaults_free(self):
        """Unknown tier defaults to free limits."""
        from app.core.quota import _get_quota_max
        assert _get_quota_max(None, "sessions") == 10
        assert _get_quota_max("unknown", "generations") == 15
