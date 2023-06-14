# coding=utf-8
"""Felt API client Test.

.. note:: This program is free software; you can redistribute it and/or modify
     it under the terms of the GNU General Public License as published by
     the Free Software Foundation; either version 2 of the License, or
     (at your option) any later version.

"""

__author__ = '(C) 2022 by Nyall Dawson'
__date__ = '23/11/2022'
__copyright__ = 'Copyright 2022, North Road'
# This will get replaced with a git SHA1 when you do a git archive
__revision__ = '$Format:%H$'

import unittest
from pathlib import Path

from qgis.core import (
    Qgis,
    QgsVectorLayer,
    QgsRasterLayer,
    QgsCoordinateTransformContext,
    QgsCoordinateReferenceSystem,
    QgsWkbTypes
)

from .utilities import get_qgis_app
from ..core import (
    LayerExporter,
    LayerExportResult
)

QGIS_APP = get_qgis_app()

TEST_DATA_PATH = Path(__file__).parent


class LayerExporterTest(unittest.TestCase):
    """Test layer exporting works."""

    def test_file_name(self):
        """
        Test building temporary file names
        """
        exporter = LayerExporter(
            QgsCoordinateTransformContext()
        )
        file_name = exporter.generate_file_name('.gpkg')
        self.assertTrue(file_name)
        self.assertTrue(file_name.endswith('.gpkg'))
        file_name2 = exporter.generate_file_name('.gpkg')
        self.assertNotEqual(file_name, file_name2)

    def test_vector_conversion(self):
        """
        Test vector layer conversion
        """
        file = str(TEST_DATA_PATH / 'points.gpkg')
        layer = QgsVectorLayer(file, 'test')
        self.assertTrue(layer.isValid())

        exporter = LayerExporter(
            QgsCoordinateTransformContext()
        )
        result = exporter.export_layer_for_felt(layer)
        self.assertEqual(result.result, LayerExportResult.Success)
        self.assertTrue(result.filename)

        out_layer = QgsVectorLayer(result.filename, 'test')
        self.assertTrue(out_layer.isValid())
        self.assertEqual(out_layer.featureCount(), layer.featureCount())
        self.assertEqual(out_layer.wkbType(), QgsWkbTypes.MultiPoint)

    def test_gml_conversion(self):
        """
        Test GML vector layer conversion
        """
        file = str(TEST_DATA_PATH / 'polys.gml')
        layer = QgsVectorLayer(file, 'test')
        self.assertTrue(layer.isValid())

        exporter = LayerExporter(
            QgsCoordinateTransformContext()
        )
        result = exporter.export_layer_for_felt(layer)
        self.assertEqual(result.result, LayerExportResult.Success)
        self.assertTrue(result.filename)

        out_layer = QgsVectorLayer(result.filename, 'test')
        self.assertTrue(out_layer.isValid())
        self.assertEqual(out_layer.featureCount(), layer.featureCount())
        self.assertEqual(out_layer.wkbType(), QgsWkbTypes.MultiPolygon)

    def test_raster_conversion(self):
        """
        Test raster layer conversion
        """
        file = str(TEST_DATA_PATH / 'dem.tif')
        layer = QgsRasterLayer(file, 'test')
        self.assertTrue(layer.isValid())

        exporter = LayerExporter(
            QgsCoordinateTransformContext()
        )
        result = exporter.export_layer_for_felt(layer)
        self.assertEqual(result.result, LayerExportResult.Success)
        self.assertTrue(result.filename)

        out_layer = QgsRasterLayer(result.filename, 'test')
        self.assertTrue(out_layer.isValid())
        self.assertEqual(out_layer.width(), 373)
        self.assertEqual(out_layer.height(), 502)
        self.assertEqual(out_layer.bandCount(), 4)
        self.assertEqual(out_layer.dataProvider().dataType(1),
                         Qgis.DataType.Byte)
        self.assertEqual(out_layer.dataProvider().dataType(2),
                         Qgis.DataType.Byte)
        self.assertEqual(out_layer.dataProvider().dataType(3),
                         Qgis.DataType.Byte)
        self.assertEqual(out_layer.dataProvider().dataType(4),
                         Qgis.DataType.Byte)
        self.assertEqual(out_layer.crs(),
                         QgsCoordinateReferenceSystem('EPSG:3857'))
        self.assertAlmostEqual(out_layer.extent().xMinimum(),
                         2077922, -3)
        self.assertAlmostEqual(out_layer.extent().xMaximum(),
                         2082074, -3)
        self.assertAlmostEqual(out_layer.extent().yMinimum(),
                         5744637, -3)
        self.assertAlmostEqual(out_layer.extent().yMaximum(),
                         5750225, -3)


if __name__ == "__main__":
    suite = unittest.makeSuite(LayerExporterTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
