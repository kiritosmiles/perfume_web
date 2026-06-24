"""Tests for emotion resolution and value dimension mapping (FR-2.5)."""

import pytest
from app.services.emotion import (
    compute_value_dimensions,
    resolve_emotion_from_cards,
    VALUE_DIMENSION_KEYS,
    DIMENSIONS,
)
from app.models.guest import GuestSessionInput


class TestValueDimensions:
    """FR-2.5: 8-dim emotion → 6-dim value space mapping."""

    def test_pure_joy_yields_high_pleasure(self):
        """Joy-dominant vector should score high on pleasure, aesthetic, social."""
        vec = dict.fromkeys(DIMENSIONS, 0.0)
        vec["joy"] = 1.0
        vd = compute_value_dimensions(vec)
        assert vd["pleasure"] > 0.3
        assert vd["social"] > 0.3
        assert vd["aesthetic"] > 0.2

    def test_pure_sadness_yields_low_pleasure(self):
        """Sadness-dominant vector should score low on pleasure."""
        vec = dict.fromkeys(DIMENSIONS, 0.0)
        vec["sadness"] = 1.0
        vd = compute_value_dimensions(vec)
        assert vd["pleasure"] == 0.0  # floor at 0 after clamp
        assert vd["nostalgia"] >= 0  # melancholy * 0.5 contributes, but melancholy=0 here

    def test_output_keys_and_range(self):
        """All 6 value dimensions present and values in [0, 1]."""
        vec = {
            "joy": 0.5, "sadness": 0.1, "anxiety": 0.2, "calm": 0.4,
            "excitement": 0.6, "nostalgia": 0.3, "romance": 0.7, "melancholy": 0.1,
        }
        vd = compute_value_dimensions(vec)
        assert set(vd.keys()) == set(VALUE_DIMENSION_KEYS)
        for val in vd.values():
            assert 0.0 <= val <= 1.0

    def test_missing_dimensions_default_to_zero(self):
        """Partial vectors should not crash — missing dims default to 0."""
        vec = {"joy": 0.8}
        vd = compute_value_dimensions(vec)
        assert set(vd.keys()) == set(VALUE_DIMENSION_KEYS)

    def test_high_nostalgia_melancholy(self):
        """nostalgia + melancholy combo should yield high nostalgia value."""
        vec = dict.fromkeys(DIMENSIONS, 0.0)
        vec["nostalgia"] = 1.0
        vec["melancholy"] = 1.0
        vd = compute_value_dimensions(vec)
        assert vd["nostalgia"] > 0.7  # 1.0 + 0.5*1.0 + 0 = 1.5 → clamp to 1.0

    def test_excitement_anxiety_yields_high_activation(self):
        """Excitement + anxiety should drive activation up."""
        vec = dict.fromkeys(DIMENSIONS, 0.0)
        vec["excitement"] = 1.0
        vec["anxiety"] = 1.0
        vd = compute_value_dimensions(vec)
        assert vd["activation"] > 0.7  # (1+1-0-0)/2 = 1.0

    def test_resolve_emotion_from_cards_includes_value_dims(self):
        """Integration: resolve_emotion_from_cards returns value_dimensions."""
        inp = GuestSessionInput(emotion_card_ids=["joy"])
        result = resolve_emotion_from_cards(inp)
        assert "value_dimensions" in result
        vd = result["value_dimensions"]
        assert len(vd) == 6
        assert set(vd.keys()) == set(VALUE_DIMENSION_KEYS)
        assert vd["pleasure"] > 0  # joy card should yield positive pleasure
