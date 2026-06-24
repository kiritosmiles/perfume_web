"""Tests for FR-5.9 Agent Role Boundary Protection (LLM Call B)."""

import json as _json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.boundary import (
    _call_boundary_llm,
    check_boundary_result,
    BOUNDARY_TIMEOUT,
    BOUNDARY_SYSTEM_PROMPT,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

VALID_NORMAL_RESULT = {
    "overstep_flag": "normal",
    "injection_flag": False,
    "hostile_flag": False,
    "reasoning": "用户正常咨询香水推荐",
}

VALID_OVERSTEP_RESULT = {
    "overstep_flag": "overstep",
    "injection_flag": False,
    "hostile_flag": False,
    "reasoning": "用户要求助手帮忙写Python代码",
}

VALID_INJECTION_RESULT = {
    "overstep_flag": "normal",
    "injection_flag": True,
    "hostile_flag": False,
    "reasoning": "用户尝试注入系统指令",
}

VALID_HOSTILE_RESULT = {
    "overstep_flag": "overstep",
    "injection_flag": False,
    "hostile_flag": True,
    "reasoning": "用户使用攻击性语言辱骂助手",
}

VALID_BORDERLINE_RESULT = {
    "overstep_flag": "borderline",
    "injection_flag": False,
    "hostile_flag": False,
    "reasoning": "用户试图引导助手提供医疗建议但措辞模糊",
}


def _mock_llm_response(response_dict: dict) -> MagicMock:
    """Build a mock httpx.AsyncClient that returns the given JSON response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": _json.dumps(response_dict, ensure_ascii=False),
                },
            },
        ],
    }
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_response)
    return mock_client


# ── TestBoundaryVerdict ─────────────────────────────────────────────────────────

class TestBoundaryVerdict:
    """Test check_boundary_result() verdict mapping."""

    def test_llm_returns_normal_no_block(self):
        """Normal result → verdict normal."""
        result = check_boundary_result(VALID_NORMAL_RESULT)
        assert result["verdict"] == "normal"
        assert result["overstep_flag"] == "normal"
        assert result["injection_flag"] is False
        assert result["hostile_flag"] is False

    def test_llm_returns_overstep_blocks(self):
        """Overstep result → verdict overstep."""
        result = check_boundary_result(VALID_OVERSTEP_RESULT)
        assert result["verdict"] == "overstep"
        assert result["overstep_flag"] == "overstep"

    def test_llm_returns_injection_blocks(self):
        """Injection result → verdict injection (higher priority than overstep)."""
        result = check_boundary_result(VALID_INJECTION_RESULT)
        assert result["verdict"] == "injection"
        assert result["injection_flag"] is True

    def test_llm_returns_hostile_blocks(self):
        """Hostile result → verdict hostile (highest priority)."""
        # hostile takes priority over injection per check_boundary_result logic
        result = check_boundary_result(VALID_HOSTILE_RESULT)
        assert result["verdict"] == "hostile"
        assert result["hostile_flag"] is True

    def test_borderline_returns_warn(self):
        """Borderline → verdict borderline (continue with gentle warning)."""
        result = check_boundary_result(VALID_BORDERLINE_RESULT)
        assert result["verdict"] == "borderline"
        assert result["overstep_flag"] == "borderline"

    def test_malformed_llm_output_defaults_to_normal(self):
        """Malformed JSON (missing overstep_flag) → defaults to normal."""
        result = check_boundary_result({"other_field": "value"})
        assert result["verdict"] == "normal"

    def test_invalid_overstep_flag_defaults_to_normal(self):
        """Unknown overstep_flag value → defaults to normal."""
        result = check_boundary_result({"overstep_flag": "invalid_value"})
        assert result["verdict"] == "normal"


# ── TestBoundaryLLM ─────────────────────────────────────────────────────────────

class TestBoundaryLLM:
    """Test _call_boundary_llm() async call."""

    @pytest.mark.asyncio
    async def test_llm_returns_valid_response(self):
        """LLM returns valid JSON → parsed correctly."""
        with patch(
            "httpx.AsyncClient",
            return_value=_mock_llm_response(VALID_NORMAL_RESULT),
        ):
            result = await _call_boundary_llm("推荐一款香水")
            assert result is not None
            assert result["overstep_flag"] == "normal"
            assert result["injection_flag"] is False
            assert result["hostile_flag"] is False

    @pytest.mark.asyncio
    async def test_llm_unavailable_returns_none(self):
        """LLM timeout → returns None."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=Exception("connection refused"))

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await _call_boundary_llm("推荐一款香水")
            assert result is None

    @pytest.mark.asyncio
    async def test_no_api_key_returns_none(self):
        """No API key configured → returns None immediately (no HTTP call)."""
        with patch("app.services.boundary.settings.LLM_API_KEY", ""):
            result = await _call_boundary_llm(
                "推荐一款香水",
                api_key_override=None,
            )
            assert result is None


# ── TestBoundaryUnchecked ───────────────────────────────────────────────────────

class TestBoundaryUnchecked:
    """Test check_boundary_result with None input."""

    def test_llm_unavailable_returns_unchecked(self):
        """None input → verdict unchecked (pipeline should proceed)."""
        result = check_boundary_result(None)
        assert result["verdict"] == "unchecked"
        assert result["overstep_flag"] == "unchecked"
        assert result["injection_flag"] is False
        assert result["hostile_flag"] is False


# ── TestBoundaryCounter ─────────────────────────────────────────────────────────

class TestBoundaryCounter:
    """Test Redis-based overstep counter."""

    @pytest.mark.asyncio
    async def test_counter_increments_on_overstep(self):
        """increment_boundary_overstep uses correct Redis key pattern."""
        from app.core.redis import increment_boundary_overstep

        mock_redis = MagicMock()
        counter_value = 1

        async def mock_incr(key):
            nonlocal counter_value
            counter_value += 1
            return counter_value - 1  # returns pre-increment value? No — INCR returns post-increment

        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()

        with patch("app.core.redis._get_client", return_value=mock_redis):
            count = await increment_boundary_overstep("test-session-abc")
            assert count == 1
            mock_redis.incr.assert_called_once_with("boundary:overstep:test-session-abc")
            mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_counter_returns_minus_one_when_redis_down(self):
        """Redis unavailable → returns -1 (caller treats as counter=0)."""
        from app.core.redis import increment_boundary_overstep

        with patch("app.core.redis._get_client", return_value=None):
            count = await increment_boundary_overstep("test-session")
            assert count == -1

    @pytest.mark.asyncio
    async def test_three_consecutive_overstep_detected(self):
        """Simulate 3 consecutive oversteps → counter reaches 3."""
        from app.core.redis import increment_boundary_overstep, reset_boundary_overstep

        mock_redis = MagicMock()
        current = 0

        async def mock_incr_side_effect(key):
            nonlocal current
            current += 1
            return current

        mock_redis.incr = AsyncMock(side_effect=mock_incr_side_effect)
        mock_redis.expire = AsyncMock()
        mock_redis.delete = AsyncMock()

        with patch("app.core.redis._get_client", return_value=mock_redis):
            c1 = await increment_boundary_overstep("session-1")
            c2 = await increment_boundary_overstep("session-1")
            c3 = await increment_boundary_overstep("session-1")
            assert c1 == 1
            assert c2 == 2
            assert c3 == 3  # trigger handoff threshold

            # Reset works
            await reset_boundary_overstep("session-1")
            mock_redis.delete.assert_called_once_with("boundary:overstep:session-1")

    def test_reset_counter_noop_when_redis_down(self):
        """reset_boundary_overstep is no-op when Redis unavailable."""
        import asyncio as _asyncio

        async def _run():
            from app.core.redis import reset_boundary_overstep
            with patch("app.core.redis._get_client", return_value=None):
                await reset_boundary_overstep("any-session")  # Should not raise

        _asyncio.get_event_loop().run_until_complete(_run())
