# -*- coding: utf-8 -*-
"""
Generalized driver for the Ti / DeePMD example.

    python -m phonopy_mlip -c configs/ti_deepmd.yaml
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phonopy_mlip import PhononWorkflow, WorkflowConfig


def main() -> None:
    config = WorkflowConfig(
        structure_file="Ti_unitcell.txt",
        structure_format="lammps-data",
        species_map={1: "Ti"},
        supercell=[3, 3, 3],
        displacement=0.01,
        mesh=[16, 16, 16],
        backend="deepmd",
        deepmd_model="graph-compress.pb",
        lammps_cmd="lmp",
        lammps_input="inputfile.txt",
        data_filename="disp.lammps",
        work_dir=".",
        qpoints={
            "Gamma": [0.0, 0.0, 0.0],
            "A": [0.0, 0.0, 0.5],
            "M": [0.5, 0.0, 0.0],
            "K": [1.0 / 3.0, 1.0 / 3.0, 0.0],
        },
    )
    PhononWorkflow(config).run()


if __name__ == "__main__":
    main()
