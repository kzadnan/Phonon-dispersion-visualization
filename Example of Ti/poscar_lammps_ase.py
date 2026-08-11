# -*- coding: utf-8 -*-
"""Backward-compatible shim -> phonopy_mlip.structures.convert_all_poscars_to_lammps"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phonopy_mlip.structures import convert_all_poscars_to_lammps


def POSCAR_LAMMPS_ASE(deepmd_order):
    return convert_all_poscars_to_lammps(deepmd_order)
