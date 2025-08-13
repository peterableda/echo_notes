"""Configuration and settings management."""

import os
import json
from typing import List, Dict
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv


class ConfigurationError(Exception):
    """Raised when required configuration is missing."""
    pass


class Settings:
    """Application settings and configuration."""

    def __init__(self):
        """Initialize settings and load from environment."""
        # Load environment variables from .env file
        load_dotenv()

        # API Configuration (unified for both Whisper and LLM)
        # Priority: env var API_KEY -> env var WHISPER_API_KEY -> /tmp/jwt access_token (AMP/Inference)
        self.api_key = os.getenv("API_KEY") or os.getenv("WHISPER_API_KEY")
        if not self.api_key:
            # Fallback to Cloudera AMP/Inference token file if present
            try:
                with open("/tmp/jwt", "r", encoding="utf-8") as f:
                    token_data = json.load(f)
                    self.api_key = token_data.get("access_token")
            except Exception:
                self.api_key = None
        if not self.api_key:
            raise ConfigurationError(
                "API_KEY is required. Set API_KEY (or WHISPER_API_KEY) in env/.env, or ensure /tmp/jwt contains access_token."
            )

        # Whisper API Configuration
        self.whisper_base_url = os.getenv("WHISPER_BASE_URL")
        if not self.whisper_base_url:
            raise ConfigurationError(
                "WHISPER_BASE_URL is required. Please set WHISPER_BASE_URL in your .env file or environment variables."
            )

        # LLM API Configuration
        self.llm_base_url = os.getenv("LLM_BASE_URL")
        if not self.llm_base_url:
            raise ConfigurationError(
                "LLM_BASE_URL is required. Please set LLM_BASE_URL in your .env file or environment variables."
            )

        self.llm_model_id = os.getenv("LLM_MODEL_ID")
        if not self.llm_model_id:
            raise ConfigurationError(
                "LLM_MODEL_ID is required. Please set LLM_MODEL_ID in your .env file or environment variables."
            )

        # Directory Configuration (configurable via environment variables)
        self.home_dir = Path.home()
        self.documents_dir = self.home_dir / "Documents"

        # Meetings directory - configurable with default
        meetings_dir_env = os.getenv("MEETINGS_DIR")
        if meetings_dir_env:
            self.meetings_dir = Path(meetings_dir_env).expanduser()
        else:
            self.meetings_dir = self.documents_dir / "meetings"

        # Transcriptions directory - configurable with default
        transcriptions_dir_env = os.getenv("TRANSCRIPTIONS_DIR")
        if transcriptions_dir_env:
            self.transcriptions_dir = Path(transcriptions_dir_env).expanduser()
        else:
            self.transcriptions_dir = self.documents_dir / "transcriptions"

        # Ensure directories exist
        self.meetings_dir.mkdir(parents=True, exist_ok=True)
        self.transcriptions_dir.mkdir(parents=True, exist_ok=True)

        # Audio Configuration
        self.supported_audio_formats = ['.m4a', '.mp3', '.wav', '.flac', '.aac', '.ogg']
        self.target_sample_rate = 16000
        self.target_channels = 1  # Mono
        self.target_sample_width = 2  # 16-bit

        # Language Configuration
        self.supported_languages = [
            "en-US", "es-ES", "fr-FR", "de-DE", "it-IT",
            "pt-PT", "ru-RU", "ja-JP", "ko-KR", "zh-CN"
        ]

        # UI Configuration
        self.default_language = "en-US"
        self.transcript_preview_lines = 5

        # API Limits (conservative values to ensure reliability)
        self.max_file_size_mb = 20  # 20MB limit (conservative)
        self.max_duration_minutes = 20  # 20 minute limit (conservative)

        # Chunking parameters
        self.chunk_duration_minutes = 10  # 10 minute chunks for safety
        self.chunk_overlap_seconds = 5    # 5 second overlap between chunks

        # Quick Actions configuration for Chat page
        self.quick_actions: List[Dict[str, str]] = self._load_quick_actions()

    @property
    def whisper_headers(self) -> dict:
        """Get headers for Whisper API requests."""
        return {"Authorization": f"Bearer {self.api_key}"}

    @property
    def llm_headers(self) -> dict:
        """Get headers for LLM API requests."""
        return {"Authorization": f"Bearer {self.api_key}"}

    def get_project_dir(self, name: str, timestamp: str) -> Path:
        """Get project directory path for a transcription."""
        sanitized_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        project_dir_name = f"{timestamp}_{sanitized_name}"
        return self.transcriptions_dir / project_dir_name

    def _load_quick_actions(self) -> List[Dict[str, str]]:
        """Load configurable Quick Actions for Chat page.

        Order of precedence:
        1) QUICK_ACTIONS_FILE (JSON array of {label, prompt})
        2) QUICK_ACTIONS (JSON string)
        3) Built-in defaults
        """
        # Defaults (updated): Summary, Sentiment, and Action Items
        defaults: List[Dict[str, str]] = [
            {"label": "🧾 Summary", "prompt": "Write a concise summary of the transcription."},
            {"label": "🙂 Sentiment", "prompt": "Analyze the overall sentiment and emotional tone of the conversation."},
            {"label": "✅ Action Items", "prompt": "Extract action items with owners and suggested due dates when possible."},
        ]

        # File-based override
        file_path = os.getenv("QUICK_ACTIONS_FILE")
        if file_path and Path(file_path).expanduser().exists():
            try:
                data = json.loads(Path(file_path).expanduser().read_text(encoding="utf-8"))
                if isinstance(data, list) and all(isinstance(x, dict) for x in data):
                    return data
            except Exception:
                pass

        # Env var JSON override
        env_json = os.getenv("QUICK_ACTIONS")
        if env_json:
            try:
                data = json.loads(env_json)
                if isinstance(data, list) and all(isinstance(x, dict) for x in data):
                    return data
            except Exception:
                pass

        return defaults
