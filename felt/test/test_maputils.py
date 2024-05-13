"""
Map Utils Test.
"""

import unittest

from qgis.PyQt.QtCore import QSize
from qgis.core import (
    QgsReferencedRectangle,
    QgsRectangle,
    QgsCoordinateReferenceSystem
)

from .utilities import get_qgis_app
from ..core.map_utils import MapUtils

QGIS_APP = get_qgis_app()


class MapUtilsTest(unittest.TestCase):
    """Test MapUtils work."""

    def test_extent_to_zoom(self):
        """
        Test conversion of map extents to leaflet zoom levels
        """
        self.assertEqual(
            MapUtils.calculate_leaflet_tile_zoom_for_extent(
                QgsReferencedRectangle(
                    QgsRectangle(
                        -13844205, 2747610, -8721688, 5988165
                    ),
                    QgsCoordinateReferenceSystem('EPSG:3857')
                ),
                QSize(1024, 800)
            ), 4
        )
        self.assertEqual(
            MapUtils.calculate_leaflet_tile_zoom_for_extent(
                QgsReferencedRectangle(
                    QgsRectangle(
                        -13844205, 2747610, -8721688, 5988165
                    ),
                    QgsCoordinateReferenceSystem('EPSG:3857')
                ),
                QSize(500, 300)
            ), 3
        )
        self.assertEqual(
            MapUtils.calculate_leaflet_tile_zoom_for_extent(
                QgsReferencedRectangle(
                    QgsRectangle(
                        20.74, -123.05, 50.42, -79.67
                    ),
                    QgsCoordinateReferenceSystem('EPSG:4326')
                ),
                QSize(1024, 800)
            ), 7
        )


if __name__ == "__main__":
    suite = unittest.makeSuite(MapUtilsTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
