"""Force-calculation backends: DeePMD, MTP (LAMMPS), and VASP."""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import textwrap
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from ..config import WorkflowConfig
from ..structures import list_disp_indices


class ForceBackend(ABC):
    name: str = "base"

    def __init__(self, config: WorkflowConfig):
        self.config = config

    @abstractmethod
    def prepare(self) -> None:
        """Convert structures and stage per-displacement calculation folders."""

    @abstractmethod
    def run(self) -> None:
        """Execute force evaluations (or write job scripts if remote)."""

    @property
    def force_glob(self) -> str:
        return "disp-*/forces.lammpstrj"


def get_backend(config: WorkflowConfig) -> ForceBackend:
    backend = config.backend.lower().strip()
    if backend in {"deepmd", "dp"}:
        return DeepMDBackend(config)
    if backend in {"mtp", "mlip"}:
        return MTPBackend(config)
    if backend in {"vasp", "dft"}:
        return VASPBackend(config)
    raise ValueError(f"Unknown backend {config.backend!r}. Use deepmd, mtp, or vasp.")


class LAMMPSBackend(ForceBackend, ABC):
    """Shared LAMMPS organize + run logic for DeePMD / MTP."""

    def prepare(self) -> None:
        from ..structures import convert_all_poscars_to_lammps

        species_order = self.config.species_order_resolved()
        convert_all_poscars_to_lammps(species_order)
        self._write_lammps_input_if_missing()
        self._organize_folders()

    def _pair_style_block(self) -> str:
        raise NotImplementedError

    def _write_lammps_input_if_missing(self) -> None:
        path = Path(self.config.lammps_input)
        if path.exists():
            # Rewrite read_data to use a variable so folder-local names work.
            text = path.read_text(encoding="utf-8")
            if "variable fname" not in text and "-var" not in text:
                # Keep existing file; runner passes -var fname
                pass
            return

        content = textwrap.dedent(
            f"""\
            # Auto-generated LAMMPS input for phonon force evaluation
            units metal
            dimension 3
            boundary p p p
            atom_style atomic

            variable fname string {self.config.data_filename}
            read_data ${{fname}}

            {self._pair_style_block()}

            fix 1 all setforce NULL NULL NULL
            thermo_style custom step temp pe press
            dump 1 all custom 1 {self.config.force_dump} id type x y z fx fy fz
            run 0
            """
        )
        path.write_text(content, encoding="utf-8")
        print(f"Wrote {path}")

    def _organize_folders(self) -> None:
        indices = list_disp_indices("POSCAR-*")
        common = self.config.default_common_files()
        data_name = self.config.data_filename

        for idx in indices:
            folder = f"disp-{idx:03d}"
            os.makedirs(folder, exist_ok=True)
            src = f"disp-{idx:03d}.lammps"
            dst = os.path.join(folder, data_name)
            if os.path.exists(src):
                shutil.move(src, dst)
                print(f"Moved {src} -> {dst}")
            elif not os.path.exists(dst):
                print(f"Warning: {src} not found.")

            for item in common:
                if os.path.exists(item):
                    shutil.copy(item, folder)
                else:
                    print(f"Warning: common file '{item}' missing.")

        # Ensure each folder's input uses the local data filename
        for idx in indices:
            folder = f"disp-{idx:03d}"
            inp = Path(folder) / self.config.lammps_input
            if not inp.exists():
                continue
            text = inp.read_text(encoding="utf-8")
            # Normalize hardcoded read_data lines from legacy inputs
            lines = []
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("read_data"):
                    lines.append(f"read_data {data_name}")
                else:
                    lines.append(line)
            # Guarantee variable-friendly form if runner uses -var
            if "variable fname" not in "\n".join(lines):
                # keep simple read_data form
                pass
            inp.write_text("\n".join(lines) + "\n", encoding="utf-8")

        print("Organization complete.")

    def run(self) -> None:
        folders = sorted(glob.glob("disp-*"))
        if not folders:
            raise FileNotFoundError("No disp-* folders found. Run prepare first.")

        print(f"Found {len(folders)} folders. Starting LAMMPS ({self.name})...")
        data_name = self.config.data_filename
        for i, folder in enumerate(folders, start=1):
            data_path = os.path.join(folder, data_name)
            if not os.path.exists(data_path):
                # fallback to legacy naming
                legacy = os.path.join(folder, "disp-001.lammps")
                alt = os.path.join(folder, f"{folder}.lammps")
                if os.path.exists(legacy):
                    data_name_local = "disp-001.lammps"
                elif os.path.exists(alt):
                    data_name_local = f"{folder}.lammps"
                else:
                    print(f"Skipping {folder}: no LAMMPS data file.")
                    continue
            else:
                data_name_local = data_name

            cmd = [
                self.config.lammps_cmd,
                "-in",
                self.config.lammps_input,
                "-log",
                "log.lammps",
                "-var",
                "fname",
                data_name_local,
            ]
            print(f"Running in {folder} ({i}/{len(folders)})...")
            try:
                subprocess.run(cmd, cwd=folder, check=True, text=True)
            except FileNotFoundError:
                print(
                    f"LAMMPS executable {self.config.lammps_cmd!r} not found. "
                    "Folders are prepared; submit 'job' scripts manually or set lammps_cmd."
                )
                return
            except subprocess.CalledProcessError as exc:
                print(f"Error in {folder}: {exc}")
                if not self.config.continue_on_error:
                    raise
        print("All LAMMPS runs finished (or skipped).")


class DeepMDBackend(LAMMPSBackend):
    name = "deepmd"

    def _pair_style_block(self) -> str:
        return textwrap.dedent(
            f"""\
            pair_style deepmd {self.config.deepmd_model}
            pair_coeff * *
            """
        ).strip()


class MTPBackend(LAMMPSBackend):
    name = "mtp"

    def _pair_style_block(self) -> str:
        return textwrap.dedent(
            f"""\
            pair_style mlip {self.config.mlip_ini}
            pair_coeff * *
            """
        ).strip()

    def prepare(self) -> None:
        # Ensure mlip.ini points at the MTP potential if missing
        ini = Path(self.config.mlip_ini)
        if not ini.exists():
            ini.write_text(
                f"mtp-filename       {self.config.mtp_potential}\n",
                encoding="utf-8",
            )
            print(f"Wrote {ini}")
        super().prepare()


class VASPBackend(ForceBackend):
    name = "vasp"

    @property
    def force_glob(self) -> str:
        # Prefer vasprun.xml; fallback handled in forces.find_force_files
        return "disp-*/vasprun.xml"

    def prepare(self) -> None:
        self._write_incar()
        self._write_kpoints()
        self._write_potcar()
        self._organize_folders()
        if self.config.write_job_script:
            self._write_job_script()

    def _write_incar(self) -> None:
        path = Path("INCAR")
        if self.config.incar_template and Path(self.config.incar_template).exists():
            shutil.copy(self.config.incar_template, path)
            print(f"Copied INCAR template -> {path}")
            return
        if path.exists():
            return

        content = textwrap.dedent(
            f"""\
            SYSTEM = phonon force
            PREC   = Accurate
            ENCUT  = {self.config.encut}
            IBRION = -1
            NSW    = 0
            ISIF   = 2
            ISMEAR = 0
            SIGMA  = 0.05
            EDIFF  = {self.config.ediff}
            LREAL  = .FALSE.
            LWAVE  = .FALSE.
            LCHARG = .FALSE.
            ADDGRID= .TRUE.
            NCORE  = {self.config.ncore}
            """
        )
        if self.config.kspacing:
            content += f"KSPACING = {self.config.kspacing}\n"
            content += "KGAMMA   = .TRUE.\n"
        path.write_text(content, encoding="utf-8")
        print(f"Wrote {path}")

    def _write_kpoints(self) -> None:
        path = Path("KPOINTS")
        if self.config.kpoints_template and Path(self.config.kpoints_template).exists():
            shutil.copy(self.config.kpoints_template, path)
            print(f"Copied KPOINTS template -> {path}")
            return
        if path.exists() or self.config.kspacing:
            return
        nx, ny, nz = self.config.kmesh
        content = textwrap.dedent(
            f"""\
            Automatic mesh
            0
            Gamma
            {nx} {ny} {nz}
            0 0 0
            """
        )
        path.write_text(content, encoding="utf-8")
        print(f"Wrote {path}")

    def _write_potcar(self) -> None:
        path = Path("POTCAR")
        if path.exists():
            return
        if not self.config.potcar_dir:
            print(
                "POTCAR not generated: set potcar_dir and potcar_map in the config, "
                "or place a POTCAR in the work directory."
            )
            return

        order = self.config.species_order_resolved()
        chunks: List[str] = []
        for symbol in order:
            pot_name = self.config.potcar_map.get(symbol, symbol)
            candidates = [
                Path(self.config.potcar_dir) / pot_name / "POTCAR",
                Path(self.config.potcar_dir) / f"POTCAR_{pot_name}",
                Path(self.config.potcar_dir) / pot_name,
            ]
            found = next((c for c in candidates if c.is_file()), None)
            if found is None:
                raise FileNotFoundError(
                    f"Could not find POTCAR for {symbol} (tried {pot_name}) under {self.config.potcar_dir}"
                )
            chunks.append(found.read_text(encoding="utf-8"))
        path.write_text("".join(chunks), encoding="utf-8")
        print(f"Wrote concatenated POTCAR for {order}")

    def _organize_folders(self) -> None:
        indices = list_disp_indices("POSCAR-*")
        common = [f for f in ("INCAR", "KPOINTS", "POTCAR") if Path(f).exists()]
        for idx in indices:
            folder = f"disp-{idx:03d}"
            os.makedirs(folder, exist_ok=True)
            src = f"POSCAR-{idx:03d}"
            dst = os.path.join(folder, "POSCAR")
            if os.path.exists(src):
                shutil.copy(src, dst)
                print(f"Copied {src} -> {dst}")
            for item in common:
                shutil.copy(item, folder)
            if self.config.write_job_script:
                job = Path(self.config.job_script_name)
                if job.exists():
                    shutil.copy(job, folder)
        print(f"Staged {len(indices)} VASP displacement folders.")

    def _write_job_script(self) -> None:
        path = Path(self.config.job_script_name)
        if path.exists():
            return
        modules = "\n".join(f"module load {m}" for m in self.config.vasp_modules)
        account = f"#SBATCH --account={self.config.slurm_account}" if self.config.slurm_account else ""
        partition = (
            f"#SBATCH --partition={self.config.slurm_partition}"
            if self.config.slurm_partition
            else ""
        )
        content = textwrap.dedent(
            f"""\
            #!/bin/bash
            #SBATCH --time={self.config.slurm_time}
            #SBATCH --nodes=1
            #SBATCH --ntasks={self.config.slurm_ntasks}
            #SBATCH -o slurm-%j.out
            {account}
            {partition}

            cd "$SLURM_SUBMIT_DIR"
            {modules}

            # DFT force evaluation for one displaced supercell
            srun -n $SLURM_NTASKS {self.config.vasp_cmd}
            """
        )
        path.write_text(content, encoding="utf-8")
        path.chmod(path.stat().st_mode | 0o111)
        print(f"Wrote {path}")

        # Batch submit helper at top level
        submit = Path("submit_all_vasp.sh")
        if not submit.exists():
            submit.write_text(
                textwrap.dedent(
                    f"""\
                    #!/bin/bash
                    # Submit one VASP job per displacement folder
                    for d in disp-*; do
                      if [[ -d "$d" ]]; then
                        (cd "$d" && sbatch {self.config.job_script_name})
                      fi
                    done
                    """
                ),
                encoding="utf-8",
            )
            submit.chmod(submit.stat().st_mode | 0o111)
            print(f"Wrote {submit}")

    def run(self) -> None:
        folders = sorted(glob.glob("disp-*"))
        if not folders:
            raise FileNotFoundError("No disp-* folders found.")

        if self.config.skip_force_calc:
            print("skip_force_calc=True: not launching VASP.")
            return

        print(f"Found {len(folders)} folders. Starting VASP...")
        for i, folder in enumerate(folders, start=1):
            if not (Path(folder) / "POSCAR").exists():
                print(f"Skipping {folder}: POSCAR missing.")
                continue
            cmd = self.config.vasp_cmd.split()
            print(f"Running in {folder} ({i}/{len(folders)})...")
            try:
                subprocess.run(cmd, cwd=folder, check=True, text=True)
            except FileNotFoundError:
                print(
                    f"VASP executable {self.config.vasp_cmd!r} not found. "
                    f"Use ./submit_all_vasp.sh or set vasp_cmd. Folders are prepared."
                )
                return
            except subprocess.CalledProcessError as exc:
                print(f"Error in {folder}: {exc}")
                if not self.config.continue_on_error:
                    raise
        print("All VASP runs finished (or skipped).")
