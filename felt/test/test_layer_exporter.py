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
import zipfile
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

    def test_can_export_layer(self):
        """
        Test determining if layers can be exported
        """
        file = str(TEST_DATA_PATH / 'points.gpkg')
        layer = QgsVectorLayer(file, 'test')
        self.assertTrue(layer.isValid())
        self.assertTrue(LayerExporter.can_export_layer(layer))

        file = str(TEST_DATA_PATH / 'dem.tif')
        layer = QgsRasterLayer(file, 'test')
        self.assertTrue(layer.isValid())
        self.assertTrue(LayerExporter.can_export_layer(layer))

        layer = QgsRasterLayer(
            'crs=EPSG:3857&format&type=xyz&url='
            'https://tile.openstreetmap.org/%7Bz%7D/%7Bx%7D/%7By%7D.png'
            '&zmax=19&zmin=0',
            'test', 'wms')
        self.assertFalse(LayerExporter.can_export_layer(layer))

    def test_file_name(self):
        """
        Test building temporary file names
        """
        exporter = LayerExporter(
            QgsCoordinateTransformContext()
        )
        file_name = exporter.generate_file_name('.gpkg')
        self.assertTrue(file_name)
        self.assertIn('/qgis_export_', file_name)
        self.assertTrue(file_name.endswith('.gpkg'))
        file_name2 = exporter.generate_file_name('.gpkg')
        self.assertNotEqual(file_name, file_name2)

    # pylint: disable=protected-access
    def test_layer_style(self):
        """
        Test retrieving original layer style XML
        """
        file = str(TEST_DATA_PATH / "points.gpkg")
        layer = QgsVectorLayer(file, "test")

        style = LayerExporter._get_original_style_xml(layer)
        self.assertEqual(
            style[:58],
            "<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>"
        )
        # should only be the layer's style, not the source information
        self.assertNotIn('points.gpkg', style)
    # pylint: enable=protected-access

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
        self.assertEqual(result.filename[-4:], '.zip')
        with zipfile.ZipFile(result.filename) as z:
            gpkg_files = [f for f in z.namelist() if f.endswith('gpkg')]

            qgis_style = z.read('qgis_style.xml')
            self.assertEqual(
                qgis_style[:58],
                b"<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>"
            )
        self.assertEqual(len(gpkg_files), 1)

        self.assertEqual(
            result.qgis_style_xml[:58],
            "<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>"
        )

        out_layer = QgsVectorLayer(
            '/vsizip/{}/{}'.format(result.filename, gpkg_files[0]),
            'test')
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
        self.assertEqual(result.filename[-4:], '.zip')
        with zipfile.ZipFile(result.filename) as z:
            gpkg_files = [f for f in z.namelist() if f.endswith('gpkg')]
        self.assertEqual(len(gpkg_files), 1)

        out_layer = QgsVectorLayer(
            '/vsizip/{}/{}'.format(result.filename, gpkg_files[0]),
            'test')
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
        self.assertEqual(result.filename[-4:], '.zip')
        with zipfile.ZipFile(result.filename) as z:
            tif_files = [f for f in z.namelist() if f.endswith('tif')]
        self.assertEqual(len(tif_files), 2)

        styled_tif = [f for f in tif_files if '_styled' in f][0]

        self.assertEqual(
            result.qgis_style_xml[:58],
            "<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>"
        )

        out_layer = QgsRasterLayer(
            '/vsizip/{}/{}'.format(result.filename, styled_tif),
            'test')
        self.assertTrue(out_layer.isValid())
        self.assertEqual(out_layer.width(), 373)
        self.assertEqual(out_layer.height(), 350)
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
                         QgsCoordinateReferenceSystem('EPSG:4326'))
        self.assertAlmostEqual(out_layer.extent().xMinimum(),
                               18.6662979442, 3)
        self.assertAlmostEqual(out_layer.extent().xMaximum(),
                               18.7035979442, 3)
        self.assertAlmostEqual(out_layer.extent().yMinimum(),
                               45.7767014376, 3)
        self.assertAlmostEqual(out_layer.extent().yMaximum(),
                               45.8117014376, 3)

        raw_tif = [f for f in tif_files if '_styled' not in f][0]
        out_layer = QgsRasterLayer(
            '/vsizip/{}/{}'.format(result.filename, raw_tif),
            'test')
        self.assertTrue(out_layer.isValid())
        self.assertEqual(out_layer.width(), 373)
        self.assertEqual(out_layer.height(), 350)
        self.assertEqual(out_layer.bandCount(), 1)
        self.assertEqual(out_layer.dataProvider().dataType(1),
                         Qgis.DataType.Float32)
        self.assertEqual(out_layer.crs(),
                         QgsCoordinateReferenceSystem('EPSG:4326'))
        self.assertAlmostEqual(out_layer.extent().xMinimum(),
                               18.6662979442, 3)
        self.assertAlmostEqual(out_layer.extent().xMaximum(),
                               18.7035979442, 3)
        self.assertAlmostEqual(out_layer.extent().yMinimum(),
                               45.7767014376, 3)
        self.assertAlmostEqual(out_layer.extent().yMaximum(),
                               45.8117014376, 3)


if __name__ == "__main__":
    suite = unittest.makeSuite(LayerExporterTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
