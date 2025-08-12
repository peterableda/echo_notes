"""Transcribe page - upload files or transcribe recent recordings."""

import os
import streamlit as st
import tempfile
import time
from pathlib import Path

from ...config.settings import Settings
from ...core.transcription import (
    transcribe_audio,
    get_transcript_preview
)
from ...core.audio import get_audio_info
from ..services import get_recent_recordings, format_filename_for_display
# Navigation is handled via Page objects exposed in session state


def page_transcribe():
    """Page for transcribing audio - either uploaded files or recent recordings."""
    settings = Settings()

    st.header("🚀 Transcribe Audio")
    st.markdown("Upload a new audio file or select from your recent recordings to transcribe.")

    # Clean up old temporary files from session state (older than 1 hour)
    _cleanup_old_temp_files()

    # Use tabs - Recent Recordings first as primary use case
    tab1, tab2 = st.tabs(["📁 Recent Recordings", "📤 Upload"])

    with tab1:
        _show_recent_recordings_section(settings)

    with tab2:
        _show_upload_section(settings)


def _show_upload_section(settings: Settings):
    """Upload section for new files - optimized for full-width layout."""

    # Check if we have a file already processed and stored
    has_processed_file = any(key.startswith("upload_") for key in st.session_state.keys())

    if not has_processed_file:
        # Create a centered layout for the uploader
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            uploaded_file = st.file_uploader(
                "Choose your audio file:",
                type=['wav', 'mp3', 'm4a', 'flac', 'ogg', 'mp4', 'avi', 'mov'],
                help="Drag and drop or browse for audio/video files",
                key="transcribe_uploader"
            )

        # Handle file upload and processing
        if uploaded_file is not None:
            # Save uploaded file temporarily and store in session state
            file_extension = uploaded_file.name.split('.')[-1].lower()

            # Create a unique key for this upload
            upload_key = f"upload_{uploaded_file.name}_{len(uploaded_file.getvalue())}"

            # Store file in session state
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file.flush()
                st.session_state[upload_key] = {
                    'temp_path': tmp_file.name,
                    'original_name': uploaded_file.name,
                    'size_mb': len(uploaded_file.getvalue()) / (1024 * 1024)
                }

            # Rerun to hide uploader and show file processing UI
            st.rerun()

        else:
            # Compact help information
            st.info("📁 **Supported formats:** WAV, MP3, M4A, FLAC, MP4, AVI, MOV, OGG")
            st.caption("💡 Audio files work best. Video files will have audio extracted automatically.")

    else:
        # File uploader is hidden, show the processed file UI in optimized layout
        upload_keys = [key for key in st.session_state.keys() if key.startswith("upload_")]
        upload_key = upload_keys[0]  # Get the first (should be only one)
        file_info = st.session_state[upload_key]

        # Show file processing UI with better use of horizontal space
        _show_file_processing_ui(file_info, settings)


def _show_file_processing_ui(file_info: dict, settings: Settings):
    """Show the file processing UI for an uploaded file."""
    upload_time = time.strftime("%H:%M", time.localtime())

    # Show temporary success notification if file was just uploaded
    upload_key = f"upload_{file_info['original_name']}_{file_info['size_mb']}"
    notification_key = f"notification_shown_{upload_key}"

    # Show notification only once when file is first processed
    if notification_key not in st.session_state:
        st.toast("📁 File uploaded successfully!", icon="✅")
        st.session_state[notification_key] = True

    # Center the file tile in the available space
    col1, col2, col3 = st.columns([1, 3, 1])

    with col2:
        # Show uploaded file in a beautiful tile/card with embedded X button
        with st.container():
            # Create columns for the tile layout
            tile_col1, tile_col2 = st.columns([5, 1])

            with tile_col1:
                # Main tile content
                tile_css = f"""
                <div style="
                    border: 2px solid #28a745;
                    border-radius: 12px;
                    padding: 20px;
                    margin-bottom: 16px;
                    background: linear-gradient(135deg, #f8fff9 0%, #e8f5e8 100%);
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    position: relative;
                ">
                    <div>
                        <div style="font-weight: bold; color: #155724; margin-bottom: 8px; font-size: 1.2em;">
                            📁 {file_info['original_name']}
                        </div>
                        <div style="color: #6c757d; font-size: 0.95em; margin-bottom: 4px;">
                            📊 {file_info['size_mb']:.1f}MB • 🕒 {upload_time}
                        </div>
                        <div style="color: #28a745; font-size: 0.9em; font-weight: 500;">
                            ✅ Ready for transcription
                        </div>
                    </div>
                </div>
                """
                st.markdown(tile_css, unsafe_allow_html=True)

            with tile_col2:
                # X button positioned in the top-right area of the tile
                st.markdown("<div style='margin-top: 8px;'>", unsafe_allow_html=True)

                # Disable X button if transcription is in progress
                transcription_in_progress = (st.session_state.get('transcription_in_progress') and
                                           st.session_state.get('transcription_file') == file_info['temp_path'])

                if transcription_in_progress:
                    # Show disabled button with different styling
                    st.markdown("""
                    <div style="
                        background-color: #f8f9fa;
                        border: 1px solid #dee2e6;
                        border-radius: 4px;
                        color: #6c757d;
                        padding: 8px;
                        text-align: center;
                        cursor: not-allowed;
                        opacity: 0.5;
                    ">✖</div>
                    """, unsafe_allow_html=True)
                else:
                    if st.button("✖", key=f"clear_{file_info['original_name']}", help="Upload different file",
                                use_container_width=True):
                        # Clear any stored upload data
                        keys_to_remove = [key for key in st.session_state.keys() if key.startswith("upload_")]
                        for key in keys_to_remove:
                            if key in st.session_state:
                                # Clean up temporary file
                                try:
                                    temp_path = st.session_state[key].get('temp_path')
                                    if temp_path and os.path.exists(temp_path):
                                        os.unlink(temp_path)
                                except:
                                    pass
                                del st.session_state[key]

                        # Also clear notification state
                        notification_keys_to_remove = [key for key in st.session_state.keys() if key.startswith("notification_")]
                        for notif_key in notification_keys_to_remove:
                            del st.session_state[notif_key]

                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        # Project Name input - centered and with better layout
        st.markdown("**Project Name:**")
        project_name = st.text_input(
            "Enter project name (optional):",
            value=file_info['original_name'].rsplit('.', 1)[0],  # Default to filename without extension
            key=f"project_name_upload_{file_info['original_name']}",
            label_visibility="collapsed"
        )

        # Start transcription directly - centered button
        if st.button(f"🚀 **Start Transcription**",
                    key=f"transcribe_upload_{file_info['original_name']}",
                    use_container_width=True,
                    type="primary"):

            final_project_name = project_name.strip() if project_name.strip() else file_info['original_name'].rsplit('.', 1)[0]

            if not final_project_name:
                st.error("Please enter a project name")
            else:
                # Set transcription in progress state
                st.session_state.transcription_in_progress = True
                st.session_state.transcription_file = file_info['temp_path']
                st.session_state.transcription_project_name = final_project_name
                st.rerun()

    # Check if transcription is in progress for this file
    if (st.session_state.get('transcription_in_progress') and
        st.session_state.get('transcription_file') == file_info['temp_path']):

        # Show transcription progress instead of file controls
        st.markdown("---")
        st.markdown("### 🔄 Transcription in Progress")

        # Show progress
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            status_text.text("🔄 Starting transcription...")
            progress_bar.progress(10)

            # Show audio file info
            try:
                audio_info = get_audio_info(file_info['temp_path'])
                if audio_info:
                    duration_str = f"{audio_info['duration']:.1f}s"
                    st.caption(f"📊 Duration: {duration_str} | Size: {file_info['size_mb']:.1f}MB")
            except Exception:
                pass  # Don't fail if we can't get audio info

            # Detailed transcription with progress tracking
            audio_size_mb = Path(file_info['temp_path']).stat().st_size / (1024 * 1024)
            needs_chunking = audio_size_mb > settings.max_file_size_mb

            if needs_chunking:
                status_text.text(f"📝 Large file detected ({audio_size_mb:.1f}MB) - using smart chunking...")
                st.caption("💡 Large files are automatically split into chunks for optimal transcription")

                # Detailed chunking progress
                result = _transcribe_with_detailed_progress(
                    Path(file_info['temp_path']),
                    st.session_state.transcription_project_name,
                    status_text,
                    progress_bar,
                    settings,
                    is_temporary_file=True
                )
            else:
                status_text.text("📝 Transcribing audio...")
                result = transcribe_audio(
                    Path(file_info['temp_path']),  # Convert to Path object
                    st.session_state.transcription_project_name,
                    language="en-US",  # Default language
                    is_temporary_file=True,
                    settings=settings
                )

            progress_bar.progress(90)

            # Always generate preview
            if result.get('success'):
                status_text.text("📋 Generating preview...")
                try:
                    # Generate preview from the transcript text directly
                    result['preview'] = get_transcript_preview(
                        result['transcript'],
                        num_lines=5
                    )
                except Exception as e:
                    # Don't fail the whole process if preview fails
                    st.warning(f"Preview generation failed: {e}")

            progress_bar.progress(100)
            status_text.text("✅ Transcription completed!")

            # Clear transcription state
            st.session_state.transcription_in_progress = False
            if 'transcription_file' in st.session_state:
                del st.session_state['transcription_file']
            if 'transcription_project_name' in st.session_state:
                del st.session_state['transcription_project_name']

            # Show results; navigation is presented as a link in the success UI
            if result.get('success'):
                _show_transcription_success(result, settings)
            else:
                _show_transcription_error(result)

        except ValueError as e:
            # Clear transcription state on error
            st.session_state.transcription_in_progress = False
            _show_validation_error(e)
        except Exception as e:
            # Clear transcription state on error
            st.session_state.transcription_in_progress = False
            _show_general_error(e)
        finally:
            # Clean up progress indicators
            progress_bar.empty()
            status_text.empty()


def _show_recent_recordings_section(settings: Settings):
    """Recent recordings section with two-column layout."""

    recordings = get_recent_recordings(settings)

    if not recordings:
        st.info("📂 **No recent recordings found.**")
        st.markdown("Go to the **Record** page to create some recordings first.")
        return

    # Two-column layout: recordings list on left, controls on right (50/50 split)
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown(f"**Choose from {len(recordings)} recent recordings:**")

        # Group by date for better organization
        recordings_by_date = {}
        for recording in recordings:
            date = time.strftime("%Y-%m-%d", time.localtime(recording.stat().st_mtime))
            if date not in recordings_by_date:
                recordings_by_date[date] = []
            recordings_by_date[date].append(recording)

        # Show recordings grouped by date
        for date, date_recordings in recordings_by_date.items():
            with st.expander(f"📅 {date} ({len(date_recordings)} files)", expanded=(date == list(recordings_by_date.keys())[0])):
                for i, recording in enumerate(date_recordings):
                    # Create a container for each recording
                    with st.container():
                        # Recording info
                        size_mb = recording.stat().st_size / (1024 * 1024)
                        mod_time = time.strftime("%H:%M", time.localtime(recording.stat().st_mtime))

                        # Check if this recording is selected
                        is_selected = (st.session_state.get('selected_recent_file') == str(recording) and
                                     st.session_state.get('selected_recent_name') == recording.name)

                        # Recording display with selection
                        rec_col1, rec_col2 = st.columns([3, 1])
                        with rec_col1:
                            st.write(f"🎵 **{recording.name}**")
                            st.caption(f"{size_mb:.1f}MB • {mod_time}")

                        with rec_col2:
                            if is_selected:
                                st.success("✅ Selected")
                            else:
                                if st.button("Select", key=f"select_{recording.name}", type="primary"):
                                    st.session_state.selected_recent_file = str(recording)
                                    st.session_state.selected_recent_name = recording.name
                                    st.rerun()

                        # Only show separator between recordings if there are multiple recordings in this date
                        if len(date_recordings) > 1 and i < len(date_recordings) - 1:
                            st.markdown("---")  # Separator between recordings

    with col2:
        # Show transcription controls when a recording is selected
        if st.session_state.get('selected_recent_file') and st.session_state.get('selected_recent_name'):
            st.markdown("**📋 Transcription Setup**")

            # Get selected file info
            selected_file = st.session_state.get('selected_recent_file')
            selected_name = st.session_state.get('selected_recent_name')

            # Project name input
            project_name = st.text_input(
                "Project Name:",
                value=selected_name.rsplit('.', 1)[0],  # Default to filename without extension
                key=f"project_name_recent_{selected_name}",
                help="This will be used as the folder name for organizing transcripts"
            )

            # Start transcription button
            if st.button("🚀 **Start Transcription**",
                        key=f"transcribe_recent_{selected_name}",
                        type="primary",
                        use_container_width=True):

                if not project_name.strip():
                    st.error("Please enter a project name")
                else:
                    # Show progress
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    try:
                        status_text.text("🔄 Starting transcription...")
                        progress_bar.progress(10)

                        # Show audio file info
                        try:
                            audio_info = get_audio_info(selected_file)
                            if audio_info:
                                duration_str = f"{audio_info['duration']:.1f}s"
                                size_mb = audio_info['size_mb']
                                st.caption(f"📊 Duration: {duration_str} | Size: {size_mb:.1f}MB")
                        except Exception:
                            pass  # Don't fail if we can't get audio info

                        # Detailed transcription with progress tracking
                        audio_size_mb = Path(selected_file).stat().st_size / (1024 * 1024)
                        needs_chunking = audio_size_mb > settings.max_file_size_mb

                        if needs_chunking:
                            status_text.text(f"📝 Large file detected ({audio_size_mb:.1f}MB) - using smart chunking...")
                            st.caption("💡 Large files are automatically split into chunks for optimal transcription")

                            # Detailed chunking progress
                            result = _transcribe_with_detailed_progress(
                                Path(selected_file),
                                project_name.strip(),
                                status_text,
                                progress_bar,
                                settings,
                                is_temporary_file=False
                            )
                        else:
                            status_text.text("📝 Transcribing audio...")
                            result = transcribe_audio(
                                Path(selected_file),  # Convert to Path object
                                project_name.strip(),
                                language="en-US",  # Default language
                                is_temporary_file=False,  # Recent recordings are not temporary
                                settings=settings
                            )

                        progress_bar.progress(90)

                        # Always generate preview
                        if result.get('success'):
                            status_text.text("📋 Generating preview...")
                            try:
                                # Generate preview from the transcript text directly
                                result['preview'] = get_transcript_preview(
                                    result['transcript'],
                                    num_lines=5
                                )
                            except Exception as e:
                                # Don't fail the whole process if preview fails
                                st.warning(f"Preview generation failed: {e}")

                        progress_bar.progress(100)
                        status_text.text("✅ Transcription completed!")

                        # Show results; navigation is presented as a link in the success UI
                        if result.get('success'):
                            _show_transcription_success(result, settings)
                        else:
                            _show_transcription_error(result)

                    except ValueError as e:
                        _show_validation_error(e)
                    except Exception as e:
                        _show_general_error(e)
                    finally:
                        # Clean up progress indicators
                        progress_bar.empty()
                        status_text.empty()
        else:
            st.info("👈 **Select a recording** from the list to start transcription")


def show_transcription_options(audio_file: str, selection_method: str, settings: Settings, project_name: str = None, is_temporary_file: bool = False) -> None:
    """Transcription UI component for processing audio files."""
    st.markdown("**Transcription Options**")

    # Get default name from filename
    if selection_method == "Upload file":
        filename = st.session_state.get('uploaded_filename', Path(audio_file).name)
        default_name = format_filename_for_display(filename)
    elif selection_method == "Use recent recording":
        default_name = format_filename_for_display(Path(audio_file).name)
    else:
        default_name = format_filename_for_display(Path(audio_file).name)

    # Use provided project name or ask for input
    if project_name:
        transcription_name = project_name
        st.info(f"📁 **Project Name:** {transcription_name}")
    else:
        # Transcription name input
        transcription_name = st.text_input(
            "Project Name:",
            value=default_name,
            help="This will be used as the folder name for organizing transcripts"
        )

        if not transcription_name.strip():
            st.warning("⚠️ Please enter a project name")
            return

    # Audio file info
    try:
        audio_info = get_audio_info(audio_file)
        if audio_info:
            duration_str = f"{audio_info['duration']:.1f}s"
            size_mb = audio_info['size_mb']
            st.caption(f"📊 Duration: {duration_str} | Size: {size_mb:.1f}MB")
    except Exception:
        pass  # Don't fail if we can't get audio info

    # Start transcription button
    if st.button("🚀 Start Transcription", type="primary", use_container_width=True):
        if not transcription_name.strip():
            st.error("Please enter a project name")
            return

        # Show progress
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            status_text.text("🔄 Starting transcription...")
            progress_bar.progress(10)

            # Transcribe audio
            status_text.text("📝 Transcribing audio...")
            result = transcribe_audio(
                Path(audio_file),  # Convert to Path object
                transcription_name.strip(),
                language="en-US",  # Default language
                is_temporary_file=is_temporary_file,
                settings=settings
            )

            progress_bar.progress(90)

            # Always generate preview
            if result.get('success'):
                status_text.text("📋 Generating preview...")
                try:
                    # Generate preview from the transcript text directly
                    result['preview'] = get_transcript_preview(
                        result['transcript'],
                        num_lines=5
                    )
                except Exception as e:
                    # Don't fail the whole process if preview fails
                    st.warning(f"Preview generation failed: {e}")

            progress_bar.progress(100)
            status_text.text("✅ Transcription completed!")

            # Show results; navigation is presented as a link in the success UI
            if result.get('success'):
                _show_transcription_success(result, settings)
            else:
                _show_transcription_error(result)

        except ValueError as e:
            _show_validation_error(e)
        except Exception as e:
            _show_general_error(e)
        finally:
            # Clean up progress indicators
            progress_bar.empty()
            status_text.empty()


def _show_transcription_success(result: dict, settings: Settings) -> bool:
    """Display successful transcription results.

    Returns False (kept for backward compatibility). Navigation is offered as a page link.
    """
    # Check if this was a partial success
    partial_success = result.get('partial_success', False)
    successful_chunks = result.get('successful_chunks', 1)
    total_chunks = result.get('total_chunks', 1)

    if partial_success:
        st.warning(f"⚠️ **Transcription Partially Completed** ({successful_chunks}/{total_chunks} chunks succeeded)")
        st.info("Some chunks failed to transcribe, but we recovered what we could. Check the transcript for any gaps.")
    else:
        st.success("🎉 **Transcription Completed Successfully!**")

    # Project info
    project_name = result.get('project_name', 'Unknown')
    st.info(f"📁 **Project:** {project_name}")

    # Show file paths
    with st.expander("📄 Generated Files", expanded=True):
        if 'transcript_path' in result:
            st.text(f"📝 Transcript: {result['transcript_path']}")
        if 'metadata_path' in result:
            st.text(f"📊 Metadata: {result['metadata_path']}")

    # Show preview (always generated)
    if 'preview' in result:
        st.text_area(
            "📋 Preview (first 100 words):",
            value=result['preview'],
            height=120,
            disabled=True
        )

    # Quick actions
    col1, col2 = st.columns(2)

    transcript_path = result.get('transcript_path')
    project_name = result.get('project_name')

    with col1:
        if transcript_path and project_name:
            # Set preselect for Chat page
            st.session_state.preselect_transcript_path = transcript_path
            st.session_state.preselect_project_name = project_name

            # Show a single, reliable page link (requires Page object exposure in session_state)
            chat_page = st.session_state.get("page_refs", {}).get("Chat with Transcription")
            if chat_page is not None:
                st.page_link(page=chat_page, label="Chat with Transcript", use_container_width=True)
            else:
                st.info("Use the 'Chat with Transcription' tab above to continue.")
        else:
            st.button(
                "💬 Chat with Transcript",
                disabled=True,
                help="Transcript data not available",
                use_container_width=True,
                key="chat_from_transcribe_disabled",
            )
            if not transcript_path:
                st.caption("⚠️ Missing transcript path")
            if not project_name:
                st.caption("⚠️ Missing project name")

    with col2:
        browse_page = st.session_state.get("page_refs", {}).get("Browse Transcriptions")
        if browse_page is not None:
            st.page_link(page=browse_page, label="Browse All Transcripts", use_container_width=True)
        else:
            st.page_link(page="Browse Transcriptions", label="Browse All Transcripts", use_container_width=True)

    # We no longer rely on a return flag; navigation is handled above or via link.
    return False


def _show_transcription_error(result: dict) -> None:
    """Display transcription error information."""
    st.error("❌ **Transcription Failed**")

    error_msg = result.get('error', 'Unknown error occurred')
    st.error(f"**Error:** {error_msg}")

    # Show additional error details if available
    if 'details' in result:
        with st.expander("🔍 Error Details"):
            st.code(result['details'])


def _show_validation_error(error: ValueError) -> None:
    """Display validation error."""
    st.error("⚠️ **Validation Error**")
    st.error(f"**Issue:** {str(error)}")
    st.info("Please check your input and try again.")


def _show_general_error(error: Exception) -> None:
    """Display general error information."""
    st.error("💥 **Unexpected Error**")
    st.error(f"**Error:** {str(error)}")
    st.info("Please try again or contact support if the problem persists.")


def _cleanup_old_temp_files() -> None:
    """Clean up old temporary files from session state."""
    import os
    import time

    keys_to_remove = []
    current_time = time.time()

    for key in st.session_state:
        if key.startswith("upload_") and isinstance(st.session_state[key], dict):
            file_info = st.session_state[key]
            if 'temp_path' in file_info:
                temp_path = file_info['temp_path']
                try:
                    # Check if file exists and is older than 1 hour
                    if os.path.exists(temp_path):
                        file_age = current_time - os.path.getmtime(temp_path)
                        if file_age > 3600:  # 1 hour
                            os.unlink(temp_path)
                            keys_to_remove.append(key)
                    else:
                        # File doesn't exist, remove from session state
                        keys_to_remove.append(key)
                except:
                    # If there's any error, just remove from session state
                    keys_to_remove.append(key)

    # Remove old entries from session state
    for key in keys_to_remove:
        del st.session_state[key]


def _transcribe_with_detailed_progress(
    audio_file: Path,
    project_name: str,
    status_text,
    progress_bar,
    settings,
    is_temporary_file: bool = False
):
    """Transcribe audio with detailed UI progress updates for chunking."""
    from ...core.audio import convert_to_whisper_format
    from ...core.smart_chunker import SmartChunker, merge_transcripts
    from ...core.transcription import TranscriptionProject
    from ...api.whisper_client import WhisperClient
    from datetime import datetime
    import streamlit as st

    start_time = datetime.now()

    try:
        # Step 1: Convert audio format
        status_text.text("🔧 Converting to optimal audio format...")
        progress_bar.progress(5)
        converted_file = convert_to_whisper_format(audio_file, settings=settings)

        # Step 2: Create chunks
        status_text.text("✂️ Creating smart chunks...")
        progress_bar.progress(10)
        smart_chunker = SmartChunker(settings)
        chunk_files = smart_chunker.chunk_large_file(converted_file)
        total_chunks = len(chunk_files)

        # Show chunk info
        status_text.text(f"📦 Created {total_chunks} chunks for transcription")
        st.caption(f"🎯 Processing {total_chunks} audio segments of ~{settings.max_file_size_mb}MB each")
        progress_bar.progress(15)

        # Step 3: Transcribe chunks with detailed progress
        client = WhisperClient(settings)
        transcripts = []
        chunk_progress_container = st.empty()

        for i, chunk_file in enumerate(chunk_files, 1):
            # Update main progress (15% to 80% for chunk transcription)
            chunk_progress = 15 + ((i - 1) / total_chunks) * 65
            progress_bar.progress(int(chunk_progress))

            # Update status
            status_text.text(f"📝 Transcribing chunk {i}/{total_chunks}...")

            # Show detailed chunk info
            chunk_size_mb = chunk_file.stat().st_size / (1024 * 1024)
            chunk_progress_container.markdown(f"""
            **Current Chunk:** `{chunk_file.name}`
            **Size:** {chunk_size_mb:.1f}MB | **Progress:** {i}/{total_chunks} chunks
            **Status:** 🔄 Processing...
            """)

            try:
                chunk_transcript = client.transcribe(chunk_file, "en-US", skip_validation=True)
                transcripts.append(chunk_transcript)

                # Show success for this chunk
                chunk_progress_container.markdown(f"""
                **Completed Chunk:** `{chunk_file.name}`
                **Size:** {chunk_size_mb:.1f}MB | **Progress:** {i}/{total_chunks} chunks
                **Status:** ✅ Complete ({len(chunk_transcript)} characters)
                """)

                # Brief pause to show completion
                import time
                time.sleep(0.5)

            except Exception as e:
                st.warning(f"⚠️ Error in chunk {i}/{total_chunks}: {str(e)}")
                transcripts.append(f"[Error transcribing chunk {i}: {str(e)}]")

        # Step 4: Merge transcripts
        status_text.text("🔗 Merging chunk transcripts...")
        progress_bar.progress(85)
        chunk_progress_container.markdown(f"""
        **Merging Results:** Combining {len(transcripts)} transcripts
        **Status:** 🔄 Removing overlaps and joining text...
        """)

        transcript = merge_transcripts(transcripts)

        # Step 5: Save project files
        status_text.text("💾 Saving project files...")
        progress_bar.progress(95)

        project = TranscriptionProject(project_name, audio_file, settings)
        project.save_original_file(is_temporary_file)
        project.save_converted_file(converted_file)
        project.save_transcript(transcript)

        # Save metadata
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        metadata = {
            'language': "en-US",
            'processing_time': processing_time,
            'chunks_processed': total_chunks
        }
        project.save_project_info(metadata)

        # Cleanup
        smart_chunker.cleanup_chunks(chunk_files)

        # Final success message
        chunk_progress_container.markdown(f"""
        **✅ Transcription Complete!**
        **Total chunks:** {total_chunks} | **Processing time:** {processing_time:.1f}s
        **Final transcript:** {len(transcript):,} characters
        """)

        return {
            'success': True,
            'transcript': transcript,
            'project_name': project_name,
            'project_dir': project.project_dir,
            'transcript_path': str(project.transcript_file),
            'metadata_path': str(project.project_info_file),
            'processing_time': processing_time,
            'files_created': project.get_files_created(),
            'metadata': metadata
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'project_dir': None
        }
