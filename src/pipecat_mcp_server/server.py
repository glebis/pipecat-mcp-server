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
import atexit
import sys

from loguru import logger
from mcp.server.fastmcp import FastMCP

from pipecat_mcp_server.agent_ipc import send_command, start_pipecat_process, stop_pipecat_process

# Configure any loguru logging to stderr, not stdout
logger.remove()
logger.add(sys.stderr, level="DEBUG")

# Create MCP server
mcp = FastMCP(name="pipecat-mcp-server")


@mcp.tool()
async def start() -> bool:
    """Start a new Pipecat Voice Agent.

    Once the voice agent has started you can continuously use the listen() and
    speak() tools to talk to the user.

    Returns true if the agent was started successfully, false otherwise.
    """
    start_pipecat_process()
    return True


@mcp.tool()
async def listen() -> str:
    """Listen for user speech and return the transcribed text."""
    result = await send_command("listen")
    return result["text"]


@mcp.tool()
async def speak(text: str) -> bool:
    """Speak the given text to the user using text-to-speech.

    Returns true if the agent spoke the text, false otherwise.
    """
    await send_command("speak", text=text)
    return True


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
    atexit.register(stop_pipecat_process)
    mcp.run()


if __name__ == "__main__":
    main()
