"""Environment perception service (FR-2.8).

Maps season, time-of-day, and weather to an 8-D emotion adjustment vector
that is blended into the user's emotion vector before GraphRAG search.

Weights (from PRD §3.2.8): default 0.1, extreme weather 0.2.
Not affected by user intent.
"""

import logging
from typing import Any

from app.services.emotion import DIMENSIONS

logger = logging.getLogger(__name__)

# ── Season → emotion adjustment (northern hemisphere) ─────────────────────────
# Each season vector sums to ~1.0 before normalization.
_SEASON_VECTOR: dict[str, dict[str, float]] = {
    "spring": {
        "joy": 0.20, "romance": 0.20, "excitement": 0.15, "calm": 0.10,
        "nostalgia": 0.10, "sadness": 0.05, "anxiety": 0.10, "melancholy": 0.10,
    },
    "summer": {
        "joy": 0.25, "excitement": 0.20, "romance": 0.15, "calm": 0.05,
        "nostalgia": 0.10, "sadness": 0.05, "anxiety": 0.10, "melancholy": 0.10,
    },
    "autumn": {
        "nostalgia": 0.20, "melancholy": 0.15, "calm": 0.15, "romance": 0.10,
        "joy": 0.10, "excitement": 0.10, "sadness": 0.10, "anxiety": 0.10,
    },
    "winter": {
        "nostalgia": 0.25, "calm": 0.20, "romance": 0.10, "melancholy": 0.10,
        "joy": 0.10, "excitement": 0.05, "sadness": 0.10, "anxiety": 0.10,
    },
}

# ── Time of day → emotion adjustment ──────────────────────────────────────────
_TIME_VECTOR: dict[str, dict[str, float]] = {
    "morning": {
        "excitement": 0.20, "calm": 0.15, "joy": 0.15,
        "sadness": 0.10, "anxiety": 0.10, "nostalgia": 0.10,
        "romance": 0.10, "melancholy": 0.10,
    },
    "afternoon": {
        "joy": 0.20, "excitement": 0.15, "calm": 0.10,
        "sadness": 0.10, "anxiety": 0.15, "nostalgia": 0.10,
        "romance": 0.10, "melancholy": 0.10,
    },
    "evening": {
        "romance": 0.20, "calm": 0.15, "joy": 0.10,
        "sadness": 0.10, "anxiety": 0.10, "excitement": 0.10,
        "nostalgia": 0.15, "melancholy": 0.10,
    },
    "night": {
        "melancholy": 0.20, "calm": 0.20, "nostalgia": 0.15,
        "sadness": 0.10, "anxiety": 0.10, "excitement": 0.05,
        "joy": 0.10, "romance": 0.10,
    },
}

# ── WMO weather code → emotion adjustment ─────────────────────────────────────
# Simplified: clear (0-3), cloudy/overcast (45-48), rain/drizzle (50-67, 80-82),
# snow (71-77, 85-86), thunderstorm (95-99), extreme.
_WEATHER_GROUPS: dict[str, dict[str, float]] = {
    "clear": {
        "joy": 0.25, "excitement": 0.15, "calm": 0.10,
        "sadness": 0.05, "anxiety": 0.10, "nostalgia": 0.10,
        "romance": 0.15, "melancholy": 0.10,
    },
    "cloudy": {
        "calm": 0.20, "melancholy": 0.15, "nostalgia": 0.15,
        "sadness": 0.10, "anxiety": 0.10, "excitement": 0.05,
        "joy": 0.10, "romance": 0.15,
    },
    "rain": {
        "calm": 0.25, "melancholy": 0.15, "nostalgia": 0.15,
        "romance": 0.10, "sadness": 0.10, "anxiety": 0.10,
        "joy": 0.10, "excitement": 0.05,
    },
    "snow": {
        "nostalgia": 0.25, "calm": 0.20, "joy": 0.10,
        "melancholy": 0.10, "romance": 0.10, "excitement": 0.05,
        "sadness": 0.10, "anxiety": 0.10,
    },
    "thunderstorm": {
        "anxiety": 0.25, "sadness": 0.15, "calm": 0.10,
        "melancholy": 0.15, "romance": 0.10, "nostalgia": 0.10,
        "joy": 0.05, "excitement": 0.10,
    },
    "extreme": {
        "anxiety": 0.30, "sadness": 0.20, "calm": 0.05,
        "melancholy": 0.15, "nostalgia": 0.10, "romance": 0.05,
        "joy": 0.05, "excitement": 0.10,
    },
}

# WMO codes → weather group
_WMO_TO_GROUP: dict[tuple[int, ...], str] = {
    (0, 1, 2, 3): "clear",
}
_CLOUDY_CODES = (45, 48)
_RAIN_CODES = (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82)
_SNOW_CODES = (71, 73, 75, 77, 85, 86)
_THUNDER_CODES = (95, 96, 99)
_EXTREME_CODES = (96, 99)  # Hail


def _classify_weather(weather_code: int | None) -> str | None:
    """Map WMO weather code to a named group."""
    if weather_code is None:
        return None
    if weather_code in _CLOUDY_CODES:
        return "cloudy"
    if weather_code in _RAIN_CODES:
        return "rain"
    if weather_code in _SNOW_CODES:
        return "snow"
    if weather_code in _THUNDER_CODES:
        return "thunderstorm"
    if weather_code <= 3:
        return "clear"
    return "cloudy"  # Default for unknown codes


def is_extreme_weather(weather_code: int | None = None, temperature: float | None = None) -> bool:
    """Returns True if weather conditions qualify as 'extreme' (PRD: weight → 0.2).

    Extreme triggers: thunderstorm with hail, temperature >35°C or <0°C.
    """
    if weather_code is not None and weather_code in _EXTREME_CODES:
        return True
    if temperature is not None and (temperature > 35.0 or temperature < 0.0):
        return True
    return False


def _weather_label(weather_code: int | None) -> str:
    """Human-readable Chinese weather label for the `environment` metadata field."""
    if weather_code is None:
        return "unknown"
    group = _classify_weather(weather_code)
    return {
        "clear": "晴天", "cloudy": "多云/阴天", "rain": "雨天",
        "snow": "雪天", "thunderstorm": "雷暴", "extreme": "极端天气",
    }.get(group or "", "未知")


def compute_environment_vector(
    season: str | None = None,
    time_of_day: str | None = None,
    weather_code: int | None = None,
    temperature: float | None = None,
) -> dict[str, float]:
    """Compute an 8-D environment adjustment vector (0-1 range, sum≈1).

    Blend weights: season 0.4 + time_of_day 0.3 + weather 0.3.
    Missing dimensions default to uniform distribution.

    Returns:
        dict with all 8 DIMENSIONS keys, values in [0, 1], normalized.
    """
    env: dict[str, float] = dict.fromkeys(DIMENSIONS, 0.0)

    # Weighted blend: season 0.4 + time 0.3 + weather 0.3
    season_vec = _SEASON_VECTOR.get(season or "") if season else None
    time_vec = _TIME_VECTOR.get(time_of_day or "") if time_of_day else None
    weather_group = _classify_weather(weather_code)
    weather_vec = _WEATHER_GROUPS.get(weather_group or "") if weather_group else None

    active_sources = 0
    for dim in DIMENSIONS:
        total = 0.0
        total_weight = 0.0
        if season_vec:
            total += season_vec.get(dim, 0.0) * 0.4
            total_weight += 0.4
        if time_vec:
            total += time_vec.get(dim, 0.0) * 0.3
            total_weight += 0.3
        if weather_vec:
            total += weather_vec.get(dim, 0.0) * 0.3
            total_weight += 0.3
        if total_weight > 0:
            env[dim] = total / total_weight  # Renormalize within available sources
        else:
            env[dim] = 1.0 / len(DIMENSIONS)  # Uniform fallback

    # Ensure at least one source was active
    if not season_vec and not time_vec and not weather_vec:
        return dict.fromkeys(DIMENSIONS, 1.0 / len(DIMENSIONS))

    # Normalize to sum ≈ 1
    total = sum(env.values())
    if total > 0:
        env = {k: round(v / total, 4) for k, v in env.items()}
    else:
        env = {k: round(1.0 / len(DIMENSIONS), 4) for k in DIMENSIONS}

    return env


def fuse_environment(
    emotion_vector: dict[str, float],
    season: str | None = None,
    time_of_day: str | None = None,
    weather_code: int | None = None,
    temperature: float | None = None,
) -> tuple[dict[str, float], dict[str, Any]]:
    """Blend environment signal into the emotion vector.

    Returns:
        (fused_vector, metadata) where metadata is suitable for gen.complete.
    """
    env_weight = 0.2 if is_extreme_weather(weather_code, temperature) else 0.1
    env_vector = compute_environment_vector(season, time_of_day, weather_code, temperature)

    fused: dict[str, float] = {}
    for dim in DIMENSIONS:
        fused[dim] = round(
            emotion_vector.get(dim, 0.0) * (1.0 - env_weight)
            + env_vector.get(dim, 0.0) * env_weight,
            4,
        )

    # Re-normalize
    total = sum(fused.values())
    if total > 0:
        fused = {k: round(v / total, 4) for k, v in fused.items()}
    else:
        fused = {k: round(1.0 / len(DIMENSIONS), 4) for k in DIMENSIONS}

    metadata: dict[str, Any] = {
        "season": season,
        "time_of_day": time_of_day,
        "weather": _weather_label(weather_code) if weather_code is not None else None,
        "temperature": temperature,
        "fusion_weight": env_weight,
        "is_extreme": env_weight > 0.1,
        "env_vector": env_vector,
    }
    # Strip None values for cleaner JSON
    metadata = {k: v for k, v in metadata.items() if v is not None}

    return fused, metadata
