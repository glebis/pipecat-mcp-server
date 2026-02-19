"""Tests for screen capture permission error propagation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestScreenCapturePermissionErrorPropagation:
    """pmc-jjg: Permission errors should propagate, not be swallowed."""

    @pytest.mark.asyncio
    async def test_permission_error_propagates_from_start_capture(self):
        """_start_capture should raise PermissionError, not catch it."""
        with patch(
            "pipecat_mcp_server.processors.screen_capture.screen_capture_processor.get_capture_backend",
            return_value=AsyncMock(),
        ):
            from pipecat_mcp_server.processors.screen_capture.screen_capture_processor import (
                ScreenCaptureProcessor,
            )

            processor = ScreenCaptureProcessor()

        processor._backend = AsyncMock()
        processor._backend.start = AsyncMock(
            side_effect=PermissionError("Screen recording permission denied")
        )

        with pytest.raises(PermissionError, match="Screen recording permission denied"):
            await processor._start_capture(window_id=123)

    @pytest.mark.asyncio
    async def test_screen_capture_method_propagates_permission_error(self):
        """screen_capture() (public method) should also raise on permission error."""
        with patch(
            "pipecat_mcp_server.processors.screen_capture.screen_capture_processor.get_capture_backend",
            return_value=AsyncMock(),
        ):
            from pipecat_mcp_server.processors.screen_capture.screen_capture_processor import (
                ScreenCaptureProcessor,
            )

            processor = ScreenCaptureProcessor()

        processor._backend = AsyncMock()
        processor._backend.start = AsyncMock(
            side_effect=PermissionError("Screen recording permission denied")
        )
        processor._backend.stop = AsyncMock()

        with pytest.raises(PermissionError, match="Screen recording permission denied"):
            await processor.screen_capture(window_id=123)


class TestScreenCaptureProcessorListWindows:
    """pmc-xhi: ScreenCaptureProcessor should expose a public list_windows() method."""

    @pytest.mark.asyncio
    async def test_list_windows_delegates_to_backend(self):
        """list_windows() should delegate to the backend and return its results."""
        mock_window = MagicMock()
        mock_window.title = "Terminal"
        mock_window.app_name = "Terminal.app"
        mock_window.window_id = 42

        with patch(
            "pipecat_mcp_server.processors.screen_capture.screen_capture_processor.get_capture_backend",
            return_value=AsyncMock(),
        ):
            from pipecat_mcp_server.processors.screen_capture.screen_capture_processor import (
                ScreenCaptureProcessor,
            )

            processor = ScreenCaptureProcessor()

        processor._backend = AsyncMock()
        processor._backend.list_windows = AsyncMock(return_value=[mock_window])

        result = await processor.list_windows()

        processor._backend.list_windows.assert_called_once()
        assert result == [mock_window]

    @pytest.mark.asyncio
    async def test_list_windows_returns_empty_list(self):
        """list_windows() should return an empty list when no windows are available."""
        with patch(
            "pipecat_mcp_server.processors.screen_capture.screen_capture_processor.get_capture_backend",
            return_value=AsyncMock(),
        ):
            from pipecat_mcp_server.processors.screen_capture.screen_capture_processor import (
                ScreenCaptureProcessor,
            )

            processor = ScreenCaptureProcessor()

        processor._backend = AsyncMock()
        processor._backend.list_windows = AsyncMock(return_value=[])

        result = await processor.list_windows()

        assert result == []

    @pytest.mark.asyncio
    async def test_list_windows_is_public_method(self):
        """ScreenCaptureProcessor should have list_windows as a proper public method."""
        with patch(
            "pipecat_mcp_server.processors.screen_capture.screen_capture_processor.get_capture_backend",
            return_value=AsyncMock(),
        ):
            from pipecat_mcp_server.processors.screen_capture.screen_capture_processor import (
                ScreenCaptureProcessor,
            )

        assert hasattr(ScreenCaptureProcessor, "list_windows"), (
            "ScreenCaptureProcessor must have a public list_windows() method"
        )
        assert callable(getattr(ScreenCaptureProcessor, "list_windows"))


class TestScreenCaptureServerErrorResponse:
    """Server screen_capture tool should surface errors from child process."""

    @pytest.mark.asyncio
    async def test_screen_capture_tool_returns_error(self):
        """When child process returns error, server should raise."""
        with patch(
            "pipecat_mcp_server.server.send_command",
            new_callable=AsyncMock,
            return_value={"error": "Screen recording permission denied"},
        ):
            from pipecat_mcp_server.server import screen_capture

            # Currently the server ignores errors -- this should fail
            with pytest.raises(RuntimeError, match="Screen recording permission denied"):
                await screen_capture(window_id=123)

    @pytest.mark.asyncio
    async def test_screen_capture_tool_returns_window_id_on_success(self):
        """On success, should return the window_id."""
        with patch(
            "pipecat_mcp_server.server.send_command",
            new_callable=AsyncMock,
            return_value={"ok": True, "window_id": 42},
        ):
            from pipecat_mcp_server.server import screen_capture

            result = await screen_capture(window_id=42)

        assert result == 42
