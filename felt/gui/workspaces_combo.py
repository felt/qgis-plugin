# -*- coding: utf-8 -*-
"""Widgets for selection from Workspaces

.. note:: This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

from typing import Optional

from qgis.PyQt.QtWidgets import (
    QWidget,
    QComboBox,
)
from ..core import WorkspacesModel


class WorkspacesComboBox(QComboBox):
    """
    Custom combo box for workspace selection
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._model = WorkspacesModel(self)
        self.setModel(self._model)
