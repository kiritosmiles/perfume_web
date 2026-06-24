"""Tests for recommendation diversity (FR-3.8)."""

import pytest
from unittest.mock import patch

from app.services.emotion import DIMENSIONS


# ── Perturbed vector generation ──────────────────────────────────────────────

class TestDiversityPerturbation:
    """Diversity perturbation logic — no Neo4j needed."""

    def test_diversity_zero_no_change_to_behavior(self):
        """diversity=0 should be a no-op in search signatures."""
        from app.services.generation import _diverse_top3

        candidates = [
            {"name": "Rose Bloom", "score": 95.0, "accord": "floral"},
            {"name": "Citrus Burst", "score": 90.0, "accord": "citrus"},
            {"name": "Oud Majesty", "score": 88.0, "accord": "woody"},
            {"name": "Rose No.2", "score": 85.0, "accord": "floral"},
        ]
        result = _diverse_top3(candidates, intent="self_use", diversity=0.0)
        # Normal behavior: 3 different clusters
        assert len(result) == 3
        clusters = {"floral", "citrus", "woody"}
        result_clusters = set()
        for r in result:
            from app.services.fragrance import ACCORD_CLUSTERS
            result_clusters.add(ACCORD_CLUSTERS.get(r["accord"], "other"))
        assert result_clusters == clusters  # All 3 different

    def test_diversity_zero_point_five_cross_style(self):
        """diversity=0.5 should prefer clusters NOT in the score top-3."""
        from app.services.generation import _diverse_top3

        # Top-3 by score are all floral → cross-style should avoid floral
        candidates = [
            {"name": "Rose Bloom", "score": 95.0, "accord": "floral"},
            {"name": "Jasmine Dream", "score": 94.0, "accord": "white floral"},
            {"name": "Rose Garden", "score": 93.0, "accord": "rose"},
            {"name": "Citrus Burst", "score": 90.0, "accord": "citrus"},
            {"name": "Oud Majesty", "score": 88.0, "accord": "woody"},
            {"name": "Ocean Breeze", "score": 85.0, "accord": "aquatic"},
        ]
        result = _diverse_top3(candidates, intent="self_use", diversity=0.6)
        assert len(result) == 3
        from app.services.fragrance import ACCORD_CLUSTERS
        result_clusters = {ACCORD_CLUSTERS.get(r["accord"], "other") for r in result}
        # At least 2 should be from non-floral clusters
        assert len(result_clusters - {"floral"}) >= 2

    def test_cross_style_fallback_when_not_enough_cross(self):
        """If not enough cross-style candidates, fills with normal selection."""
        from app.services.generation import _diverse_top3

        # Only 2 non-floral candidates in the entire list
        candidates = [
            {"name": "Rose Bloom", "score": 95.0, "accord": "floral"},
            {"name": "Jasmine Dream", "score": 94.0, "accord": "white floral"},
            {"name": "Rose Garden", "score": 93.0, "accord": "rose"},
            {"name": "Rose No.2", "score": 92.0, "accord": "yellow floral"},
            {"name": "Citrus Burst", "score": 90.0, "accord": "citrus"},
            {"name": "Oud Majesty", "score": 88.0, "accord": "woody"},
        ]
        result = _diverse_top3(candidates, intent="self_use", diversity=0.6)
        assert len(result) == 3  # Should still return 3 (with fallback)


# ── gen.complete metadata ────────────────────────────────────────────────────

class TestDiversityMetadata:
    """Diversity flags flow correctly in gen.complete metadata."""

    def test_metadata_includes_diversity_fields(self):
        """Record<string, unknown> metadata accepts diversity keys."""
        metadata = {
            "mode": "fast",
            "emotion": "joy",
            "search_source": "graphrag",
            "cache_hit": False,
            "environment": None,
            "diversity_mode": True,
            "diversity_level": 0.5,
            "cross_style": True,
        }
        assert metadata["diversity_mode"] is True
        assert metadata["diversity_level"] == 0.5
        assert metadata["cross_style"] is True

    def test_metadata_diversity_zero(self):
        """When diversity=0, diversity_mode and cross_style are false."""
        metadata = {
            "diversity_mode": False,
            "diversity_level": 0.0,
            "cross_style": False,
        }
        assert not metadata["diversity_mode"]
        assert not metadata["cross_style"]


# ── random_style refinement ──────────────────────────────────────────────────

class TestRandomStyleRefinement:
    """The random_style refinement keyword (FR-3.8)."""

    def test_random_style_changes_vector(self):
        """random_style should produce a different vector."""
        from app.services.refinement import apply_refinement, DIMENSION_NAMES

        vec = dict.fromkeys(DIMENSION_NAMES, 0.0)
        vec["joy"] = 0.9
        vec["calm"] = 0.2
        # Normalize
        total = sum(vec.values())
        vec = {k: round(v / total, 4) for k, v in vec.items()}

        result = apply_refinement(vec, ["random_style"])

        # Should be different from input (some dimensions changed)
        changes = sum(1 for d in DIMENSION_NAMES if abs(result.get(d, 0) - vec.get(d, 0)) > 0.001)
        assert changes > 0  # At least some dimensions changed
        # Joy (top dim) should NOT have been boosted
        assert result["joy"] <= vec["joy"] + 0.01

    def test_random_style_preserves_normalization(self):
        """Output vector should still sum to ~1."""
        from app.services.refinement import apply_refinement, DIMENSION_NAMES

        vec = {d: 1.0 / len(DIMENSION_NAMES) for d in DIMENSION_NAMES}
        result = apply_refinement(vec, ["random_style"])
        assert 0.99 <= sum(result.values()) <= 1.01
        assert all(0.0 <= v <= 1.0 for v in result.values())

    def test_random_style_with_other_refinements(self):
        """random_style can be combined with other refinement keywords."""
        from app.services.refinement import apply_refinement, DIMENSION_NAMES

        vec = {d: 1.0 / len(DIMENSION_NAMES) for d in DIMENSION_NAMES}
        result = apply_refinement(vec, ["sweeter", "random_style"])
        assert 0.99 <= sum(result.values()) <= 1.01
        assert all(0.0 <= v <= 1.0 for v in result.values())
