"""Tests for VisionProcessor on-demand screenshot capture."""

import asyncio
import os
from unittest.mock import patch, MagicMock

import pytest

from pipecat.frames.frames import Frame, OutputImageRawFrame
from pipecat.processors.frame_processor import FrameDirection
from pipecat_mcp_server.processors.vision import VisionProcessor


@pytest.fixture
def vision():
    return VisionProcessor()


def _make_image_frame(width=2, height=2) -> OutputImageRawFrame:
    """Create a minimal valid OutputImageRawFrame with real RGB pixel data."""
    # 2x2 red image: 3 bytes per pixel (RGB) * 4 pixels = 12 bytes
    pixel_data = b"\xff\x00\x00" * (width * height)
    frame = OutputImageRawFrame(image=pixel_data, size=(width, height))
    return frame


class TestVisionProcessorCapturesOnRequest:
    """Slice 3: request_capture() + process_frame() saves PNG and returns path."""

    @pytest.mark.asyncio
    async def test_saves_png_when_capture_requested(self, vision):
        # Arrange
        frame = _make_image_frame()
        vision.request_capture()

        # Act
        await vision.process_frame(frame, FrameDirection.DOWNSTREAM)

        # Assert
        path = await asyncio.wait_for(vision.get_result(), timeout=2.0)
        assert path.endswith(".png")
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0

        # Cleanup
        os.unlink(path)


class TestVisionProcessorIgnoresWithoutRequest:
    """Slice 4: frames pass through without saving when capture not requested."""

    @pytest.mark.asyncio
    async def test_does_not_save_without_request(self, vision):
        # Arrange
        frame = _make_image_frame()
        # Do NOT call request_capture()

        # Act
        await vision.process_frame(frame, FrameDirection.DOWNSTREAM)

        # Assert -- result queue should be empty
        assert vision._result_queue.empty()

    @pytest.mark.asyncio
    async def test_non_image_frame_passes_through(self, vision):
        # Arrange
        non_image_frame = Frame()
        vision.request_capture()

        # Act
        await vision.process_frame(non_image_frame, FrameDirection.DOWNSTREAM)

        # Assert -- result queue should be empty (non-image frames ignored)
        assert vision._result_queue.empty()
        # Capture flag should still be set (not consumed by non-image frame)
        assert vision._capture_requested is True


class TestVisionProcessorSingleShot:
    """Slice 5: capture flag resets after one capture (single-shot behavior)."""

    @pytest.mark.asyncio
    async def test_flag_resets_after_capture(self, vision):
        # Arrange
        frame1 = _make_image_frame()
        frame2 = _make_image_frame()
        vision.request_capture()

        # Act -- process two frames, only one capture requested
        await vision.process_frame(frame1, FrameDirection.DOWNSTREAM)
        path1 = await asyncio.wait_for(vision.get_result(), timeout=2.0)

        await vision.process_frame(frame2, FrameDirection.DOWNSTREAM)

        # Assert -- only one result produced, queue is empty after first
        assert vision._result_queue.empty()
        assert vision._capture_requested is False

        # Cleanup
        os.unlink(path1)

    @pytest.mark.asyncio
    async def test_push_frame_always_called(self, vision):
        """Frames are always forwarded downstream regardless of capture state."""
        frame = _make_image_frame()

        await vision.process_frame(frame, FrameDirection.DOWNSTREAM)

        # The frame should be pushed even without capture request
        assert len(vision._pushed_frames) == 1
        assert vision._pushed_frames[0] == (frame, FrameDirection.DOWNSTREAM)


class TestVisionProcessorGetResultTimeout:
    """get_result() raises TimeoutError when no frame arrives within timeout."""

    @pytest.mark.asyncio
    async def test_get_result_times_out_when_no_capture(self, vision):
        """get_result(timeout=0.1) should raise asyncio.TimeoutError quickly."""
        with pytest.raises(asyncio.TimeoutError):
            await vision.get_result(timeout=0.1)

    @pytest.mark.asyncio
    async def test_get_result_succeeds_within_timeout(self, vision):
        """get_result(timeout=2.0) returns path when frame arrives before timeout."""
        frame = _make_image_frame()
        vision.request_capture()
        await vision.process_frame(frame, FrameDirection.DOWNSTREAM)

        path = await vision.get_result(timeout=2.0)
        assert path.endswith(".png")
        os.unlink(path)

    @pytest.mark.asyncio
    async def test_get_result_default_timeout(self, vision):
        """get_result() without explicit timeout should still timeout (not block forever)."""
        with pytest.raises(asyncio.TimeoutError):
            await vision.get_result(timeout=0.2)
