# -*- coding: utf-8 -*-
"""Backward-compatible shim -> phonopy_mlip.structures.lammps_to_poscar"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phonopy_mlip.structures import lammps_to_poscar as Lammps_poscar  # noqa: F401
