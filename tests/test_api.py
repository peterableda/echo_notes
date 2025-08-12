#!/usr/bin/env python3
"""
Test script for the hosted Whisper API integration.
This script tests the basic functionality of the hosted Whisper API.
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from echo_notes.config.settings import Settings
from echo_notes.api.whisper_client import WhisperClient
from echo_notes.core.audio import convert_to_whisper_format

def test_api_connection():
    """Test if the API connection is working."""
    print("Testing hosted Whisper API connection...")

    # Check if we have a test audio file
    test_files = [
        "test_audio.mp3",
        "test_audio.wav",
        "test_audio.m4a"
    ]

    audio_file = None
    for test_file in test_files:
        if os.path.exists(test_file):
            audio_file = test_file
            break

    if not audio_file:
        print("No test audio file found. Please create a test file named 'test_audio.mp3', 'test_audio.wav', or 'test_audio.m4a'")
        return False

    try:
        print(f"Using test file: {audio_file}")

        # Initialize settings and client
        settings = Settings()
        client = WhisperClient(settings)

        # Convert to Whisper API format first
        print("Converting audio to Whisper API format (Mono, 16-bit WAV)...")
        converted_file = convert_to_whisper_format(Path(audio_file), settings=settings)
        print(f"Converted file: {converted_file}")

        # Test transcription
        print("Testing transcription...")
        transcript = client.transcribe(converted_file, "en-US")
        print(f"Transcription result: {transcript[:100]}..." if len(transcript) > 100 else f"Transcription result: {transcript}")

        # Test translation (if the audio is not in English)
        print("\nTesting translation...")
        translation = client.translate(converted_file, "en")
        print(f"Translation result: {translation[:100]}..." if len(translation) > 100 else f"Translation result: {translation}")

        # Clean up converted file if it's different from original
        if str(converted_file) != audio_file and converted_file.exists():
            converted_file.unlink()
            print(f"Cleaned up temporary file: {converted_file}")

        print("\n✅ API test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_api_connection()
    sys.exit(0 if success else 1)
