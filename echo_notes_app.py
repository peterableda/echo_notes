#!/usr/bin/env python3
"""
EchoNotes Streamlit app entry point.
"""

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from echo_notes.ui.streamlit_app import main

if __name__ == "__main__":
    main()
