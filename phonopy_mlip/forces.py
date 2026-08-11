"""Parse LAMMPS dumps / VASP outputs into FORCE_CONSTANTS (+ optional bands)."""

from __future__ import annotations

import glob
from pathlib import Path
from typing import List, Optional, Sequence, Union

import numpy as np


def parse_lammps_forces(filename: Union[str, Path], num_atoms: Optional[int] = None) -> np.ndarray:
    """Parse a LAMMPS custom dump with id ... fx fy fz, sorted by atom id."""
    forces: List[List[float]] = []
    ids: List[int] = []
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()

    start_idx = 0
    for i, line in enumerate(lines):
        if "ITEM: ATOMS" in line:
            start_idx = i + 1
            break

    for line in lines[start_idx:]:
        data = line.strip().split()
        if len(data) < 4:
            continue
        ids.append(int(data[0]))
        forces.append([float(data[-3]), float(data[-2]), float(data[-1])])

    forces_arr = np.asarray(forces, dtype=float)
    ids_arr = np.asarray(ids, dtype=int)
    if forces_arr.size == 0:
        raise ValueError(f"No forces parsed from {filename}")
    sorted_forces = forces_arr[np.argsort(ids_arr)]

    if num_atoms is not None and sorted_forces.shape != (num_atoms, 3):
        raise ValueError(
            f"{filename}: expected ({num_atoms}, 3) forces, got {sorted_forces.shape}"
        )
    return sorted_forces


def find_force_files(
    pattern: str = "disp-*/forces.lammpstrj",
    fallbacks: Optional[Sequence[str]] = None,
) -> List[str]:
    files = sorted(glob.glob(pattern))
    if files:
        return files
    for alt in fallbacks or (
        "disp-*/forces.dump",
        "forces.disp-*",
        "disp-*/vasprun.xml",
        "disp-*/OUTCAR",
    ):
        files = sorted(glob.glob(alt))
        if files:
            return files
    return []


def write_band_txt(phonon, filename: str = "band.txt") -> None:
    bands = phonon.get_band_structure_dict()
    distances = bands["distances"]
    frequencies = bands["frequencies"]
    nbands = frequencies[0].shape[1]

    with open(filename, "w", encoding="utf-8") as f:
        for band_index in range(nbands):
            for segment_dist, segment_freq in zip(distances, frequencies):
                for x, freq_vals in zip(segment_dist, segment_freq):
                    f.write(f"{x:.8f} {freq_vals[band_index]:.8f}\n")
                f.write("\n")
            f.write("\n\n")
    print(f"Wrote {filename}")


def _parse_vasp_forces(path: Path, num_atoms: int) -> np.ndarray:
    """Parse forces from vasprun.xml or OUTCAR."""
    if path.name.lower() == "vasprun.xml":
        from ase.io import read

        atoms = read(str(path))
        forces = np.asarray(atoms.get_forces(), dtype=float)
    else:
        from phonopy.interface.vasp import parse_set_of_forces

        forces = np.asarray(parse_set_of_forces(num_atoms, [str(path)])[0], dtype=float)

    if forces.shape != (num_atoms, 3):
        raise ValueError(f"{path}: force shape {forces.shape}, expected {(num_atoms, 3)}")
    return forces


def compute_force_constants(
    supercell_matrix,
    force_pattern: str = "disp-*/forces.lammpstrj",
    disp_yaml: str = "phonopy_disp.yaml",
    is_nac: bool = False,
    write_fc: str = "FORCE_CONSTANTS",
    plot_bands: bool = True,
    band_plot: str = "band_structure.png",
    backend: str = "lammps",
) -> object:
    """Produce FORCE_CONSTANTS and optionally plot the band structure once."""
    from phonopy import load
    from phonopy.file_IO import write_FORCE_CONSTANTS

    print(f"Loading {disp_yaml}...")
    phonon = load(disp_yaml, supercell_matrix=supercell_matrix, is_nac=is_nac)
    num_atoms = phonon.supercell.get_number_of_atoms()

    force_files = find_force_files(force_pattern)
    if not force_files:
        raise FileNotFoundError(
            f"No force files matched {force_pattern!r}. Run force calculations first."
        )
    print(f"Found {len(force_files)} force files.")

    n_disp = len(phonon.displacements)
    if len(force_files) < n_disp:
        raise RuntimeError(
            f"Found {len(force_files)} force files but phonopy expects {n_disp} displacements."
        )

    force_sets = []
    for filename in force_files[:n_disp]:
        print(f"Parsing {filename}...")
        path = Path(filename)
        if path.name.lower() in {"vasprun.xml", "outcar"}:
            forces = _parse_vasp_forces(path, num_atoms)
        else:
            forces = parse_lammps_forces(path, num_atoms=num_atoms)
        force_sets.append(forces)

    print("Computing force constants...")
    phonon.produce_force_constants(forces=force_sets)
    write_FORCE_CONSTANTS(phonon.force_constants, filename=write_fc)
    print(f"Wrote {write_fc}")

    # Also write FORCE_SETS when phonopy dataset supports it
    try:
        from phonopy.file_IO import write_FORCE_SETS

        if getattr(phonon, "dataset", None) is not None:
            write_FORCE_SETS(phonon.dataset, filename="FORCE_SETS")
            print("Wrote FORCE_SETS")
    except Exception as exc:
        print(f"Note: FORCE_SETS not written ({exc})")

    if plot_bands:
        print("Calculating band structure...")
        phonon.auto_band_structure(plot=True, write_yaml=True, with_eigenvectors=True)
        plt = phonon.plot_band_structure()
        plt.savefig(band_plot)
        print(f"Wrote {band_plot}")
        write_band_txt(phonon, "band.txt")

    return phonon
