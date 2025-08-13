"""Main Streamlit application - navigation and configuration only."""

import streamlit as st
import logging

from ..config.settings import Settings, ConfigurationError
from echo_notes.ui.pages.record import page_record
from echo_notes.ui.pages.transcribe import page_transcribe
from echo_notes.ui.pages.browse import page_browse_transcriptions
from echo_notes.ui.pages.chat import page_chat_with_transcription

# Configure logging for debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main Streamlit application."""
    # Disable Streamlit usage telemetry
    try:
        st.set_option("browser.gatherUsageStats", False)
    except Exception:
        pass

    # Page configuration - must be first
    st.set_page_config(
        page_title="EchoNotes",
        page_icon="📝",
        layout="wide"
    )

    # Initialize settings - show error page if configuration fails
    try:
        settings = Settings()
    except ConfigurationError as e:
        st.error("⚠️ **Configuration Error**")
        st.error(str(e))
        st.markdown("---")
        st.markdown("### 🔧 **How to fix this:**")
        st.markdown("1. Copy `.env.example` to `.env` in your project root")
        st.markdown("2. Fill in your actual API credentials and endpoints")
        st.markdown("3. Restart the application")

        st.markdown("### 📋 **Required Environment Variables:**")
        st.code("""
# Unified API Key for both services
API_KEY=your_api_key_here

# Whisper transcription service endpoint
WHISPER_BASE_URL=https://your-whisper-endpoint.com/v1

# LLM service endpoint (OpenAI-compatible)
LLM_BASE_URL=https://your-llm-endpoint.com/v1

# LLM model identifier
LLM_MODEL_ID=your_model_id
        """, language="bash")

        st.markdown("### 📁 **Optional Directory Configuration:**")
        st.code("""
# Directory for storing audio recordings (default: ~/Documents/meetings)
# MEETINGS_DIR=/path/to/your/recordings

# Directory for storing transcription projects (default: ~/Documents/transcriptions)
# TRANSCRIPTIONS_DIR=/path/to/your/transcripts
        """, language="bash")

        st.stop()
        return

    # Create navigation structure
    pages = [
        st.Page(page_record, title="Record", icon="🎙️"),
        st.Page(page_transcribe, title="Transcribe", icon="🚀"),
        st.Page(page_browse_transcriptions, title="Browse Transcriptions", icon="📚"),
        st.Page(page_chat_with_transcription, title="Chat with Transcription", icon="💬"),
    ]

    # Expose page references in session state for programmatic navigation
    # This avoids ambiguity about titles/paths and works with st.switch_page
    st.session_state.page_refs = {
        "Record": pages[0],
        "Transcribe": pages[1],
        "Browse Transcriptions": pages[2],
        "Chat with Transcription": pages[3],
    }

    # Create navigation with top position
    nav = st.navigation(pages, position="top")
    nav.run()


if __name__ == "__main__":
    main()
