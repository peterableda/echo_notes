"""Browse page - browsing existing transcriptions."""

import streamlit as st
import os

from ...config.settings import Settings
from ...core.transcription import get_transcript_preview
from ..services import get_transcription_projects
# Navigation handled via Page objects exposed in session state


def page_browse_transcriptions():
    """Page for browsing existing transcriptions"""
    settings = Settings()

    st.subheader("📚 Browse Transcriptions")
    projects = get_transcription_projects(settings)

    if projects:
        st.info(f"Found {len(projects)} transcription projects")

        for project in projects:
            with st.expander(f"📄 **{project['name']}** - {project['created']}", expanded=False):
                # Project metadata
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Language:** {project['language']}")
                    st.write(f"**Created:** {project['created']}")
                with col2:
                    st.write(f"**Audio files:** {len(project['audio_files'])}")
                    if project['audio_files']:
                        st.write(f"**Original:** {project['audio_files'][0].name}")

                # Audio playback
                if project['audio_files']:
                    st.markdown("**🎵 Audio Playback:**")
                    # Use the first audio file (usually the original)
                    audio_file = project['audio_files'][0]

                    # Check if file exists before trying to load
                    if audio_file.exists():
                        try:
                            # Use a unique key for each audio file to avoid session conflicts
                            audio_key = f"audio_{project['dir'].name}_{audio_file.name}"

                            # Read the file as bytes to avoid path-related issues
                            with open(audio_file, 'rb') as f:
                                audio_bytes = f.read()

                            st.audio(audio_bytes, format='audio/wav')

                        except Exception as e:
                            st.warning(f"⚠️ Audio file exists but could not be loaded: {e}")
                            st.caption(f"File path: `{audio_file}`")
                    else:
                        st.warning(f"⚠️ Audio file not found: `{audio_file.name}`")

                # Transcript preview
                if project['transcript_file'].exists():
                    try:
                        with open(project['transcript_file'], 'r', encoding='utf-8') as f:
                            transcript = f.read()

                        st.markdown("**📝 Transcript Preview:**")
                        preview = get_transcript_preview(transcript, 5)
                        st.text_area(
                            "Transcript content:",
                            value=preview,
                            height=150,
                            disabled=True,
                            key=f"preview_{project['dir'].name}"
                        )

                        # Download and action buttons
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            # Open chat button with consistent styling
                            if st.button(
                                "💬 Open Chat",
                                key=f"chat_{project['dir'].name}",
                                help="Open this transcript in the chat interface",
                                use_container_width=True
                            ):
                                # Set preselect data and navigate
                                st.session_state.preselect_transcript_path = str(project['transcript_file'])
                                st.session_state.preselect_project_name = project['name']

                                # Navigate to chat page
                                page_refs = st.session_state.get("page_refs", {})
                                chat_page = page_refs.get("Chat with Transcription")
                                if chat_page is not None:
                                    st.switch_page(chat_page)
                                else:
                                    st.switch_page("Chat with Transcription")

                        with col2:
                            # Download button styled to match page_link
                            st.download_button(
                                label="⬇️ Download Transcript",
                                data=transcript,
                                file_name=f"{project['name']}_transcript.txt",
                                mime="text/plain",
                                key=f"download_{project['dir'].name}",
                                use_container_width=True
                            )

                        with col3:
                            # Open folder button styled to match page_link
                            if st.button(
                                "📁 Open Folder",
                                key=f"folder_{project['dir'].name}",
                                help=f"Open {project['dir']} in Finder",
                                use_container_width=True
                            ):
                                try:
                                    os.system(f"open '{project['dir']}'")
                                    st.toast("📁 Folder opened!", icon="✅")
                                except Exception as e:
                                    st.toast(f"❌ Could not open folder: {e}", icon="⚠️")

                    except Exception as e:
                        st.error(f"Could not read transcript: {e}")
                else:
                    st.warning("Transcript file not found")

                st.divider()
    else:
        st.info("No transcription projects found. Create some transcriptions first!")
        st.markdown("💡 **Tip:** Record audio or upload files, then transcribe them to see projects here.")
