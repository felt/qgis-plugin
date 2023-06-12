# -*- coding: utf-8 -*-
"""GUI Utilities

.. note:: This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

__author__ = '(C) 2018 by Nyall Dawson'
__date__ = '20/04/2018'
__copyright__ = 'Copyright 2018, North Road'
# This will get replaced with a git SHA1 when you do a git archive
__revision__ = '$Format:%H$'

import math
import os
import re
from typing import Optional

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import (
    QIcon,
    QFont,
    QFontMetrics,
    QImage,
    QPixmap,
    QFontDatabase,
    QColor,
    QPainter
)
from qgis.PyQt.QtSvg import QSvgRenderer
from qgis.core import (
    Qgis
)

FONT_FAMILIES = ""


class GuiUtils:
    """
    Utilities for GUI plugin components
    """

    APPLICATION_FONT_MAP = {}

    @staticmethod
    def get_icon(icon: str) -> QIcon:
        """
        Returns a plugin icon
        :param icon: icon name (svg file name)
        :return: QIcon
        """
        path = GuiUtils.get_icon_svg(icon)
        if not path:
            return QIcon()

        return QIcon(path)

    @staticmethod
    def get_icon_svg(icon: str) -> str:
        """
        Returns a plugin icon's SVG file path
        :param icon: icon name (svg file name)
        :return: icon svg path
        """
        path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'icons',
            icon)
        if not os.path.exists(path):
            return ''

        return path

    @staticmethod
    def get_icon_pixmap(icon: str) -> QPixmap:
        """
        Returns a plugin icon's PNG file path
        :param icon: icon name (png file name)
        :return: icon png path
        """
        path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'icons',
            icon)
        if not os.path.exists(path):
            return QPixmap()

        im = QImage(path)
        return QPixmap.fromImage(im)

    @staticmethod
    def get_svg_as_image(icon: str, width: int, height: int,
                         background_color: Optional[QColor] = None) -> QImage:
        """
        Returns an SVG returned as an image
        """
        path = GuiUtils.get_icon_svg(icon)
        if not os.path.exists(path):
            return QImage()

        renderer = QSvgRenderer(path)
        image = QImage(width, height, QImage.Format_ARGB32)
        if not background_color:
            image.fill(Qt.transparent)
        else:
            image.fill(background_color)

        painter = QPainter(image)
        renderer.render(painter)
        painter.end()

        return image

    @staticmethod
    def get_ui_file_path(file: str) -> str:
        """
        Returns a UI file's path
        :param file: file name (uifile name)
        :return: ui file path
        """
        path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'ui',
            file)
        if not os.path.exists(path):
            return ''

        return path

    @staticmethod
    def scale_icon_size(standard_size: int) -> int:
        """
        Scales an icon size accounting for device DPI
        """
        fm = QFontMetrics((QFont()))
        scale = 1.1 * standard_size / 24.0
        return int(math.floor(max(Qgis.UI_SCALE_FACTOR * fm.height() * scale,
                                  float(standard_size))))

    @staticmethod
    def get_default_font() -> QFont:
        """
        Returns the best font match for the Koordinates default font
        families which is available on the system
        """
        for family in FONT_FAMILIES.split(','):
            family_cleaned = re.match(r'^\s*\'?(.*?)\'?\s*$', family).group(1)
            font = QFont(family_cleaned)
            if font.exactMatch():
                return font

        return QFont()

    @staticmethod
    def get_font_path(font: str) -> str:
        """
        Returns the path to an included font file
        :param font: font name
        :return: font file path
        """
        path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'fonts',
            font)
        if not os.path.exists(path):
            return ''

        return path

    @staticmethod
    def get_embedded_font(font: str) -> QFont:
        """
        Returns a font created from an embedded font file
        """
        if font in GuiUtils.APPLICATION_FONT_MAP:
            return GuiUtils.APPLICATION_FONT_MAP[font]

        path = GuiUtils.get_font_path(font)
        if not path:
            return QFont()

        res = QFontDatabase.addApplicationFont(path)
        families = QFontDatabase.applicationFontFamilies(res)
        installed_font = QFont(families[0])
        GuiUtils.APPLICATION_FONT_MAP[font] = installed_font
        return installed_font
