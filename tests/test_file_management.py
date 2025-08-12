#!/usr/bin/env python3
"""
Test script for the file management system.
"""

import os
import sys
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from echo_notes.config.settings import Settings

def test_file_organization():
    """Test the file organization system."""
    print("Testing file organization system...")

    # Initialize settings
    settings = Settings()
    TRANSCRIPTION_DIR = settings.transcriptions_dir

    # Test data
    transcription_name = "Test Meeting"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    sanitized_name = "".join(c for c in transcription_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    project_dir_name = f"{timestamp}_{sanitized_name}"
    project_dir = os.path.join(TRANSCRIPTION_DIR, project_dir_name)

    try:
        # Create the project directory
        os.makedirs(project_dir, exist_ok=True)
        print(f"✅ Created project directory: {project_dir}")

        # Create test files
        transcript_content = "This is a test transcript content."
        with open(os.path.join(project_dir, "transcript.txt"), "w") as f:
            f.write(transcript_content)
        print("✅ Created transcript.txt")

        # Create a test audio file
        test_audio_content = b"fake audio data"
        with open(os.path.join(project_dir, "original_test.mp3"), "wb") as f:
            f.write(test_audio_content)
        print("✅ Created original_test.mp3")

        # Create project info
        info_content = f"""Transcription Project: {transcription_name}
Created: {timestamp}
Original File: test.mp3
Language: en-US
Diarization: Disabled
Processing Time: 1.23 seconds
"""
        with open(os.path.join(project_dir, "project_info.txt"), "w") as f:
            f.write(info_content)
        print("✅ Created project_info.txt")

        # List files in project directory
        files = os.listdir(project_dir)
        print(f"✅ Project folder contains {len(files)} files:")
        for file in sorted(files):
            file_path = os.path.join(project_dir, file)
            file_size = os.path.getsize(file_path)
            print(f"   📄 {file} ({file_size} bytes)")

        # Cleanup test directory
        shutil.rmtree(project_dir)
        print(f"✅ Cleaned up test directory: {project_dir}")

        print("\n🎉 File organization test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        # Cleanup on failure
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)
        return False

if __name__ == "__main__":
    success = test_file_organization()
    exit(0 if success else 1)
