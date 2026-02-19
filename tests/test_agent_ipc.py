"""Tests for agent_ipc port cleanup and startup health check."""

import pytest
from unittest.mock import patch, MagicMock
from pipecat_mcp_server.agent_ipc import _cleanup_port, check_startup_health


class TestCleanupPort:
    """pmc-ctd: Port cleanup should only kill pipecat-owned processes."""

    def test_kills_python_process_on_port(self):
        """Should kill a python/pipecat process occupying the port."""
        mock_lsof = MagicMock(stdout="12345\n", returncode=0)
        mock_ps = MagicMock(stdout="python pipecat", returncode=0)

        with patch("subprocess.run", side_effect=[mock_lsof, mock_ps, MagicMock()]) as mock_run:
            killed, warned = _cleanup_port(7860)

        assert killed == ["12345"]
        assert warned == []

    def test_warns_about_non_pipecat_process(self):
        """Should NOT kill and should warn about non-pipecat processes."""
        mock_lsof = MagicMock(stdout="99999\n", returncode=0)
        mock_ps = MagicMock(stdout="nginx: master process", returncode=0)

        with patch("subprocess.run", side_effect=[mock_lsof, mock_ps]) as mock_run:
            killed, warned = _cleanup_port(7860)

        assert killed == []
        assert warned == ["99999"]

    def test_no_processes_on_port(self):
        """When no processes occupy the port, should return empty lists."""
        mock_lsof = MagicMock(stdout="", returncode=1)

        with patch("subprocess.run", return_value=mock_lsof):
            killed, warned = _cleanup_port(7860)

        assert killed == []
        assert warned == []

    def test_handles_lsof_failure_gracefully(self):
        """If lsof fails, should return empty lists without raising."""
        with patch("subprocess.run", side_effect=FileNotFoundError("lsof not found")):
            killed, warned = _cleanup_port(7860)

        assert killed == []
        assert warned == []


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
        import multiprocessing
        mock_process = MagicMock()
        mock_process.is_alive.return_value = False
        mock_process.exitcode = 1

        mock_queue = MagicMock()
        mock_queue.get_nowait.return_value = {"_startup_error": "ImportError: no module"}

        result = await check_startup_health(mock_process, mock_queue)
        assert "ImportError: no module" in result
