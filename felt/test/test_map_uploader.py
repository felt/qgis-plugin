"""
Map Exporter Test.
"""

import unittest
import os
from tempfile import TemporaryDirectory

from qgis.PyQt.QtCore import QDate
from qgis.core import (
    QgsProject
)

from .utilities import get_qgis_app
from ..core.map_uploader import MapUploaderTask

QGIS_APP = get_qgis_app()


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


if __name__ == "__main__":
    suite = unittest.makeSuite(MapUploaderTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
