"""Mesh properties, eigenvectors, and mode animations."""

from __future__ import annotations

import os
from typing import Dict, List, Mapping, Optional, Sequence, Union

import numpy as np


DEFAULT_FCC_QPOINTS = {
    "Gamma": [0.0, 0.0, 0.0],
    "X": [0.5, 0.0, 0.5],
    "L": [0.5, 0.5, 0.5],
}

DEFAULT_HCP_QPOINTS = {
    "Gamma": [0.0, 0.0, 0.0],
    "A": [0.0, 0.0, 0.5],
    "M": [0.5, 0.0, 0.0],
    "K": [1.0 / 3.0, 1.0 / 3.0, 0.0],
}


def _inject_lattice_into_xyz(filename: str, lattice_str: str) -> None:
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()
    if not lines:
        return
    num_atoms = int(lines[0].strip())
    step = num_atoms + 2
    for i in range(1, len(lines), step):
        lines[i] = f"{lines[i].strip()} {lattice_str}\n"
    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(lines)


def auto_qpoints_from_seekpath(unitcell) -> Dict[str, List[float]]:
    """Return a small set of named high-symmetry points via SeeK-path."""
    try:
        import seekpath
    except ImportError:
        return {"Gamma": [0.0, 0.0, 0.0]}

    cell = (
        unitcell.get_cell(),
        unitcell.get_scaled_positions(),
        unitcell.get_atomic_numbers(),
    )
    path = seekpath.get_path(cell)
    points = path["point_coords"]
    # Keep unique labels that appear on the suggested path
    labels = []
    for a, b in path["path"]:
        labels.extend([a, b])
    unique = []
    for lab in labels:
        if lab not in unique:
            unique.append(lab)
    return {lab: list(points[lab]) for lab in unique}


def extract_properties(
    supercell_matrix,
    mesh: Sequence[int] = (16, 16, 16),
    poscar: str = "POSCAR",
    force_constants_file: str = "FORCE_CONSTANTS",
    qpoints: Optional[Mapping[str, Sequence[float]]] = None,
    amplitude: float = 5.0,
    num_div: int = 20,
    write_animations: bool = True,
    crystal_family: Optional[str] = None,
) -> dict:
    """Run mesh calculation and optionally export OVITO-ready mode animations."""
    from phonopy import Phonopy
    from phonopy.file_IO import parse_FORCE_CONSTANTS
    from phonopy.interface.vasp import read_vasp

    force_constants = parse_FORCE_CONSTANTS(force_constants_file)
    unitcell = read_vasp(poscar)
    phonon = Phonopy(unitcell, supercell_matrix)
    phonon.force_constants = force_constants

    phonon.run_mesh(
        mesh,
        with_group_velocities=True,
        with_eigenvectors=True,
        is_mesh_symmetry=False,
    )
    phonon.write_yaml_mesh()

    mesh_dict = phonon.get_mesh_dict()
    np.savetxt("QPOINTS", mesh_dict["qpoints"], fmt="%.6f")
    np.savetxt("eigenvalues.txt", mesh_dict["frequencies"], fmt="%.6f")

    eigenvec = mesh_dict["eigenvectors"]
    flattened = np.real(eigenvec).reshape(eigenvec.shape[0], -1)
    np.savetxt("eigenvectors_real.txt", flattened, fmt="%.6f")

    # Complex eigenvectors as float view (legacy format from get_properties.py)
    stacked = eigenvec.reshape(eigenvec.shape[0], -1)
    split = stacked.view(float)
    np.savetxt("eigenvectors.txt", split, fmt="%.6f")
    print("Wrote QPOINTS, eigenvalues.txt, eigenvectors(_real).txt")

    if not write_animations:
        return mesh_dict

    if qpoints:
        target = {k: list(v) for k, v in qpoints.items()}
    elif crystal_family and crystal_family.lower() in {"fcc", "diamond"}:
        target = dict(DEFAULT_FCC_QPOINTS)
    elif crystal_family and crystal_family.lower() in {"hcp"}:
        target = dict(DEFAULT_HCP_QPOINTS)
    else:
        target = auto_qpoints_from_seekpath(unitcell)

    cell_matrix = phonon.unitcell.get_cell()
    lattice_str = 'Lattice="' + " ".join(f"{x:.6f}" for x in cell_matrix.flatten()) + '"'
    num_bands = mesh_dict["frequencies"].shape[1]

    for point_name, q_point in target.items():
        safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in point_name)
        folder = f"animations_{safe_name}"
        os.makedirs(folder, exist_ok=True)
        print(f"Generating animations for {point_name} -> {folder}/")
        for band in range(1, num_bands + 1):
            filename = os.path.join(folder, f"{safe_name}_band_{band:04d}.xyz")
            phonon.write_animation(
                q_point=list(q_point),
                anime_type="xyz",
                band_index=band,
                amplitude=amplitude,
                num_div=num_div,
                filename=filename,
            )
            _inject_lattice_into_xyz(filename, lattice_str)

    print("Mode animations written with embedded Lattice= for OVITO.")
    return mesh_dict


def extract_band_eigenvalues(band_yaml: str = "band.yaml", output: str = "band_eigenvalues.txt") -> None:
    """Parse phonopy band.yaml into a distance + frequencies table."""
    import yaml

    try:
        from yaml import CLoader as Loader
    except ImportError:
        from yaml import Loader

    with open(band_yaml, "r", encoding="utf-8") as f:
        data = yaml.load(f, Loader=Loader)

    distances = []
    all_frequencies = []
    for q_point in data["phonon"]:
        distances.append(q_point["distance"])
        all_frequencies.append([band["frequency"] for band in q_point["band"]])

    eigenvalues = np.asarray(all_frequencies)
    distances = np.asarray(distances)
    output_data = np.column_stack((distances, eigenvalues))
    np.savetxt(
        output,
        output_data,
        fmt="%15.8f",
        header="Distance  Band_1  Band_2  Band_3 ...",
    )
    print(f"Wrote {output}")
