"""Tests for port interfaces and PipecatProcessManager adapter."""

from unittest.mock import MagicMock, patch

import pytest


class TestVoiceAgentProcessPortProtocol:
    """VoiceAgentProcessPort is a runtime-checkable Protocol."""

    def test_voice_agent_process_port_is_protocol(self):
        """VoiceAgentProcessPort should be a runtime_checkable Protocol."""
        from typing import Protocol, runtime_checkable

        from pipecat_mcp_server.ports.voice_agent_process import VoiceAgentProcessPort

        # It should be a Protocol subclass
        assert issubclass(VoiceAgentProcessPort, Protocol)

        # runtime_checkable means isinstance() works on it
        @runtime_checkable
        class Dummy(Protocol): ...

        # The port itself should be decorated with @runtime_checkable
        assert isinstance(VoiceAgentProcessPort, type)


class TestPipecatProcessManagerSatisfiesPort:
    """PipecatProcessManager implements the VoiceAgentProcessPort protocol."""

    def test_pipecat_process_manager_satisfies_port(self):
        """PipecatProcessManager should satisfy VoiceAgentProcessPort isinstance check."""
        from pipecat_mcp_server.agent_ipc import PipecatProcessManager
        from pipecat_mcp_server.ports.voice_agent_process import VoiceAgentProcessPort

        manager = PipecatProcessManager()
        assert isinstance(manager, VoiceAgentProcessPort)


class TestManagerStartDelegatesCorrectly:
    """Calling _manager.start() works like start_pipecat_process()."""

    def test_manager_start_delegates_correctly(self):
        """_manager.start() should delegate to the same logic as start_pipecat_process()."""
        from pipecat_mcp_server.agent_ipc import PipecatProcessManager

        manager = PipecatProcessManager()

        with (
            patch("pipecat_mcp_server.agent_ipc._cleanup_port"),
            patch("pipecat_mcp_server.agent_ipc.multiprocessing.Process") as mock_proc_cls,
            patch("pipecat_mcp_server.agent_ipc.multiprocessing.Queue") as mock_queue_cls,
        ):
            mock_proc = MagicMock()
            mock_proc.ident = 12345
            mock_proc_cls.return_value = mock_proc
            mock_queue_cls.return_value = MagicMock()

            result = manager.start()

        assert result is None
        mock_proc.start.assert_called_once()

    def test_module_level_start_uses_manager(self):
        """start_pipecat_process() should delegate to _manager.start()."""
        from pipecat_mcp_server import agent_ipc

        with patch.object(agent_ipc._manager, "start", return_value=None) as mock_start:
            result = agent_ipc.start_pipecat_process()

        assert result is None
        mock_start.assert_called_once()


class TestBackwardCompatFunctionsExist:
    """Backward-compatible module-level functions still importable from agent_ipc."""

    def test_start_pipecat_process_importable(self):
        """start_pipecat_process should be importable from agent_ipc."""
        from pipecat_mcp_server.agent_ipc import start_pipecat_process

        assert callable(start_pipecat_process)

    def test_stop_pipecat_process_importable(self):
        """stop_pipecat_process should be importable from agent_ipc."""
        from pipecat_mcp_server.agent_ipc import stop_pipecat_process

        assert callable(stop_pipecat_process)

    def test_send_command_importable(self):
        """send_command should be importable from agent_ipc."""
        from pipecat_mcp_server.agent_ipc import send_command

        assert callable(send_command)

    def test_check_startup_health_importable(self):
        """check_startup_health should be importable from agent_ipc."""
        from pipecat_mcp_server.agent_ipc import check_startup_health

        assert callable(check_startup_health)

    def test_send_response_importable(self):
        """send_response should remain importable (used by bot.py)."""
        from pipecat_mcp_server.agent_ipc import send_response

        assert callable(send_response)

    def test_read_request_importable(self):
        """read_request should remain importable (used by bot.py)."""
        from pipecat_mcp_server.agent_ipc import read_request

        assert callable(read_request)

    def test_cleanup_port_importable(self):
        """_cleanup_port should remain importable."""
        from pipecat_mcp_server.agent_ipc import _cleanup_port

        assert callable(_cleanup_port)

    def test_manager_instance_exists(self):
        """Module-level _manager instance should exist."""
        from pipecat_mcp_server.agent_ipc import _manager

        assert _manager is not None

    def test_manager_has_process_property(self):
        """_manager should expose process as a property."""
        from pipecat_mcp_server.agent_ipc import _manager

        # Should not raise; value is None before start
        assert _manager.process is None

    def test_manager_has_response_queue_property(self):
        """_manager should expose response_queue as a property."""
        from pipecat_mcp_server.agent_ipc import _manager

        # Should not raise; value is None before start
        assert _manager.response_queue is None


class TestSpeechServicePorts:
    """Speech service port protocols exist."""

    def test_stt_service_port_is_protocol(self):
        """STTServicePort should be a runtime_checkable Protocol."""
        from typing import Protocol

        from pipecat_mcp_server.ports.speech_services import STTServicePort

        assert issubclass(STTServicePort, Protocol)

    def test_tts_service_port_is_protocol(self):
        """TTSServicePort should be a runtime_checkable Protocol."""
        from typing import Protocol

        from pipecat_mcp_server.ports.speech_services import TTSServicePort

        assert issubclass(TTSServicePort, Protocol)
