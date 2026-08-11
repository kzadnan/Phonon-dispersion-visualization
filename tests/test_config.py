"""Lightweight tests that do not require phonopy/LAMMPS binaries."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from phonopy_mlip.config import WorkflowConfig


class ConfigTests(unittest.TestCase):
    def test_roundtrip_yaml(self):
        cfg = WorkflowConfig(
            structure_file="POSCAR",
            species_map={1: "C", 2: "Au"},
            supercell=[2, 2, 2],
            backend="vasp",
            potcar_map={"C": "C", "Au": "Au"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cfg.yaml"
            cfg.save(path)
            loaded = WorkflowConfig.from_file(path)
        self.assertEqual(loaded.backend, "vasp")
        self.assertEqual(loaded.species_order_resolved(), ["C", "Au"])
        self.assertEqual(loaded.default_common_files(), ["INCAR", "KPOINTS", "POTCAR", "job"])

    def test_deepmd_defaults(self):
        cfg = WorkflowConfig(backend="deepmd", deepmd_model="model.pb")
        self.assertIn("model.pb", cfg.default_common_files())

    def test_mtp_defaults(self):
        cfg = WorkflowConfig(backend="mtp")
        files = cfg.default_common_files()
        self.assertIn("pot.mtp", files)
        self.assertIn("mlip.ini", files)

    def test_supercell_matrix(self):
        import numpy as np

        cfg = WorkflowConfig(supercell=[3, 3, 3])
        np.testing.assert_array_equal(cfg.supercell_matrix(), np.diag([3, 3, 3]))


class ImportTests(unittest.TestCase):
    def test_package_imports(self):
        from phonopy_mlip import PhononWorkflow, WorkflowConfig
        from phonopy_mlip.backends import get_backend

        cfg = WorkflowConfig(backend="deepmd", species_map={1: "C"})
        backend = get_backend(cfg)
        self.assertEqual(backend.name, "deepmd")
        self.assertIsInstance(PhononWorkflow(cfg), PhononWorkflow)


if __name__ == "__main__":
    unittest.main()
