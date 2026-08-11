# -*- coding: utf-8 -*-
"""
Generalized driver using phonopy_mlip.

    python -m phonopy_mlip -c configs/mo_mtp.yaml
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
        structure_file="Mo_primitive_cell.txt",
        structure_format="lammps-data",
        species_map={1: "C", 2: "Mo"},
        supercell=[4, 4, 4],
        displacement=0.01,
        mesh=[16, 16, 16],
        backend="mtp",
        mtp_potential="pot.mtp",
        mlip_ini="mlip.ini",
        lammps_cmd="lmp",
        lammps_input="inputfile.txt",
        data_filename="disp.lammps",
        work_dir=".",
        qpoints={
            "Gamma": [0.0, 0.0, 0.0],
            "H": [0.5, -0.5, 0.5],
            "N": [0.0, 0.0, 0.5],
            "P": [0.25, 0.25, 0.25],
        },
    )
    PhononWorkflow(config).run()


if __name__ == "__main__":
    main()
