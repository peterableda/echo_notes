"""Smart chunking for extremely large files that need recursive splitting."""

import os
import math
from pathlib import Path
from typing import List, Optional
from pydub import AudioSegment

from ..config.settings import Settings


class SmartChunker:
    """Advanced chunker that handles extremely large files with recursive splitting."""

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the smart chunker."""
        self.settings = settings or Settings()

    def chunk_large_file(self, audio_file: Path) -> List[Path]:
        """
        Intelligently chunk a large audio file, ensuring all chunks meet API requirements.

        Args:
            audio_file: Path to the audio file to chunk

        Returns:
            List of paths to the chunked audio files that meet API requirements
        """
        try:
            audio = AudioSegment.from_file(str(audio_file))

            # Calculate optimal chunk parameters
            total_duration_ms = len(audio)
            total_size_mb = audio_file.stat().st_size / (1024 * 1024)

            # Estimate bitrate
            estimated_bitrate_mbps = total_size_mb / (total_duration_ms / (1000 * 60))  # MB per minute

            # Calculate safe chunk duration to stay under size limit
            safe_size_mb = self.settings.max_file_size_mb * 0.8  # 80% of limit for safety
            safe_duration_minutes = min(
                self.settings.chunk_duration_minutes,
                safe_size_mb / estimated_bitrate_mbps if estimated_bitrate_mbps > 0 else self.settings.chunk_duration_minutes
            )

            # Ensure minimum chunk size
            safe_duration_minutes = max(3.0, safe_duration_minutes)  # At least 3 minutes

            print(f"Smart chunking: {total_size_mb:.1f}MB file, estimated bitrate: {estimated_bitrate_mbps:.2f}MB/min")
            print(f"Using chunk duration: {safe_duration_minutes:.1f} minutes")

            # Create chunks
            chunk_duration_ms = int(safe_duration_minutes * 60 * 1000)
            overlap_ms = int(self.settings.chunk_overlap_seconds * 1000)

            chunks = []
            chunk_dir = audio_file.parent / f"{audio_file.stem}_smart_chunks"
            chunk_dir.mkdir(exist_ok=True)

            num_chunks = math.ceil(total_duration_ms / chunk_duration_ms)

            for i in range(num_chunks):
                start_time = i * chunk_duration_ms

                # Add overlap to all chunks except the first
                if i > 0:
                    start_time -= overlap_ms

                end_time = min(start_time + chunk_duration_ms + overlap_ms, total_duration_ms)

                chunk = audio[start_time:end_time]

                # Create chunk filename
                chunk_filename = chunk_dir / f"{audio_file.stem}_smart_chunk_{i+1:03d}.wav"

                # Export with optimal settings for API
                chunk.export(
                    str(chunk_filename),
                    format="wav",
                    parameters=[
                        "-acodec", "pcm_s16le",  # 16-bit PCM
                        "-ar", "16000",          # 16kHz sample rate
                        "-ac", "1"               # Mono
                    ]
                )

                # Verify chunk meets requirements
                chunk_size_mb = chunk_filename.stat().st_size / (1024 * 1024)
                chunk_duration_min = len(chunk) / (1000 * 60)

                print(f"  Chunk {i+1}/{num_chunks}: {chunk_size_mb:.1f}MB, {chunk_duration_min:.1f}min")

                # If chunk is STILL too large, split it recursively
                if chunk_size_mb > self.settings.max_file_size_mb * 0.9:
                    print(f"  Warning: Chunk {i+1} is still {chunk_size_mb:.1f}MB, splitting further...")
                    sub_chunks = self._split_chunk_further(chunk_filename)
                    chunks.extend(sub_chunks)
                    # Remove the oversized chunk
                    chunk_filename.unlink()
                else:
                    chunks.append(chunk_filename)

            return chunks

        except Exception as e:
            raise RuntimeError(f"Smart chunking failed: {e}")

    def _split_chunk_further(self, chunk_file: Path) -> List[Path]:
        """
        Recursively split a chunk that's still too large.

        Args:
            chunk_file: Path to the chunk file to split further

        Returns:
            List of smaller chunk files
        """
        try:
            audio = AudioSegment.from_file(str(chunk_file))

            # Use very conservative duration for recursive splits
            safe_duration_minutes = 5.0  # 5 minutes max
            chunk_duration_ms = int(safe_duration_minutes * 60 * 1000)
            overlap_ms = int(self.settings.chunk_overlap_seconds * 1000)

            total_duration_ms = len(audio)
            num_sub_chunks = math.ceil(total_duration_ms / chunk_duration_ms)

            sub_chunks = []
            base_name = chunk_file.stem

            for i in range(num_sub_chunks):
                start_time = i * chunk_duration_ms

                if i > 0:
                    start_time -= overlap_ms

                end_time = min(start_time + chunk_duration_ms + overlap_ms, total_duration_ms)

                sub_chunk = audio[start_time:end_time]

                # Create sub-chunk filename
                sub_chunk_filename = chunk_file.parent / f"{base_name}_sub_{i+1:02d}.wav"

                # Export with minimal settings
                sub_chunk.export(
                    str(sub_chunk_filename),
                    format="wav",
                    parameters=[
                        "-acodec", "pcm_s16le",
                        "-ar", "16000",
                        "-ac", "1"
                    ]
                )

                sub_chunk_size_mb = sub_chunk_filename.stat().st_size / (1024 * 1024)
                sub_chunk_duration_min = len(sub_chunk) / (1000 * 60)

                print(f"    Sub-chunk {i+1}: {sub_chunk_size_mb:.1f}MB, {sub_chunk_duration_min:.1f}min")

                sub_chunks.append(sub_chunk_filename)

            return sub_chunks

        except Exception as e:
            raise RuntimeError(f"Recursive chunk splitting failed: {e}")

    def cleanup_chunks(self, chunk_files: List[Path]) -> None:
        """
        Clean up chunk files and directories.

        Args:
            chunk_files: List of chunk file paths to clean up
        """
        for chunk_file in chunk_files:
            try:
                if chunk_file.exists():
                    chunk_file.unlink()

                # Try to remove the chunk directory if it's empty
                chunk_dir = chunk_file.parent
                if chunk_dir.exists() and ('chunks' in chunk_dir.name):
                    try:
                        chunk_dir.rmdir()
                    except OSError:
                        pass  # Directory not empty, that's fine

            except Exception:
                pass  # Ignore cleanup errors


def merge_transcripts(transcripts: List[str], overlap_words: int = 10) -> str:
    """Merge transcripts from multiple chunks, removing overlapping content.

    Args:
        transcripts: List of transcript strings from chunks
        overlap_words: Number of words to check for overlap removal

    Returns:
        Merged transcript string
    """
    if not transcripts:
        return ""

    if len(transcripts) == 1:
        return transcripts[0]

    merged = transcripts[0]

    for i in range(1, len(transcripts)):
        current_transcript = transcripts[i]

        if not current_transcript.strip():
            continue

        # Try to find and remove overlap
        try:
            # Get the last few words from merged transcript
            merged_words = merged.strip().split()
            current_words = current_transcript.strip().split()

            if len(merged_words) >= overlap_words and len(current_words) >= overlap_words:
                # Look for overlap in the last overlap_words of merged and first overlap_words of current
                last_words = ' '.join(merged_words[-overlap_words:])
                first_words = ' '.join(current_words[:overlap_words])

                # Simple overlap detection - look for common sequence
                best_overlap = 0
                for j in range(1, min(overlap_words + 1, len(current_words) + 1)):
                    test_sequence = ' '.join(current_words[:j])
                    if test_sequence in last_words:
                        best_overlap = j

                if best_overlap > 0:
                    # Remove the overlapping part from the current transcript
                    current_transcript = ' '.join(current_words[best_overlap:])

            # Add the current transcript
            if current_transcript.strip():
                merged += " " + current_transcript.strip()

        except Exception:
            # If overlap detection fails, just concatenate
            merged += " " + current_transcript.strip()

    return merged.strip()
