"""Chat page - chatting with transcriptions using LLM."""

import streamlit as st

from ...config.settings import Settings
from ...core.transcription import get_transcript_preview
from ..services import get_transcription_projects


def page_chat_with_transcription():
    """Page for chatting with transcriptions using LLM"""
    settings = Settings()

    # Check if we were navigated here from transcription completion
    if 'preselect_transcript_path' in st.session_state:
        preselect_name = st.session_state.get('preselect_project_name', 'Unknown')
        st.info(f"🎯 **Ready to chat with:** {preselect_name}")
        st.markdown("---")

    # Initialize LLM client - cache in session state to avoid recreation on every rerun
    if 'llm_client' not in st.session_state:
        try:
            from echo_notes.api.llm_client import LLMClient
            st.session_state.llm_client = LLMClient(settings)
        except Exception as e:
            st.error(f"Failed to initialize LLM client: {e}")
            st.info("Please check your API configuration in the environment variables.")
            return

    llm_client = st.session_state.llm_client

    # Sidebar for transcription selection and controls
    with st.sidebar:
        st.header("💬 Chat Controls")

        # Transcription selector
        projects = get_transcription_projects(settings)

        if projects:
            st.markdown("**📄 Select Transcription:**")
            # Create a selectbox with project names
            project_options = [f"{p['name']} ({p['created']})" for p in projects]

            # Check if we should pre-select a specific transcript
            default_idx = 0
            preselected = False
            if 'preselect_transcript_path' in st.session_state:
                preselect_path = st.session_state.preselect_transcript_path
                preselect_name = st.session_state.get('preselect_project_name', 'Unknown')
                # Find the project that matches this transcript path
                for i, project in enumerate(projects):
                    if str(project['transcript_file']) == preselect_path:
                        default_idx = i
                        preselected = True
                        break
                # Clear the preselect after using it
                del st.session_state.preselect_transcript_path
                if 'preselect_project_name' in st.session_state:
                    del st.session_state.preselect_project_name

                # Show success message for navigation
                if preselected:
                    st.success(f"✅ **{preselect_name}** is ready for chat!")
                else:
                    st.warning("⚠️ Could not find the requested transcript.")

            selected_project_idx = st.selectbox(
                "Choose project:",
                range(len(project_options)),
                format_func=lambda x: project_options[x],
                key="chat_project_selector",
                label_visibility="collapsed",
                index=default_idx
            )

            if selected_project_idx is not None:
                selected_project = projects[selected_project_idx]
                transcript_file = selected_project['transcript_file']
                chat_key = f"chat_history_{selected_project['dir'].name}"

                # Quick Actions in sidebar
                if transcript_file.exists():
                    # Load transcription text for quick actions
                    with open(transcript_file, 'r', encoding='utf-8') as f:
                        transcription_text = f.read()

                        # Show transcript preview in sidebar
                        st.markdown("**📝 Transcript Preview:**")
                        preview = get_transcript_preview(transcription_text, 3)  # Shorter preview for sidebar
                        st.text_area(
                            "Content:",
                            value=preview,
                            height=150,
                            disabled=True,
                            key=f"sidebar_preview_{selected_project['dir'].name}",
                            label_visibility="collapsed"
                        )

                    if transcription_text:
                        st.markdown("**⚡ Quick Actions:**")

                        # Initialize chat history in session state
                        if chat_key not in st.session_state:
                            st.session_state[chat_key] = []

                        if st.button("📋 Meeting Notes", key="quick_summary", use_container_width=True, help="Generate comprehensive meeting notes"):
                            prompt = "Write meeting notes for the transcription."
                            st.session_state[chat_key].append({"role": "user", "content": prompt})
                            st.session_state[f"{chat_key}_pending_response"] = True
                            st.rerun()

                        if st.button("🎯 Impactful Quotes", key="quick_keypoints", use_container_width=True, help="Extract high-impact quotes"):
                            prompt = "Collect High impact quotes from the transcription."
                            st.session_state[chat_key].append({"role": "user", "content": prompt})
                            st.session_state[f"{chat_key}_pending_response"] = True
                            st.rerun()

                        if st.button("👥 Participants", key="quick_participants", use_container_width=True, help="Identify key participants"):
                            prompt = "Who were the key participants in this conversation? What were their main contributions and viewpoints?"
                            st.session_state[chat_key].append({"role": "user", "content": prompt})
                            st.session_state[f"{chat_key}_pending_response"] = True
                            st.rerun()

                        if st.button("🗑️ Clear Chat", key="quick_clear", use_container_width=True, help="Clear conversation history"):
                            st.session_state[chat_key] = []
                            if f"{chat_key}_pending_response" in st.session_state:
                                del st.session_state[f"{chat_key}_pending_response"]
                            st.rerun()

                # Show project info in sidebar
                st.markdown("**📊 Project Info:**")
                st.write(f"**Language:** {selected_project['language']}")
                st.write(f"**Created:** {selected_project['created']}")
                if selected_project['audio_files']:
                    st.write(f"**Audio:** {selected_project['audio_files'][0].name}")

        else:
            st.info("No transcription projects found.")
            st.markdown("💡 Create some transcriptions first!")

    # Main content area
    if projects and selected_project_idx is not None:
        selected_project = projects[selected_project_idx]
        transcript_file = selected_project['transcript_file']
        chat_key = f"chat_history_{selected_project['dir'].name}"
        max_chat_messages = 100

        if transcript_file.exists():
            # Load the transcript content
            with open(transcript_file, 'r', encoding='utf-8') as f:
                transcription_text = f.read()

            if transcription_text:
                # Initialize chat history in session state
                if chat_key not in st.session_state:
                    st.session_state[chat_key] = []

                # Create a container for the chat history with responsive height
                chat_container = st.container()

                with chat_container:
                    # Display chat history using st.chat_message
                    for idx, message in enumerate(st.session_state[chat_key]):
                        with st.chat_message(message["role"]):
                            st.markdown(message["content"])

                            # Add copy functionality for assistant messages (single implementation)
                            if message["role"] == "assistant":
                                copy_key = f"copy_{chat_key}_{idx}"
                                if st.button("📋 Copy Response", key=copy_key, help="Copy response to clipboard", type="secondary"):
                                    import pyperclip
                                    try:
                                        pyperclip.copy(message["content"])
                                        st.toast("Copied to clipboard", icon="📋")
                                    except Exception as e:
                                        st.error(f"Failed to copy: {e}")

                    # Handle pending responses from quick actions - inside chat container
                    if st.session_state.get(f"{chat_key}_pending_response", False):
                        # Clear the pending flag
                        del st.session_state[f"{chat_key}_pending_response"]

                        # Get the last user message (the one from quick action)
                        if st.session_state[chat_key] and st.session_state[chat_key][-1]["role"] == "user":
                            # Prepare messages for LLM
                            messages = [
                                {"role": msg["role"], "content": msg["content"]}
                                for msg in st.session_state[chat_key]
                            ]

                            # Get response from LLM with streaming
                            with st.chat_message("assistant"):
                                response_placeholder = st.empty()
                                response_text = ""

                                try:
                                    # Use chat_with_context instead of chat_stream
                                    for chunk in llm_client.chat_with_context(messages, context=transcription_text):
                                        response_text += chunk
                                        response_placeholder.markdown(response_text)

                                    # Add assistant response to chat history
                                    st.session_state[chat_key].append({
                                        "role": "assistant",
                                        "content": response_text
                                    })
                                    # Cap chat history
                                    if len(st.session_state[chat_key]) > max_chat_messages:
                                        st.session_state[chat_key] = st.session_state[chat_key][-max_chat_messages:]

                                    # Rerun to show the response with copy button in the main chat loop
                                    st.rerun()

                                except Exception as e:
                                    st.error(f"Error getting response: {e}")

                    # Show helpful message if no chat history
                    if not st.session_state[chat_key]:
                        st.info("💡 Start a conversation by typing a question below or using the Quick Actions in the sidebar.")

                # Chat input at the bottom - always visible and prominent
                if user_input := st.chat_input("💬 Ask a question about the transcription..."):
                    # Add user message to chat history and display immediately
                    st.session_state[chat_key].append({
                        "role": "user",
                        "content": user_input
                    })
                    # Cap chat history
                    if len(st.session_state[chat_key]) > max_chat_messages:
                        st.session_state[chat_key] = st.session_state[chat_key][-max_chat_messages:]

                    # Prepare messages for LLM - use simple user message since context is handled by chat_with_context
                    messages = [{"role": "user", "content": user_input}]

                    # Get response from LLM with streaming - this will appear in the chat container on rerun
                    try:
                        response_text = ""
                        for chunk in llm_client.chat_with_context(messages, context=transcription_text):
                            response_text += chunk

                        # Add assistant response to chat history
                        st.session_state[chat_key].append({
                            "role": "assistant",
                            "content": response_text
                        })
                        # Cap chat history
                        if len(st.session_state[chat_key]) > max_chat_messages:
                            st.session_state[chat_key] = st.session_state[chat_key][-max_chat_messages:]

                        # Rerun to show the new messages in the chat container
                        st.rerun()

                    except Exception as e:
                        st.error(f"Error getting response: {e}")

            else:
                st.warning("No transcription text found in this project.")
        else:
            st.warning("Transcript file not found for this project.")
    else:
        st.info("No transcription projects found.")
        st.markdown("💡 **Tip:** Create some transcriptions first, then come back to chat with them!")
