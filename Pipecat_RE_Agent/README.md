# Pipecat_RE_Agent

A Pipecat AI voice agent built with a cascade pipeline (STT → LLM → TTS).

## How It Works

1. Twilio receives an incoming call to your phone number
2. Twilio calls your webhook server (`/call` endpoint in `server.py`)
3. The server creates a Daily room with SIP capabilities
4. The server starts the bot process with the room details (locally or via Pipecat Cloud)
5. The caller is put on hold with music (a US ringtone in this example)
6. The bot joins the Daily room and signals readiness
7. Twilio forwards the call to Daily's SIP endpoint
8. The caller and the bot are connected, and the bot handles the conversation

## Configuration

- **Bot Type**: Telephony
- **Transport(s)**: Twilio + Daily SIP (Dial-in)
- **Pipeline**: Cascade
  - **STT**: Deepgram
  - **LLM**: Grok
  - **TTS**: Inworld
- **Features**:
  - Transcription
  - smart-turn v3
  - Observability (Whisker + Tail)

## Setup

1. Create a virtual environment and install dependencies

   ```bash
   uv sync
   ```

2. Set up environment variables

   Copy the example file and fill in your API keys:

    ```bash
    cp .env.example .env
    # Edit .env with your API keys
    ```

3. Configure your Twilio webhook

In the Twilio console:

- Go to your phone number's configuration
- Set the webhook for "A call comes in" to your server's URL + "/call"
- For local testing, you can use ngrok to expose your local server

```bash
ngrok http 8080
# Then use the provided URL (e.g., https://abc123.ngrok.io/call) in Twilio
```

## Environment Configuration

The bot supports two deployment modes controlled by the `ENV` variable:

### Local Development (`ENV=local`)

- Uses your local server or ngrok URL for handling the webhook and starting the bot
- Default configuration for development and testing

### Production (`ENV=production`)

- Bot is deployed to Pipecat Cloud; requires `PIPECAT_API_KEY` and `PIPECAT_AGENT_NAME`
- Set these when deploying to production environments
- Your FastAPI server runs either locally or deployed to your infrastructure

## Run the Bot Locally

You'll need three terminal windows open:

1. Terminal 1: Start the webhook server:

   ```bash
   uv run server.py
   ```

2. Terminal 2: Start an ngrok tunnel to expose the FastAPI server running on server.py

   ```bash
   ngrok http 8080
   ```

   Important: Make sure that this URL matches the webhook URL configured in your Twilio phone number settings.

   > Tip: Use the `--subdomain` flag for a reusable ngrok link.

3. Terminal 3: Run your bot:

   ```bash
   uv run bot.py -t daily
   ```

   > The bot.py file includes a FastAPI server. This emulates the Pipecat Cloud service, and is as if you're running with `min_agents=1`.

4. Call your bot!

   Call the Twilio number you configured to talk to your bot.

## Project Structure

Pipecat_RE_Agent/
├── server/              # Python bot server
│   ├── bot.py           # Main bot implementation
│   ├── server.py        # FastAPI webhook server for Twilio + Daily SIP dial-in
│   ├── server_utils.py  # Utility functions for Twilio and Daily API interactions
│   ├── pyproject.toml   # Python dependencies
│   ├── env.example      # Environment variables template
│   ├── .env             # Your API keys (git-ignored)
│   ├── Dockerfile       # Container image for Pipecat Cloud
│   └── pcc-deploy.toml  # Pipecat Cloud deployment config
├── .gitignore           # Git ignore patterns
└── README.md            # This file

This example is organized to be production-ready and easy to customize:

- **`server.py`** - FastAPI webhook server that handles incoming calls
  - Receives Twilio call webhooks
  - Creates Daily rooms with SIP capabilities
  - Routes to local or production bot deployment
  - Uses shared HTTP session for optimal performance

- **`server_utils.py`** - Utility functions for Twilio and Daily API interactions

  - Data models for call data and agent requests  - Room creation logic
  - Bot starting logic (production and local modes)
  - Easy to extend with custom business logic

- **`bot.py`** - The voice bot implementation
  - Handles the conversation with the caller
  - Deployed to Pipecat Cloud in production or run locally for development
## Observability

This project includes observability tools to help you debug and monitor your bot:

### Whisker - Live Pipeline Debugger

**Whisker** is a live graphical debugger that lets you visualize pipelines and debug frames in real time.

With Whisker you can:

- 🗺️ View a live graph of your pipeline
- ⚡ Watch frame processors flash in real time as frames pass through them
- 📌 Select a processor to inspect the frames it has handled
- 🔍 Filter frames by name to quickly find the ones you care about
- 🧵 Select a frame to trace its full path through the pipeline
- 💾 Save and load previous sessions for review and troubleshooting

**To use Whisker:**

1. Run an ngrok tunnel to expose your bot:

   ```bash
   ngrok http 9090
   ```

   > Tip: Use `--subdomain` for a repeatable ngrok URL

2. Navigate to [https://whisker.pipecat.ai/](https://whisker.pipecat.ai/) and enter your ngrok URL (e.g., `your-subdomain.ngrok.io`)

3. Once your bot is running, press connect

### Tail - Terminal Dashboard

**Tail** is a terminal dashboard that lets you monitor your Pipecat sessions in real time.

With Tail you can:

- 📜 Follow system logs in real time
- 💬 Track conversations as they happen
- 🔊 Monitor user and agent audio levels
- 📈 Keep an eye on service metrics and usage

**To use Tail:**

1. Run your bot (in one terminal)

2. Launch Tail in another terminal:
   ```bash
   pipecat tail
   ```

## Learn More

- [Pipecat Documentation](https://docs.pipecat.ai/)
- [Pipecat GitHub](https://github.com/pipecat-ai/pipecat)
- [Pipecat Examples](https://github.com/pipecat-ai/pipecat-examples)
- [Discord Community](https://discord.gg/pipecat)