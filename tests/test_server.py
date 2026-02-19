"""Tests for server.py MCP tool wrappers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestServerCaptureScreenshotTool:
    """Slice 7: Server capture_screenshot tool extracts path from IPC response."""

    @pytest.mark.asyncio
    async def test_returns_path_from_ipc_response(self):
        with patch(
            "pipecat_mcp_server.server.send_command",
            new_callable=AsyncMock,
            return_value={"path": "/tmp/screenshot.png"},
        ):
            from pipecat_mcp_server.server import capture_screenshot

            result = await capture_screenshot()

        assert result == "/tmp/screenshot.png"

    @pytest.mark.asyncio
    async def test_returns_fallback_when_no_path(self):
        with patch(
            "pipecat_mcp_server.server.send_command",
            new_callable=AsyncMock,
            return_value={},
        ):
            from pipecat_mcp_server.server import capture_screenshot

            result = await capture_screenshot()

        assert result == "No screen capture available."


class TestServerSpeakErrorPropagation:
    """speak() should propagate errors from the child process."""

    @pytest.mark.asyncio
    async def test_speak_raises_on_error_response(self):
        """When child process returns error, speak() should raise RuntimeError."""
        with patch(
            "pipecat_mcp_server.server.send_command",
            new_callable=AsyncMock,
            return_value={"error": "TTS service unavailable"},
        ):
            from pipecat_mcp_server.server import speak

            with pytest.raises(RuntimeError, match="TTS service unavailable"):
                await speak("hello")

    @pytest.mark.asyncio
    async def test_speak_returns_true_on_success(self):
        """When child process returns ok, speak() should return True."""
        with patch(
            "pipecat_mcp_server.server.send_command",
            new_callable=AsyncMock,
            return_value={"ok": True},
        ):
            from pipecat_mcp_server.server import speak

            result = await speak("hello")

        assert result is True


# ---------------------------------------------------------------------------
# Bug 1 (pmc-rud): _check_transport_readiness tests
# ---------------------------------------------------------------------------


def _mock_aiohttp_get_200():
    """Create a mock aiohttp session where GET returns 200."""
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = AsyncMock()
    mock_session.get = MagicMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    return mock_session


def _mock_aiohttp_post_200(json_data):
    """Create a mock aiohttp session where POST returns 200 with json_data."""
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=json_data)
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = AsyncMock()
    mock_session.post = MagicMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    return mock_session


class TestCheckTransportReadiness:
    """_check_transport_readiness dispatches correctly per transport type."""

    @pytest.mark.asyncio
    async def test_daily_transport_posts_to_start(self):
        """Daily transport should POST /start and return room URL."""
        from pipecat_mcp_server.server import _check_transport_readiness

        mock_session = _mock_aiohttp_post_200({"dailyRoom": "https://daily.co/room123"})
        mock_cs = MagicMock(return_value=mock_session)

        with patch("pipecat_mcp_server.server.aiohttp.ClientSession", mock_cs):
            result = await _check_transport_readiness("daily")

        assert "room123" in result
        assert "ok" in result.lower()

    @pytest.mark.asyncio
    async def test_webrtc_transport_gets_client(self):
        """WebRTC transport should GET /client and return playground URL."""
        from pipecat_mcp_server.server import _check_transport_readiness

        mock_session = _mock_aiohttp_get_200()
        mock_cs = MagicMock(return_value=mock_session)

        with patch("pipecat_mcp_server.server.aiohttp.ClientSession", mock_cs):
            result = await _check_transport_readiness("webrtc")

        assert "/client" in result
        assert "ok" in result.lower()

    @pytest.mark.asyncio
    async def test_livekit_transport_no_http_polling(self):
        """LiveKit transport should return immediately without HTTP polling."""
        from pipecat_mcp_server.server import _check_transport_readiness

        result = await _check_transport_readiness("livekit")

        assert "ok" in result.lower()
        assert "livekit" in result.lower()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("transport", ["twilio", "telnyx", "plivo", "exotel"])
    async def test_telephony_transports_no_http_polling(self, transport):
        """Telephony transports should return immediately without HTTP polling."""
        from pipecat_mcp_server.server import _check_transport_readiness

        result = await _check_transport_readiness(transport)

        assert "ok" in result.lower()
        assert transport in result.lower()
        assert "telephony" in result.lower()

    @pytest.mark.asyncio
    async def test_unknown_transport_returns_ok(self):
        """Unknown transport should return ok with transport name."""
        from pipecat_mcp_server.server import _check_transport_readiness

        result = await _check_transport_readiness("custom-ws")

        assert "ok" in result.lower()
        assert "custom-ws" in result


# ---------------------------------------------------------------------------
# Bug 2 (pmc-faz): _validate_preset tests
# ---------------------------------------------------------------------------


class TestValidatePreset:
    """_validate_preset checks VOICE_PRESET and required API keys."""

    def test_default_preset_is_groq(self):
        """With no VOICE_PRESET env var, default should be 'groq'."""
        from pipecat_mcp_server.server import _validate_preset

        with patch.dict("os.environ", {}, clear=False):
            # Remove VOICE_PRESET if present
            env = {k: v for k, v in __import__("os").environ.items() if k != "VOICE_PRESET"}
            with patch.dict("os.environ", env, clear=True):
                result = _validate_preset()

        assert result["preset"] == "groq"

    def test_groq_preset_missing_key(self):
        """groq preset with no GROQ_API_KEY should report missing key."""
        from pipecat_mcp_server.server import _validate_preset

        env = {k: v for k, v in __import__("os").environ.items()
               if k not in ("VOICE_PRESET", "GROQ_API_KEY")}
        env["VOICE_PRESET"] = "groq"
        with patch.dict("os.environ", env, clear=True):
            result = _validate_preset()

        assert result["preset"] == "groq"
        assert "GROQ_API_KEY" in result["missing_keys"]

    def test_groq_preset_key_present(self):
        """groq preset with GROQ_API_KEY set should have empty missing_keys."""
        from pipecat_mcp_server.server import _validate_preset

        env = {"VOICE_PRESET": "groq", "GROQ_API_KEY": "test-key-123"}
        with patch.dict("os.environ", env, clear=True):
            result = _validate_preset()

        assert result["preset"] == "groq"
        assert result["missing_keys"] == []

    def test_deepgram_preset_missing_key(self):
        """deepgram preset requires DEEPGRAM_API_KEY."""
        from pipecat_mcp_server.server import _validate_preset

        env = {"VOICE_PRESET": "deepgram"}
        with patch.dict("os.environ", env, clear=True):
            result = _validate_preset()

        assert result["preset"] == "deepgram"
        assert "DEEPGRAM_API_KEY" in result["missing_keys"]

    def test_cartesia_preset_missing_both_keys(self):
        """cartesia preset requires DEEPGRAM_API_KEY + CARTESIA_API_KEY."""
        from pipecat_mcp_server.server import _validate_preset

        env = {"VOICE_PRESET": "cartesia"}
        with patch.dict("os.environ", env, clear=True):
            result = _validate_preset()

        assert result["preset"] == "cartesia"
        assert "DEEPGRAM_API_KEY" in result["missing_keys"]
        assert "CARTESIA_API_KEY" in result["missing_keys"]

    def test_cartesia_preset_partial_keys(self):
        """cartesia preset with only one key still reports the other as missing."""
        from pipecat_mcp_server.server import _validate_preset

        env = {"VOICE_PRESET": "cartesia", "DEEPGRAM_API_KEY": "dg-key"}
        with patch.dict("os.environ", env, clear=True):
            result = _validate_preset()

        assert "CARTESIA_API_KEY" in result["missing_keys"]
        assert "DEEPGRAM_API_KEY" not in result["missing_keys"]

    def test_local_preset_no_keys_needed(self):
        """local preset requires no API keys."""
        from pipecat_mcp_server.server import _validate_preset

        env = {"VOICE_PRESET": "local"}
        with patch.dict("os.environ", env, clear=True):
            result = _validate_preset()

        assert result["preset"] == "local"
        assert result["missing_keys"] == []

    def test_kokoro_preset_no_keys_needed(self):
        """kokoro preset requires no API keys."""
        from pipecat_mcp_server.server import _validate_preset

        env = {"VOICE_PRESET": "kokoro"}
        with patch.dict("os.environ", env, clear=True):
            result = _validate_preset()

        assert result["preset"] == "kokoro"
        assert result["missing_keys"] == []

    def test_invalid_preset_name(self):
        """Invalid preset name should be reported in result."""
        from pipecat_mcp_server.server import _validate_preset

        env = {"VOICE_PRESET": "nonexistent"}
        with patch.dict("os.environ", env, clear=True):
            result = _validate_preset()

        # Should have an error indicator -- either missing_keys with a
        # sentinel or a separate field. We check that the preset is reported.
        assert result["preset"] == "nonexistent"
        assert "error" in result or len(result["missing_keys"]) > 0 or "invalid" in str(result).lower()


# ---------------------------------------------------------------------------
# Integration: start() uses both _validate_preset and _check_transport_readiness
# ---------------------------------------------------------------------------


class TestStartIntegration:
    """start() integrates preset validation and transport readiness."""

    @pytest.mark.asyncio
    async def test_start_returns_preset_in_success_response(self):
        """Successful start() should mention the active preset."""
        from pipecat_mcp_server.server import start

        mock_session = _mock_aiohttp_get_200()
        mock_cs = MagicMock(return_value=mock_session)

        with patch("pipecat_mcp_server.server.start_pipecat_process", return_value=None), \
             patch("pipecat_mcp_server.server.check_startup_health", new_callable=AsyncMock, return_value=None), \
             patch("pipecat_mcp_server.server.TRANSPORT", "webrtc"), \
             patch("pipecat_mcp_server.server.aiohttp.ClientSession", mock_cs), \
             patch.dict("os.environ", {"VOICE_PRESET": "groq", "GROQ_API_KEY": "key123"}, clear=False):
            result = await start()

        assert "preset" in result.lower()
        assert "groq" in result.lower()

    @pytest.mark.asyncio
    async def test_start_fails_on_missing_api_key(self):
        """start() should return error when required API key is missing."""
        from pipecat_mcp_server.server import start

        env = {k: v for k, v in __import__("os").environ.items()
               if k not in ("GROQ_API_KEY",)}
        env["VOICE_PRESET"] = "groq"

        with patch("pipecat_mcp_server.server.start_pipecat_process", return_value=None), \
             patch("pipecat_mcp_server.server.check_startup_health", new_callable=AsyncMock, return_value=None), \
             patch.dict("os.environ", env, clear=True):
            result = await start()

        assert "GROQ_API_KEY" in result
        assert "missing" in result.lower() or "Missing" in result

    @pytest.mark.asyncio
    async def test_start_with_livekit_transport(self):
        """start() with livekit transport should not poll HTTP."""
        from pipecat_mcp_server.server import start

        with patch("pipecat_mcp_server.server.start_pipecat_process", return_value=None), \
             patch("pipecat_mcp_server.server.check_startup_health", new_callable=AsyncMock, return_value=None), \
             patch("pipecat_mcp_server.server.TRANSPORT", "livekit"), \
             patch.dict("os.environ", {"VOICE_PRESET": "local"}, clear=False):
            result = await start()

        assert "ok" in result.lower()
        assert "livekit" in result.lower()

    @pytest.mark.asyncio
    async def test_start_with_twilio_transport(self):
        """start() with twilio transport returns telephony-specific message."""
        from pipecat_mcp_server.server import start

        with patch("pipecat_mcp_server.server.start_pipecat_process", return_value=None), \
             patch("pipecat_mcp_server.server.check_startup_health", new_callable=AsyncMock, return_value=None), \
             patch("pipecat_mcp_server.server.TRANSPORT", "twilio"), \
             patch.dict("os.environ", {"VOICE_PRESET": "local"}, clear=False):
            result = await start()

        assert "ok" in result.lower()
        assert "twilio" in result.lower()

    @pytest.mark.asyncio
    async def test_start_preset_validation_before_process(self):
        """Missing key error should be returned even before child process starts."""
        from pipecat_mcp_server.server import start

        mock_start = MagicMock(return_value=None)
        env = {"VOICE_PRESET": "groq"}  # no GROQ_API_KEY

        with patch("pipecat_mcp_server.server.start_pipecat_process", mock_start), \
             patch("pipecat_mcp_server.server.check_startup_health", new_callable=AsyncMock, return_value=None), \
             patch.dict("os.environ", env, clear=True):
            result = await start()

        # Preset validation should catch the missing key before child starts
        assert "GROQ_API_KEY" in result
        # start_pipecat_process should NOT have been called
        mock_start.assert_not_called()
