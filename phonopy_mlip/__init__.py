"""
Generalized phonon workflow for MLIP (DeePMD / MTP) and DFT (VASP).

Replaces the duplicated per-example scripts with a single configurable pipeline.
"""

from .pipeline import PhononWorkflow
from .config import WorkflowConfig

__all__ = ["PhononWorkflow", "WorkflowConfig"]
__version__ = "1.0.0"
