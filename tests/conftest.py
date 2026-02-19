"""Test configuration: mock heavy pipecat dependencies for unit testing.

This conftest mocks module-level imports from pipecat and related packages
so that pure-logic tests can run without the full dependency tree installed.
"""

import importlib
import sys
from unittest.mock import MagicMock


def _make_mock_module(name: str) -> MagicMock:
    """Create a mock module with proper import-system attributes."""
    mock = MagicMock()
    mock.__name__ = name
    mock.__loader__ = None
    mock.__package__ = name
    mock.__path__ = []
    mock.__file__ = f"<mock:{name}>"
    mock.__spec__ = importlib.machinery.ModuleSpec(name, None)
    return mock


# Mock all pipecat submodules that agent.py and processors import at module level
_MOCK_MODULES = [
    "pipecat",
    "pipecat.audio",
    "pipecat.audio.filters",
    "pipecat.audio.filters.rnnoise_filter",
    "pipecat.audio.turn",
    "pipecat.audio.turn.smart_turn",
    "pipecat.audio.turn.smart_turn.local_smart_turn_v3",
    "pipecat.audio.vad",
    "pipecat.audio.vad.silero",
    "pipecat.audio.vad.vad_analyzer",
    "pipecat.frames",
    "pipecat.frames.frames",
    "pipecat.pipeline",
    "pipecat.pipeline.parallel_pipeline",
    "pipecat.pipeline.pipeline",
    "pipecat.pipeline.runner",
    "pipecat.pipeline.task",
    "pipecat.processors",
    "pipecat.processors.aggregators",
    "pipecat.processors.aggregators.llm_context",
    "pipecat.processors.aggregators.llm_response_universal",
    "pipecat.processors.frame_processor",
    "pipecat.runner",
    "pipecat.runner.run",
    "pipecat.runner.types",
    "pipecat.runner.utils",
    "pipecat.services",
    "pipecat.services.stt_service",
    "pipecat.services.tts_service",
    "pipecat.services.whisper",
    "pipecat.services.whisper.stt",
    "pipecat.services.deepgram",
    "pipecat.services.groq",
    "pipecat.transports",
    "pipecat.transports.base_transport",
    "pipecat.transports.websocket",
    "pipecat.transports.websocket.fastapi",
    "pipecat.turns",
    "pipecat.turns.user_stop",
    "pipecat.turns.user_stop.turn_analyzer_user_turn_stop_strategy",
    "pipecat.turns.user_turn_strategies",
    "pipecat.transcriptions",
    "pipecat.transcriptions.language",
    # Screen capture / vision dependencies
    "pyobjc",
    "Quartz",
    "ScreenCaptureKit",
    "CoreMedia",
    # Note: PIL/Pillow is available globally, do NOT mock it
    # Other heavy deps
    "aiohttp",
    "kokoro_onnx",
    "dotenv",
    "mcp",
    "mcp.server",
    "mcp.server.fastmcp",
]

for mod_name in _MOCK_MODULES:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = _make_mock_module(mod_name)

# Make dotenv.load_dotenv a no-op
sys.modules["dotenv"].load_dotenv = lambda *a, **kw: None


# ---------------------------------------------------------------------------
# Stub classes for Pipecat frame types (needed for isinstance() checks)
# ---------------------------------------------------------------------------


class _Frame:
    """Stub for pipecat.frames.frames.Frame."""

    pass


class _ImageRawFrame(_Frame):
    """Stub for pipecat.frames.frames.ImageRawFrame."""

    def __init__(self, image=b"", size=(0, 0)):
        self.image = image
        self.size = size


class _OutputImageRawFrame(_ImageRawFrame):
    """Stub for pipecat.frames.frames.OutputImageRawFrame."""

    pass


class _FrameDirection:
    """Stub for pipecat.processors.frame_processor.FrameDirection."""

    DOWNSTREAM = "downstream"
    UPSTREAM = "upstream"


class _FrameProcessor:
    """Stub for pipecat.processors.frame_processor.FrameProcessor."""

    def __init__(self, name="", **kwargs):
        self.name = name
        self._pushed_frames = []

    async def process_frame(self, frame, direction):
        pass

    async def push_frame(self, frame, direction):
        self._pushed_frames.append((frame, direction))


# Wire stub classes into the mock modules so imports resolve to real types
_frames_mod = sys.modules["pipecat.frames.frames"]
_frames_mod.Frame = _Frame
_frames_mod.ImageRawFrame = _ImageRawFrame
_frames_mod.OutputImageRawFrame = _OutputImageRawFrame

_fp_mod = sys.modules["pipecat.processors.frame_processor"]
_fp_mod.FrameDirection = _FrameDirection
_fp_mod.FrameProcessor = _FrameProcessor


# ---------------------------------------------------------------------------
# Make @mcp.tool() a passthrough decorator so server.py functions stay callable
# ---------------------------------------------------------------------------


class _PassthroughFastMCP:
    """Stub FastMCP that makes @mcp.tool() a no-op decorator."""

    def __init__(self, **kwargs):
        pass

    def tool(self, *args, **kwargs):
        """Return the function unchanged."""
        if args and callable(args[0]):
            return args[0]
        return lambda fn: fn

    def run(self, **kwargs):
        pass


sys.modules["mcp.server.fastmcp"].FastMCP = _PassthroughFastMCP
