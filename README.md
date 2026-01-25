# Pipecat MCP Server

Pipecat MCP Server gives your AI assistant a voice using [Pipecat](https://github.com/pipecat-ai/pipecat). It should work with any [MCP](https://modelcontextprotocol.io/)-compatible client, exposing four simple tools:

- **start()** / **stop()**: Start and stop the voice agent
- **listen()**: Wait for you to speak and return the transcription
- **speak(text)**: Say something back to you

## 🧭 Getting started

### Prerequisites

- Python 3.10 or later
- [uv](https://docs.astral.sh/uv/getting-started/installation/) package manager
- API keys for third-party services (Speech-to-Text, Text-to-Speech, ...)

By default, the voice agent uses [Deepgram](https://deepgram.com) for speech-to-text and [Cartesia](https://cartesia.ai/) for text-to-speech.

### Installation

```bash
uv tool install pipecat-ai-mcp-server
```

This will install the `pipecat-mcp-server` tool.

If you want to use different services or modify the Pipecat pipeline somehow, you will need to clone the repository:

```bash
git clone https://github.com/pipecat-ai/pipecat-mcp-server.git
```

and install your local version with:

```bash
uv tool install -e /path/to/repo/pipecat-mcp-server
```

## Running the server

In one terminal, run the server by simply typing:

```bash
pipecat-mcp-server
```

This will make the Pipecat MCP Server available at `http://localhost:9090/mcp`.

## 💻 MCP Client: Claude Code

### Adding the MCP server

Register the MCP server:

```bash
claude mcp add pipecat --transport http http://localhost:9090/mcp --scope user
```

Scope options:
- `local`: Stored in `~/.claude.json`, applies only to this project
- `user`: Stored in `~/.claude.json`, applies to all projects
- `project`: Stored in `.mcp.json` in the project directory

### Auto-approving permissions

For hands-free voice conversations, you can auto-approve tool permissions. Otherwise, Claude Code will prompt for confirmation on each tool use, which interrupts the conversation flow.

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
      "mcp__pipecat__*"
    ]
  }
}
```

This grants permissions for Bash commands, file operations, web fetching, and all Pipecat MCP tools without prompting.

> ⚠️ **Warning**: Enabling broad permissions is at your own risk.

### Starting a voice conversation

The recommended approach is to install the [Pipecat skill](.claude/skills/pipecat/SKILL.md), then run `/pipecat` in Claude Code.

> ℹ️ **Note**: The skill is configured to ask for verbal confirmation before making changes to files, adding a layer of safety when using broad permissions.

Alternatively, just type:

```
Let's have a voice conversation.
```

> ⚠️ **Warning**: Without the skill, if permissions are auto-approved, Claude won't ask for verbal confirmation before making changes to your files.

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

For hands-free voice conversations, you can auto-approve tool permissions. Otherwise, Cursor will prompt for confirmation on each tool use, which interrupts the conversation flow. For this, you need to go to the `Auto-Run` agent settings and configure it to `Run Everything`.

> ⚠️ **Warning**: Enabling broad permissions is at your own risk.

### Starting a voice conversation

The recommended approach is to install the [Pipecat skill](.claude/skills/pipecat/SKILL.md) (Cursor supports Claude skills), then run `/pipecat` in Cursor.

> ℹ️ **Note**: The skill is configured to ask for verbal confirmation before making changes to files, adding a layer of safety when using broad permissions.

Alternatively, just create an agent and type:

```
Let's have a voice conversation.
```

> ⚠️ **Warning**: Without the skill, if permissions are auto-approved, Cursor won't ask for verbal confirmation before making changes to your files.

## 💻 MCP Client: OpenAI Codex

### Adding the MCP server

Register the MCP server:

```bash
codex mcp add pipecat --url http://localhost:9090/mcp
```

### Auto-approving permissions

For hands-free voice conversations, you can auto-approve tool permissions. Otherwise, Cursor will prompt for confirmation on each tool use, which interrupts the conversation flow.

If you start `codex` inside a version controlled project, you will be asked if you allow `Codex` to work on the folder without approvar, just say `Yes`, which adds the following to `~/.codex/config.toml`

```toml
[projects."/path/to/your/project"]
trust_level = "trusted"
```

> ⚠️ **Warning**: Enabling broad permissions is at your own risk.

### Starting a voice conversation

The recommended approach is to install the [Pipecat skill](.claude/skills/pipecat/SKILL.md) (Cursor supports Claude skills), then run `/pipecat` in Cursor.

> ℹ️ **Note**: The skill is configured to ask for verbal confirmation before making changes to files, adding a layer of safety when using broad permissions.

Alternatively, just create an agent and type:

```
Let's have a voice conversation.
```

> ⚠️ **Warning**: Without the skill, if permissions are auto-approved, Cursor won't ask for verbal confirmation before making changes to your files.

## 🗣️ Connecting to the voice agent

Once the voice agent starts, you can connect using different methods depending on how the server is configured.

### Pipecat Playground (default)

When no arguments are specified to the `pipecat-mcp-server` command, the server uses Pipecat's local playground. Connect by opening **http://localhost:7860** in your browser.

You can also run an ngrok tunnel that you can connect to remotely:

```
ngrok http --url=your-proxy.ngrok.app 7860
```

### Daily Prebuilt

To use Daily's WebRTC infrastructure, first install the server with the Daily dependency:

```bash
uv tool install pipecat-ai-mcp-server[daily]
```

Then pass the `-d` argument to `pipecat-mcp-server` and set the `DAILY_API_KEY` environment variable to your Daily API key and `DAILY_SAMPLE_ROOM_URL` to your desired Daily room URL.

```bash
claude mcp add pipecat --scope user \
  -e DAILY_API_KEY=your-daily-api-key \
  -e DAILY_SAMPLE_ROOM_URL=your-daily-room \
  -e DEEPGRAM_API_KEY=your-deepgram-key \
  -e CARTESIA_API_KEY=your-cartesia-key \
  -- pipecat-mcp-server -d
```

Connect by opening your Daily room URL (e.g., **https://yourdomain.daily.co/room**) in your browser. Daily Prebuilt provides a ready-to-use video/audio interface.

### Phone call

To connect via phone call, pass `-t <provider> -x <your-proxy>` where `<provider>` is one of `twilio`, `telnyx`, `exotel`, or `plivo`, and `<your-proxy>` is your ngrok tunnel domain (e.g., `your-proxy.ngrok.app`).

First, start your ngrok tunnel:

```bash
ngrok http --url=your-proxy.ngrok.app 7860
```

Then register the MCP server with your ngrok URL and the required environment variables for your chosen provider.

| Provider | Environment Variables                     |
|----------|-------------------------------------------|
| Twilio   | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` |
| Telnyx   | `TELNYX_API_KEY`                          |
| Exotel   | `EXOTEL_API_KEY`, `EXOTEL_API_TOKEN`      |
| Plivo    | `PLIVO_AUTH_ID`, `PLIVO_AUTH_TOKEN`       |

#### Twilio

```bash
claude mcp add pipecat --scope user \
  -e DEEPGRAM_API_KEY=your-deepgram-key \
  -e CARTESIA_API_KEY=your-cartesia-key \
  -e TWILIO_ACCOUNT_SID=your-twilio-account-sid \
  -e TWILIO_AUTH_TOKEN=your-twilio-auth-token \
  -- pipecat-mcp-server -t twilio -x your-proxy.ngrok.app
```

Configure your provider's phone number to point to your ngrok tunnel, then call your number to connect.

## 🧩 MCP Tools

### start()

Initialize and start the voice agent. Call this before using `listen()` or `speak()`.

### listen() -> str

Wait for user speech and return the transcribed text.

- Blocks until the user completes an utterance (detected via voice activity detection)
- Automatically starts the agent if not already running

**Returns:** Transcribed text from the user's speech.

### speak(text: str)

Speak text to the user using text-to-speech.

- Queues the text for synthesis and playback
- Automatically starts the agent if not already running

**Parameters:**
- `text` - The text to speak to the user

### stop()

Gracefully stop the voice pipeline and clean up resources.

Call this when the conversation is complete to properly shut down the audio processing pipeline.

## 📚 What's Next?

- **Customize services**: Edit `agent.py` to use different STT/TTS providers (ElevenLabs, OpenAI, etc.)
- **Change transport**: Configure for Twilio, WebRTC, or other transports
- **Add to your project**: Use this as a template for voice-enabled MCP tools
- **Learn more**: Check out [Pipecat's docs](https://docs.pipecat.ai/) for advanced features
- **Get help**: Join [Pipecat's Discord](https://discord.gg/pipecat) to connect with the community
