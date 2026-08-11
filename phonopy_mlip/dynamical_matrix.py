"""Evaluate dynamical matrix / frequencies at arbitrary q-points."""

from __future__ import annotations

from typing import Sequence

import numpy as np


def run_qpoints(
    supercell_matrix,
    q_points: Sequence[Sequence[float]],
    poscar: str = "POSCAR",
    force_constants_file: str = "FORCE_CONSTANTS",
):
    from phonopy import Phonopy
    from phonopy.file_IO import parse_FORCE_CONSTANTS
    from phonopy.interface.vasp import read_vasp

    force_constants = parse_FORCE_CONSTANTS(force_constants_file)
    unitcell = read_vasp(poscar)
    phonon = Phonopy(unitcell, supercell_matrix)
    phonon.force_constants = force_constants
    phonon.run_qpoints(q_points=list(q_points), with_eigenvectors=True)
    return phonon.get_qpoints_dict()


def print_qpoints_report(q_points, qpoints_dict) -> None:
    for idx, q_point in enumerate(q_points):
        frequencies = qpoints_dict["frequencies"][idx]
        eigenvectors = qpoints_dict["eigenvectors"][idx]
        print(f"Q-point {q_point}:")
        print("Frequencies (THz):", frequencies)
        print("Eigenvectors:")
        print(eigenvectors)
        print("-" * 30)


if __name__ == "__main__":
    sc = np.eye(3, dtype=int) * 2
    qs = [
        [0.0, 0.0, 0.0],
        [0.5, 0.5, 0.0],
        [0.5, 0.0, 0.0],
        [0.0, 0.5, 0.5],
    ]
    data = run_qpoints(sc, qs)
    print_qpoints_report(qs, data)
