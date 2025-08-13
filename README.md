# EchoNotes 📝

An audio recording and transcription tool built with Private AI endpoints.


## Features
- 🎤 Recording: Native cross-platform audio recording
- 📝 Transcription: Hosted Whisper API with multi-language support (hosted by Cloudera AI Inference service)
- 💬 Chat with Transcriptions: Ask questions, generate notes, and run configurable Quick Actions (OpenAI-compatible LLM hosted by Cloudera AI Inference service)
- 📁 Project Organization: Per-transcription folders with original + transcript
- ⚡ AMP-ready: One-click import to Cloudera AI

## Installation

### Running in Cloudera AI

This repo includes an AMP manifest (`.project-metadata.yaml`). To deploy via Cloudera AI Workbench:

1. In Cloudera AI, create a new AMP project from this repo (URL or uploaded archive)
2. Set these environment variables in the AMP form:
   - `WHISPER_BASE_URL` (required)
   - `LLM_BASE_URL` (required)
   - `LLM_MODEL_ID` (required)
   - `API_KEY` (optional; if not provided, the app reads `/tmp/jwt` and uses `access_token` automatically)
   - `MEETINGS_DIR`, `TRANSCRIPTIONS_DIR` (optional overrides)
3. During deployment, Step 1 (Session) runs `pip install .`; Step 2 (Application) starts Streamlit process
4. Launch the Application; the app will be reachable at the AMP-provided URL

### Running Locally

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd echo_notes
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Configure API credentials (REQUIRED):**
   ```bash
   # Copy the example configuration file
   cp .env.example .env

   # Edit .env with your actual API credentials
   # All required variables must be set - see .env.example for details
   ```

   **Required environment variables:**
   - `API_KEY`: Your API key for both Whisper and LLM services
   - `WHISPER_BASE_URL`: Whisper transcription service endpoint
   - `LLM_BASE_URL`: LLM service endpoint (OpenAI-compatible)
   - `LLM_MODEL_ID`: LLM model identifier

4. **Start Application:**
```bash
# Start the application
./start_ui.sh

# Or directly with uv
uv run python echo_notes_app.py
```

## Advanced Configuration

Quick Actions (Chat) overrides:
- QUICK_ACTIONS_FILE: Path to JSON file with an array of `{label, prompt}`
- QUICK_ACTIONS: JSON string for the same structure
- Defaults: Summary, Sentiment, Action Items

Example QUICK_ACTIONS JSON:
```
[
  {"label": "🧾 Summary", "prompt": "Write a concise summary of the transcription focusing on key points."},
  {"label": "🙂 Sentiment", "prompt": "Analyze the overall sentiment and tone."},
  {"label": "✅ Action Items", "prompt": "Extract action items with owners and suggested due dates."}
]
```
