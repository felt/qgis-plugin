# -*- coding: utf-8 -*-
"""Felt API Map

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

import json
from dataclasses import dataclass
from typing import (
    Optional
)

from .enums import ObjectType

from qgis.PyQt.QtCore import (
    QObject,
    QDate
)

from qgis.core import (
    QgsProject
)


class MapUploader(QObject):
    """
    Handles map creation/uploading logic
    """

    def __init__(self, project: Optional[QgsProject] = None):
        super().__init__()
        self.project = project or QgsProject.instance()

    def default_map_title(self):
        date_string = QDate.currentDate().toString('yyyy-MM-dd')
        if self.project.title():
            return self.tr('{} QGIS Map - {}').format(
                self.project.title(),
                date_string
            )

        return self.tr('Untitled QGIS Map - {}').format(
            date_string
        )
