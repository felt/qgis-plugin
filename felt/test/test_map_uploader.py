"""
Map Exporter Test.
"""

import unittest
import os
from pathlib import Path
from tempfile import TemporaryDirectory


from qgis.PyQt.QtCore import QDate
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsLayerTreeGroup
)

from .utilities import get_qgis_app
from ..core.map_uploader import MapUploaderTask

QGIS_APP = get_qgis_app()
TEST_DATA_PATH = Path(__file__).parent


class MapUploaderTest(unittest.TestCase):
    """Test map uploader works."""

    def test_map_name(self):
        """
        Test generation of map names
        """
        project = QgsProject()
        # no name, no file name
        uploader = MapUploaderTask(project)
        self.assertEqual(uploader.default_map_title(),
                         'QGIS Map - {}'.format(
                             QDate.currentDate().toString('yyyy-MM-dd')
                         ))

        # save project to temporary file
        with TemporaryDirectory() as d:
            path = os.path.join(d, 'my-awesome_project.qgs')
            project.write(path)
            uploader = MapUploaderTask(project)
            self.assertEqual(uploader.default_map_title(),
                             'my awesome project')

        # with explicit title
        project.setTitle('My project title')
        uploader = MapUploaderTask(project)
        self.assertEqual(uploader.default_map_title(),
                         'My project title')

    def test_group_names(self):
        """
        Test destination group name logic
        """
        project = QgsProject()

        file = str(TEST_DATA_PATH / 'points.gpkg')
        layer1 = QgsVectorLayer(file, 'layer1')
        layer2 = QgsVectorLayer(file, 'layer2')
        layer3 = QgsVectorLayer(file, 'layer3')
        layer4 = QgsVectorLayer(file, 'layer4')

        project.addMapLayer(layer1, addToLegend=False)
        project.addMapLayer(layer2, addToLegend=False)
        project.addMapLayer(layer3, addToLegend=False)
        project.addMapLayer(layer4, addToLegend=False)

        transport_group: QgsLayerTreeGroup = (
            project.layerTreeRoot().addGroup('Transport'))
        transport_group.addLayer(layer1)
        lines_group = transport_group.addGroup('Lines')
        lines_group.addLayer(layer2)

        environment_group = project.layerTreeRoot().addGroup('Environment')
        environment_group.addLayer(layer3)

        project.layerTreeRoot().addLayer(layer4)

        # group names should be top level groups, if set
        details1 = MapUploaderTask.layer_and_group(project, layer1)
        self.assertEqual(details1.layer.name(), 'layer1')
        self.assertEqual(details1.destination_group_name, 'Transport')
        details2 = MapUploaderTask.layer_and_group(project, layer2)
        self.assertEqual(details2.layer.name(), 'layer2')
        # this must be the top level group name, not "Lines"
        self.assertEqual(details2.destination_group_name, 'Transport')
        details3 = MapUploaderTask.layer_and_group(project, layer3)
        self.assertEqual(details3.layer.name(), 'layer3')
        self.assertEqual(details3.destination_group_name, 'Environment')
        details4 = MapUploaderTask.layer_and_group(project, layer4)
        self.assertEqual(details4.layer.name(), 'layer4')
        self.assertIsNone(details4.destination_group_name)


if __name__ == "__main__":
    suite = unittest.makeSuite(MapUploaderTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
