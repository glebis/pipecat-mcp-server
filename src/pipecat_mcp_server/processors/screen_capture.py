#
# Copyright (c) 2026, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Screen capture processor for Pipecat MCP Server.

This module provides a FrameProcessor that captures screenshots of the screen
or a specific window and injects them into the pipeline as OutputImageRawFrames.

Note: Window capture is based on window position (coordinates), not window content.
This means that if another window overlaps the target window, the overlapping content
will be captured. If the target window is moved, the capture region updates dynamically.
"""

import asyncio
import os
from concurrent.futures import ProcessPoolExecutor
from typing import Optional, Tuple

from loguru import logger
from pipecat.frames.frames import (
    CancelFrame,
    EndFrame,
    Frame,
    OutputImageRawFrame,
    StartFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

_screen_capture_supported = False

try:
    import mss
    import pywinctl as pwc

    _screen_capture_supported = True
except ModuleNotFoundError as e:
    logger.error(f"Exception: {e}")
    logger.error(
        "In order to use screen capture, you need to `uv tool install pipecat-mcp-server[screen]`."
    )

# Environment variable names
ENV_SCREEN_CAPTURE = "PIPECAT_MCP_SERVER_SCREEN_CAPTURE"
ENV_SCREEN_WINDOW = "PIPECAT_MCP_SERVER_SCREEN_WINDOW"


def _get_window_geometry(window_name: str) -> Optional[Tuple[int, int, int, int]]:
    """Get window geometry using pywinctl (cross-platform).

    Args:
        window_name: The name/title of the window to find (partial match, case-insensitive).

    Returns:
        Tuple of (x, y, width, height) if window found, None otherwise.

    """
    # Search for windows containing the given name (case-insensitive)
    windows = pwc.getWindowsWithTitle(
        window_name,
        condition=pwc.Re.CONTAINS,
        flags=pwc.Re.IGNORECASE,
    )
    if not windows:
        logger.warning(f"Window '{window_name}' not found")
        return None

    # Get the first matching window
    window = windows[0]

    # Get window geometry
    left, top, right, bottom = window.left, window.top, window.right, window.bottom
    width = right - left
    height = bottom - top

    if width > 0 and height > 0:
        return (left, top, width, height)

    logger.warning(f"Invalid geometry for window '{window_name}'")
    return None


def _capture_screen(
    monitor_index: int, window_name: Optional[str]
) -> Optional[Tuple[bytes, Tuple[int, int]]]:
    """Capture screen or window (blocking function to run in separate process).

    Args:
        monitor_index: The monitor index to capture.
        window_name: Optional window name to capture instead of full screen.

    Returns:
        Tuple of (rgb_bytes, (width, height)) or None if capture failed.

    """
    with mss.mss() as sct:
        # Determine capture region
        if window_name:
            geometry = _get_window_geometry(window_name)
            if geometry is None:
                logger.warning(
                    f"Could not find window '{window_name}', falling back to full screen"
                )
                monitor = sct.monitors[monitor_index + 1]
            else:
                x, y, width, height = geometry
                monitor = {"left": x, "top": y, "width": width, "height": height}
        else:
            # +1 because monitor 0 is "all monitors combined"
            monitor = sct.monitors[monitor_index + 1]

        # Capture the screen
        screenshot = sct.grab(monitor)

        return (screenshot.rgb, (screenshot.width, screenshot.height))


class ScreenCaptureProcessor(FrameProcessor):
    """FrameProcessor that periodically captures screenshots.

    This processor captures the screen (or a specific window) once per second
    and pushes OutputImageRawFrames downstream.

    The processor is only active if the environment variable
    PIPECAT_MCP_SERVER_SCREEN_CAPTURE is set.

    Optionally, PIPECAT_MCP_SERVER_SCREEN_WINDOW can be set to capture
    a specific window by name instead of the entire screen.

    Example:
        export PIPECAT_MCP_SERVER_SCREEN_CAPTURE=1
        export PIPECAT_MCP_SERVER_SCREEN_WINDOW="Firefox"  # Optional

    """

    def __init__(self, monitor: int = 0, capture_interval: float = 1.0):
        """Initialize the screen capture processor.

        Args:
            monitor: The monitor index to capture (default: 0 for primary monitor).
                    Only used when not capturing a specific window.
            capture_interval: Time in seconds between captures (default: 1.0).

        """
        super().__init__(name="screen-capture")
        self._monitor = monitor
        self._capture_interval = capture_interval
        self._capture_task: Optional[asyncio.Task] = None
        self._executor: Optional[ProcessPoolExecutor] = None

        # Check if screen capture is enabled
        self._enabled = os.getenv(ENV_SCREEN_CAPTURE) is not None

        # Get optional window name
        self._window_name = os.getenv(ENV_SCREEN_WINDOW)

    async def cleanup(self) -> None:
        """Clean up resources when processor is shutting down."""
        await super().cleanup()
        await self._stop_capture_task()

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process incoming frames and manage capture task lifecycle.

        Args:
            frame: The frame to process.
            direction: The frame direction (DOWNSTREAM or UPSTREAM).

        """
        await super().process_frame(frame, direction)

        if isinstance(frame, StartFrame):
            await self._start(frame)
        elif isinstance(frame, (EndFrame, CancelFrame)):
            await self._stop_capture_task()

        await self.push_frame(frame, direction)

    async def _start(self, frame: StartFrame):
        if self._enabled:
            if not _screen_capture_supported:
                logger.warning(f"Screen capture enabled but not supported!")
                return

            logger.debug("Screen capture processor enabled")
            if self._window_name:
                logger.debug(f"Will capture window: {self._window_name}")
            else:
                logger.debug(f"Will capture monitor {self._monitor}")

            self._create_capture_task()
        else:
            logger.debug(f"Screen capture disabled. Set {ENV_SCREEN_CAPTURE}=1 to enable.")

    def _create_capture_task(self) -> None:
        """Create and start the periodic capture task."""
        if not self._enabled:
            return

        if not self._capture_task:
            self._capture_task = self.create_task(self._capture_task_handler())

        if not self._executor:
            # Create process pool for capture to avoid GIL contention with audio
            self._executor = ProcessPoolExecutor(max_workers=1)

    async def _stop_capture_task(self) -> None:
        """Stop the periodic capture task and shutdown executor."""
        if self._capture_task:
            await self.cancel_task(self._capture_task)
            self._capture_task = None
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None

    async def _capture_task_handler(self) -> None:
        """Periodically capture screenshots and push them downstream."""
        loop = asyncio.get_event_loop()
        while True:
            try:
                # Capture screen in separate process to avoid GIL contention with audio
                result = await loop.run_in_executor(
                    self._executor, _capture_screen, self._monitor, self._window_name
                )

                if result:
                    rgb_bytes, (width, height) = result
                    frame = OutputImageRawFrame(
                        image=rgb_bytes,
                        size=(width, height),
                        format="RGB",
                    )
                    await self.push_frame(frame)

                await asyncio.sleep(self._capture_interval)
            except Exception as e:
                logger.error(f"Error in capture task: {e}")
                await asyncio.sleep(self._capture_interval)
