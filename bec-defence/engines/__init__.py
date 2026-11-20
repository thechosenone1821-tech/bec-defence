"""Detection engines.

Two detector prototypes live here:

* ``SpectralCondensationDetector`` / ``RollingSpectralMonitor`` -- spectral
  coordination detection on numerical session-feature matrices.
* ``InformationScramblingMonitor`` -- entropy + contextual file-write
  inspection for ransomware-like scrambling.

These are research-inspired detection prototypes, not a production defence
system. See ``README.md`` for what is implemented versus planned.
"""

from engines.spectral import (
    SpectralCondensationDetector,
    RollingSpectralMonitor,
    MeanShiftBaseline,
    DistanceBaseline,
)
from engines.blackhole import InformationScramblingMonitor, FileWriteAssessment

__all__ = [
    "SpectralCondensationDetector",
    "RollingSpectralMonitor",
    "MeanShiftBaseline",
    "DistanceBaseline",
    "InformationScramblingMonitor",
    "FileWriteAssessment",
]
