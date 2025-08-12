# EchoNotes 📝

A professional audio recording and transcription tool with pure Python recording and hosted Whisper API transcription.

## Quick Start

### Web Interface
```bash
# Start the application
./start_ui.sh

# Or directly with uv
uv run python echo_notes_app.py
```

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd call_capture
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Configure API credentials (REQUIRED):**
   ```bash
   # Copy the example configuration file
   cp env.example .env

   # Edit .env with your actual API credentials
   # All required variables must be set - see env.example for details
   ```

   **Required environment variables:**
   - `API_KEY`: Your API key for both Whisper and LLM services
   - `WHISPER_BASE_URL`: Whisper transcription service endpoint
   - `LLM_BASE_URL`: LLM service endpoint (OpenAI-compatible)
   - `LLM_MODEL_ID`: LLM model identifier

## Project Structure

```
call_capture/
├── src/echo_notes/            # Main package
│   ├── api/                   # API clients
│   ├── core/                  # Business logic & recording
│   ├── ui/                    # Streamlit interface
│   └── config/                # Configuration management
├── tests/                     # Test files
├── echo_notes_app.py          # Streamlit entry point
├── start_ui.sh                # UI launcher script
└── pyproject.toml            # Project configuration
```

## Features

- 🎤 **Pure Python Recording**: Cross-platform audio recording with sounddevice
- 📝 **Transcription**: Hosted Whisper API with multi-language support
- 📁 **File Organization**: Automatic project-based file management
- 🖥️ **Web Interface**: Beautiful, modern Streamlit UI
- 🎛️ **Device Selection**: Choose your preferred microphone
- 🔒 **Secure**: Environment-based credential management
- ⚡ **Fast**: No local model downloads required
- 🌍 **Cross-platform**: Works on macOS, Windows, and Linux

## Documentation

### Features

- 🎤 Audio Recording: Record audio via Streamlit UI
- 📝 Transcription: Hosted Whisper API to text
- 🌐 Multi-language Support: English, Spanish, French, German, etc.
- 🔄 Format Conversion: Mono, 16‑bit WAV conversion handled automatically
- 💾 Auto-save: Recordings saved to `~/Documents/meetings`
- 📁 Project Organization: Each transcription has its own folder in `~/Documents/transcriptions`
- 🔒 Secure: API keys via environment variables
- ⚡ Fast: No local models required

### Requirements

- Python 3.12+
- macOS/Windows/Linux with a microphone
- [uv](https://github.com/astral-sh/uv) recommended, or pip

### Usage (Web Interface)

```bash
uv run python echo_notes_app.py
# or
streamlit run echo_notes_app.py
```

The web app includes:
- Recording controls (start/stop)
- Upload for transcription
- Language selection
- Transcript preview and downloads

### Project Organization

Each transcription creates a folder under `~/Documents/transcriptions/`:

```
~/Documents/transcriptions/
└── YYYY-MM-DD_ProjectName/
    ├── transcript.txt           # Generated transcript
    ├── original_filename.ext    # Original audio file
    └── project_info.txt         # Project metadata
```

### Dependencies

- Streamlit, Requests, PyDub, python-dotenv, sounddevice, numpy, soundfile, OpenAI

## Development

### Running Tests
```bash
uv run python -m pytest tests/
```

### Code Style
```bash
uv run black src/ tests/
uv run ruff check src/ tests/
```

## License

MIT License - see [LICENSE](LICENSE) for details.
