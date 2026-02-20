"""Tests for infrastructure.service_factory -- STT/TTS factory functions."""

import sys
from unittest.mock import MagicMock, patch

import pytest


class TestCreateSttServiceGroq:
    """create_stt_service('groq') uses GroqSTTService when key is present."""

    def test_groq_stt_with_api_key_returns_service(self):
        """Groq STT with GROQ_API_KEY set should return a GroqSTTService instance."""
        with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}, clear=False):
            from pipecat_mcp_server.infrastructure.service_factory import (
                create_stt_service,
            )

            result = create_stt_service("groq")
        assert result is not None

    def test_groq_stt_without_api_key_raises(self):
        """Groq STT without GROQ_API_KEY should raise ValueError."""
        with patch.dict("os.environ", {}, clear=True):
            from pipecat_mcp_server.infrastructure.service_factory import (
                create_stt_service,
            )

            with pytest.raises(ValueError, match="GROQ_API_KEY"):
                create_stt_service("groq")


class TestCreateSttServiceLocal:
    """create_stt_service('local') picks platform-appropriate Whisper backend."""

    def test_local_stt_on_darwin_returns_mlx(self):
        """Local STT on macOS (darwin) should return WhisperSTTServiceMLX."""
        with patch.object(sys, "platform", "darwin"):
            from pipecat_mcp_server.infrastructure.service_factory import (
                create_stt_service,
            )

            result = create_stt_service("local")
        assert result is not None

    def test_local_stt_on_linux_returns_faster_whisper(self):
        """Local STT on Linux should return WhisperSTTService (faster-whisper)."""
        with patch.object(sys, "platform", "linux"):
            from pipecat_mcp_server.infrastructure.service_factory import (
                create_stt_service,
            )

            result = create_stt_service("local")
        assert result is not None


class TestCreateSttServiceDeepgram:
    """create_stt_service('deepgram') uses DeepgramSTTService."""

    def test_deepgram_stt_with_api_key(self):
        """Deepgram STT with DEEPGRAM_API_KEY set should return a service."""
        with patch.dict("os.environ", {"DEEPGRAM_API_KEY": "dg-key"}, clear=False):
            from pipecat_mcp_server.infrastructure.service_factory import (
                create_stt_service,
            )

            result = create_stt_service("deepgram")
        assert result is not None

    def test_deepgram_stt_without_api_key_raises(self):
        """Deepgram STT without DEEPGRAM_API_KEY should raise ValueError."""
        with patch.dict("os.environ", {}, clear=True):
            from pipecat_mcp_server.infrastructure.service_factory import (
                create_stt_service,
            )

            with pytest.raises(ValueError, match="DEEPGRAM_API_KEY"):
                create_stt_service("deepgram")


class TestCreateTtsServiceGroq:
    """create_tts_service('groq') uses GroqTTSService."""

    def test_groq_tts_returns_service(self):
        """Groq TTS should return a GroqTTSService instance (no key check)."""
        with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}, clear=False):
            from pipecat_mcp_server.infrastructure.service_factory import (
                create_tts_service,
            )

            result = create_tts_service("groq")
        assert result is not None


class TestCreateTtsServiceDeepgram:
    """create_tts_service('deepgram') uses DeepgramTTSService."""

    def test_deepgram_tts_with_api_key(self):
        """Deepgram TTS with DEEPGRAM_API_KEY set should return a service."""
        with patch.dict("os.environ", {"DEEPGRAM_API_KEY": "dg-key"}, clear=False):
            from pipecat_mcp_server.infrastructure.service_factory import (
                create_tts_service,
            )

            result = create_tts_service("deepgram")
        assert result is not None

    def test_deepgram_tts_without_api_key_raises(self):
        """Deepgram TTS without DEEPGRAM_API_KEY should raise ValueError."""
        with patch.dict("os.environ", {}, clear=True):
            from pipecat_mcp_server.infrastructure.service_factory import (
                create_tts_service,
            )

            with pytest.raises(ValueError, match="DEEPGRAM_API_KEY"):
                create_tts_service("deepgram")


class TestCreateTtsServiceCartesia:
    """create_tts_service('cartesia') uses CartesiaTTSService."""

    def test_cartesia_tts_with_api_key(self):
        """Cartesia TTS with CARTESIA_API_KEY set should return a service."""
        # Ensure the mock module for cartesia is available
        if "pipecat.services.cartesia" not in sys.modules:
            mock = MagicMock()
            sys.modules["pipecat.services.cartesia"] = mock
        with patch.dict("os.environ", {"CARTESIA_API_KEY": "cart-key"}, clear=False):
            from pipecat_mcp_server.infrastructure.service_factory import (
                create_tts_service,
            )

            result = create_tts_service("cartesia")
        assert result is not None

    def test_cartesia_tts_without_api_key_raises(self):
        """Cartesia TTS without CARTESIA_API_KEY should raise ValueError."""
        with patch.dict("os.environ", {}, clear=True):
            from pipecat_mcp_server.infrastructure.service_factory import (
                create_tts_service,
            )

            with pytest.raises(ValueError, match="CARTESIA_API_KEY"):
                create_tts_service("cartesia")


class TestCreateTtsServiceLocal:
    """create_tts_service('local') uses PiperTTSService."""

    def test_local_tts_returns_service(self):
        """Local TTS should return a PiperTTSService instance."""
        # Ensure piper mock is available
        if "pipecat.services.piper" not in sys.modules:
            mock = MagicMock()
            sys.modules["pipecat.services.piper"] = mock
        from pipecat_mcp_server.infrastructure.service_factory import (
            create_tts_service,
        )

        result = create_tts_service("local")
        assert result is not None


class TestCreateTtsServiceKokoro:
    """create_tts_service('kokoro') uses KokoroTTSService."""

    def test_kokoro_tts_returns_service(self):
        """Kokoro TTS should return a KokoroTTSService instance."""
        # The kokoro_tts processor has heavy deps (pydantic + mocked Language enum).
        # Mock the entire processor module so the factory can import it cleanly.
        kokoro_mock = MagicMock()
        with patch.dict("sys.modules", {"pipecat_mcp_server.processors.kokoro_tts": kokoro_mock}):
            from pipecat_mcp_server.infrastructure.service_factory import (
                create_tts_service,
            )

            result = create_tts_service("kokoro")
        kokoro_mock.KokoroTTSService.assert_called_once_with(voice_id="af_heart")
        assert result is not None
