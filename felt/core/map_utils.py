"""Map utilities

.. note:: This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

from qgis.PyQt.QtCore import (
    QSize
)
from qgis.core import (
    QgsMapSettings,
    QgsReferencedRectangle
)


class MapUtils:
    """
    Utilities for working with maps
    """

    ZOOM_LEVEL_SCALE_BREAKS = [
        591657527.591555,
        295828763.795777,
        147914381.897889,
        73957190.948944,
        36978595.474472,
        18489297.737236,
        9244648.868618,
        4622324.434309,
        2311162.217155,
        1155581.108577,
        577790.554289,
        288895.277144,
        144447.638572,
        72223.819286,
        36111.909643,
        18055.954822,
        9027.977411,
        4513.988705,
        2256.994353,
        1128.497176,
        564.248588,
        282.124294,
        141.062147,
        70.5310735
    ]

    @staticmethod
    def map_scale_to_leaflet_tile_zoom(
            scale: float
    ) -> int:
        """
        Returns the leaflet tile zoom level roughly
        corresponding to a QGIS map scale
        """
        for level, min_scale in enumerate(MapUtils.ZOOM_LEVEL_SCALE_BREAKS):
            if min_scale < scale:
                # we play it safe and zoom out a step -- this is because
                # we don't know the screen size or DPI on which the map
                # will actually be viewed, so we err on the conservative side
                return level - 1

        return len(MapUtils.ZOOM_LEVEL_SCALE_BREAKS) - 1

    @staticmethod
    def calculate_leaflet_tile_zoom_for_extent(
            extent: QgsReferencedRectangle,
            target_map_size: QSize,
    ) -> int:
        """
        Calculates the required leaflet tile zoom level in order
        to completely fit a specified extent.

        :param extent: required minimum map extent
        :param target_map_size: size of leaflet map, in pixels
        """

        map_settings = QgsMapSettings()
        map_settings.setDestinationCrs(extent.crs())
        map_settings.setExtent(extent)
        map_settings.setOutputDpi(96)
        map_settings.setOutputSize(target_map_size)

        scale = map_settings.scale()
        return MapUtils.map_scale_to_leaflet_tile_zoom(scale)
