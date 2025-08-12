"""Audio processing utilities."""

import os
from pathlib import Path
from typing import Optional
from pydub import AudioSegment

from ..config.settings import Settings


def convert_to_whisper_format(
    input_file: Path,
    output_file: Optional[Path] = None,
    settings: Optional[Settings] = None
) -> Path:
    """
    Convert an audio file to the format required by hosted Whisper API:
    Mono, 16-bit WAV format.

    Args:
        input_file: Path to the input audio file
        output_file: Path to save the WAV file. If None, creates default name
        settings: Settings instance for configuration

    Returns:
        Path to the converted WAV file

    Raises:
        FileNotFoundError: If input file doesn't exist
        Exception: If conversion fails
    """
    if settings is None:
        settings = Settings()

    input_path = Path(input_file)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Set default output file name if not provided
    if output_file is None:
        output_file = input_path.parent / f"{input_path.stem}_whisper.wav"
    else:
        output_file = Path(output_file)

    try:
        # Load the audio file (supports multiple formats)
        audio = AudioSegment.from_file(str(input_path))

        # Convert to mono (single channel)
        if audio.channels > 1:
            audio = audio.set_channels(settings.target_channels)
            print(f"Converted to mono (from {audio.channels} channels)")

        # Set sample width to 16-bit (2 bytes)
        audio = audio.set_sample_width(settings.target_sample_width)

        # Set sample rate
        audio = audio.set_frame_rate(settings.target_sample_rate)

        # Export as WAV with 16-bit PCM
        audio.export(str(output_file), format="wav", parameters=["-acodec", "pcm_s16le"])
        print(f"Converted {input_path} to {output_file} (Mono, 16-bit WAV)")

        return output_file

    except Exception as e:
        print(f"Error converting file: {e}")
        raise


def get_audio_info(audio_file: Path) -> dict:
    """
    Get information about an audio file.

    Args:
        audio_file: Path to the audio file

    Returns:
        Dictionary with audio information
    """
    try:
        audio = AudioSegment.from_file(str(audio_file))
        return {
            "duration": len(audio) / 1000.0,  # Duration in seconds
            "channels": audio.channels,
            "sample_rate": audio.frame_rate,
            "sample_width": audio.sample_width * 8,  # Convert to bits
            "format": audio_file.suffix.lower()
        }
    except Exception as e:
        return {"error": str(e)}

