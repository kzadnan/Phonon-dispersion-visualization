#!/usr/bin/env python
"""Thin example driver using the generalized phonopy_mlip package.

Usage (from repository root):
    python run_example.py configs/diamond_deepmd.yaml
    python run_example.py configs/diamond_vasp.yaml --skip-force-calc
    python -m phonopy_mlip -c configs/ti_deepmd.yaml --stages prepare_structure make_supercell
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phonopy_mlip.__main__ import main


if __name__ == "__main__":
    raise SystemExit(main())
