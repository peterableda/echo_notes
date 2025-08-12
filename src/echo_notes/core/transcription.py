"""Transcription business logic and project management."""

import os
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from ..api.whisper_client import WhisperClient
from ..config.settings import Settings
from .audio import convert_to_whisper_format
from .smart_chunker import SmartChunker, merge_transcripts

logger = logging.getLogger(__name__)


class TranscriptionProject:
    """Manages a transcription project with organized file structure."""

    def __init__(
        self,
        name: str,
        audio_file: Path,
        settings: Optional[Settings] = None
    ):
        """Initialize a transcription project."""
        self.settings = settings or Settings()
        self.name = name
        self.original_audio_file = Path(audio_file)
        self.timestamp = datetime.now().strftime("%Y-%m-%d")

        # Create unique project directory
        base_project_dir = self.settings.get_project_dir(name, self.timestamp)
        self.project_dir = self._ensure_unique_project_dir(base_project_dir)
        self.project_dir.mkdir(parents=True, exist_ok=True)

        # File paths
        self.transcript_file = self.project_dir / "transcript.txt"
        self.project_info_file = self.project_dir / "project_info.txt"
        self.original_file_path = self.project_dir / f"original_{self.original_audio_file.name}"

    def _ensure_unique_project_dir(self, base_dir: Path) -> Path:
        """Ensure the project directory is unique by adding a counter if necessary."""
        if not base_dir.exists():
            return base_dir

        # Extract base name and parent
        base_name = base_dir.name
        parent = base_dir.parent

        # Try adding numbers until we find a unique directory
        counter = 1
        while True:
            new_name = f"{base_name}_{counter:02d}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1

            # Safety check to avoid infinite loop
            if counter > 999:
                # Fallback to timestamp with time if we somehow hit 999 projects
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                return parent / f"{base_name}_{timestamp}"

    def save_original_file(self, is_temporary: bool = False):
        """Save the original audio file to the project directory."""
        if is_temporary:
            # For uploaded temporary files, copy instead of move
            shutil.copy2(self.original_audio_file, self.original_file_path)
        else:
            # For recordings, move the file
            if self.original_audio_file != self.original_file_path:
                shutil.move(str(self.original_audio_file), self.original_file_path)

    def save_converted_file(self, converted_file: Path):
        """DEPRECATED: No longer saving converted files to avoid clutter.
        Converted files are now cleaned up after transcription."""
        # This method is kept for backward compatibility but does nothing
        pass

    def save_transcript(self, transcript: str):
        """Save the transcript to the project directory."""
        with open(self.transcript_file, "w", encoding="utf-8") as f:
            f.write(transcript)

    def save_project_info(self, metadata: Dict[str, Any]):
        """Save project metadata."""
        info_content = f"""Transcription Project: {self.name}
Created: {self.timestamp}
Original File: {self.original_audio_file.name}
Language: {metadata.get('language', 'unknown')}

Processing Time: {metadata.get('processing_time', 0):.2f} seconds
"""
        with open(self.project_info_file, "w", encoding="utf-8") as f:
            f.write(info_content)

    def get_files_created(self) -> list:
        """Get list of files created in the project."""
        files = []
        if self.project_dir.exists():
            for file_path in self.project_dir.iterdir():
                if file_path.is_file():
                    size = file_path.stat().st_size
                    files.append({
                        'name': file_path.name,
                        'path': file_path,
                        'size': size,
                        'type': self._get_file_type(file_path)
                    })
        return sorted(files, key=lambda x: x['name'])

    def _get_file_type(self, file_path: Path) -> str:
        """Determine file type for display."""
        suffix = file_path.suffix.lower()
        if suffix == '.txt':
            return 'text'
        elif suffix in self.settings.supported_audio_formats:
            return 'audio'
        else:
            return 'other'


def transcribe_audio(
    audio_file: Path,
    project_name: str,
    language: str = "en-US",
    is_temporary_file: bool = False,
    settings: Optional[Settings] = None,
    client: Optional[WhisperClient] = None
) -> Dict[str, Any]:
    """
    Transcribe an audio file and create an organized project.

    Args:
        audio_file: Path to the audio file
        project_name: Name for the transcription project
        language: Language code for transcription
        is_temporary_file: Whether the audio file is temporary (uploaded)
        settings: Settings instance
        client: WhisperClient instance

    Returns:
        Dictionary with transcription results and metadata
    """
    if settings is None:
        settings = Settings()
    if client is None:
        client = WhisperClient(settings)

    start_time = datetime.now()

    # Create transcription project
    project = TranscriptionProject(project_name, audio_file, settings)

    converted_file = None
    try:
        # STEP 1: Save original file first (preserve it immediately)
        project.save_original_file(is_temporary_file)
        logger.info(f"Original file preserved: {project.original_file_path}")

        # STEP 2: Convert audio to Whisper format for processing
        # Use the preserved original inside the project directory to avoid using a path that may be moved
        source_audio_for_conversion = project.original_file_path
        converted_file = convert_to_whisper_format(source_audio_for_conversion, settings=settings)
        logger.info(f"Audio converted for processing: {converted_file}")

        # Decide if we need chunking based on size/duration using SmartChunker logic
        audio_size_mb = converted_file.stat().st_size / (1024 * 1024)
        should_chunk = audio_size_mb > settings.max_file_size_mb or True  # always allow smart chunker to decide duration

        if should_chunk:
            file_size_mb = converted_file.stat().st_size / (1024*1024)
            logger.info(f"File is large ({file_size_mb:.1f}MB), chunking for transcription: {converted_file.name}")

            # Always use smart chunker
            smart_chunker = SmartChunker(settings)
            chunk_files = smart_chunker.chunk_large_file(converted_file)

            transcripts = []
            successful_chunks = 0
            failed_chunks = 0

            try:
                # Transcribe each chunk (skip validation since chunks are pre-validated to be small)
                total_chunks = len(chunk_files)
                for i, chunk_file in enumerate(chunk_files, 1):
                    logger.info(f"Transcribing chunk {i}/{total_chunks}: {chunk_file.name}")

                    try:
                        chunk_transcript = client.transcribe(chunk_file, language, skip_validation=True)
                        if chunk_transcript and chunk_transcript.strip():
                            transcripts.append(chunk_transcript)
                            successful_chunks += 1
                            logger.info(f"Chunk {i}/{total_chunks} completed successfully")
                        else:
                            logger.warning(f"Chunk {i}/{total_chunks} returned empty transcript")
                            failed_chunks += 1
                    except Exception as e:
                        logger.error(f"Failed to transcribe chunk {i}/{total_chunks}: {e}")
                        failed_chunks += 1
                        # Continue with other chunks, but track the failure

                # Check if we have any successful transcriptions
                if successful_chunks == 0:
                    raise RuntimeError(f"All {total_chunks} chunks failed to transcribe. No usable content generated.")
                elif failed_chunks > 0:
                    logger.warning(f"Transcription partially successful: {successful_chunks}/{total_chunks} chunks succeeded")

                # Merge transcripts
                transcript = merge_transcripts(transcripts)
                logger.info(f"Successfully merged {successful_chunks} chunk transcripts")

            finally:
                # Clean up chunk files
                smart_chunker.cleanup_chunks(chunk_files)
                logger.info("Chunk files cleaned up")
        else:
            # Transcribe audio normally (with validation)
            try:
                transcript = client.transcribe(converted_file, language, skip_validation=False)
                if not transcript or not transcript.strip():
                    raise RuntimeError("Transcription returned empty content")
                logger.info("Single file transcription completed successfully")
            except Exception as e:
                logger.error(f"Single file transcription failed: {e}")
                raise RuntimeError(f"Transcription failed: {str(e)}")

        # Calculate processing time
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        # STEP 3: Save transcript
        project.save_transcript(transcript)

        # STEP 4: Save project metadata
        metadata = {
            'language': language,
            'processing_time': processing_time
        }
        project.save_project_info(metadata)
        logger.info("Project metadata saved")

        # STEP 5: Clean up processing files
        try:
            # Clean up temporary uploaded file if needed
            if is_temporary_file and audio_file.exists():
                audio_file.unlink()
                logger.info(f"Temporary uploaded file cleaned up: {audio_file}")

            # Clean up converted file if it's different from original and not in project directory
            if (converted_file and
                converted_file.exists() and
                converted_file != project.original_file_path and
                not str(converted_file).startswith(str(project.project_dir))):
                converted_file.unlink()
                logger.info(f"Converted processing file cleaned up: {converted_file}")
        except Exception as cleanup_error:
            logger.warning(f"Cleanup warning: {cleanup_error}")
            # Don't fail the transcription due to cleanup issues

        # Determine if this was a partial success (for chunked files)
        partial_success = 'failed_chunks' in locals() and failed_chunks > 0

        return {
            'success': True,
            'transcript': transcript,
            'project_name': project_name,
            'project_dir': project.project_dir,
            'transcript_path': str(project.transcript_file),
            'metadata_path': str(project.project_info_file),
            'processing_time': processing_time,
            'files_created': project.get_files_created(),
            'metadata': metadata,
            'partial_success': partial_success,
            'successful_chunks': locals().get('successful_chunks', 1),
            'total_chunks': locals().get('total_chunks', 1)
        }

    except Exception as e:
        logger.error(f"Transcription failed: {e}")

        # Clean up converted file on error too
        try:
            if (converted_file and
                converted_file.exists() and
                not str(converted_file).startswith(str(project.project_dir))):
                converted_file.unlink()
                logger.info(f"Cleaned up converted file after error: {converted_file}")
        except Exception:
            pass  # Ignore cleanup errors during error handling

        return {
            'success': False,
            'error': str(e),
            'project_dir': project.project_dir
        }



def get_transcript_preview(transcript: str, num_lines: int = 5) -> str:
    """
    Get a preview of the transcript showing the first few lines.

    Args:
        transcript: Full transcript text
        num_lines: Number of lines to show in preview

    Returns:
        Preview text with line count if truncated
    """
    lines = transcript.split('\n')
    preview_lines = lines[:num_lines]
    preview_text = '\n'.join(preview_lines)

    if len(lines) > num_lines:
        preview_text += f"\n\n... ({len(lines) - num_lines} more lines)"

    return preview_text
