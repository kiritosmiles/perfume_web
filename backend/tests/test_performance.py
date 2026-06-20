"""Performance benchmarks — verify TRD latency targets.

Key metrics from docs/superpowers/specs/2026-06-19-D-质量准则.md:
  - chat.emotion (cards): < 50ms
  - gen.skeleton:           < 200ms
  - build_copy_stream:      < 10ms
  - crisis_check:           < 5ms

Run:  pytest tests/test_performance.py -v -m perf
"""

import time

import pytest

from app.models.guest import GuestSessionInput
from app.services.emotion import resolve_emotion_from_cards
from app.services.generation import build_skeleton, build_copy_stream
from app.services.safety import crisis_check

# ── Thresholds from TRD ────────────────────────────────────
EMOTION_CARDS_MAX_MS = 50     # chat.emotion (card path) — BERT ~50ms, card_preset instant
SKELETON_MAX_MS = 200         # gen.skeleton — GraphRAG + normalization
COPY_STREAM_MAX_MS = 10       # build_copy_stream — template instantiation
CRISIS_CHECK_MAX_MS = 5       # crisis_check — keyword scan

# Number of warm-up + measured iterations
WARMUP = 3
ITERS = 20


def _measure(func, *args, **kwargs) -> tuple[float, float]:
    """Run WARMUP + ITERS iterations, return (min, avg) in milliseconds."""
    # Warmup
    for _ in range(WARMUP):
        func(*args, **kwargs)

    times: list[float] = []
    for _ in range(ITERS):
        t0 = time.perf_counter()
        func(*args, **kwargs)
        times.append((time.perf_counter() - t0) * 1000)

    return min(times), sum(times) / len(times)


@pytest.mark.perf
class TestEmotionLatency:
    """chat.emotion — must respond within 50ms for card-based input."""

    def test_single_card_latency(self):
        input_data = GuestSessionInput(emotion_card_ids=["joy"], scene_tag=None)
        mn, avg = _measure(resolve_emotion_from_cards, input_data)
        assert avg < EMOTION_CARDS_MAX_MS, (
            f"Single-card emotion resolution: avg={avg:.1f}ms exceeds {EMOTION_CARDS_MAX_MS}ms"
        )

    def test_two_card_merge_latency(self):
        input_data = GuestSessionInput(emotion_card_ids=["joy", "calm"], scene_tag=None)
        mn, avg = _measure(resolve_emotion_from_cards, input_data)
        assert avg < EMOTION_CARDS_MAX_MS, (
            f"Two-card emotion merge: avg={avg:.1f}ms exceeds {EMOTION_CARDS_MAX_MS}ms"
        )


@pytest.mark.perf
class TestSkeletonLatency:
    """gen.skeleton — build_skeleton() constructs 3 skeleton cards from GraphRAG candidates."""

    @staticmethod
    def _sample_candidates() -> list[dict]:
        return [
            {
                "name": "No.5 Chanel", "brand": "Chanel", "score": 6.75,
                "rating": 4.5, "longevity": 4.2, "sillage": 3.8,
                "seasons": ["spring", "fall"],
                "accord": "floral", "accord_score": 5.2,
            },
            {
                "name": "Light Blue Dolce & Gabbana", "brand": "Dolce & Gabbana",
                "score": 5.85, "rating": 4.3, "longevity": 3.5, "sillage": 3.0,
                "seasons": ["summer"],
                "accord": "citrus", "accord_score": 4.8,
            },
            {
                "name": "Sauvage Dior", "brand": "Dior", "score": 5.20,
                "rating": 4.2, "longevity": 4.5, "sillage": 4.0,
                "seasons": ["spring", "summer", "fall"],
                "accord": "woody", "accord_score": 4.5,
            },
            {
                "name": "J'adore Dior", "brand": "Dior", "score": 5.10,
                "rating": 4.4, "longevity": 3.8, "sillage": 3.5,
                "seasons": ["spring"],
                "accord": "floral", "accord_score": 4.2,
            },
            {
                "name": "Shalimar Guerlain", "brand": "Guerlain", "score": 4.95,
                "rating": 4.3, "longevity": 4.0, "sillage": 3.5,
                "seasons": ["fall", "winter"],
                "accord": "oriental", "accord_score": 4.0,
            },
        ]

    def test_skeleton_latency(self):
        emotion_vector = {"joy": 0.9, "excitement": 0.7, "calm": 0.2}
        candidates = self._sample_candidates()
        mn, avg = _measure(build_skeleton, candidates, emotion_vector)
        assert avg < SKELETON_MAX_MS, (
            f"build_skeleton: avg={avg:.1f}ms exceeds {SKELETON_MAX_MS}ms"
        )


@pytest.mark.perf
class TestCopyStreamLatency:
    """gen.copy — build_copy_stream instantiates template chunks."""

    def test_copy_stream_latency(self):
        mn, avg = _measure(build_copy_stream, 1, "test-gen-id", "开心")
        assert avg < COPY_STREAM_MAX_MS, (
            f"build_copy_stream: avg={avg:.1f}ms exceeds {COPY_STREAM_MAX_MS}ms"
        )

    def test_copy_stream_fallback_latency(self):
        """Unknown emotion falls back to generic template — same budget."""
        mn, avg = _measure(build_copy_stream, 2, "test-gen-id", "some-unknown-emotion")
        assert avg < COPY_STREAM_MAX_MS, (
            f"build_copy_stream (fallback): avg={avg:.1f}ms exceeds {COPY_STREAM_MAX_MS}ms"
        )


@pytest.mark.perf
class TestCrisisCheckLatency:
    """safety.crisis — keyword scan must be near-instant."""

    def test_normal_text_latency(self):
        mn, avg = _measure(crisis_check, "I'm feeling a bit tired today but generally okay")
        assert avg < CRISIS_CHECK_MAX_MS, (
            f"crisis_check (normal): avg={avg:.1f}ms exceeds {CRISIS_CHECK_MAX_MS}ms"
        )

    def test_crisis_text_latency(self):
        mn, avg = _measure(crisis_check, "I feel like ending it all I can't go on anymore")
        assert avg < CRISIS_CHECK_MAX_MS, (
            f"crisis_check (crisis): avg={avg:.1f}ms exceeds {CRISIS_CHECK_MAX_MS}ms"
        )

    def test_long_text_latency(self):
        long_text = "Today was a really long day at work. " * 10
        mn, avg = _measure(crisis_check, long_text)
        # Long text may be slightly slower but should still complete in < 20ms
        assert avg < 20, (
            f"crisis_check (long text): avg={avg:.1f}ms exceeds 20ms"
        )
