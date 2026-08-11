# -*- coding: utf-8 -*-
"""
Generalized driver using phonopy_mlip.

    python -m phonopy_mlip -c configs/diamond_al_interface_mtp.yaml
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phonopy_mlip import PhononWorkflow, WorkflowConfig


def main() -> None:
    config = WorkflowConfig(
        structure_file="C_unitcell_new.txt",
        structure_format="lammps-data",
        species_map={1: "C", 2: "Al"},
        supercell=[3, 3, 3],
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
            "X": [0.5, 0.0, 0.5],
            "L": [0.5, 0.5, 0.5],
        },
    )
    PhononWorkflow(config).run()


if __name__ == "__main__":
    main()
