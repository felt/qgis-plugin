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
    QPainter,
    QImage
)
from qgis.PyQt.QtSvg import QSvgWidget
from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QSizePolicy,
    QHBoxLayout
)

from .gui_utils import (
    GuiUtils
)


class FeltDialogHeader(QWidget):
    """
    A widget for dialog headers
    """

    FIXED_HEIGHT_PIXELS = 107
    LOGO_HEIGHT_PIXELS = 42
    LOGO_WIDTH_PIXELS = int(1938 / 1084 * LOGO_HEIGHT_PIXELS)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._cached_image: Optional[QImage] = None

        self.setSizePolicy(
            QSizePolicy.Minimum,
            QSizePolicy.Fixed
        )

        svg_logo_widget = QSvgWidget()
        fixed_size = QSize(self.LOGO_WIDTH_PIXELS,
                           self.LOGO_HEIGHT_PIXELS)
        svg_logo_widget.setFixedSize(fixed_size)
        svg_logo_widget.load(GuiUtils.get_icon_svg('felt_logo_white.svg'))
        svg_logo_widget.setStyleSheet('background: transparent;')
        svg_logo_container = QVBoxLayout()
        svg_logo_container.setContentsMargins(0, 0, 0, 4)
        svg_logo_container.addWidget(svg_logo_widget)
        vl = QVBoxLayout()
        vl.setContentsMargins(12, 0, 12, 15)
        vl.addStretch(1)

        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.addLayout(svg_logo_container)
        self.header_layout.addStretch()

        vl.addLayout(self.header_layout)
        self.setLayout(vl)

    # QWidget interface
    # pylint: disable=missing-function-docstring

    def push_widget(self, widget: QWidget):
        """
        Pushes a new widget into the right section of the header
        """
        self.header_layout.addWidget(widget)

    def sizeHint(self):
        return QSize(0, self.FIXED_HEIGHT_PIXELS)

    def paintEvent(self, event):  # pylint: disable=unused-argument
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # image has 437 x 107 aspect ratio
        if not self._cached_image or \
                (self._cached_image.size() /
                 self._cached_image.devicePixelRatioF()) != self.rect().size():
            image_height = int(self.rect().width() / 437 * 107)

            self._cached_image = (
                GuiUtils.get_svg_as_image('felt_header.svg',
                                          self.rect().width(),
                                          image_height, None,
                                          self.devicePixelRatioF()))

        painter.drawImage(QRectF(0, 0,
                                 self._cached_image.width() /
                                 self._cached_image.devicePixelRatioF(),
                                 self._cached_image.height() /
                                 self._cached_image.devicePixelRatioF()),
                          self._cached_image)

        painter.end()

    # pylint: enable=missing-function-docstring
