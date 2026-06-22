import pytest

from app.models.guest import GuestSessionInput
from app.services.emotion import resolve_emotion_from_cards
from app.services.safety import crisis_check
from app.services.generation import build_skeleton, build_copy_stream


class TestEmotionService:
    def test_single_card_returns_its_vector(self):
        inp = GuestSessionInput(emotion_card_ids=["joy"])
        result = resolve_emotion_from_cards(inp)

        assert result["emotion_vector"]["joy"] == 0.9
        assert result["primary_emotion"] == "开心"
        assert result["confidence"] == 0.9
        assert result["source"] == "card_preset"

    def test_two_card_merge_averages_vectors(self):
        inp = GuestSessionInput(emotion_card_ids=["joy", "sadness"])
        result = resolve_emotion_from_cards(inp)

        # joy.joy=0.9, sadness.joy=0.0 → avg=0.45
        assert result["emotion_vector"]["joy"] == pytest.approx(0.45)
        # joy.sadness=0.0, sadness.sadness=0.9 → avg=0.45
        assert result["emotion_vector"]["sadness"] == pytest.approx(0.45)
        # Max should be one of them (or tie)
        assert result["confidence"] > 0

    def test_unknown_card_id_raises_gracefully(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="Invalid card id"):
            GuestSessionInput(emotion_card_ids=["nonexistent"])


class TestSafetyService:
    def test_normal_text_clean(self):
        result = crisis_check("今天心情不错，想找一款清新的香水")
        assert result["is_crisis"] is False
        assert result["severity"] == "none"
        assert result["matched_keywords"] == []

    def test_crisis_keyword_triggers_alert(self):
        result = crisis_check("最近真的很想死，不知道该怎么做")
        assert result["is_crisis"] is True
        assert result["severity"] == "high"
        assert "想死" in result["matched_keywords"]

    def test_multiple_keywords_all_matched(self):
        result = crisis_check("自杀和自残的想法挥之不去")
        assert result["is_crisis"] is True
        assert len(result["matched_keywords"]) >= 2

    def test_medium_severity_keyword(self):
        result = crisis_check("我最近撑不下去了")
        assert result["is_crisis"] is True
        # "撑不下去了" is not in high_risk set
        assert result["severity"] == "medium"

    def test_crisis_includes_hotlines(self):
        result = crisis_check("我想自杀")
        assert result["is_crisis"] is True
        assert len(result["hotlines"]) >= 3
        assert all("name" in h and "phone" in h for h in result["hotlines"])

    def test_normal_text_has_empty_hotlines(self):
        result = crisis_check("今天天气真好")
        assert result["is_crisis"] is False
        assert result["hotlines"] == []


class TestGenerationService:
    @pytest.fixture
    def candidates(self):
        return [
            {"name": "Bleu de Chanel", "brand": "Chanel", "score": 0.85},
            {"name": "Aventus", "brand": "Creed", "score": 0.72},
            {"name": "Sauvage", "brand": "Dior", "score": 0.68},
            {"name": "No.5", "brand": "Chanel", "score": 0.55},
        ]

    @pytest.fixture
    def emotion_vector(self):
        return {"joy": 0.3, "excitement": 0.9, "calm": 0.1, "romance": 0.2,
                "sadness": 0.0, "anxiety": 0.0, "nostalgia": 0.0, "melancholy": 0.0}

    def test_build_skeleton_returns_top_3(self, candidates, emotion_vector):
        skeletons = build_skeleton(candidates, emotion_vector)
        assert len(skeletons) == 3

    def test_build_skeleton_has_required_fields(self, candidates, emotion_vector):
        skeletons = build_skeleton(candidates, emotion_vector)
        for s in skeletons:
            assert "rank" in s
            assert "name" in s
            assert "brand" in s
            assert "notes_combination" in s
            assert isinstance(s["notes_combination"], list)
            assert len(s["notes_combination"]) == 3
            assert "match_score" in s
            assert s["is_partial"] is True
            assert s["source"] == "graphrag_match"

    def test_build_skeleton_match_score_capped_at_95(self, candidates, emotion_vector):
        candidates[0]["score"] = 9.9  # Very high score
        skeletons = build_skeleton(candidates[:1], emotion_vector)
        assert skeletons[0]["match_score"] <= 95

    def test_build_copy_stream_returns_chunks(self):
        chunks = build_copy_stream(1, "gen-001", "开心")
        assert len(chunks) > 0
        assert all(isinstance(c, str) for c in chunks)
        assert all(len(c) > 0 for c in chunks)

    def test_build_copy_stream_fallback_for_unknown_emotion(self):
        chunks = build_copy_stream(2, "gen-002", "unknown_mood")
        assert len(chunks) > 0  # Falls back to "calm"
