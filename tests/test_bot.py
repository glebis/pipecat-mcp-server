"""Tests for bot.py command routing."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestBotCaptureScreenshotRouting:
    """Slice 6: Bot routes capture_screenshot command to agent and returns path."""

    @pytest.mark.asyncio
    async def test_capture_screenshot_dispatches_to_agent(self):
        # Arrange
        mock_agent = AsyncMock()
        mock_agent.capture_screenshot.return_value = "/tmp/screenshot.png"
        mock_agent.start = AsyncMock()

        responses = []
        call_count = 0

        async def mock_read_request():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"cmd": "capture_screenshot"}
            # read_request is outside the try block, so this breaks the loop
            raise KeyboardInterrupt("test done")

        async def mock_send_response(resp):
            responses.append(resp)

        with (
            patch(
                "pipecat_mcp_server.bot.create_agent",
                new_callable=AsyncMock,
                return_value=mock_agent,
            ),
            patch(
                "pipecat_mcp_server.bot.read_request",
                side_effect=mock_read_request,
            ),
            patch(
                "pipecat_mcp_server.bot.send_response",
                side_effect=mock_send_response,
            ),
        ):
            from pipecat_mcp_server.bot import bot

            mock_runner_args = MagicMock()
            with pytest.raises(KeyboardInterrupt):
                await bot(mock_runner_args)

        # Assert
        mock_agent.capture_screenshot.assert_called_once()
        assert len(responses) == 1
        assert responses[0] == {"path": "/tmp/screenshot.png"}


class TestBotErrorResponsesUseErrorKey:
    """Errors from command handlers should use {"error": ...} not {"text": ...}."""

    @pytest.mark.asyncio
    async def test_exception_sends_error_key_not_text(self):
        """When a command raises, response should have 'error' key."""
        mock_agent = AsyncMock()
        mock_agent.listen.side_effect = RuntimeError("mic disconnected")
        mock_agent.start = AsyncMock()

        responses = []
        call_count = 0

        async def mock_read_request():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"cmd": "listen"}
            raise KeyboardInterrupt("done")

        async def mock_send_response(resp):
            responses.append(resp)

        with (
            patch("pipecat_mcp_server.bot.create_agent", new_callable=AsyncMock, return_value=mock_agent),
            patch("pipecat_mcp_server.bot.read_request", side_effect=mock_read_request),
            patch("pipecat_mcp_server.bot.send_response", side_effect=mock_send_response),
        ):
            from pipecat_mcp_server.bot import bot
            with pytest.raises(KeyboardInterrupt):
                await bot(MagicMock())

        assert len(responses) == 1
        assert "error" in responses[0], f"Expected 'error' key, got: {responses[0]}"
        assert "text" not in responses[0], f"Should not have 'text' key for errors"


class TestBotLoopSurvivesErrors:
    """Bot loop should continue processing after non-fatal errors."""

    @pytest.mark.asyncio
    async def test_loop_continues_after_error(self):
        """After a command raises, bot should process the next command."""
        mock_agent = AsyncMock()
        mock_agent.start = AsyncMock()
        # First listen fails, second succeeds
        mock_agent.listen.side_effect = [RuntimeError("temporary error"), "hello world"]

        responses = []
        call_count = 0

        async def mock_read_request():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return {"cmd": "listen"}
            raise KeyboardInterrupt("done")

        async def mock_send_response(resp):
            responses.append(resp)

        with (
            patch("pipecat_mcp_server.bot.create_agent", new_callable=AsyncMock, return_value=mock_agent),
            patch("pipecat_mcp_server.bot.read_request", side_effect=mock_read_request),
            patch("pipecat_mcp_server.bot.send_response", side_effect=mock_send_response),
        ):
            from pipecat_mcp_server.bot import bot
            with pytest.raises(KeyboardInterrupt):
                await bot(MagicMock())

        # Should have 2 responses: error from first, text from second
        assert len(responses) == 2
        assert "error" in responses[0]
        assert responses[1] == {"text": "hello world"}
