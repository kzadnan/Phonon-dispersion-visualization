# -*- coding: utf-8 -*-
"""Backward-compatible LAMMPS runner (fixed per-folder data filenames)."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phonopy_mlip.backends import DeepMDBackend
from phonopy_mlip.config import WorkflowConfig


def running_lammps(lammps_cmd="lmp", input_script="inputfile.txt"):
    cfg = WorkflowConfig(
        backend="deepmd",
        lammps_cmd=lammps_cmd,
        lammps_input=input_script,
        data_filename="disp.lammps",
    )
    DeepMDBackend(cfg).run()


if __name__ == "__main__":
    running_lammps()
