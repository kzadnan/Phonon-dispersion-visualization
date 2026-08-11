# -*- coding: utf-8 -*-
"""Backward-compatible organize helper using DeePMD defaults."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phonopy_mlip.backends import DeepMDBackend
from phonopy_mlip.config import WorkflowConfig


def organize_folders(common_files=None):
    cfg = WorkflowConfig(backend="deepmd")
    if common_files is not None:
        cfg.common_files = list(common_files)
    DeepMDBackend(cfg)._organize_folders()
