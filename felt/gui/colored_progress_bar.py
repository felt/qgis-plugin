"""
A colored progress bar
"""

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

    # QWidget interface

    # pylint: disable=missing-function-docstring,unused-argument
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

    # pylint: enable=missing-function-docstring,unused-argument
