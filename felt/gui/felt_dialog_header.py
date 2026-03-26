"""
Felt Authorization dialog
"""

from typing import Optional

from qgis.PyQt.QtCore import (
    Qt,
    QSize,
    QRectF
)
from qgis.PyQt.QtGui import (
    QPainter,
    QImage
)
from qgis.PyQt.QtSvg import QSvgRenderer
from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QSizePolicy,
    QHBoxLayout
)

from .gui_utils import (
    GuiUtils
)


class _SvgWidget(QWidget):
    """
    A simple widget that renders an SVG file, replacing QSvgWidget
    which is not available through qgis.PyQt in QGIS 4.
    """

    def __init__(self, path: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._renderer = QSvgRenderer(path)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):  # pylint: disable=unused-argument
        painter = QPainter(self)
        self._renderer.render(painter, QRectF(self.rect()))
        painter.end()


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
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Fixed
        )

        svg_logo_widget = _SvgWidget(
            GuiUtils.get_icon_svg('felt_logo_white.svg'))
        fixed_size = QSize(self.LOGO_WIDTH_PIXELS,
                           self.LOGO_HEIGHT_PIXELS)
        svg_logo_widget.setFixedSize(fixed_size)
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
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

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
