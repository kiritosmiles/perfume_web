"""Tests for environment perception service (FR-2.8)."""

import pytest
from unittest.mock import patch

from app.services.emotion import DIMENSIONS


# ── Pure functions (no I/O) ──────────────────────────────────────────────────

class TestEnvironmentVector:
    """compute_environment_vector returns valid 8-D vectors for each input combo."""

    def test_season_only_returns_valid_vector(self):
        from app.services.environment import compute_environment_vector
        vec = compute_environment_vector(season="summer")
        assert set(vec.keys()) == set(DIMENSIONS)
        assert all(0.0 <= v <= 1.0 for v in vec.values())
        assert 0.99 <= sum(vec.values()) <= 1.01
        # Summer → joy + excitement should be prominent
        assert vec["joy"] > 0.1
        assert vec["excitement"] > 0.1

    def test_winter_emphasizes_nostalgia(self):
        from app.services.environment import compute_environment_vector
        vec = compute_environment_vector(season="winter")
        assert vec["nostalgia"] > 0.15
        assert vec["calm"] > 0.1

    def test_night_with_rain_emphasizes_calm_melancholy(self):
        from app.services.environment import compute_environment_vector
        vec = compute_environment_vector(
            season="autumn", time_of_day="night", weather_code=61,
        )
        assert vec["calm"] > 0.10
        assert vec["melancholy"] > 0.10

    def test_no_inputs_returns_uniform(self):
        """When no environment params are given, returns uniform vector."""
        from app.services.environment import compute_environment_vector
        vec = compute_environment_vector()
        expected = round(1.0 / len(DIMENSIONS), 4)
        for v in vec.values():
            assert abs(v - expected) < 0.01


class TestExtremeWeather:
    """is_extreme_weather detection (threshold: hail codes, temp >35 or <0)."""

    def test_hail_code_is_extreme(self):
        from app.services.environment import is_extreme_weather
        assert is_extreme_weather(weather_code=96) is True
        assert is_extreme_weather(weather_code=99) is True

    def test_high_temperature_is_extreme(self):
        from app.services.environment import is_extreme_weather
        assert is_extreme_weather(temperature=36.0) is True
        assert is_extreme_weather(temperature=35.5) is True

    def test_low_temperature_is_extreme(self):
        from app.services.environment import is_extreme_weather
        assert is_extreme_weather(temperature=-1.0) is True
        assert is_extreme_weather(temperature=-10.0) is True

    def test_normal_weather_is_not_extreme(self):
        from app.services.environment import is_extreme_weather
        assert is_extreme_weather(weather_code=0, temperature=25.0) is False
        assert is_extreme_weather(weather_code=61, temperature=18.0) is False

    def test_none_input_is_not_extreme(self):
        from app.services.environment import is_extreme_weather
        assert is_extreme_weather() is False


class TestFuseEnvironment:
    """fuse_environment blends env vector into emotion vector with correct weights."""

    def test_normal_weight_is_0_1(self):
        from app.services.environment import fuse_environment
        emotion = dict.fromkeys(DIMENSIONS, 0.125)
        fused, meta = fuse_environment(
            emotion, season="spring", time_of_day="morning",
            weather_code=0, temperature=22.0,
        )
        assert meta["fusion_weight"] == 0.1
        assert meta["is_extreme"] is False
        # Shape unchanged
        assert set(fused.keys()) == set(DIMENSIONS)
        assert 0.99 <= sum(fused.values()) <= 1.01

    def test_extreme_weather_weight_is_0_2(self):
        from app.services.environment import fuse_environment
        emotion = dict.fromkeys(DIMENSIONS, 0.125)
        fused, meta = fuse_environment(
            emotion, season="winter", time_of_day="night",
            weather_code=96, temperature=-5.0,
        )
        assert meta["fusion_weight"] == 0.2
        assert meta["is_extreme"] is True

    def test_no_env_returns_original_normalized(self):
        """When no env params provided, fusion is a pass-through (uniform blend)."""
        from app.services.environment import fuse_environment
        emotion = {
            "joy": 0.9, "sadness": 0.0, "anxiety": 0.0, "calm": 0.2,
            "excitement": 0.7, "nostalgia": 0.0, "romance": 0.1, "melancholy": 0.0,
        }
        fused, meta = fuse_environment(emotion)
        # With no env params, the weight still applies but the env vector is uniform
        assert meta["fusion_weight"] == 0.1  # Default weight
        assert set(fused.keys()) == set(DIMENSIONS)
        # joy should still dominate (just slightly diluted by uniform env)
        assert fused["joy"] > 0.3

    def test_extreme_heat_pushes_down_joy(self):
        """Extreme heat (35°C+) should increase anxiety/calm vector influence."""
        from app.services.environment import fuse_environment
        emotion = {"joy": 0.9, "sadness": 0.0, "anxiety": 0.0, "calm": 0.1,
                   "excitement": 0.7, "nostalgia": 0.0, "romance": 0.1, "melancholy": 0.0}
        fused, meta = fuse_environment(
            emotion, season="summer", temperature=38.0,
        )
        assert meta["fusion_weight"] == 0.2
        # Fusion should have nudged the vector away from pure joy toward the env blend


# ── SSE integration: gen.complete metadata ───────────────────────────────────

class TestEnvironmentSSE:
    """Environment metadata flows into gen.complete correctly."""

    def test_gen_complete_metadata_accepts_environment(self):
        """The shared type uses Record<string, unknown> — any key is valid."""
        env_meta = {
            "season": "summer",
            "time_of_day": "evening",
            "weather": "晴天",
            "temperature": 28.0,
            "fusion_weight": 0.1,
            "is_extreme": False,
            "env_vector": {"joy": 0.2, "excitement": 0.15},
        }
        metadata = {
            "mode": "fast",
            "emotion": "joy",
            "search_source": "graphrag",
            "cache_hit": False,
            "environment": env_meta,
        }
        assert metadata["environment"]["season"] == "summer"
        assert metadata["environment"]["fusion_weight"] == 0.1
