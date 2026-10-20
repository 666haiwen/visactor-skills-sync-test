"""Load the independently packaged biography runtime for regression tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills/life-chronicle/scripts"))
