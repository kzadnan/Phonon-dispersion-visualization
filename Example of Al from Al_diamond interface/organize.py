# -*- coding: utf-8 -*-
"""Backward-compatible organize helper (mtp)."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phonopy_mlip.backends import MTPBackend
from phonopy_mlip.config import WorkflowConfig


def organize_folders(common_files=None):
    cfg = WorkflowConfig(backend="mtp")
    if common_files is not None:
        cfg.common_files = list(common_files)
    MTPBackend(cfg)._organize_folders()
