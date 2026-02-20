"""Tests for server.py MCP tool wrappers."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest


# aiohttp is mocked by conftest, so ClientConnectorError is a MagicMock.
# We need a real exception class for ``except aiohttp.ClientConnectorError``.
class _ClientConnectorError(Exception):
    """Stand-in for aiohttp.ClientConnectorError usable in except clauses."""


aiohttp.ClientConnectorError = _ClientConnectorError


class TestServerCaptureScreenshotTool:
    """Slice 7: Server capture_screenshot tool extracts path from IPC response."""

    @pytest.mark.asyncio
    async def test_returns_path_from_ipc_response(self):
        """IPC response with 'path' key should be returned directly."""
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
        """Missing 'path' key should return fallback message."""
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
    """validate_preset_with_env checks VOICE_PRESET and required API keys."""

    def test_default_preset_is_groq(self):
        """With no VOICE_PRESET env var, default should be 'groq'."""
        from pipecat_mcp_server.domain.voice_preset import validate_preset_with_env

        result = validate_preset_with_env({})
        assert result.name == "groq"

    def test_groq_preset_missing_key(self):
        """Groq preset with no GROQ_API_KEY should report missing key."""
        from pipecat_mcp_server.domain.voice_preset import validate_preset_with_env

        result = validate_preset_with_env({"VOICE_PRESET": "groq"})
        assert result.name == "groq"
        assert "GROQ_API_KEY" in result.missing_keys

    def test_groq_preset_key_present(self):
        """Groq preset with GROQ_API_KEY set should have empty missing_keys."""
        from pipecat_mcp_server.domain.voice_preset import validate_preset_with_env

        result = validate_preset_with_env({"VOICE_PRESET": "groq", "GROQ_API_KEY": "test-key-123"})
        assert result.name == "groq"
        assert result.missing_keys == []

    def test_deepgram_preset_missing_key(self):
        """Deepgram preset requires DEEPGRAM_API_KEY."""
        from pipecat_mcp_server.domain.voice_preset import validate_preset_with_env

        result = validate_preset_with_env({"VOICE_PRESET": "deepgram"})
        assert result.name == "deepgram"
        assert "DEEPGRAM_API_KEY" in result.missing_keys

    def test_cartesia_preset_missing_both_keys(self):
        """Cartesia preset requires DEEPGRAM_API_KEY + CARTESIA_API_KEY."""
        from pipecat_mcp_server.domain.voice_preset import validate_preset_with_env

        result = validate_preset_with_env({"VOICE_PRESET": "cartesia"})
        assert result.name == "cartesia"
        assert "DEEPGRAM_API_KEY" in result.missing_keys
        assert "CARTESIA_API_KEY" in result.missing_keys

    def test_cartesia_preset_partial_keys(self):
        """Cartesia preset with only one key still reports the other as missing."""
        from pipecat_mcp_server.domain.voice_preset import validate_preset_with_env

        result = validate_preset_with_env(
            {"VOICE_PRESET": "cartesia", "DEEPGRAM_API_KEY": "dg-key"}
        )
        assert "CARTESIA_API_KEY" in result.missing_keys
        assert "DEEPGRAM_API_KEY" not in result.missing_keys

    def test_local_preset_no_keys_needed(self):
        """Local preset requires no API keys."""
        from pipecat_mcp_server.domain.voice_preset import validate_preset_with_env

        result = validate_preset_with_env({"VOICE_PRESET": "local"})
        assert result.name == "local"
        assert result.missing_keys == []

    def test_kokoro_preset_no_keys_needed(self):
        """Kokoro preset requires no API keys."""
        from pipecat_mcp_server.domain.voice_preset import validate_preset_with_env

        result = validate_preset_with_env({"VOICE_PRESET": "kokoro"})
        assert result.name == "kokoro"
        assert result.missing_keys == []

    def test_invalid_preset_name(self):
        """Invalid preset name should be reported in result."""
        from pipecat_mcp_server.domain.voice_preset import validate_preset_with_env

        result = validate_preset_with_env({"VOICE_PRESET": "nonexistent"})
        assert result.name == "nonexistent"
        assert result.is_valid is False
        assert result.error is not None


# ---------------------------------------------------------------------------
# Integration: start() uses both _validate_preset and _check_transport_readiness
# ---------------------------------------------------------------------------


class TestStartIntegration:
    """start() integrates preset validation and transport readiness."""

    @pytest.mark.asyncio
    async def test_start_returns_preset_in_success_response(self):
        """Successful start() should mention the active preset."""
        from pipecat_mcp_server.server import agent_process, start

        mock_session = _mock_aiohttp_get_200()
        mock_cs = MagicMock(return_value=mock_session)

        with (
            patch("pipecat_mcp_server.server.start_pipecat_process", return_value=None),
            patch.object(agent_process, "check_health", new_callable=AsyncMock, return_value=None),
            patch("pipecat_mcp_server.server.TRANSPORT", "webrtc"),
            patch("pipecat_mcp_server.server.aiohttp.ClientSession", mock_cs),
            patch.dict(
                "os.environ", {"VOICE_PRESET": "groq", "GROQ_API_KEY": "key123"}, clear=False
            ),
        ):
            result = await start()

        assert "preset" in result.lower()
        assert "groq" in result.lower()

    @pytest.mark.asyncio
    async def test_start_fails_on_missing_api_key(self):
        """start() should return error when required API key is missing."""
        from pipecat_mcp_server.server import agent_process, start

        env = {k: v for k, v in __import__("os").environ.items() if k not in ("GROQ_API_KEY",)}
        env["VOICE_PRESET"] = "groq"

        with (
            patch("pipecat_mcp_server.server.start_pipecat_process", return_value=None),
            patch.object(agent_process, "check_health", new_callable=AsyncMock, return_value=None),
            patch.dict("os.environ", env, clear=True),
        ):
            result = await start()

        assert "GROQ_API_KEY" in result
        assert "missing" in result.lower() or "Missing" in result

    @pytest.mark.asyncio
    async def test_start_with_livekit_transport(self):
        """start() with livekit transport should not poll HTTP."""
        from pipecat_mcp_server.server import agent_process, start

        with (
            patch("pipecat_mcp_server.server.start_pipecat_process", return_value=None),
            patch.object(agent_process, "check_health", new_callable=AsyncMock, return_value=None),
            patch("pipecat_mcp_server.server.TRANSPORT", "livekit"),
            patch.dict("os.environ", {"VOICE_PRESET": "local"}, clear=False),
        ):
            result = await start()

        assert "ok" in result.lower()
        assert "livekit" in result.lower()

    @pytest.mark.asyncio
    async def test_start_with_twilio_transport(self):
        """start() with twilio transport returns telephony-specific message."""
        from pipecat_mcp_server.server import agent_process, start

        with (
            patch("pipecat_mcp_server.server.start_pipecat_process", return_value=None),
            patch.object(agent_process, "check_health", new_callable=AsyncMock, return_value=None),
            patch("pipecat_mcp_server.server.TRANSPORT", "twilio"),
            patch.dict("os.environ", {"VOICE_PRESET": "local"}, clear=False),
        ):
            result = await start()

        assert "ok" in result.lower()
        assert "twilio" in result.lower()

    @pytest.mark.asyncio
    async def test_start_preset_validation_before_process(self):
        """Missing key error should be returned even before child process starts."""
        from pipecat_mcp_server.server import agent_process, start

        mock_start = MagicMock(return_value=None)
        env = {"VOICE_PRESET": "groq"}  # no GROQ_API_KEY

        with (
            patch("pipecat_mcp_server.server.start_pipecat_process", mock_start),
            patch.object(agent_process, "check_health", new_callable=AsyncMock, return_value=None),
            patch.dict("os.environ", env, clear=True),
        ):
            result = await start()

        # Preset validation should catch the missing key before child starts
        assert "GROQ_API_KEY" in result
        # start_pipecat_process should NOT have been called
        mock_start.assert_not_called()


# ---------------------------------------------------------------------------
# Slice 3: _diagnose_port and transport failure enrichment
# ---------------------------------------------------------------------------


class TestDiagnosePort:
    """_diagnose_port returns human-readable port status."""

    def test_diagnose_port_occupied(self):
        """When lsof finds a process on the port, return PID and process name."""
        from pipecat_mcp_server.server import _diagnose_port

        lsof_output = "python3 12345 user   3u  IPv4  0x1234  0t0  TCP *:7860 (LISTEN)\n"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = lsof_output

        with patch("pipecat_mcp_server.server.subprocess.run", return_value=mock_result):
            result = _diagnose_port(7860)

        assert "12345" in result
        assert "python3" in result
        assert "in use" in result.lower()

    def test_diagnose_port_free(self):
        """When lsof finds nothing, return that the port is free."""
        from pipecat_mcp_server.server import _diagnose_port

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("pipecat_mcp_server.server.subprocess.run", return_value=mock_result):
            result = _diagnose_port(7860)

        assert "free" in result.lower()
        assert "crash" in result.lower() or "child process" in result.lower()


def _mock_aiohttp_always_fail():
    """Create a mock aiohttp session where every request raises ClientConnectorError."""
    conn_error = _ClientConnectorError("Connection refused")

    mock_session = AsyncMock()
    mock_session.get = MagicMock(side_effect=conn_error)
    mock_session.post = MagicMock(side_effect=conn_error)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    return mock_session


class TestTransportFailureIncludesDiagnosis:
    """Transport failure messages should include port diagnosis info."""

    @pytest.mark.asyncio
    async def test_daily_transport_failure_includes_diagnosis(self):
        """Daily transport failure after 5 attempts should include port diagnosis."""
        from pipecat_mcp_server.server import _check_transport_readiness

        mock_session = _mock_aiohttp_always_fail()
        mock_cs = MagicMock(return_value=mock_session)
        diagnosis = " Port 7860 is in use by PID 99999 (fake_proc)."

        with (
            patch("pipecat_mcp_server.server.aiohttp.ClientSession", mock_cs),
            patch("pipecat_mcp_server.server.asyncio.sleep", new_callable=AsyncMock),
            patch("pipecat_mcp_server.server._diagnose_port", return_value=diagnosis),
        ):
            result = await _check_transport_readiness("daily")

        assert "5 attempts" in result
        assert "PID 99999" in result
        assert "fake_proc" in result

    @pytest.mark.asyncio
    async def test_webrtc_transport_failure_includes_diagnosis(self):
        """WebRTC transport failure after 5 attempts should include port diagnosis."""
        from pipecat_mcp_server.server import _check_transport_readiness

        mock_session = _mock_aiohttp_always_fail()
        mock_cs = MagicMock(return_value=mock_session)
        diagnosis = " Port 7860 is free — the child process may have crashed. Check logs."

        with (
            patch("pipecat_mcp_server.server.aiohttp.ClientSession", mock_cs),
            patch("pipecat_mcp_server.server.asyncio.sleep", new_callable=AsyncMock),
            patch("pipecat_mcp_server.server._diagnose_port", return_value=diagnosis),
        ):
            result = await _check_transport_readiness("webrtc")

        assert "5 attempts" in result
        assert "free" in result.lower()
        assert "child process" in result.lower()
