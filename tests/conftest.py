"""Shared test fixtures — headless pygame + project root on path."""
import os
import sys
from pathlib import Path

# Ensure project root is importable.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Headless SDL so pygame tests run without a display.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
