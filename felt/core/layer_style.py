"""
Layer exporter for Felt
"""

from dataclasses import dataclass
from typing import (
    Optional,
    Dict
)

from qgis.PyQt.QtGui import QColor


@dataclass
class LayerStyle:
    """
    Represents styling of a Felt vector layer
    """
    fill_color: Optional[QColor] = None
    stroke_color: Optional[QColor] = None
    fsl: Optional[Dict[str, object]] = None
