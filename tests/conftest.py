"""Keep direct pytest runs from scattering bytecode through the repository."""

from __future__ import annotations

import sys
from pathlib import Path

if sys.pycache_prefix is None:
    sys.pycache_prefix = str(
        Path(__file__).resolve().parents[1] / ".cache" / "pycache"
    )
