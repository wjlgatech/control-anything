"""Test configuration.

Two guarantees the whole suite rests on:

1. ``src/`` is importable without installing the package, so a fresh clone can run
   ``pytest`` immediately.
2. Provider API keys are stripped. Nothing under ``make check`` may ever go live — that is
   what makes the gate offline, deterministic, and safe to run in CI.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

for key in list(os.environ):
    if key.endswith(("_API_KEY", "_TOKEN")) or key.startswith(("OPENAI", "ANTHROPIC", "GEMINI")):
        os.environ.pop(key, None)
