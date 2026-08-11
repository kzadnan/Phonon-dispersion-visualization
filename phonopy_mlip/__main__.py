"""CLI: python -m phonopy_mlip --config configs/diamond_deepmd.yaml"""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import WorkflowConfig
from .pipeline import PhononWorkflow


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="phonopy_mlip",
        description="Generalized phonon workflow for DeePMD, MTP, and VASP.",
    )
    p.add_argument(
        "-c",
        "--config",
        default=None,
        help="YAML/JSON workflow config path",
    )
    p.add_argument(
        "--work-dir",
        default=None,
        help="Override work_dir from config",
    )
    p.add_argument(
        "--stages",
        nargs="+",
        default=None,
        help="Subset of stages to run",
    )
    p.add_argument(
        "--backend",
        choices=["deepmd", "mtp", "vasp"],
        default=None,
        help="Override force backend",
    )
    p.add_argument(
        "--skip-force-calc",
        action="store_true",
        help="Prepare inputs but do not launch LAMMPS/VASP",
    )
    p.add_argument(
        "--write-example-config",
        metavar="PATH",
        default=None,
        help="Write a starter config to PATH and exit",
    )
    return p


def example_config(backend: str = "deepmd") -> WorkflowConfig:
    if backend == "vasp":
        return WorkflowConfig(
            structure_file="POSCAR",
            structure_format="vasp",
            species_order=["C"],
            supercell=[2, 2, 2],
            displacement=0.01,
            mesh=[16, 16, 16],
            backend="vasp",
            encut=520.0,
            kmesh=[1, 1, 1],
            skip_force_calc=True,
            potcar_dir="/path/to/POTCARs",
            potcar_map={"C": "C"},
        )
    if backend == "mtp":
        return WorkflowConfig(
            structure_file="final_relaxed_structure.data",
            structure_format="lammps-data",
            species_map={1: "C"},
            supercell=[3, 3, 3],
            displacement=0.01,
            mesh=[16, 16, 16],
            backend="mtp",
            mtp_potential="pot.mtp",
            mlip_ini="mlip.ini",
        )
    return WorkflowConfig(
        structure_file="final_relaxed_structure.data",
        structure_format="lammps-data",
        species_map={1: "C"},
        supercell=[3, 3, 3],
        displacement=0.01,
        mesh=[16, 16, 16],
        backend="deepmd",
        deepmd_model="graph-compress.pb",
    )


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.write_example_config:
        cfg = example_config(args.backend or "deepmd")
        cfg.save(args.write_example_config)
        print(f"Wrote example config -> {args.write_example_config}")
        return 0

    if not args.config:
        parser.error("--config is required unless --write-example-config is used")

    config = WorkflowConfig.from_file(args.config)
    if args.work_dir:
        config.work_dir = args.work_dir
    if args.backend:
        config.backend = args.backend
    if args.skip_force_calc:
        config.skip_force_calc = True

    workflow = PhononWorkflow(config)
    workflow.run(stages=args.stages)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
