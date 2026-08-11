# -*- coding: utf-8 -*-
"""Backward-compatible shim -> phonopy_mlip.forces.compute_force_constants"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phonopy_mlip.forces import compute_force_constants as FORCE_CONSTS  # noqa: F401


if __name__ == "__main__":
    import numpy as np

    FORCE_CONSTS(2 * np.diag([1, 1, 1]))
