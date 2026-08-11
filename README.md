# Phonon Dispersion Visualization from MLIP-MD (and DFT/VASP)

This repository computes phonon dispersions, eigenvectors, and OVITO-ready mode
animations with **Phonopy**. Force evaluations can use:

- **DeePMD** (LAMMPS `pair_style deepmd`)
- **MTP / MLIP** (LAMMPS `pair_style mlip`)
- **DFT / VASP** (`vasprun.xml` / `OUTCAR` collection)

The duplicated per-example scripts are generalized into the `phonopy_mlip` package.
Example folders still contain results and potentials; diamond and Ti drivers now
call the shared pipeline.

## Quick start

```bash
pip install -e .
# or: pip install numpy ase phonopy PyYAML matplotlib

# DeePMD example (run from repo root)
python -m phonopy_mlip -c configs/diamond_deepmd.yaml

# MTP example
python -m phonopy_mlip -c configs/diamond_au_interface_mtp.yaml

# Prepare VASP displacement folders + INCAR/KPOINTS/job scripts (no VASP launch)
python -m phonopy_mlip -c configs/diamond_vasp.yaml --skip-force-calc
```

Write a starter config:

```bash
python -m phonopy_mlip --write-example-config my.yaml --backend vasp
```

### Pipeline stages

`prepare_structure` → `make_supercell` → `make_displacements` →
`prepare_calculations` → `run_forces` → `force_constants` → `properties`

Run a subset with `--stages`, e.g.:

```bash
python -m phonopy_mlip -c configs/diamond_deepmd.yaml --stages force_constants properties
```

## Corrections included in the generalized code

- Displacement folders no longer all rename data files to `disp-001.lammps`; each
  folder uses a consistent `disp.lammps` (or configurable) name.
- LAMMPS runner uses the **folder-local** data file (the old runner always pointed
  at `disp-001.lammps`).
- `make_displaced_structures` now respects its `filename` argument.
- Force-constant / band plotting path no longer double-plots and is shared.
- High-symmetry animation q-points are configurable (FCC, HCP, or SeeK-path auto).
- Backend-specific common files (DeePMD model vs `pot.mtp`/`mlip.ini` vs VASP inputs).

## VASP / DFT workflow

1. Point `structure_file` at a POSCAR (or convert from LAMMPS first).
2. Set `backend: vasp`, optional `potcar_dir` + `potcar_map`, `encut`, `kmesh`.
3. Run prepare stages → creates `disp-*/` with `POSCAR`, `INCAR`, `KPOINTS`,
   `POTCAR` (if configured), and `job_vasp.sh`.
4. Submit with `./submit_all_vasp.sh` or run `vasp_std` locally.
5. Re-run with stages `force_constants` and `properties` to parse `vasprun.xml`.

Templates live in `phonopy_mlip/templates/`.

## Citations & Usage

If you incorporate these machine learning interatomic potentials (MLIPs), training datasets, or associated simulation methodologies into your research, please cite the corresponding publication:

### Metal/Diamond Moment Tensor Potentials (MTPs)
When utilizing the MTPs developed for metal–diamond interfaces (including Al, Mo, Zr, and Au systems), please cite the following article:

**Citation:**
Adnan, K. Z., Neupane, M. R., & Feng, T. (2024). Thermal boundary conductance of metal–diamond interfaces predicted by machine learning interatomic potentials. *International Journal of Heat and Mass Transfer*. https://doi.org/10.1016/j.ijheatmasstransfer.2024.126227

**BibTeX:**
```bibtex
@article{adnan2024thermal,
  title = {Thermal boundary conductance of metal–diamond interfaces predicted by machine learning interatomic potentials},
  author = {Adnan, Khalid Zobaid and Neupane, Mahesh R. and Feng, Tianli},
  journal = {International Journal of Heat and Mass Transfer},
  year = {2024},
  publisher = {Elsevier},
  doi = {10.1016/j.ijheatmasstransfer.2024.126227},
  url = {https://doi.org/10.1016/j.ijheatmasstransfer.2024.126227}
}
```
