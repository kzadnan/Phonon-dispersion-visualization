"""Configuration schema for phonon workflows."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union
import json

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


BackendName = str  # "deepmd" | "mtp" | "vasp"


def _as_int_list(value: Sequence[int], name: str, n: int = 3) -> List[int]:
    values = [int(v) for v in value]
    if len(values) != n:
        raise ValueError(f"{name} must have length {n}, got {values}")
    return values


def _as_species_map(raw: Mapping[Any, Any]) -> Dict[int, str]:
    return {int(k): str(v) for k, v in raw.items()}


@dataclass
class WorkflowConfig:
    """End-to-end settings for a phonon calculation."""

    # Structure / chemistry
    structure_file: str = "POSCAR"
    structure_format: str = "auto"  # auto | vasp | lammps-data
    species_map: Dict[int, str] = field(default_factory=dict)
    species_order: Optional[List[str]] = None

    # Phonopy
    supercell: List[int] = field(default_factory=lambda: [2, 2, 2])
    displacement: float = 0.01
    mesh: List[int] = field(default_factory=lambda: [16, 16, 16])
    is_nac: bool = False
    amplitude: float = 5.0
    anime_div: int = 20

    # High-symmetry animation points. Empty -> seekpath auto (or Gamma only).
    qpoints: Dict[str, List[float]] = field(default_factory=dict)

    # Force backend
    backend: BackendName = "deepmd"
    work_dir: str = "."
    skip_force_calc: bool = False
    continue_on_error: bool = True

    # LAMMPS shared
    lammps_cmd: str = "lmp"
    lammps_input: str = "inputfile.txt"
    data_filename: str = "disp.lammps"  # name inside each disp-* folder
    force_dump: str = "forces.lammpstrj"
    common_files: List[str] = field(default_factory=list)

    # DeePMD
    deepmd_model: str = "graph-compress.pb"

    # MTP
    mtp_potential: str = "pot.mtp"
    mlip_ini: str = "mlip.ini"

    # VASP
    vasp_cmd: str = "vasp_std"
    incar_template: Optional[str] = None
    kpoints_template: Optional[str] = None
    potcar_map: Dict[str, str] = field(default_factory=dict)
    potcar_dir: Optional[str] = None
    encut: float = 520.0
    kspacing: Optional[float] = None
    kmesh: List[int] = field(default_factory=lambda: [1, 1, 1])
    ediff: float = 1.0e-8
    ncore: int = 4
    write_job_script: bool = True
    job_script_name: str = "job_vasp.sh"
    vasp_modules: List[str] = field(default_factory=list)
    slurm_account: str = ""
    slurm_partition: str = ""
    slurm_ntasks: int = 16
    slurm_time: str = "24:00:00"

    # Pipeline stages
    stages: List[str] = field(
        default_factory=lambda: [
            "prepare_structure",
            "make_supercell",
            "make_displacements",
            "prepare_calculations",
            "run_forces",
            "force_constants",
            "properties",
        ]
    )

    def species_order_resolved(self) -> List[str]:
        if self.species_order:
            return list(self.species_order)
        if self.species_map:
            return [self.species_map[i] for i in sorted(self.species_map)]
        raise ValueError(
            "species_order or species_map is required to define chemical element order."
        )

    def supercell_matrix(self):
        import numpy as np

        sc = _as_int_list(self.supercell, "supercell")
        return np.diag(sc)

    def default_common_files(self) -> List[str]:
        if self.common_files:
            return list(self.common_files)
        if self.backend == "deepmd":
            return [self.deepmd_model, self.lammps_input, "job"]
        if self.backend == "mtp":
            return [self.mtp_potential, self.mlip_ini, self.lammps_input, "job"]
        if self.backend == "vasp":
            return ["INCAR", "KPOINTS", "POTCAR", "job"]
        return [self.lammps_input, "job"]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save(self, path: Union[str, Path]) -> None:
        path = Path(path)
        data = self.to_dict()
        if path.suffix.lower() in {".yaml", ".yml"}:
            if yaml is None:
                raise ImportError("PyYAML is required to write YAML configs.")
            path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        else:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "WorkflowConfig":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        kwargs = {k: v for k, v in data.items() if k in known}
        if "species_map" in kwargs:
            kwargs["species_map"] = _as_species_map(kwargs["species_map"])
        if "supercell" in kwargs:
            kwargs["supercell"] = _as_int_list(kwargs["supercell"], "supercell")
        if "mesh" in kwargs:
            kwargs["mesh"] = _as_int_list(kwargs["mesh"], "mesh")
        return cls(**kwargs)

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "WorkflowConfig":
        path = Path(path)
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() in {".yaml", ".yml"}:
            if yaml is None:
                raise ImportError("PyYAML is required to read YAML configs.")
            data = yaml.safe_load(text)
        else:
            data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError(f"Config in {path} must be a mapping.")
        return cls.from_dict(data)
