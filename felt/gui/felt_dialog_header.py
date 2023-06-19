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
    QSize,
    QRectF
)
from qgis.PyQt.QtGui import (
    QFontMetrics,
    QPainter,
    QImage
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

        self._cached_image: Optional[QImage] = None

        self.setFixedHeight(font_metrics.height() * 10)
        self.setStyleSheet('{ background: solid #3d521e; }')
        svg_logo_widget = QSvgWidget()
        fixed_size = QSize(int(font_metrics.height() * 7.150951),
                           font_metrics.height() * 4)
        svg_logo_widget.setFixedSize(fixed_size)
        svg_logo_widget.load(GuiUtils.get_icon_svg('felt_logo_white.svg'))
        svg_logo_widget.setStyleSheet('background: transparent !important;')
        vl = QVBoxLayout()
        vl.addStretch(1)
        vl.setContentsMargins(12,
                              0, 0, 19)
        vl.addWidget(svg_logo_widget)
        self.setLayout(vl)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # image has 437 x 107 aspect ratio
        if not self._cached_image or self._cached_image.size() != self.rect().size():
            image_height = int(self.rect().width() / 437 * 107)

            self._cached_image = GuiUtils.get_svg_as_image('felt_header.svg',
                                                           self.rect().width(),
                                                           image_height)

        painter.drawImage(QRectF(0, 0,
                                 self._cached_image.width(),
                                 self._cached_image.height()),
                          self._cached_image)

        painter.end()
