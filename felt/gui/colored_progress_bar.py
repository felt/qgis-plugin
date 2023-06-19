# -*- coding: utf-8 -*-
"""A colored progress bar

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

from qgis.PyQt.QtCore import (
    Qt
)
from qgis.PyQt.QtGui import (
    QPalette,
    QColor,
    QPainter
)
from qgis.PyQt.QtWidgets import (
    QProgressBar,
    QStyleOptionProgressBar,
    QStyle
)


class ColorBar(QProgressBar):
    """
    A colored progress bar
    """

    def paintEvent(self, event):
        option = QStyleOptionProgressBar()
        self.initStyleOption(option)

        option.textAlignment = Qt.AlignHCenter
        option.palette.setColor(QPalette.Highlight, QColor("#3d521e"))
        if self.value() > 45:
            option.palette.setColor(QPalette.HighlightedText,
                                    QColor(255, 255, 255))
        else:
            option.palette.setColor(QPalette.Text,
                                    QColor(0, 0, 0))
            option.palette.setColor(QPalette.HighlightedText,
                                    QColor(0, 0, 0))

        painter = QPainter(self)
        self.style().drawControl(QStyle.CE_ProgressBar, option, painter, self)
