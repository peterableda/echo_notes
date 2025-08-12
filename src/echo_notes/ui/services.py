"""Shared services and utility functions used by multiple pages."""

from pathlib import Path
from typing import List, Dict, Any

from ..config.settings import Settings


def format_filename_for_display(filename: str) -> str:
    """Format filename for better display as default project name."""
    name = Path(filename).stem
    name = name.replace("_", " ").replace("-", " ").title()
    return name


def get_transcription_projects(settings: Settings) -> List[Dict[str, Any]]:
    """Get list of transcription projects with metadata."""
    if not settings.transcriptions_dir.exists():
        return []

    projects = []
    for project_dir in settings.transcriptions_dir.iterdir():
        if project_dir.is_dir():
            project_info_file = project_dir / "project_info.txt"
            transcript_file = project_dir / "transcript.txt"

            audio_files = []
            for ext in settings.supported_audio_formats:
                audio_files.extend(project_dir.glob(f"*{ext}"))

            if transcript_file.exists():
                project_name = project_dir.name
                created_date = "Unknown"
                language = "Unknown"

                if project_info_file.exists():
                    try:
                        content = project_info_file.read_text(encoding='utf-8')
                        for line in content.split('\n'):
                            if line.startswith("Transcription Project:"):
                                project_name = line.split(":", 1)[1].strip()
                            elif line.startswith("Created:"):
                                created_date = line.split(":", 1)[1].strip()
                            elif line.startswith("Language:"):
                                language = line.split(":", 1)[1].strip()
                    except Exception:
                        pass

                projects.append({
                    'name': project_name,
                    'dir': project_dir,
                    'created': created_date,
                    'language': language,
                    'transcript_file': transcript_file,
                    'audio_files': audio_files,
                    'modified_time': project_dir.stat().st_mtime,
                })

    projects.sort(key=lambda x: x['modified_time'], reverse=True)
    return projects


def get_recent_recordings(settings: Settings) -> List[Path]:
    """Get list of recent recordings."""
    if not settings.meetings_dir.exists():
        return []

    recordings = []
    for ext in settings.supported_audio_formats:
        recordings.extend(settings.meetings_dir.glob(f"*{ext}"))

    # Sort by modification time (newest first) and return top 10
    recordings.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return recordings[:10]
