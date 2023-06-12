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
    QgsVectorLayer,
    QgsCoordinateTransformContext,
    QgsVectorFileWriter,
    QgsWkbTypes
)

from .utilities import get_qgis_app
from ..core import (
    LayerExporter
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
        self.assertEqual(result.result, QgsVectorFileWriter.NoError)
        self.assertTrue(result.filename)

        out_layer = QgsVectorLayer(result.filename, 'test')
        self.assertTrue(out_layer.isValid())
        self.assertEqual(out_layer.featureCount(), layer.featureCount())
        self.assertEqual(out_layer.wkbType(), QgsWkbTypes.MultiPoint)


if __name__ == "__main__":
    suite = unittest.makeSuite(LayerExporterTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
