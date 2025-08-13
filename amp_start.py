import os
import sys
import subprocess
from pathlib import Path

ROOT = "/home/cdsw"
SRC = ROOT + "/src"
sys.path.insert(0, str(SRC))

port = int(os.environ.get("CDSW_APP_PORT", "8090"))
cmd = [
    sys.executable,
    "-m",
    "streamlit",
    "run",
    str(ROOT + "/echo_notes_app.py"),
    "--server.address",
    "127.0.0.1",
    "--server.port",
    str(port),
]

env = os.environ.copy()
env["STREAMLIT_BROWSER_GATHERUSAGESTATS"] = "false"
subprocess.check_call(cmd, env=env)
