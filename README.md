<h1><div align="center">
 <img alt="Pipecat MCP Server" width="300px" height="auto" src="https://github.com/pipecat-ai/pipecat-mcp-server/raw/refs/heads/main/pipecat.png">
</div></h1>

[![PyPI](https://img.shields.io/pypi/v/pipecat-ai-mcp-server)](https://pypi.org/project/pipecat-ai-mcp-server) [![Discord](https://img.shields.io/discord/1239284677165056021)](https://discord.gg/pipecat)

# Pipecat MCP Server

Pipecat MCP Server gives your AI agents a voice using [Pipecat](https://github.com/pipecat-ai/pipecat). It should work with any [MCP](https://modelcontextprotocol.io/)-compatible client:

The Pipecat MCP Server exposes **voice-related** and **screen capture** tools to MCP-compatible clients, but **it does not itself provide microphone or speaker access**.

Audio input/output is handled by a **separate audio/video transport**, such as:

- **Pipecat Playground** (local browser UI)
- **Daily** (WebRTC room)
- **Phone providers** (Twilio, Telnyx, etc.)

> **MCP clients like Cursor, Claude Code, and Codex control the agent, but they are not audio devices.**
> To hear, speak or see, you must connect via one of the audio transports.

<p align="center"><video src="https://github.com/user-attachments/assets/0ad14e37-2de7-46df-870a-167aa667df16" width="500" controls></video></p>

## 🧭 Getting started

### Prerequisites

- Python 3.10 or later
- [uv](https://docs.astral.sh/uv/getting-started/installation/) package manager

By default, the voice agent uses [Groq](https://groq.com/) cloud services (Whisper STT + Orpheus TTS). Set `GROQ_API_KEY` to get started. See [Voice Presets](#-voice-presets) below for alternative configurations including fully local options.

### Installation

Clone this repository and install from source:

```bash
git clone https://github.com/glebis/pipecat-mcp-server.git
cd pipecat-mcp-server
uv tool install -e .
```

This will install the `pipecat-mcp-server` command from your local checkout, so any changes you make are immediately available.

> **Note**: The upstream PyPI package (`uv tool install pipecat-ai-mcp-server`) installs the official release from [pipecat-ai/pipecat-mcp-server](https://github.com/pipecat-ai/pipecat-mcp-server). This fork includes additional DDD architecture improvements, port conflict detection, and expanded test coverage.

## Running the server

Start the server:

```bash
pipecat-mcp-server
```

The server uses **stdio** transport by default and is designed to be launched by an MCP client (Claude Code, Cursor, Codex). After the MCP client calls the `start` tool, the voice agent's audio playground becomes available at `http://localhost:7860`.

## 🎙️ Voice Presets

Set `VOICE_PRESET` to switch between STT/TTS combinations:

| Preset | STT | TTS | Requires | Notes |
|--------|-----|-----|----------|-------|
| `groq` (default) | Groq Whisper | Groq Orpheus | `GROQ_API_KEY` | Supports Orpheus emotion tags natively |
| `deepgram` | Deepgram Nova-3 | Deepgram Aura | `DEEPGRAM_API_KEY` | Streaming, low latency |
| `cartesia` | Deepgram Nova-3 | Cartesia Sonic | `DEEPGRAM_API_KEY`, `CARTESIA_API_KEY` | Lowest latency, Orpheus tags converted to SSML |
| `local` | MLX Whisper | Piper TTS | None | Fully local, macOS only |
| `kokoro` | MLX Whisper | Kokoro TTS | None | Fully local, macOS, better voice quality |

Example:

```bash
export VOICE_PRESET=cartesia
export DEEPGRAM_API_KEY=your-key
export CARTESIA_API_KEY=your-key
pipecat-mcp-server
```

### Emotion tag handling

The agent processes [Orpheus-style emotion tags](https://huggingface.co/canopylabs/orpheus-tts-0.1-finetune-prod) differently per preset:

- **groq**: Tags like `[cheerful]`, `<laugh>` pass through natively
- **cartesia**: Bracket tags convert to Cartesia SSML (`[cheerful]` -> `<emotion value="happy"/>`)
- **deepgram/local/kokoro**: All emotion markup is stripped

## Auto-approving permissions

For hands-free voice conversations, you will need to auto-approve tool permissions. Otherwise, your agent will prompt for confirmation, which interrupts the conversation flow.

> ⚠️ **Warning**: Enabling broad permissions is at your own risk.

## Installing the Pipecat skill (recommended)

The [Pipecat skill](.claude/skills/pipecat/SKILL.md) provides a better voice conversation experience. It asks for verbal confirmation before making changes to files, adding a layer of safety when using broad permissions.

Alternatively, just tell your agent something like `Let's have a voice conversation`. In this case, the agent won't ask for verbal confirmation before making changes.

## 🖥️ Screen Capture & Analysis

Screen capture lets you stream your screen (or a specific window) to your configured transport, and ask the agent to help with what it sees.

For example:
- *"capture my browser window"* — starts streaming that window
- *"what's causing this error?"* — the agent analyzes the screen and helps debug
- *"how does this UI look?"* — get feedback on your design

**Supported platforms:**

- **macOS** — uses ScreenCaptureKit for true window-level capture (not affected by overlapping windows)
- **Linux (X11)** — uses Xlib for window and full-screen capture

## 💻 MCP Client: Claude Code

### Adding the MCP server

Register the MCP server using stdio transport:

```bash
claude mcp add pipecat --transport stdio pipecat-mcp-server --scope user
```

Scope options:
- `local`: Stored in `~/.claude.json`, applies only to your project
- `user`: Stored in `~/.claude.json`, applies to all projects
- `project`: Stored in `.mcp.json` in your project directory

### Auto-approving permissions

Create `.claude/settings.local.json` in your project directory:

```json
{
  "permissions": {
    "allow": [
      "Bash",
      "Read",
      "Edit",
      "Write",
      "WebFetch",
      "WebSearch",
      "mcp__pipecat__*"
    ]
  }
}
```

This grants permissions for bash commands, file operations, web fetching and searching, and all Pipecat MCP tools without prompting. See [available tools](https://code.claude.com/docs/en/settings#tools-available-to-claude) if you need to grant more permissions.

### Starting a voice conversation

1. Install the Pipecat skill into `.claude/skills/pipecat/SKILL.md`
2. Start the Pipecat MCP Server.
3. Connect to an audio transport (see **🗣️ Connecting to the voice agent** below).
4. Run `/pipecat`.

## 💻 MCP Client: Cursor

### Adding the MCP server

Register the MCP server by editing `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "pipecat": {
      "url": "http://localhost:9090/mcp"
    }
  }
}
```

### Auto-approving permissions

Go to the `Auto-Run` agent settings and configure it to `Run Everything`.

### Starting a voice conversation

1. Install the Pipecat skill into `.claude/skills/pipecat/SKILL.md` (Cursor supports the Claude skills location).
2. Start the Pipecat MCP Server.
3. Connect to an audio transport (see **🗣️ Connecting to the voice agent** below).
4. In a **new Cursor agent**, run `/pipecat`.

## 💻 MCP Client: OpenAI Codex

### Adding the MCP server

Register the MCP server:

```bash
codex mcp add pipecat --url http://localhost:9090/mcp
```

### Auto-approving permissions

If you start `codex` inside a version controlled project, you will be asked if you allow Codex to work on the folder without approval. Say `Yes`, which adds the following to `~/.codex/config.toml`.

```toml
[projects."/path/to/your/project"]
trust_level = "trusted"
```

### Starting a voice conversation

1. Install the Pipecat skill into `.codex/skills/pipecat/SKILL.md`.
2. Start the Pipecat MCP Server.
3. Connect to an audio transport (see **🗣️ Connecting to the voice agent** below).
4. Run `$pipecat`.

## 🗣️ Connecting to the voice agent

Once the voice agent starts, you can connect using different methods depending on how the server is configured.

### Pipecat Playground (default)

When no arguments are specified to the `pipecat-mcp-server` command, the server uses Pipecat's local playground. Connect by opening http://localhost:7860 in your browser.

You can also run an ngrok tunnel that you can connect to remotely:

```
ngrok http --url=your-proxy.ngrok.app 7860
```

### Daily Prebuilt

You can also use [Daily](https://daily.co) and access your agent through a Daily room, which is convenient because you can then access from anywhere without tunnels.

First, install the server with the Daily dependency:

```bash
uv tool install -e ".[daily]"
```

Then, set the `DAILY_API_KEY` environment variable to your Daily API key and `DAILY_ROOM_URL` to your desired Daily room URL and pass the `-d` argument to `pipecat-mcp-server`.

```bash
export DAILY_API_KEY=your-daily-api-key
export DAILY_ROOM_URL=your-daily-room

pipecat-mcp-server -d
```

Connect by opening your Daily room URL (e.g., `https://yourdomain.daily.co/room`) in your browser. Daily Prebuilt provides a ready-to-use video/audio interface.

### LiveKit

[LiveKit](https://livekit.io) provides low-latency WebRTC rooms, similar to Daily but self-hostable.

```bash
export LIVEKIT_URL=wss://your-livekit-server
export LIVEKIT_API_KEY=your-api-key
export LIVEKIT_API_SECRET=your-api-secret

pipecat-mcp-server --transport livekit
```

### Phone call

To connect via phone call, pass `-t <provider> -x <your-proxy>` where `<provider>` is one of `twilio`, `telnyx`, `exotel`, or `plivo`, and `<your-proxy>` is your ngrok tunnel domain (e.g., `your-proxy.ngrok.app`).

First, start your ngrok tunnel:

```bash
ngrok http --url=your-proxy.ngrok.app 7860
```

Then, run the Pipecat MCP server with your ngrok URL and the required environment variables for your chosen telephony provider.

| Provider | Environment variables                     |
|----------|-------------------------------------------|
| Twilio   | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` |
| Telnyx   | `TELNYX_API_KEY`                          |
| Exotel   | `EXOTEL_API_KEY`, `EXOTEL_API_TOKEN`      |
| Plivo    | `PLIVO_AUTH_ID`, `PLIVO_AUTH_TOKEN`       |

#### Twilio

```bash
export TWILIO_ACCOUNT_SID=your-twilio-account-sid
export TWILIO_AUTH_TOKEN=your-twilio-auth-token

pipecat-mcp-server -t twilio -x your-proxy.ngrok.app
```

Configure your provider's phone number to point to your ngrok URL, then call your number to connect.

## 🧪 Testing

The project includes a test suite that runs without the full Pipecat dependency tree. Tests mock heavy framework imports while preserving real type hierarchies for `isinstance()` checks.

```bash
pip install pytest pytest-asyncio
python -m pytest tests/ -v
```

Tests cover: emotion tag processing, VisionProcessor capture/passthrough, bot command routing, and MCP tool wrappers.

## 📚 What's Next?

- **Switch voice presets**: Set `VOICE_PRESET` to try different STT/TTS combinations
- **Change transport**: Configure for Daily, LiveKit, Twilio, WebRTC, or other transports
- **Add to your project**: Use this as a template for voice-enabled MCP tools
- **Learn more**: Check out [Pipecat's docs](https://docs.pipecat.ai/) for advanced features
- **Get help**: Join [Pipecat's Discord](https://discord.gg/pipecat) to connect with the community
