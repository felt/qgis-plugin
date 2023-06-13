# -*- coding: utf-8 -*-
"""Felt Authorization dialog

.. note:: This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

__author__ = '(C) 2022 by Nyall Dawson'
__date__ = '22/11/2022'
__copyright__ = 'Copyright 2022, North Road'
# This will get replaced with a git SHA1 when you do a git archive
__revision__ = '$Format:%H$'

from typing import Optional

from qgis.PyQt.QtCore import (
    QSize
)
from qgis.PyQt.QtGui import (
    QFontMetrics
)
from qgis.PyQt.QtSvg import QSvgWidget
from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout
)

from .gui_utils import (
    GuiUtils
)


class FeltDialogHeader(QWidget):
    """
    A widget for dialog headers
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        font_metrics = QFontMetrics(self.font())

        self.setFixedHeight(font_metrics.height() * 10)
        self.setStyleSheet('background: solid #3d521e;')
        svg_logo_widget = QSvgWidget()
        fixed_size = QSize(int(font_metrics.height() * 7.150951),
                           font_metrics.height() * 4)
        svg_logo_widget.setFixedSize(fixed_size)
        svg_logo_widget.load(GuiUtils.get_icon_svg('felt_logo_white.svg'))
        vl = QVBoxLayout()
        vl.setContentsMargins(font_metrics.height() * 2,
                              font_metrics.height() * 2, 0, 0)
        vl.addWidget(svg_logo_widget)
        self.setLayout(vl)
