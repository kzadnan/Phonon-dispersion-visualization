# -*- coding: utf-8 -*-
"""Backward-compatible shim -> phonopy_mlip.properties.extract_properties"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phonopy_mlip.properties import extract_properties as properties  # noqa: F401
