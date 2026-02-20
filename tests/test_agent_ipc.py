"""Tests for agent_ipc port cleanup and startup health check."""

from unittest.mock import MagicMock, patch

import pytest

from pipecat_mcp_server.agent_ipc import _cleanup_port, check_startup_health


class TestCleanupPort:
    """pmc-ctd: Port cleanup should only kill pipecat-owned processes."""

    def test_kills_python_process_on_port(self):
        """Should kill a python/pipecat process occupying the port."""
        mock_lsof = MagicMock(stdout="12345\n", returncode=0)
        mock_ps = MagicMock(stdout="python pipecat", returncode=0)

        with patch("subprocess.run", side_effect=[mock_lsof, mock_ps, MagicMock()]) as mock_run:
            result = _cleanup_port(7860)

        assert result.killed == ["12345"]
        assert result.warned == []

    def test_warns_about_non_pipecat_process(self):
        """Should NOT kill and should warn about non-pipecat processes."""
        mock_lsof = MagicMock(stdout="99999\n", returncode=0)
        mock_ps = MagicMock(stdout="nginx: master process", returncode=0)

        with patch("subprocess.run", side_effect=[mock_lsof, mock_ps]) as mock_run:
            result = _cleanup_port(7860)

        assert result.killed == []
        assert result.warned == ["99999"]

    def test_no_processes_on_port(self):
        """When no processes occupy the port, should return empty lists."""
        mock_lsof = MagicMock(stdout="", returncode=1)

        with patch("subprocess.run", return_value=mock_lsof):
            result = _cleanup_port(7860)

        assert result.killed == []
        assert result.warned == []

    def test_handles_lsof_failure_gracefully(self):
        """If lsof fails, should return empty lists without raising."""
        with patch("subprocess.run", side_effect=FileNotFoundError("lsof not found")):
            result = _cleanup_port(7860)

        assert result.killed == []
        assert result.warned == []


class TestCheckStartupHealth:
    """pmc-5i4: Startup health check should be async-friendly."""

    @pytest.mark.asyncio
    async def test_returns_none_when_process_alive(self):
        """Should return None when process is still running."""
        mock_process = MagicMock()
        mock_process.is_alive.return_value = True

        result = await check_startup_health(mock_process, None)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_error_when_process_dead(self):
        """Should return error string when process died."""
        mock_process = MagicMock()
        mock_process.is_alive.return_value = False
        mock_process.exitcode = 1

        result = await check_startup_health(mock_process, None)
        assert result is not None
        assert "exit code: 1" in result

    @pytest.mark.asyncio
    async def test_returns_startup_error_from_queue(self):
        """Should extract startup error message from response queue."""
        mock_process = MagicMock()
        mock_process.is_alive.return_value = False
        mock_process.exitcode = 1

        mock_queue = MagicMock()
        mock_queue.get_nowait.return_value = {"_startup_error": "ImportError: no module"}

        result = await check_startup_health(mock_process, mock_queue)
        assert "ImportError: no module" in result


class TestCleanupPortReturnsDataclass:
    """_cleanup_port should return a PortCleanupResult dataclass."""

    def test_cleanup_port_returns_dataclass(self):
        """Verify _cleanup_port returns a PortCleanupResult with correct fields."""
        from pipecat_mcp_server.agent_ipc import PortCleanupResult

        # Simulate lsof returning no PIDs (port is free)
        mock_lsof = MagicMock()
        mock_lsof.stdout = ""

        with patch("subprocess.run", return_value=mock_lsof):
            result = _cleanup_port(7860)

        assert isinstance(result, PortCleanupResult)
        assert result.killed == []
        assert result.warned == []
        assert result.port_available is True


class TestStartReturnsErrorWhenPortOccupied:
    """start() should return an error string when port is occupied."""

    def test_start_returns_error_when_port_occupied(self):
        """When _cleanup_port returns port_available=False with warned PIDs, start() returns error."""
        from pipecat_mcp_server.agent_ipc import PipecatProcessManager, PortCleanupResult

        manager = PipecatProcessManager()

        # Create a PortCleanupResult indicating port is occupied
        occupied_result = PortCleanupResult(
            killed=[],
            warned=["9999"],
            port_available=False,
            stale_pids=[],
        )

        with (
            patch(
                "pipecat_mcp_server.agent_ipc._cleanup_port",
                return_value=occupied_result,
            ),
            patch("pipecat_mcp_server.agent_ipc.multiprocessing.Process") as mock_proc_cls,
            patch("pipecat_mcp_server.agent_ipc.multiprocessing.Queue"),
        ):
            result = manager.start()

        # Should return an error string mentioning the PID
        assert result is not None
        assert "9999" in result
        assert "occupied" in result.lower() or "Port" in result

        # Should NOT have spawned a child process
        mock_proc_cls.return_value.start.assert_not_called()


class TestCleanupPortResultHasStalePidsField:
    """PortCleanupResult should have a stale_pids field for stale process detection."""

    def test_cleanup_port_result_has_stale_pids_field(self):
        """PortCleanupResult should have a stale_pids field populated by _cleanup_port."""
        from pipecat_mcp_server.agent_ipc import PortCleanupResult

        # Simulate: no port holders, but ps aux finds a stale pipecat-mcp-server process
        mock_lsof = MagicMock(stdout="", returncode=1)
        mock_ps_aux = MagicMock(
            stdout="user  55555  0.0  0.1 python pipecat-mcp-server\n",
            returncode=0,
        )

        with (
            patch("subprocess.run", side_effect=[mock_lsof, mock_ps_aux]),
            patch("os.getpid", return_value=11111),
        ):
            result = _cleanup_port(7860)

        assert isinstance(result, PortCleanupResult)
        assert hasattr(result, "stale_pids")
        assert "55555" in result.stale_pids


class TestStartWarnsAboutStaleProcesses:
    """start() should log a warning when stale pipecat processes are detected."""

    def test_start_warns_about_stale_processes(self):
        """When stale_pids is non-empty, start() should log a warning but still proceed."""
        from pipecat_mcp_server.agent_ipc import PipecatProcessManager, PortCleanupResult

        manager = PipecatProcessManager()

        # Port is available, but there are stale processes
        stale_result = PortCleanupResult(
            killed=[],
            warned=[],
            port_available=True,
            stale_pids=["77777"],
        )

        with (
            patch(
                "pipecat_mcp_server.agent_ipc._cleanup_port",
                return_value=stale_result,
            ),
            patch("pipecat_mcp_server.agent_ipc.multiprocessing.Process") as mock_proc_cls,
            patch("pipecat_mcp_server.agent_ipc.multiprocessing.Queue") as mock_queue_cls,
            patch("pipecat_mcp_server.agent_ipc.logger") as mock_logger,
        ):
            mock_proc = MagicMock()
            mock_proc.ident = 12345
            mock_proc_cls.return_value = mock_proc
            mock_queue_cls.return_value = MagicMock()

            result = manager.start()

        # Should still start successfully
        assert result is None
        mock_proc.start.assert_called_once()

        # Should have logged a warning about the stale PID
        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
        stale_warning_found = any("77777" in call for call in warning_calls)
        assert stale_warning_found, (
            f"Expected a warning about stale PID 77777, got: {warning_calls}"
        )
