#
# Copyright (c) 2026, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Inter-process communication for the Pipecat MCP server.

This module manages the IPC queues and child process lifecycle for communication
between the MCP server (parent) and the Pipecat voice agent (child). The child
process runs separately to avoid stdio collisions with the MCP protocol.
"""

import asyncio
import multiprocessing
import queue as queue_module
from typing import Optional

from loguru import logger

# Use spawn to avoid issues with forking from async context Fork copies the
# parent's state (event loop, file descriptors, locks) which can cause
# issues. Spawn creates a fresh Python interpreter.
multiprocessing.set_start_method("spawn", force=True)

_cmd_queue: Optional[multiprocessing.Queue] = None
_response_queue: Optional[multiprocessing.Queue] = None
_pipecat_process: Optional[multiprocessing.Process] = None


def _cleanup():
    """Clean up the pipecat child process."""
    global _pipecat_process, _cmd_queue, _response_queue

    logger.debug(f"Checking if Pipecat MCP Agent process is actually running...")
    if _pipecat_process:
        # Force terminate if still alive
        if _pipecat_process.is_alive():
            logger.debug(f"Terminating Pipecat MCP Agent process (PID {_pipecat_process.ident})")
            _pipecat_process.terminate()
            _pipecat_process.join(timeout=1.0)

        # Kill if terminate didn't work
        if _pipecat_process.is_alive():
            logger.debug(f"Killing Pipecat MCP Agent process (PID {_pipecat_process.ident})")
            _pipecat_process.kill()
            _pipecat_process.join(timeout=1.0)

        _pipecat_process = None


def _cleanup_port(port: int = 7860) -> tuple[list[str], list[str]]:
    """Kill pipecat-owned processes on the given port, warn about others.

    Returns:
        Tuple of (killed_pids, warned_pids).

    """
    import subprocess

    killed = []
    warned = []
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"], capture_output=True, text=True, timeout=5
        )
        if not result.stdout.strip():
            return killed, warned
        for pid in result.stdout.strip().split("\n"):
            pid = pid.strip()
            if not pid:
                continue
            # Check what process this is
            try:
                ps_result = subprocess.run(
                    ["ps", "-p", pid, "-o", "command="], capture_output=True, text=True, timeout=5
                )
                cmd_line = ps_result.stdout.strip().lower()
                if "python" in cmd_line or "pipecat" in cmd_line:
                    logger.warning(f"Killing pipecat process {pid} on port {port}")
                    subprocess.run(["kill", "-9", pid], timeout=5)
                    killed.append(pid)
                else:
                    logger.warning(
                        f"Port {port} occupied by non-pipecat process {pid}: "
                        f"{ps_result.stdout.strip()}"
                    )
                    warned.append(pid)
            except Exception:
                warned.append(pid)
    except Exception as e:
        logger.debug(f"Port cleanup check failed: {e}")
    return killed, warned


async def check_startup_health(process, response_queue, delay: float = 1.0) -> str | None:
    """Check if the child process survived startup.

    Uses asyncio.sleep instead of time.sleep to avoid blocking the event loop.

    Returns:
        None if process is alive, or error message string if it died.

    """
    await asyncio.sleep(delay)
    if process.is_alive():
        return None

    error_msg = None
    try:
        if response_queue:
            msg = response_queue.get_nowait()
            if isinstance(msg, dict) and "_startup_error" in msg:
                error_msg = msg["_startup_error"]
    except Exception:
        pass

    exit_code = process.exitcode
    if error_msg:
        return f"Voice agent crashed on startup:\n{error_msg}"
    return f"Voice agent process exited immediately (exit code: {exit_code})"


def start_pipecat_process() -> str | None:
    """Start the Pipecat child process.

    Creates IPC queues and spawns a new process to run the Pipecat voice agent.
    Cleans up any existing process before starting a new one.

    Returns:
        None if started successfully, or an error message string if startup failed.

    """
    global _cmd_queue, _response_queue, _pipecat_process

    # Clean up any existing process first
    _cleanup()

    # Kill any orphaned pipecat processes holding the runner port
    _cleanup_port(7860)

    # Create IPC queues using spawn context
    _cmd_queue = multiprocessing.Queue()
    _response_queue = multiprocessing.Queue()

    # Capture parent sys.argv so the child process can forward CLI args
    # (e.g. --transport daily) to the pipecat runner
    import os
    import sys

    parent_argv = list(sys.argv)

    # Inject transport flag from env var
    transport = os.environ.get("TRANSPORT", "webrtc")
    if transport == "daily":
        if "--transport" not in parent_argv and "-d" not in parent_argv:
            parent_argv.extend(["-d"])
    else:
        if "--transport" not in parent_argv:
            parent_argv.extend(["--transport", transport])

    # Start pipecat as separate process
    logger.debug(f"Starting Pipecat MCP Agent process...")
    _pipecat_process = multiprocessing.Process(
        target=run_pipecat_process,
        args=(_cmd_queue, _response_queue, parent_argv),
    )
    _pipecat_process.start()
    logger.debug(f"Started Pipecat MCP Agent process (PID {_pipecat_process.ident})")

    return None


def stop_pipecat_process():
    """Stop the pipecat child process (explicit cleanup)."""
    logger.debug(f"Stopping Pipecat MCP Agent process...")
    _cleanup()
    logger.debug(f"Stopped Pipecat MCP Agent")


def run_pipecat_process(
    cmd_queue: multiprocessing.Queue,
    response_queue: multiprocessing.Queue,
    parent_argv: list | None = None,
):
    """Entry point for the Pipecat child process.

    Initializes logging and runs the Pipecat main loop. This function is called
    in a separate process to avoid stdio collisions with the MCP protocol.

    Args:
        cmd_queue: Queue for receiving commands from the MCP server.
        response_queue: Queue for sending responses back to the MCP server.
        parent_argv: CLI args from the parent process, forwarded so the pipecat
            runner can parse transport flags (e.g. --transport daily).

    """
    global _cmd_queue, _response_queue

    import os
    import sys
    import traceback

    _cmd_queue = cmd_queue
    _response_queue = response_queue

    # Forward parent CLI args so pipecat runner sees --transport, -d, etc.
    if parent_argv is not None:
        sys.argv = parent_argv

    # Change to package directory so pipecat_main() can find bot.py
    package_dir = os.path.dirname(__file__)
    os.chdir(package_dir)

    try:
        # Import and run the pipecat main (which will call our bot() function)
        from pipecat.runner.run import main as pipecat_main

        logger.debug("Pipecat MCP Agent process started. Launching Pipecat runner!")

        pipecat_main()

        logger.debug("Pipecat runner is done...")
    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        logger.error(f"Pipecat child process crashed: {error_msg}")
        # Send error back to parent via response queue so start() can report it
        try:
            response_queue.put({"_startup_error": error_msg})
        except Exception:
            pass


async def send_response(response: dict):
    """Send a response from the child process to the MCP server.

    Args:
        response: Response dictionary to send.

    Raises:
        RuntimeError: If the Pipecat process has not been started.

    """
    if _response_queue is None:
        raise RuntimeError("Pipecat process not started")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _response_queue.put, response)


async def read_request() -> dict:
    """Read a request from the MCP server in the child process.

    Blocks until a command is available in the queue.

    Returns:
        Request dictionary containing the command and arguments.

    Raises:
        RuntimeError: If the Pipecat process has not been started.

    """
    if _cmd_queue is None:
        raise RuntimeError("Pipecat process not started")
    loop = asyncio.get_event_loop()
    request = await loop.run_in_executor(None, _cmd_queue.get)
    return request


def _get_with_timeout(queue: multiprocessing.Queue, timeout: float = 0.5):
    """Get from queue with timeout to allow cancellation.

    Args:
        queue: The queue to read from.
        timeout: Timeout in seconds.

    Returns:
        Item from the queue.

    Raises:
        TimeoutError: If the timeout expires before an item is available.

    """
    try:
        return queue.get(timeout=timeout)
    except queue_module.Empty:
        raise TimeoutError("Queue get timed out")


def _check_process_alive():
    """Check if the pipecat process is still alive."""
    if _pipecat_process and not _pipecat_process.is_alive():
        # Try to get error details from the response queue
        error_msg = None
        try:
            if _response_queue:
                msg = _response_queue.get_nowait()
                if isinstance(msg, dict) and "_startup_error" in msg:
                    error_msg = msg["_startup_error"]
        except Exception:
            pass
        detail = f": {error_msg}" if error_msg else f" (exit code: {_pipecat_process.exitcode})"
        raise RuntimeError(f"Voice agent process has stopped{detail}")


async def _wait_for_command_response(timeout: float = 0.5) -> dict:
    """Wait for response from child process with health checks."""
    if _response_queue is None:
        raise RuntimeError("Pipecat process not started")

    loop = asyncio.get_event_loop()

    while True:
        try:
            return await loop.run_in_executor(None, _get_with_timeout, _response_queue, timeout)
        except TimeoutError:
            _check_process_alive()
            await asyncio.sleep(0)  # Yield to allow cancellation


async def send_command(cmd: str, **kwargs) -> dict:
    """Send a command to the Pipecat child process and wait for response.

    Args:
        cmd: Command name (e.g., "listen", "speak", "stop").
        **kwargs: Additional arguments for the command.

    Returns:
        Response dictionary from the child process.

    """
    if _cmd_queue is None or _response_queue is None:
        raise RuntimeError("Pipecat process not started")

    request = {"cmd": cmd, **kwargs}

    # Send request to child process
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _cmd_queue.put, request)

    # Wait for response with cancellation support
    try:
        response = await _wait_for_command_response()
    except asyncio.CancelledError:
        logger.info(f"Command '{cmd}' was cancelled")
        raise

    # Skip startup error messages that may be queued from previous crashes
    if isinstance(response, dict) and "_startup_error" in response:
        logger.warning(f"Skipping stale startup error in queue, re-waiting...")
        response = await _wait_for_command_response()

    # Check for errors in response
    if "error" in response:
        error_message = response["error"]
        logger.error(f"Error running command '{cmd}': {error_message}")

    logger.debug(f"Command '{cmd}' response: {response}")
    return response
