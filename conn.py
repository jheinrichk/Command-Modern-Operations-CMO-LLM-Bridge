"""
CONN launcher.

    python conn.py

Starts the CMO LLM Bridge control surface: mode selection, window layout,
live calibration, the process monitor, IKE finalization and the play modes.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conn.app import main

if __name__ == "__main__":
    main()
