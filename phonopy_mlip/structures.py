"""Structure I/O and phonopy displacement helpers."""

from __future__ import annotations

import glob
import os
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union

import numpy as np


def resolve_structure_format(path: Union[str, Path], fmt: str = "auto") -> str:
    if fmt != "auto":
        return fmt
    path = Path(path)
    name = path.name.lower()
    suffix = path.suffix.lower()
    if name in {"poscar", "sposcar"} or name.startswith("poscar") or suffix in {".vasp", ".poscar"}:
        return "vasp"
    if suffix in {".data", ".lmp", ".lammps"} or "lammps" in name or name.endswith(".txt"):
        # many examples store LAMMPS data as *.txt
        return "lammps-data"
    return "vasp"


def lammps_to_poscar(
    input_lammps: Union[str, Path],
    output_poscar: Union[str, Path] = "POSCAR",
    species_map: Optional[Dict[int, str]] = None,
) -> str:
    """Convert a LAMMPS data file to VASP POSCAR with explicit type mapping."""
    from ase.io import read, write

    if not species_map:
        raise ValueError("species_map is required when converting LAMMPS -> POSCAR.")

    atoms = read(str(input_lammps), format="lammps-data", atom_style="atomic")
    types = atoms.get_array("type")
    missing = sorted({int(t) for t in types if int(t) not in species_map})
    if missing:
        raise KeyError(f"species_map missing LAMMPS types: {missing}")
    atoms.set_chemical_symbols([species_map[int(t)] for t in types])
    write(str(output_poscar), atoms, format="vasp", direct=True, vasp5=True)
    print(f"Converted {input_lammps} -> {output_poscar}")
    return str(output_poscar)


def ensure_poscar(
    structure_file: Union[str, Path],
    output_poscar: Union[str, Path] = "POSCAR",
    structure_format: str = "auto",
    species_map: Optional[Dict[int, str]] = None,
) -> str:
    """Ensure a POSCAR exists in the working directory."""
    structure_file = Path(structure_file)
    fmt = resolve_structure_format(structure_file, structure_format)

    if fmt == "vasp":
        if Path(output_poscar).resolve() != structure_file.resolve():
            from shutil import copyfile

            copyfile(structure_file, output_poscar)
            print(f"Copied {structure_file} -> {output_poscar}")
        return str(output_poscar)

    if fmt == "lammps-data":
        return lammps_to_poscar(structure_file, output_poscar, species_map)

    raise ValueError(f"Unsupported structure_format: {fmt}")


def make_sposcar(
    filename: Union[str, Path] = "POSCAR",
    supercell_matrix=None,
    output: Union[str, Path] = "SPOSCAR",
):
    from phonopy import Phonopy
    from phonopy.interface.vasp import read_vasp, write_vasp

    if supercell_matrix is None:
        supercell_matrix = np.eye(3, dtype=int) * 2

    unitcell = read_vasp(str(filename))
    phonon = Phonopy(unitcell, supercell_matrix=supercell_matrix)
    write_vasp(str(output), phonon.supercell, direct=True)
    print(f"Wrote {output}")
    return phonon.supercell


def make_displaced_structures(
    filename: Union[str, Path] = "POSCAR",
    supercell_matrix=None,
    distance: float = 0.01,
    prefix: str = "POSCAR",
) -> int:
    """Generate irreducible displacements and phonopy_disp.yaml.

    Unlike the old scripts, this uses *filename* instead of hard-coding POSCAR.
    """
    from phonopy import Phonopy
    from phonopy.interface.vasp import read_vasp, write_vasp

    if supercell_matrix is None:
        supercell_matrix = np.eye(3, dtype=int) * 2

    unitcell = read_vasp(str(filename))
    phonon = Phonopy(unitcell, supercell_matrix=supercell_matrix)
    phonon.generate_displacements(distance=distance)

    for i, cell in enumerate(phonon.supercells_with_displacements):
        out = f"{prefix}-{i + 1:03d}"
        write_vasp(out, cell, direct=True)
        print(f"Wrote {out}")

    phonon.save("phonopy_disp.yaml")
    print("Wrote phonopy_disp.yaml")
    return len(phonon.supercells_with_displacements)


def _insert_masses(path: Union[str, Path], species_order: Sequence[str]) -> None:
    from ase.data import atomic_masses, atomic_numbers

    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if any("Masses" in line for line in lines):
        return

    mass_lines = ["\nMasses\n\n"]
    for i, symbol in enumerate(species_order):
        mass = atomic_masses[atomic_numbers[symbol]]
        mass_lines.append(f"{i + 1} {mass:.4f} # {symbol}\n")
    mass_lines.append("\n")
    mass_block = "".join(mass_lines)

    insert_idx = 0
    for idx, line in enumerate(lines):
        if "xy xz yz" in line:
            insert_idx = idx + 1
            break
    if insert_idx == 0:
        for idx, line in enumerate(lines):
            if "zlo zhi" in line:
                insert_idx = idx + 1
                break

    lines.insert(insert_idx, mass_block)
    path.write_text("".join(lines), encoding="utf-8")


def poscar_to_lammps(
    input_name: Union[str, Path],
    output_name: Union[str, Path],
    species_order: Sequence[str],
) -> None:
    from ase.io import read, write

    atoms = read(str(input_name))
    write(
        str(output_name),
        atoms,
        format="lammps-data",
        specorder=list(species_order),
        atom_style="atomic",
    )
    _insert_masses(output_name, species_order)
    print(f"Converted {input_name} -> {output_name}")


def convert_all_poscars_to_lammps(
    species_order: Sequence[str],
    pattern: str = "POSCAR-*",
    out_prefix: str = "disp",
) -> List[str]:
    files = sorted(glob.glob(pattern))
    # Prefer numeric POSCAR-001 style ordering
    numbered = []
    for path in files:
        base = os.path.basename(path)
        try:
            idx = int(base.split("-")[-1])
        except ValueError:
            continue
        numbered.append((idx, path))
    numbered.sort()

    outputs = []
    for idx, path in numbered:
        out = f"{out_prefix}-{idx:03d}.lammps"
        poscar_to_lammps(path, out, species_order)
        outputs.append(out)
    print(f"Converted {len(outputs)} POSCAR files to LAMMPS.")
    return outputs


def list_disp_indices(pattern: str = "POSCAR-*") -> List[int]:
    indices = []
    for path in glob.glob(pattern):
        try:
            indices.append(int(os.path.basename(path).split("-")[-1]))
        except ValueError:
            continue
    return sorted(indices)
