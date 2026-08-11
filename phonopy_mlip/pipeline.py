"""End-to-end phonon workflow orchestration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Sequence, Union

from .backends import get_backend
from .config import WorkflowConfig
from .forces import compute_force_constants
from .properties import extract_properties
from .structures import (
    ensure_poscar,
    make_displaced_structures,
    make_sposcar,
)


class PhononWorkflow:
    """Configurable phonon workflow for DeePMD, MTP, or VASP force backends."""

    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.backend = get_backend(config)

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "PhononWorkflow":
        return cls(WorkflowConfig.from_file(path))

    def run(self, stages: Optional[Sequence[str]] = None) -> None:
        stages = list(stages or self.config.stages)
        work = Path(self.config.work_dir).resolve()
        work.mkdir(parents=True, exist_ok=True)
        prev = Path.cwd()
        os.chdir(work)
        try:
            dispatch = {
                "prepare_structure": self.prepare_structure,
                "make_supercell": self.make_supercell,
                "make_displacements": self.make_displacements,
                "prepare_calculations": self.prepare_calculations,
                "run_forces": self.run_forces,
                "force_constants": self.force_constants,
                "properties": self.properties,
            }
            for stage in stages:
                if stage not in dispatch:
                    raise ValueError(
                        f"Unknown stage {stage!r}. Choose from: {sorted(dispatch)}"
                    )
                print(f"\n=== Stage: {stage} ===")
                dispatch[stage]()
        finally:
            os.chdir(prev)

    def prepare_structure(self) -> None:
        ensure_poscar(
            self.config.structure_file,
            output_poscar="POSCAR",
            structure_format=self.config.structure_format,
            species_map=self.config.species_map or None,
        )

    def make_supercell(self) -> None:
        make_sposcar("POSCAR", self.config.supercell_matrix())

    def make_displacements(self) -> None:
        make_displaced_structures(
            "POSCAR",
            self.config.supercell_matrix(),
            distance=self.config.displacement,
        )

    def prepare_calculations(self) -> None:
        self.backend.prepare()

    def run_forces(self) -> None:
        if self.config.skip_force_calc:
            print("skip_force_calc=True: skipping force evaluations.")
            return
        self.backend.run()

    def force_constants(self) -> None:
        compute_force_constants(
            self.config.supercell_matrix(),
            force_pattern=self.backend.force_glob,
            is_nac=self.config.is_nac,
            backend=self.config.backend,
        )

    def properties(self) -> None:
        extract_properties(
            self.config.supercell_matrix(),
            mesh=self.config.mesh,
            qpoints=self.config.qpoints or None,
            amplitude=self.config.amplitude,
            num_div=self.config.anime_div,
        )
