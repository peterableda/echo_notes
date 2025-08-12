"""Whisper API client for transcription and translation."""

import requests
import logging
from typing import Optional
from pathlib import Path
from pydub import AudioSegment

from ..config.settings import Settings

logger = logging.getLogger(__name__)


class WhisperClient:
    """Client for interacting with hosted Whisper API."""

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the Whisper client."""
        self.settings = settings or Settings()

    def transcribe(self, audio_file: Path, language: str = "en-US", skip_validation: bool = False) -> str:
        """
        Transcribe an audio file using the hosted Whisper API.

        Args:
            audio_file: Path to the audio file to transcribe
            language: Language code for transcription
            skip_validation: Skip file validation (for pre-validated chunks)

        Returns:
            Transcribed text

        Raises:
            requests.RequestException: If the API request fails
            ValueError: If file is too large or too long
        """
        # Check file size and duration before attempting transcription (unless skipped for chunks)
        if not skip_validation:
            self._validate_audio_file(audio_file)

        url = f"{self.settings.whisper_base_url}/audio/transcriptions"

        file_size = audio_file.stat().st_size
        logger.info(f"Transcribing file: {audio_file.name} ({file_size / (1024*1024):.1f} MB)")

        try:
            with open(audio_file, "rb") as f:
                files = {"file": f}
                data = {"language": language}

                response = requests.post(
                    url,
                    headers=self.settings.whisper_headers,
                    files=files,
                    data=data,
                    timeout=300  # 5 minute timeout for large files
                )

                if not response.ok:
                    # Get detailed error information
                    error_detail = self._get_error_details(response)
                    logger.error(f"API request failed: {error_detail}")
                    raise requests.RequestException(f"API Error: {error_detail}")

                result = response.json()
                return result.get("text", "")

        except requests.exceptions.Timeout:
            raise requests.RequestException("Request timed out - file may be too large or API is overloaded")
        except Exception as e:
            logger.error(f"Transcription failed for {audio_file.name}: {str(e)}")
            raise

    def translate(self, audio_file: Path, target_language: str = "en", skip_validation: bool = False) -> str:
        """
        Translate an audio file using the hosted Whisper API.

        Args:
            audio_file: Path to the audio file to translate
            target_language: Target language for translation
            skip_validation: Skip file validation (for pre-validated chunks)

        Returns:
            Translated text

        Raises:
            requests.RequestException: If the API request fails
            ValueError: If file is too large or too long
        """
        # Check file size and duration before attempting translation (unless skipped for chunks)
        if not skip_validation:
            self._validate_audio_file(audio_file)

        url = f"{self.settings.whisper_base_url}/audio/translations"

        file_size = audio_file.stat().st_size
        logger.info(f"Translating file: {audio_file.name} ({file_size / (1024*1024):.1f} MB)")

        try:
            with open(audio_file, "rb") as f:
                files = {"file": f}
                data = {"language": target_language}

                response = requests.post(
                    url,
                    headers=self.settings.whisper_headers,
                    files=files,
                    data=data,
                    timeout=300  # 5 minute timeout for large files
                )

                if not response.ok:
                    # Get detailed error information
                    error_detail = self._get_error_details(response)
                    logger.error(f"API request failed: {error_detail}")
                    raise requests.RequestException(f"API Error: {error_detail}")

                result = response.json()
                return result.get("text", "")

        except requests.exceptions.Timeout:
            raise requests.RequestException("Request timed out - file may be too large or API is overloaded")
        except Exception as e:
            logger.error(f"Translation failed for {audio_file.name}: {str(e)}")
            raise

    def _validate_audio_file(self, audio_file: Path) -> None:
        """
        Validate audio file size and duration before transcription.

        Args:
            audio_file: Path to the audio file

        Raises:
            ValueError: If file exceeds limits
        """
        # Check file size using configured limit
        file_size = audio_file.stat().st_size
        max_file_size = self.settings.max_file_size_mb * 1024 * 1024

        if file_size > max_file_size:
            raise ValueError(
                f"File too large: {file_size / (1024*1024):.1f}MB. "
                f"Maximum allowed: {self.settings.max_file_size_mb}MB"
            )

        # Check audio duration using configured limit
        try:
            audio = AudioSegment.from_file(str(audio_file))
            duration_minutes = len(audio) / (1000 * 60)  # Convert to minutes
            max_duration = self.settings.max_duration_minutes

            if duration_minutes > max_duration:
                raise ValueError(
                    f"Audio too long: {duration_minutes:.1f} minutes. "
                    f"Maximum allowed: {self.settings.max_duration_minutes} minutes"
                )

            logger.info(f"Audio validation passed: {duration_minutes:.1f} min, {file_size / (1024*1024):.1f}MB")

        except Exception as e:
            logger.warning(f"Could not validate audio duration: {e}")
            # Don't fail if we can't check duration, just log it

    def _get_error_details(self, response: requests.Response) -> str:
        """
        Extract detailed error information from API response.

        Args:
            response: The failed HTTP response

        Returns:
            Detailed error message
        """
        try:
            error_data = response.json()
            if 'error' in error_data:
                error_info = error_data['error']
                if isinstance(error_info, dict):
                    return f"{error_info.get('type', 'Unknown')}: {error_info.get('message', 'No message')}"
                else:
                    return str(error_info)
            else:
                return f"HTTP {response.status_code}: {response.text[:200]}"
        except:
            return f"HTTP {response.status_code}: {response.text[:200]}"
