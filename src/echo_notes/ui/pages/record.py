"""Record page - recording new audio and using recent recordings."""

import streamlit as st
import time
from pathlib import Path

from ...config.settings import Settings
from ...core.recorder import AudioRecorder
from ..services import get_recent_recordings


def page_record():
    """Page for using recent recordings and recording new audio"""
    settings = Settings()

    # Initialize session state for recording
    if 'recording' not in st.session_state:
        st.session_state.recording = False
    if 'recording_start_time' not in st.session_state:
        st.session_state.recording_start_time = None
    if 'last_recording' not in st.session_state:
        st.session_state.last_recording = None

    # Load saved device preference from file
    if 'device_index' not in st.session_state:
        try:
            device_pref_file = Path.home() / '.echonotes_device'
            if device_pref_file.exists():
                saved_device = device_pref_file.read_text().strip()
                if saved_device and saved_device != 'None':
                    st.session_state.device_index = int(saved_device)
                else:
                    st.session_state.device_index = None
            else:
                st.session_state.device_index = None
        except:
            st.session_state.device_index = None

    # Create two columns: recording controls (primary) and recent recordings (secondary)
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🎙️ Record Audio")

        # Audio device selection
        import sounddevice as sd
        try:
            devices = sd.query_devices()
            input_devices = [d for i, d in enumerate(devices) if d['max_input_channels'] > 0]

            if input_devices:
                device_names = ["Default Device"] + [f"[{i}] {d['name']}" for i, d in enumerate(devices) if d['max_input_channels'] > 0]

                # Determine the default selection index based on stored device_index
                default_index = 0  # Default to "Default Device"
                stored_device_index = st.session_state.get('device_index')
                if stored_device_index is not None:
                    # Find the device in the list
                    for i, device_name in enumerate(device_names[1:], 1):  # Skip "Default Device"
                        device_index_from_name = int(device_name.split(']')[0][1:])
                        if device_index_from_name == stored_device_index:
                            default_index = i
                            break

                # Simple device selection with session state persistence
                selected_device = st.selectbox(
                    "Select microphone:",
                    device_names,
                    index=default_index,
                    help="Choose the microphone to use for recording",
                    key="device_selector"
                )

                # Extract device index from selection
                new_device_index = None
                if selected_device != "Default Device":
                    new_device_index = int(selected_device.split(']')[0][1:])

                # Update session state when device changes
                if st.session_state.get('device_index') != new_device_index:
                    st.session_state.device_index = new_device_index

                    # Save device preference to file for persistence across sessions
                    try:
                        device_pref_file = Path.home() / '.echonotes_device'
                        device_pref_file.write_text(str(new_device_index) if new_device_index is not None else 'None')
                    except:
                        pass  # Fail silently if we can't save

                    # Clear recorder to use new device
                    if 'recorder' in st.session_state:
                        del st.session_state.recorder
            else:
                st.warning("⚠️ No audio devices found")
                st.caption("Make sure sounddevice is installed")

        except Exception as e:
            st.error(f"Error querying audio devices: {e}")

        # Filename input (only show when not recording)
        if not st.session_state.recording:
            recording_filename = st.text_input(
                "Filename (optional):",
                key="recording_filename",
                placeholder="e.g., team-meeting, interview",
                help="Leave empty for auto-generated timestamp"
            )

        # Status and Controls
        if st.session_state.recording:
            st.success("🔴 **Recording Active**")
            if st.session_state.recording_start_time:
                elapsed = int(time.time() - st.session_state.recording_start_time)
                mins, secs = divmod(elapsed, 60)
                st.metric("Duration", f"{mins:02d}:{secs:02d}")

            # Show current filename when recording
            if 'current_recording_filename' in st.session_state and st.session_state.current_recording_filename:
                st.caption(f"📁 Recording: {st.session_state.current_recording_filename}")
            else:
                st.caption("📁 Recording: auto-generated name")
        else:
            # Show recent recording success message if just stopped
            if ('recording_just_stopped' in st.session_state and
                st.session_state.recording_just_stopped and
                'last_recording' in st.session_state):
                st.toast(f"🎤 Recording saved: {Path(st.session_state.last_recording).name}", icon="✅")

                # Clear the flag after showing the message
                st.session_state.recording_just_stopped = False

        # Control buttons - only show the actionable one
        if st.session_state.recording:
            # Show stop button when recording
            if st.button("⏹️ **Stop Recording**", use_container_width=True, type="primary"):
                # Stop recording
                if 'recorder' in st.session_state:
                    recording_path = st.session_state.recorder.stop_recording()
                    if recording_path:
                        st.session_state.recording = False
                        st.session_state.recording_start_time = None
                        st.session_state.last_recording = recording_path
                        st.session_state.recording_just_stopped = True

                        # Clear recording filename state
                        if 'current_recording_filename' in st.session_state:
                            del st.session_state.current_recording_filename

                        # Clear selected file state to avoid conflicts
                        if 'selected_file' in st.session_state:
                            del st.session_state.selected_file
                        if 'selection_method' in st.session_state:
                            del st.session_state.selection_method

                        st.toast("🎤 Recording stopped and saved!", icon="✅")
                        st.rerun()
                    else:
                        st.toast("❌ Failed to stop recording", icon="⚠️")
        else:
            # Show start button when not recording
            if st.button("🔴 **Start Recording**", use_container_width=True, type="primary"):
                # Create recorder if needed
                if 'recorder' not in st.session_state:
                    device_index = st.session_state.get('device_index', None)
                    try:
                        st.session_state.recorder = AudioRecorder(device_index=device_index)
                    except Exception as e:
                        st.error(f"Failed to create recorder: {e}")
                        return

                # Start recording
                filename = recording_filename if 'recording_filename' in locals() and recording_filename.strip() else None
                recorder = st.session_state.recorder
                if recorder.start_recording(filename):
                    st.session_state.recording = True
                    st.session_state.recording_start_time = time.time()
                    # Store the actual filename that will be used (may include counter for uniqueness)
                    actual_filename = Path(recorder.output_file).name if hasattr(recorder, 'output_file') else filename
                    st.session_state.current_recording_filename = actual_filename
                    st.toast("🎤 Recording started!", icon="✅")
                    st.rerun()
                else:
                    st.toast("❌ Failed to start recording", icon="⚠️")

        # Auto-refresh when recording to update the clock
        if st.session_state.recording:
            time.sleep(0.5)  # Half second delay for smoother updates
            st.rerun()

    with col2:
        st.subheader("📁 Recent Recordings")
        recordings = get_recent_recordings(settings)
        if recordings:
            st.info(f"📊 **{len(recordings)} recordings found**")
            st.markdown("Go to the **Transcribe** page to transcribe these recordings.")

            # Show recent recordings list (read-only)
            for i, recording in enumerate(recordings[:5]):  # Show only first 5
                size_mb = recording.stat().st_size / (1024 * 1024)
                mod_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(recording.stat().st_mtime))
                st.text(f"🎵 {recording.name} ({size_mb:.1f}MB, {mod_time})")

            if len(recordings) > 5:
                st.caption(f"... and {len(recordings) - 5} more recordings")

        else:
            st.info("No recordings yet. Start recording to see them here!")
