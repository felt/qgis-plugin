"""
Felt API client Test.
"""

import unittest
import zipfile
from pathlib import Path

from qgis.core import (
    Qgis,
    QgsVectorLayer,
    QgsRasterLayer,
    QgsCoordinateTransformContext,
    QgsCoordinateReferenceSystem,
    QgsWkbTypes,
    QgsPalettedRasterRenderer,
    QgsRasterContourRenderer,
    QgsFeature,
    QgsGeometry,
    QgsPointXY
)

from .utilities import get_qgis_app
from ..core import (
    LayerExporter,
    LayerExportResult,
    LayerSupport,
    ConversionContext
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
        self.assertEqual(
            LayerExporter.can_export_layer(layer)[0], LayerSupport.Supported)
        self.assertTrue(layer.startEditing())
        layer.deleteFeature(next(layer.getFeatures()).id())
        self.assertEqual(
            LayerExporter.can_export_layer(layer)[0],
            LayerSupport.UnsavedEdits)

        layer.rollBack()

        file = str(TEST_DATA_PATH / 'dem.tif')
        layer = QgsRasterLayer(file, 'test')
        self.assertTrue(layer.isValid())
        self.assertEqual(
            LayerExporter.can_export_layer(layer)[0], LayerSupport.Supported)

        layer = QgsRasterLayer(
            'crs=EPSG:3857&format&type=xyz&url='
            'https://tile.openstreetmap.org/%7Bz%7D/%7Bx%7D/%7By%7D.png'
            '&zmax=19&zmin=0',
            'test', 'wms')
        support, reason = LayerExporter.can_export_layer(layer)
        self.assertEqual(support, LayerSupport.Supported)

        layer = QgsRasterLayer(
            'http-header:referer=&type=xyz&url=http://ecn.t3.tiles.'
            'virtualearth.net/tiles/a%7Bq%7D.jpeg?g%3D1&zmax=18&zmin=0',
            'test', 'wms')
        support, reason = LayerExporter.can_export_layer(layer)
        self.assertEqual(support, LayerSupport.NotImplementedProvider)
        self.assertEqual(reason, '{q} token in XYZ tile layers not supported')

        layer = QgsRasterLayer(
            'crs=EPSG:4326&dpiMode=7&format=image/png&layers='
            'wofs_summary_clear&styles&'
            'tilePixelRatio=0&url=https://ows.dea.ga.gov.au/',
            'test', 'wms')
        support, reason = LayerExporter.can_export_layer(layer)
        self.assertEqual(support, LayerSupport.NotImplementedProvider)
        self.assertEqual(reason, 'wms raster layers are not yet supported')

    def test_use_url_import_method(self):
        """
        Test determining if layers should use the URL import method
        """
        file = str(TEST_DATA_PATH / 'points.gpkg')
        layer = QgsVectorLayer(file, 'test')
        self.assertTrue(layer.isValid())
        self.assertFalse(
            LayerExporter.layer_import_url(layer))

        file = str(TEST_DATA_PATH / 'dem.tif')
        layer = QgsRasterLayer(file, 'test')
        self.assertTrue(layer.isValid())
        self.assertFalse(
            LayerExporter.layer_import_url(layer))

        layer = QgsRasterLayer(
            'crs=EPSG:3857&format&type=xyz&url='
            'https://tile.openstreetmap.org/%7Bz%7D/%7Bx%7D/%7By%7D.png'
            '&zmax=19&zmin=0',
            'test', 'wms')
        self.assertEqual(
            LayerExporter.layer_import_url(layer),
            'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
        )

        # test http -> https upgrade
        layer = QgsRasterLayer(
            'crs=EPSG:3857&format&type=xyz&url='
            'http://tile.openstreetmap.org/%7Bz%7D/%7Bx%7D/%7By%7D.png'
            '&zmax=19&zmin=0',
            'test', 'wms')
        self.assertEqual(
            LayerExporter.layer_import_url(layer),
            'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
        )

        layer = QgsRasterLayer(
            'http-header:referer=&type=xyz&url=http://ecn.t3.tiles.'
            'virtualearth.net/tiles/a%7Bq%7D.jpeg?g%3D1&zmax=18&zmin=0',
            'test', 'wms')
        self.assertFalse(
            LayerExporter.layer_import_url(layer))

        layer = QgsRasterLayer(
            'crs=EPSG:4326&dpiMode=7&format=image/png&layers='
            'wofs_summary_clear&styles&tilePixelRatio=0'
            '&url=https://ows.dea.ga.gov.au/',
            'test', 'wms')
        self.assertFalse(
            LayerExporter.layer_import_url(layer))

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
        conversion_context = ConversionContext()
        result = exporter.export_layer_for_felt(layer, conversion_context)
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
        self.assertEqual(out_layer.wkbType(), QgsWkbTypes.Point)
        self.assertEqual([f.name() for f in out_layer.fields()],
                         ['fid', 'Class', 'Heading', 'Importance',
                          'Pilots', 'Cabin Crew', 'Staff'])

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
        conversion_context = ConversionContext()
        result = exporter.export_layer_for_felt(layer, conversion_context)
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
        if Qgis.QGIS_VERSION_INT >= 32400:
            self.assertEqual([f.name() for f in out_layer.fields()],
                             ['fid', 'old_fid', 'name', 'intval', 'floatval'])
        else:
            self.assertEqual([f.name() for f in out_layer.fields()],
                             ['fid', 'name', 'intval', 'floatval'])

    def test_layer_conversion_string_fid(self):
        """
        Test vector layer conversion where FID columns are not compatible
        with geopackge
        """
        layer = QgsVectorLayer('Point?crs=EPSG:4326&'
                               'field=fid:string(255,0)&'
                               'field=label:string(255,0)', 'test', 'memory')
        self.assertTrue(layer.isValid())

        f = QgsFeature(layer.fields())
        f.setAttributes(['abc', 'def'])
        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(1, 2)))
        self.assertTrue(layer.dataProvider().addFeature(f))
        f.setAttributes(['15', 'ghi'])
        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(3, 4)))
        self.assertTrue(layer.dataProvider().addFeature(f))

        exporter = LayerExporter(
            QgsCoordinateTransformContext()
        )
        conversion_context = ConversionContext()
        result = exporter.export_layer_for_felt(layer, conversion_context)
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
        self.assertEqual(out_layer.wkbType(), QgsWkbTypes.Point)
        if Qgis.QGIS_VERSION_INT >= 32400:
            self.assertEqual([f.name() for f in out_layer.fields()],
                             ['fid', 'old_fid', 'label'])
        else:
            self.assertEqual([f.name() for f in out_layer.fields()],
                             ['fid', 'label'])
        features = list(out_layer.getFeatures())
        if Qgis.QGIS_VERSION_INT >= 32400:
            self.assertEqual([feature.attributes() for feature in features],
                             [[1, 'abc', 'def'],
                              [2, '15', 'ghi']])
        else:
            self.assertEqual([feature.attributes() for feature in features],
                             [[1, 'def'],
                              [2, 'ghi']])

    def test_layer_conversion_duplicate_fid(self):
        """
        Test vector layer conversion where FID columns are not compatible
        with geopackge
        """
        layer = QgsVectorLayer('Point?crs=EPSG:4326&'
                               'field=fid:integer&'
                               'field=label:string(255,0)', 'test', 'memory')
        self.assertTrue(layer.isValid())

        f = QgsFeature(layer.fields())
        f.setAttributes([15, 'abc'])
        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(1, 2)))
        self.assertTrue(layer.dataProvider().addFeature(f))
        f.setAttributes([15, 'def'])
        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(3, 4)))
        self.assertTrue(layer.dataProvider().addFeature(f))

        exporter = LayerExporter(
            QgsCoordinateTransformContext()
        )
        conversion_context = ConversionContext()
        result = exporter.export_layer_for_felt(layer, conversion_context)
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
        self.assertEqual(out_layer.wkbType(), QgsWkbTypes.Point)
        if Qgis.QGIS_VERSION_INT >= 32400:
            self.assertEqual([f.name() for f in out_layer.fields()],
                             ['fid', 'old_fid', 'label'])
        else:
            self.assertEqual([f.name() for f in out_layer.fields()],
                             ['fid', 'label'])

        features = list(out_layer.getFeatures())
        if Qgis.QGIS_VERSION_INT >= 32400:
            self.assertEqual([feature.attributes() for feature in features],
                             [[1, 15, 'abc'], [2, 15, 'def']])
        else:
            self.assertEqual([feature.attributes() for feature in features],
                             [[1, 'abc'], [2, 'def']])

    def test_raster_conversion_raw(self):
        """
        Test raw raster layer conversion
        """
        file = str(TEST_DATA_PATH / 'dem.tif')
        layer = QgsRasterLayer(file, 'test')
        self.assertTrue(layer.isValid())
        # set a renderer we can convert
        renderer = QgsPalettedRasterRenderer(layer.dataProvider(), 1, [])
        layer.setRenderer(renderer)

        conversion_context = ConversionContext()
        exporter = LayerExporter(
            QgsCoordinateTransformContext()
        )
        result = exporter.export_layer_for_felt(
            layer,
            conversion_context
        )
        self.assertEqual(result.result, LayerExportResult.Success)
        self.assertTrue(result.filename)
        self.assertEqual(result.filename[-4:], '.zip')
        with zipfile.ZipFile(result.filename) as z:
            tif_files = [f for f in z.namelist() if f.endswith('tif')]
        self.assertEqual(len(tif_files), 1)

        self.assertEqual(
            result.qgis_style_xml[:58],
            "<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>"
        )

        out_layer = QgsRasterLayer(
            '/vsizip/{}/{}'.format(result.filename, tif_files[0]),
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

    def test_raster_conversion_styled(self):
        """
        Test raster layer conversion
        """
        file = str(TEST_DATA_PATH / 'dem.tif')
        layer = QgsRasterLayer(file, 'test')
        self.assertTrue(layer.isValid())

        exporter = LayerExporter(
            QgsCoordinateTransformContext()
        )
        conversion_context = ConversionContext()
        result = exporter.export_layer_for_felt(
            layer,
            conversion_context,
            force_upload_raster_as_styled=True
        )
        self.assertEqual(result.result, LayerExportResult.Success)
        self.assertTrue(result.filename)
        self.assertEqual(result.filename[-4:], '.zip')
        with zipfile.ZipFile(result.filename) as z:
            tif_files = [f for f in z.namelist() if f.endswith('tif')]
        self.assertEqual(len(tif_files), 1)

        self.assertEqual(
            result.qgis_style_xml[:58],
            "<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>"
        )

        out_layer = QgsRasterLayer(
            '/vsizip/{}/{}'.format(result.filename, tif_files[0]),
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

    def test_raster_conversion_no_fsl_conversion(self):
        """
        Test raster layer conversion
        """
        file = str(TEST_DATA_PATH / 'dem.tif')
        layer = QgsRasterLayer(file, 'test')
        self.assertTrue(layer.isValid())

        # set a renderer we can't convert to FSL
        renderer = QgsRasterContourRenderer(layer.dataProvider())
        layer.setRenderer(renderer)

        conversion_context = ConversionContext()
        exporter = LayerExporter(
            QgsCoordinateTransformContext()
        )
        result = exporter.export_layer_for_felt(
            layer,
            conversion_context,
            force_upload_raster_as_styled=False
        )
        self.assertEqual(result.result, LayerExportResult.Success)
        self.assertTrue(result.filename)
        self.assertEqual(result.filename[-4:], '.zip')
        with zipfile.ZipFile(result.filename) as z:
            tif_files = [f for f in z.namelist() if f.endswith('tif')]
        self.assertEqual(len(tif_files), 1)

        self.assertEqual(
            result.qgis_style_xml[:58],
            "<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>"
        )

        out_layer = QgsRasterLayer(
            '/vsizip/{}/{}'.format(result.filename, tif_files[0]),
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


if __name__ == "__main__":
    suite = unittest.makeSuite(LayerExporterTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
