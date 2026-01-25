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

from mcp.server.fastmcp import FastMCP

from pipecat_mcp_server.agent_ipc import send_command, start_pipecat_process, stop_pipecat_process

# Create MCP server
mcp = FastMCP(name="pipecat-mcp-server")


@mcp.tool()
async def start():
    """Start a new Pipecat Voice Agent.

    Once the voice agent has started you can continuously use the listen() and
    speak() tools to talk to the user.
    """
    start_pipecat_process()


@mcp.tool()
async def listen() -> str:
    """Listen for user speech and return the transcribed text.

    This returns the next complete utterance.
    """
    try:
        result = await send_command("listen")
        return result["text"]
    except asyncio.CancelledError:
        stop_pipecat_process()
        raise


@mcp.tool()
async def speak(text: str):
    """Speak text to the user using text-to-speech.

    Args:
        text: The text to speak to the user

    """
    try:
        await send_command("speak", text=text)
    except asyncio.CancelledError:
        stop_pipecat_process()
        raise


@mcp.tool()
async def stop():
    """Stop the voice pipeline and clean up resources.

    Call this when the voice conversation is complete to gracefully
    shut down the voice agent.
    """
    await send_command("stop")


def main():
    """Start the Pipecat MCP server.

    Runs the MCP server using stdio for communication with the MCP client.
    When the server exits, any running Pipecat agent process is cleaned up.
    """
    atexit.register(stop_pipecat_process)
    mcp.run()


if __name__ == "__main__":
    main()
