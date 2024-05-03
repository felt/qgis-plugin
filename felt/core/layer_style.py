# -*- coding: utf-8 -*-
"""Layer exporter for Felt

.. note:: This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

__author__ = '(C) 2023 by Nyall Dawson'
__date__ = '1/06/2023'
__copyright__ = 'Copyright 2022, North Road'
# This will get replaced with a git SHA1 when you do a git archive
__revision__ = '$Format:%H$'

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
