"""
FSL Conversion tests
"""

import unittest
from pathlib import Path

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor

from qgis.core import (
    QgsSimpleLineSymbolLayer,
    QgsSimpleFillSymbolLayer,
    QgsUnitTypes,
    QgsLineSymbol,
    QgsShapeburstFillSymbolLayer
)

from .utilities import get_qgis_app
from ..core import (
    FslConverter,
    ConversionContext,
)

QGIS_APP = get_qgis_app()

TEST_DATA_PATH = Path(__file__).parent


class FslConversionTest(unittest.TestCase):
    """Test FSL conversion."""

    # pylint: disable=protected-access

    def test_color_conversion(self):
        """
        Test color conversion
        """
        conversion_context = ConversionContext()
        self.assertIsNone(
            FslConverter.color_to_fsl(
                QColor(), conversion_context
            )
        )
        self.assertIsNone(
            FslConverter.color_to_fsl(
                QColor(), conversion_context, opacity=0.5
            )
        )
        self.assertEqual(
            FslConverter.color_to_fsl(
                QColor(191, 105, 162), conversion_context, opacity=1
            ),
            'rgb(191, 105, 162)'
        )
        self.assertEqual(
            FslConverter.color_to_fsl(
                QColor(191, 105, 162, 100), conversion_context, opacity=1
            ),
            'rgba(191, 105, 162, 0.39)'
        )
        self.assertEqual(
            FslConverter.color_to_fsl(
                QColor(191, 105, 162), conversion_context, opacity=0.2
            ),
            'rgba(191, 105, 162, 0.2)'
        )
        self.assertEqual(
            FslConverter.color_to_fsl(
                QColor(191, 105, 162, 100), conversion_context, opacity=0.2
            ),
            'rgba(191, 105, 162, 0.08)'
        )

    def test_size_conversion(self):
        """
        Test size conversion
        """
        conversion_context = ConversionContext()
        conversion_context.render_context.setScaleFactor(3.779)

        self.assertEqual(FslConverter.convert_to_pixels(
            50, QgsUnitTypes.RenderPixels, conversion_context
        ), 50)
        self.assertEqual(FslConverter.convert_to_pixels(
            50, QgsUnitTypes.RenderMillimeters, conversion_context
        ), 188.95)

    def test_symbol_conversion(self):
        """
        Test symbol  conversion
        """
        conversion_context = ConversionContext()

        line = QgsSimpleLineSymbolLayer(color=QColor(255, 0, 0))
        symbol = QgsLineSymbol()
        symbol.changeSymbolLayer(0, line)
        symbol.setOpacity(0.5)
        self.assertEqual(
            FslConverter.symbol_to_fsl(symbol, conversion_context),
            [{'color': 'rgb(255, 0, 0)',
              'lineCap': 'square',
              'lineJoin': 'bevel',
              'opacity': 0.5,
              'size': 0.98254}]
        )

    def test_simple_line_to_fsl(self):
        """
        Test simple line conversion
        """
        conversion_context = ConversionContext()

        line = QgsSimpleLineSymbolLayer(color=QColor(255, 0, 0))

        # no pen
        line.setPenStyle(Qt.NoPen)
        self.assertFalse(
            FslConverter.simple_line_to_fsl(line, conversion_context)
        )

        # transparent color
        line.setPenStyle(Qt.SolidLine)
        line.setColor(QColor(0, 255, 0, 0))
        self.assertFalse(
            FslConverter.simple_line_to_fsl(line, conversion_context)
        )

        line.setColor(QColor(0, 255, 0))
        line.setWidth(3)
        self.assertEqual(
            FslConverter.simple_line_to_fsl(line, conversion_context),
            [{
                'color': 'rgb(0, 255, 0)',
                'size': 11.337,
                'lineCap': 'square',
                'lineJoin': 'bevel',
            }]
        )

        line.setWidthUnit(QgsUnitTypes.RenderPixels)
        self.assertEqual(
            FslConverter.simple_line_to_fsl(line, conversion_context),
            [{
                'color': 'rgb(0, 255, 0)',
                'size': 3,
                'lineCap': 'square',
                'lineJoin': 'bevel',
            }]
        )

        line.setPenCapStyle(Qt.FlatCap)
        self.assertEqual(
            FslConverter.simple_line_to_fsl(line, conversion_context),
            [{
                'color': 'rgb(0, 255, 0)',
                'size': 3,
                'lineCap': 'butt',
                'lineJoin': 'bevel',
            }]
        )

        line.setPenCapStyle(Qt.RoundCap)
        self.assertEqual(
            FslConverter.simple_line_to_fsl(line, conversion_context),
            [{
                'color': 'rgb(0, 255, 0)',
                'size': 3,
                'lineCap': 'round',
                'lineJoin': 'bevel',
            }]
        )

        line.setPenJoinStyle(Qt.RoundJoin)
        self.assertEqual(
            FslConverter.simple_line_to_fsl(line, conversion_context),
            [{
                'color': 'rgb(0, 255, 0)',
                'size': 3,
                'lineCap': 'round',
                'lineJoin': 'round',
            }]
        )

        line.setPenJoinStyle(Qt.MiterJoin)
        self.assertEqual(
            FslConverter.simple_line_to_fsl(line, conversion_context),
            [{
                'color': 'rgb(0, 255, 0)',
                'size': 3,
                'lineCap': 'round',
                'lineJoin': 'miter',
            }]
        )

        line.setPenJoinStyle(Qt.MiterJoin)
        self.assertEqual(
            FslConverter.simple_line_to_fsl(line, conversion_context, symbol_opacity=0.5),
            [{
                'color': 'rgb(0, 255, 0)',
                'size': 3,
                'lineCap': 'round',
                'lineJoin': 'miter',
                'opacity': 0.5,
            }]
        )

        line.setPenStyle(Qt.DashLine)
        self.assertEqual(
            FslConverter.simple_line_to_fsl(line, conversion_context),
            [{
                'color': 'rgb(0, 255, 0)',
                'size': 3,
                'lineCap': 'round',
                'lineJoin': 'miter',
                'dashArray': [2.5, 2],
            }]
        )

        line.setPenStyle(Qt.DotLine)
        self.assertEqual(
            FslConverter.simple_line_to_fsl(line, conversion_context),
            [{
                'color': 'rgb(0, 255, 0)',
                'size': 3,
                'lineCap': 'round',
                'lineJoin': 'miter',
                'dashArray': [0.5, 1.3],
            }]
        )

        line.setPenStyle(Qt.DashDotLine)
        self.assertEqual(
            FslConverter.simple_line_to_fsl(line, conversion_context),
            [{
                'color': 'rgb(0, 255, 0)',
                'size': 3,
                'lineCap': 'round',
                'lineJoin': 'miter',
                'dashArray': [0.5, 1.3, 2.5, 1.3],
            }]
        )

        line.setPenStyle(Qt.DashDotDotLine)
        self.assertEqual(
            FslConverter.simple_line_to_fsl(line, conversion_context),
            [{
                'color': 'rgb(0, 255, 0)',
                'size': 3,
                'lineCap': 'round',
                'lineJoin': 'miter',
                'dashArray': [0.5, 1.3, 0.5, 1.3, 2.5, 1.3],
            }]
        )

        line.setPenStyle(Qt.SolidLine)
        line.setUseCustomDashPattern(True)
        line.setCustomDashPatternUnit(QgsUnitTypes.RenderPixels)
        line.setCustomDashVector([0.5, 1, 1.5, 2])
        self.assertEqual(
            FslConverter.simple_line_to_fsl(line, conversion_context),
            [{'color': 'rgb(0, 255, 0)',
              'dashArray': [0.5, 1.0, 1.5, 2.0],
              'lineCap': 'round',
              'lineJoin': 'miter',
              'size': 3.0}]
        )
        line.setCustomDashPatternUnit(QgsUnitTypes.RenderMillimeters)
        self.assertEqual(
            FslConverter.simple_line_to_fsl(line, conversion_context),
            [{'color': 'rgb(0, 255, 0)',
              'dashArray': [1.8895, 3.779, 5.6685, 7.558],
              'lineCap': 'round',
              'lineJoin': 'miter',
              'size': 3.0}]
        )

    def test_simple_fill_to_fsl(self):
        """
        Test simple fill conversion
        """
        conversion_context = ConversionContext()

        fill = QgsSimpleFillSymbolLayer(color=QColor(255, 0, 0))

        # no brush
        fill.setBrushStyle(Qt.NoBrush)
        self.assertFalse(
            FslConverter.simple_fill_to_fsl(fill, conversion_context)
        )

        # transparent color
        fill.setBrushStyle(Qt.SolidPattern)
        fill.setColor(QColor(0, 255, 0, 0))
        self.assertFalse(
            FslConverter.simple_fill_to_fsl(fill, conversion_context)
        )

        fill.setColor(QColor(0, 255, 0))
        fill.setStrokeWidth(3)
        self.assertEqual(
            FslConverter.simple_fill_to_fsl(fill, conversion_context),
            [{'color': 'rgb(0, 255, 0)',
              'lineJoin': 'bevel',
              'strokeColor': 'rgb(35, 35, 35)',
              'strokeWidth': 11.337}]
        )

        fill.setStrokeWidthUnit(QgsUnitTypes.RenderPixels)
        self.assertEqual(
            FslConverter.simple_fill_to_fsl(fill, conversion_context),
            [{'color': 'rgb(0, 255, 0)',
              'lineJoin': 'bevel',
              'strokeColor': 'rgb(35, 35, 35)',
              'strokeWidth': 3.0}]
        )

        fill.setPenJoinStyle(Qt.RoundJoin)
        self.assertEqual(
            FslConverter.simple_fill_to_fsl(fill, conversion_context),
            [{'color': 'rgb(0, 255, 0)',
              'lineJoin': 'round',
              'strokeColor': 'rgb(35, 35, 35)',
              'strokeWidth': 3.0}]
        )

        fill.setPenJoinStyle(Qt.MiterJoin)
        self.assertEqual(
            FslConverter.simple_fill_to_fsl(fill, conversion_context),
            [{'color': 'rgb(0, 255, 0)',
              'lineJoin': 'miter',
              'strokeColor': 'rgb(35, 35, 35)',
              'strokeWidth': 3.0}]
        )

        fill.setPenJoinStyle(Qt.MiterJoin)
        self.assertEqual(
            FslConverter.simple_fill_to_fsl(fill, conversion_context, symbol_opacity=0.5),
            [{'color': 'rgb(0, 255, 0)',
              'lineJoin': 'miter',
              'opacity': 0.5,
              'strokeColor': 'rgb(35, 35, 35)',
              'strokeWidth': 3.0}]
        )

        fill.setStrokeStyle(Qt.DashLine)
        self.assertEqual(
            FslConverter.simple_fill_to_fsl(fill, conversion_context),
            [{'color': 'rgb(0, 255, 0)',
              'dashArray': [2.5, 2],
              'lineJoin': 'miter',
              'strokeColor': 'rgb(35, 35, 35)',
              'strokeWidth': 3.0}]
        )
        self.assertEqual(
            FslConverter.simple_fill_to_fsl(fill, conversion_context, symbol_opacity=0.5),
            [{'color': 'rgb(0, 255, 0)',
              'dashArray': [2.5, 2],
              'lineJoin': 'miter',
              'strokeColor': 'rgb(35, 35, 35)',
              'opacity': 0.5,
              'strokeWidth': 3.0}]
        )

    def test_shapeburst_fill_to_fsl(self):
        """
        Test shapeburst fill conversion
        """
        conversion_context = ConversionContext()

        fill = QgsShapeburstFillSymbolLayer(color=QColor(),
                                            color2=QColor())

        # no color
        self.assertFalse(
            FslConverter.shapeburst_fill_to_fsl(fill, conversion_context)
        )
        fill.setColor(QColor(0, 255, 0, 0))
        self.assertFalse(
            FslConverter.shapeburst_fill_to_fsl(fill, conversion_context)
        )

        fill.setColor(QColor(0, 255, 0))
        self.assertEqual(
            FslConverter.shapeburst_fill_to_fsl(fill, conversion_context),
            [{'color': 'rgb(0, 255, 0)', 'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )

        fill.setColor(QColor(0, 255, 0, 0))
        fill.setColor2(QColor(255, 255, 0, 0))
        self.assertFalse(
            FslConverter.shapeburst_fill_to_fsl(fill, conversion_context)
        )

        fill.setColor2(QColor(255, 255, 0))
        self.assertEqual(
            FslConverter.shapeburst_fill_to_fsl(fill, conversion_context),
            [{'color': 'rgb(255, 255, 0)', 'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )

        self.assertEqual(
            FslConverter.shapeburst_fill_to_fsl(fill, conversion_context, symbol_opacity=0.5),
            [{'color': 'rgb(255, 255, 0)',
              'opacity': 0.5,
              'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )


if __name__ == "__main__":
    suite = unittest.makeSuite(FslConversionTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
