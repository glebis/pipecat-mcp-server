#
# Copyright (c) 2026, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Pipecat MCP Server for voice I/O.

This server exposes voice tools via the MCP protocol, enabling any MCP client
to have voice conversations with users through a Pipecat pipeline.

Tools:
    start: Initialize and start the voice agent.
    listen: Wait for user speech and return transcribed text.
    speak: Speak text to the user via text-to-speech.
    stop: Gracefully shut down the voice pipeline.
"""

import asyncio
import os
import sys

import aiohttp
from loguru import logger
from mcp.server.fastmcp import FastMCP

from pipecat_mcp_server import agent_ipc
from pipecat_mcp_server.agent_ipc import (
    check_startup_health,
    send_command,
    start_pipecat_process,
    stop_pipecat_process,
)

RUNNER_URL = "http://localhost:7860"
TRANSPORT = os.environ.get("TRANSPORT", "webrtc")

logger.remove()
logger.add(sys.stderr, level="DEBUG")

# Allowed voice presets and their required API keys
_PRESET_REQUIRED_KEYS: dict[str, list[str]] = {
    "groq": ["GROQ_API_KEY"],
    "deepgram": ["DEEPGRAM_API_KEY"],
    "cartesia": ["DEEPGRAM_API_KEY", "CARTESIA_API_KEY"],
    "local": [],
    "kokoro": [],
}

# Telephony transports that use WebSocket/ngrok (no local HTTP endpoint)
_TELEPHONY_TRANSPORTS = {"twilio", "telnyx", "plivo", "exotel"}


def _validate_preset() -> dict:
    """Validate VOICE_PRESET and check required API keys.

    Returns a dict with:
        preset: the preset name
        missing_keys: list of env var names that are required but not set
        error: (optional) present if the preset name is invalid
    """
    preset = os.environ.get("VOICE_PRESET", "groq")
    if preset not in _PRESET_REQUIRED_KEYS:
        return {
            "preset": preset,
            "missing_keys": [],
            "error": f"Invalid preset '{preset}'. Allowed: {', '.join(sorted(_PRESET_REQUIRED_KEYS))}",
        }
    required = _PRESET_REQUIRED_KEYS[preset]
    missing = [k for k in required if not os.environ.get(k)]
    return {"preset": preset, "missing_keys": missing}


async def _check_transport_readiness(transport: str) -> str:
    """Check transport-specific readiness after the child process is healthy.

    Returns a human-readable status string starting with "ok" on success,
    or an error message on failure.
    """
    if transport == "daily":
        # Daily transport: trigger the bot to join a Daily room via runner's HTTP endpoint.
        for attempt in range(5):
            await asyncio.sleep(1.0)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(f"{RUNNER_URL}/start", json={}) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            room_url = data.get("dailyRoom", "unknown")
                            logger.info(f"Bot joined Daily room: {room_url}")
                            return f"ok - join room: {room_url}"
                        else:
                            body = await resp.text()
                            return f"Runner /start returned {resp.status}: {body}"
            except aiohttp.ClientConnectorError:
                logger.debug(f"Runner not ready yet (attempt {attempt + 1}/5)")
                continue
        return "Runner HTTP server did not become available after 5 attempts"

    elif transport == "webrtc":
        # WebRTC transport: wait for runner to serve the playground UI.
        for attempt in range(5):
            await asyncio.sleep(1.0)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{RUNNER_URL}/client") as resp:
                        if resp.status == 200:
                            logger.info(f"WebRTC playground ready at {RUNNER_URL}/client")
                            return f"ok - open {RUNNER_URL}/client in your browser"
            except aiohttp.ClientConnectorError:
                logger.debug(f"Runner not ready yet (attempt {attempt + 1}/5)")
                continue
        return "Runner HTTP server did not become available after 5 attempts"

    elif transport == "livekit":
        # LiveKit connects to an external WebRTC server; no local HTTP endpoint.
        return "ok - LiveKit transport ready"

    elif transport in _TELEPHONY_TRANSPORTS:
        # Telephony transports use WebSocket via ngrok; no local HTTP endpoint.
        return f"ok - {transport} telephony ready"

    else:
        # Unknown transport: assume it started correctly.
        return f"ok - transport '{transport}' started"


# Create MCP server
mcp = FastMCP(name="pipecat-mcp-server", host="localhost", port=9090)


@mcp.tool()
async def start() -> str:
    """Start a new Pipecat Voice Agent.

    Once the voice agent has started you can continuously use the listen() and
    speak() tools to talk to the user.

    Returns "ok" if the agent was started successfully, or an error message.
    """
    # Validate voice preset and API keys before starting the child process
    validation = _validate_preset()
    preset = validation["preset"]

    if "error" in validation:
        return validation["error"]

    if validation["missing_keys"]:
        keys = ", ".join(validation["missing_keys"])
        return (
            f"Missing API key(s) for '{preset}' preset: {keys}. Set the key or change VOICE_PRESET."
        )

    error = start_pipecat_process()
    if error:
        return error

    # Async health check (replaces blocking time.sleep in agent_ipc)
    health_error = await check_startup_health(agent_ipc._pipecat_process, agent_ipc._response_queue)
    if health_error:
        return health_error

    readiness = await _check_transport_readiness(TRANSPORT)

    # Append preset info to success responses
    if readiness.startswith("ok"):
        return f"{readiness} (preset: {preset})"
    return readiness


@mcp.tool()
async def listen() -> str:
    """Listen for user speech and return the transcribed text."""
    result = await send_command("listen")
    if "error" in result:
        raise RuntimeError(result["error"])
    if "text" not in result:
        raise RuntimeError(f"Unexpected response from listen: {result}")
    return result["text"]


@mcp.tool()
async def speak(text: str) -> bool:
    """Speak the given text to the user using text-to-speech.

    Returns true if the agent spoke the text, false otherwise.
    """
    result = await send_command("speak", text=text)
    if "error" in result:
        raise RuntimeError(result["error"])
    return True


@mcp.tool()
async def list_windows() -> list[dict]:
    """List all open windows visible to the screen capture backend.

    Returns a list of objects with title, app_name, and window_id fields.

    Note: Multiple windows may appear for the same app (e.g., tabs, child
    frames). When in doubt about which window the user wants, ask for
    clarification before capturing.
    """
    result = await send_command("list_windows")
    return result.get("windows", [])


@mcp.tool()
async def screen_capture(window_id: int | None = None) -> int | None:
    """Start or switch screen capture to a window or full screen.

    Captures are streamed through the Pipecat pipeline. Use list_windows()
    to find available window IDs.

    Args:
        window_id: Window ID to capture (from list_windows()). If not provided,
            captures the full screen.

    Returns the window ID if the window was found, or None if it was not found
    or capturing full screen.

    """
    result = await send_command("screen_capture", window_id=window_id)
    if "error" in result:
        raise RuntimeError(result["error"])
    return result.get("window_id")


@mcp.tool()
async def capture_screenshot() -> str:
    """Take a look at what's on screen.

    Use this when the user asks what you can see. Screen capture must
    already be started via screen_capture().

    Returns the absolute path to the saved image file.
    """
    result = await send_command("capture_screenshot")
    return result.get("path", "No screen capture available.")


@mcp.tool()
async def stop() -> bool:
    """Stop the voice pipeline and clean up resources.

    Call this when the voice conversation is complete to gracefully
    shut down the voice agent.

    Returns true if the agent was stopped successfully, false otherwise.
    """
    await send_command("stop")
    return True


def main():
    """Start the Pipecat MCP server.

    Runs the MCP server using stdio for communication with the MCP client.
    When the server exits, any running Pipecat agent process is cleaned up.
    """
    try:
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("Ctrl-C detected, exiting!")
    finally:
        stop_pipecat_process()


if __name__ == "__main__":
    main()
