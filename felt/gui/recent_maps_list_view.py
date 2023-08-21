import platform
from typing import Optional

from qgis.PyQt.QtCore import (
    Qt,
    QObject,
    QModelIndex,
    QSize,
    QRectF,
    QPointF
)
from qgis.PyQt.QtGui import (
    QFontMetrics,
    QPainter,
    QBrush,
    QPen,
    QColor,
    QFont,
    QImage,
    QPalette
)
from qgis.PyQt.QtWidgets import (
    QWidget,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QAbstractItemView,
    QListView,
    QApplication,
    QStyle,
    QVBoxLayout
)
from qgis.gui import QgsFilterLineEdit

from ..core import Map, RecentMapsModel


class RecentMapDelegate(QStyledItemDelegate):
    """
    Custom delegate for rendering map details in a list
    """

    THUMBNAIL_CORNER_RADIUS = 10
    VERTICAL_MARGIN = 7
    HORIZONTAL_MARGIN = 5
    THUMBNAIL_WIDTH = 125
    THUMBNAIL_MARGIN = 0

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

    def sizeHint(self, option, index):
        line_scale = 1
        if platform.system() == "Darwin":
            line_scale = 1.3

        return QSize(
            option.rect.width(),
            int(QFontMetrics(option.font).height() * 4.5 * line_scale),
        )

    def process_thumbnail(self, thumbnail: QImage, size: QSize) -> QImage:
        """
        Processes a raw thumbnail image, resizing to required size and
        rounding off corners
        """
        max_thumbnail_width = size.width()
        max_thumbnail_height = int(min(size.height(), thumbnail.height()))
        scaled = thumbnail.scaled(
            QSize(max_thumbnail_width, max_thumbnail_height),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        im_out = QImage(scaled.width(), scaled.height(), QImage.Format_ARGB32)
        im_out.fill(Qt.transparent)
        painter = QPainter(im_out)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        painter.drawRoundedRect(
            QRectF(0, 0, scaled.width(), scaled.height()),
            self.THUMBNAIL_CORNER_RADIUS,
            self.THUMBNAIL_CORNER_RADIUS,
        )
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.drawImage(0, 0, scaled)
        painter.end()
        return im_out

    def paint(
            self,
            painter: QPainter,
            option: QStyleOptionViewItem,
            index: QModelIndex
    ):
        self.initStyleOption(option, index)
        style = QApplication.style() if option.widget is None \
            else option.widget.style()

        is_selected = option.state & QStyle.State_Selected

        # draw background for item (i.e. selection background)
        style.drawPrimitive(
            QStyle.PE_PanelItemViewItem, option, painter, option.widget)

        _map: Map = index.data(RecentMapsModel.MapRole)
        if not _map:
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        inner_rect = QRectF(option.rect)
        inner_rect.adjust(
            self.HORIZONTAL_MARGIN,
            self.VERTICAL_MARGIN,
            -self.HORIZONTAL_MARGIN,
            -self.VERTICAL_MARGIN,
        )

        thumbnail_rect = inner_rect
        thumbnail_rect.setWidth(self.THUMBNAIL_WIDTH)

        thumbnail_image = index.data(RecentMapsModel.ThumbnailRole)
        if thumbnail_image and not thumbnail_image.isNull():
            scaled = self.process_thumbnail(
                thumbnail_image,
                QSize(
                    int(thumbnail_rect.width()) - 2 * self.THUMBNAIL_MARGIN,
                    int(thumbnail_rect.height()) - 2 * self.THUMBNAIL_MARGIN,
                ),
            )

            center_x = int((thumbnail_rect.width() - scaled.width()) / 2)
            center_y = int((thumbnail_rect.height() - scaled.height()) / 2)
            painter.drawImage(
                QRectF(
                    thumbnail_rect.left() + center_x,
                    thumbnail_rect.top() + center_y,
                    scaled.width(),
                    scaled.height(),
                ),
                scaled,
            )

        heading_font_size = 14
        line_scale = 1
        if platform.system() == "Darwin":
            heading_font_size = 16
            line_scale = 1.3

        font = QFont(option.font)
        metrics = QFontMetrics(font)
        font.setPointSizeF(heading_font_size)
        font.setBold(False)
        painter.setFont(font)

        left_text_edge = (
                inner_rect.left() +
                self.THUMBNAIL_WIDTH +
                self.HORIZONTAL_MARGIN * 2
        )

        line_heights = [1.6 * line_scale]

        painter.setBrush(Qt.NoBrush)
        font_color = option.palette.color(
            QPalette.Active,
            QPalette.HighlightedText if is_selected else QPalette.Text)
        painter.setPen(QPen(font_color))
        painter.drawText(
            QPointF(
                left_text_edge,
                inner_rect.top() + int(metrics.height() * line_heights[0]),
            ),
            _map.title,
        )

        painter.restore()


class RecentMapsListView(QListView):
    """
    Custom list view for recent maps
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._model = RecentMapsModel(self)
        self.setModel(self._model)
        delegate = RecentMapDelegate(self)
        self.setItemDelegate(delegate)

        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

    def set_filter_string(self, filter_string: str):
        """
        Sets a text filter for the view
        """
        self._model.set_filter_string(filter_string)


class RecentMapsWidget(QWidget):
    """
    Custom widget allowing users to select from recent maps
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        vl = QVBoxLayout()
        vl.setContentsMargins(0, 0, 0, 0)

        self._filter = QgsFilterLineEdit()
        self._filter.setShowSearchIcon(True)
        self._filter.setPlaceholderText(self.tr('Search maps...'))
        vl.addWidget(self._filter)

        self._view = RecentMapsListView()
        vl.addWidget(self._view, 1)
        self.setLayout(vl)

        self._filter.textChanged.connect(self._view.set_filter_string)
