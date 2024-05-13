"""
GUI Utils Test.
"""

import unittest
from ..gui.gui_utils import GuiUtils
from .utilities import get_qgis_app

QGIS_APP = get_qgis_app()


class GuiUtilsTest(unittest.TestCase):
    """Test GuiUtils work."""

    def testGetIcon(self):
        """
        Tests get_icon
        """
        self.assertFalse(
            GuiUtils.get_icon('icon.svg').isNull())
        self.assertTrue(GuiUtils.get_icon('not_an_icon.svg').isNull())

    def testGetIconSvg(self):
        """
        Tests get_icon svg path
        """
        self.assertTrue(
            GuiUtils.get_icon_svg('icon.svg'))
        self.assertIn('icon.svg',
                      GuiUtils.get_icon_svg('icon.svg'))
        self.assertFalse(GuiUtils.get_icon_svg('not_an_icon.svg'))

    def testGetUiFilePath(self):
        """
        Tests get_ui_file_path svg path
        """
        self.assertTrue(
            GuiUtils.get_ui_file_path('authorize.ui'))
        self.assertIn('authorize.ui',
                      GuiUtils.get_ui_file_path('authorize.ui'))
        self.assertFalse(GuiUtils.get_ui_file_path('not_a_form.ui'))


if __name__ == "__main__":
    suite = unittest.makeSuite(GuiUtilsTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
