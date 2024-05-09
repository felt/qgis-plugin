"""
FSL Conversion tests
"""

import unittest
from pathlib import Path

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import (
    QColor,
    QFont
)

from qgis.core import (
    NULL,
    Qgis,
    QgsSimpleLineSymbolLayer,
    QgsSimpleFillSymbolLayer,
    QgsUnitTypes,
    QgsLineSymbol,
    QgsFillSymbol,
    QgsShapeburstFillSymbolLayer,
    QgsGradientFillSymbolLayer,
    QgsLinePatternFillSymbolLayer,
    QgsSVGFillSymbolLayer,
    QgsSimpleMarkerSymbolLayer,
    QgsEllipseSymbolLayer,
    QgsSvgMarkerSymbolLayer,
    QgsFontMarkerSymbolLayer,
    QgsFilledMarkerSymbolLayer,
    QgsMarkerSymbol,
    QgsPointPatternFillSymbolLayer,
    QgsCentroidFillSymbolLayer,
    QgsRandomMarkerFillSymbolLayer,
    QgsMarkerLineSymbolLayer,
    QgsHashedLineSymbolLayer,
    QgsArrowSymbolLayer,
    QgsNullSymbolRenderer,
    QgsSingleSymbolRenderer,
    QgsCategorizedSymbolRenderer,
    QgsRendererCategory,
    QgsGraduatedSymbolRenderer,
    QgsRendererRange,
    QgsTextFormat,
    QgsStringUtils,
    QgsPalLayerSettings
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
        ), 189)

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
              'size': 1}]
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
                'size': 11,
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
            FslConverter.simple_line_to_fsl(line, conversion_context,
                                            symbol_opacity=0.5),
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
        line.setUseCustomDashPattern(False)

        # hairline
        line.setWidth(0)
        self.assertEqual(
            FslConverter.simple_line_to_fsl(line, conversion_context),
            [{
                'color': 'rgb(0, 255, 0)',
                'size': 1,
                'lineCap': 'round',
                'lineJoin': 'miter',
            }]
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
              'strokeWidth': 11}]
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
            FslConverter.simple_fill_to_fsl(fill, conversion_context,
                                            symbol_opacity=0.5),
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
            FslConverter.simple_fill_to_fsl(fill, conversion_context,
                                            symbol_opacity=0.5),
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
            FslConverter.shapeburst_fill_to_fsl(fill, conversion_context,
                                                symbol_opacity=0.5),
            [{'color': 'rgb(255, 255, 0)',
              'opacity': 0.5,
              'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )

    def test_gradient_fill_to_fsl(self):
        """
        Test gradient fill conversion
        """
        conversion_context = ConversionContext()

        fill = QgsGradientFillSymbolLayer(color=QColor(),
                                          color2=QColor())

        # no color
        self.assertFalse(
            FslConverter.gradient_fill_to_fsl(fill, conversion_context)
        )
        fill.setColor(QColor(0, 255, 0, 0))
        self.assertFalse(
            FslConverter.gradient_fill_to_fsl(fill, conversion_context)
        )

        fill.setColor(QColor(0, 255, 0))
        self.assertEqual(
            FslConverter.gradient_fill_to_fsl(fill, conversion_context),
            [{'color': 'rgb(0, 255, 0)', 'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )

        fill.setColor(QColor(0, 255, 0, 0))
        fill.setColor2(QColor(255, 255, 0, 0))
        self.assertFalse(
            FslConverter.gradient_fill_to_fsl(fill, conversion_context)
        )

        fill.setColor2(QColor(255, 255, 0))
        self.assertEqual(
            FslConverter.gradient_fill_to_fsl(fill, conversion_context),
            [{'color': 'rgb(255, 255, 0)', 'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )

        self.assertEqual(
            FslConverter.gradient_fill_to_fsl(fill, conversion_context,
                                              symbol_opacity=0.5),
            [{'color': 'rgb(255, 255, 0)',
              'opacity': 0.5,
              'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )

    def test_line_pattern_fill_to_fsl(self):
        """
        Test line pattern fill conversion
        """
        conversion_context = ConversionContext()

        fill = QgsLinePatternFillSymbolLayer()
        # invisible line
        line = QgsLineSymbol()
        simple_line = QgsSimpleLineSymbolLayer()
        simple_line.setPenStyle(Qt.NoPen)
        line.changeSymbolLayer(0, simple_line.clone())
        fill.setSubSymbol(line.clone())
        self.assertFalse(
            FslConverter.line_pattern_fill_to_fsl(fill, conversion_context)
        )

        # invisible line color
        simple_line = QgsSimpleLineSymbolLayer()
        simple_line.setColor(QColor(255, 0, 0, 0))
        line.changeSymbolLayer(0, simple_line.clone())
        fill.setSubSymbol(line.clone())
        self.assertFalse(
            FslConverter.line_pattern_fill_to_fsl(fill, conversion_context)
        )

        # line with color
        simple_line.setColor(QColor(255, 0, 255))
        line.changeSymbolLayer(0, simple_line.clone())
        fill.setSubSymbol(line.clone())
        self.assertEqual(
            FslConverter.line_pattern_fill_to_fsl(fill, conversion_context),
            [{'color': 'rgb(255, 0, 255)', 'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )

        self.assertEqual(
            FslConverter.line_pattern_fill_to_fsl(fill, conversion_context,
                                                  symbol_opacity=0.5),
            [{'color': 'rgb(255, 0, 255)',
              'opacity': 0.5,
              'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )

    def test_svg_fill_to_fsl(self):
        """
        Test SVG fill conversion
        """
        conversion_context = ConversionContext()

        fill = QgsSVGFillSymbolLayer('my.svg')
        # invisible fill
        fill.setSvgFillColor(QColor(255, 0, 0, 0))
        self.assertFalse(
            FslConverter.svg_fill_to_fsl(fill, conversion_context)
        )

        # with color
        fill.setSvgFillColor(QColor(255, 0, 255))
        self.assertEqual(
            FslConverter.svg_fill_to_fsl(fill, conversion_context),
            [{'color': 'rgb(255, 0, 255)', 'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )

        self.assertEqual(
            FslConverter.svg_fill_to_fsl(fill, conversion_context,
                                         symbol_opacity=0.5),
            [{'color': 'rgb(255, 0, 255)',
              'opacity': 0.5,
              'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )

    def test_simple_marker_to_fsl(self):
        """
        Test simple marker conversion
        """
        conversion_context = ConversionContext()

        marker = QgsSimpleMarkerSymbolLayer()
        # invisible fills and strokes
        marker.setColor(QColor(255, 0, 0, 0))
        marker.setStrokeColor(QColor(255, 0, 0, 0))
        self.assertFalse(
            FslConverter.simple_marker_to_fsl(marker, conversion_context)
        )

        marker.setStrokeColor(QColor(255, 0, 255))
        marker.setStrokeStyle(Qt.NoPen)
        self.assertFalse(
            FslConverter.simple_marker_to_fsl(marker, conversion_context)
        )

        # with fill, no stroke
        marker.setSize(5)
        marker.setColor(QColor(120, 130, 140))

        self.assertEqual(
            FslConverter.simple_marker_to_fsl(marker, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'size': 19,
              'strokeColor': 'rgba(0, 0, 0, 0)',
              'strokeWidth': 1}]
        )

        self.assertEqual(
            FslConverter.simple_marker_to_fsl(marker, conversion_context,
                                              symbol_opacity=0.5),
            [{'color': 'rgb(120, 130, 140)',
              'size': 19,
              'opacity': 0.5,
              'strokeColor': 'rgba(0, 0, 0, 0)',
              'strokeWidth': 1}]
        )

        # with stroke
        marker.setStrokeStyle(Qt.SolidLine)
        marker.setStrokeColor(QColor(255, 100, 0))
        marker.setStrokeWidth(2)
        marker.setStrokeWidthUnit(QgsUnitTypes.RenderPoints)
        self.assertEqual(
            FslConverter.simple_marker_to_fsl(marker, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'size': 19,
              'strokeColor': 'rgb(255, 100, 0)',
              'strokeWidth': 3}]
        )

        # size unit
        marker.setSizeUnit(QgsUnitTypes.RenderInches)
        marker.setSize(0.5)
        self.assertEqual(
            FslConverter.simple_marker_to_fsl(marker, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'size': 48,
              'strokeColor': 'rgb(255, 100, 0)',
              'strokeWidth': 3}]
        )

    def test_ellipse_marker_to_fsl(self):
        """
        Test ellipse marker conversion
        """
        conversion_context = ConversionContext()

        marker = QgsEllipseSymbolLayer()
        # invisible fills and strokes
        marker.setColor(QColor(255, 0, 0, 0))
        marker.setStrokeColor(QColor(255, 0, 0, 0))
        self.assertFalse(
            FslConverter.ellipse_marker_to_fsl(marker, conversion_context)
        )

        marker.setStrokeColor(QColor(255, 0, 255))
        marker.setStrokeStyle(Qt.NoPen)
        self.assertFalse(
            FslConverter.ellipse_marker_to_fsl(marker, conversion_context)
        )

        # with fill, no stroke
        marker.setSize(5)
        marker.setColor(QColor(120, 130, 140))

        self.assertEqual(
            FslConverter.ellipse_marker_to_fsl(marker, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'size': 19,
              'strokeColor': 'rgba(0, 0, 0, 0)',
              'strokeWidth': 1}]
        )

        self.assertEqual(
            FslConverter.ellipse_marker_to_fsl(marker, conversion_context,
                                               symbol_opacity=0.5),
            [{'color': 'rgb(120, 130, 140)',
              'size': 19,
              'opacity': 0.5,
              'strokeColor': 'rgba(0, 0, 0, 0)',
              'strokeWidth': 1}]
        )

        # with stroke
        marker.setStrokeStyle(Qt.SolidLine)
        marker.setStrokeColor(QColor(255, 100, 0))
        marker.setStrokeWidth(2)
        marker.setStrokeWidthUnit(QgsUnitTypes.RenderPoints)
        self.assertEqual(
            FslConverter.ellipse_marker_to_fsl(marker, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'size': 19,
              'strokeColor': 'rgb(255, 100, 0)',
              'strokeWidth': 3}]
        )

        # size unit
        marker.setSymbolWidthUnit(QgsUnitTypes.RenderInches)
        marker.setSymbolWidth(0.5)
        marker.setSymbolHeightUnit(QgsUnitTypes.RenderPoints)
        marker.setSymbolHeight(1.5)
        self.assertEqual(
            FslConverter.ellipse_marker_to_fsl(marker, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'size': 48,
              'strokeColor': 'rgb(255, 100, 0)',
              'strokeWidth': 3}]
        )

        marker.setSymbolHeight(51.5)
        self.assertEqual(
            FslConverter.ellipse_marker_to_fsl(marker, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'size': 69,
              'strokeColor': 'rgb(255, 100, 0)',
              'strokeWidth': 3}]
        )

    def test_svg_marker_to_fsl(self):
        """
        Test SVG marker conversion
        """
        conversion_context = ConversionContext()

        marker = QgsSvgMarkerSymbolLayer('my.svg')
        # invisible fills and strokes
        marker.setColor(QColor(255, 0, 0, 0))
        marker.setStrokeColor(QColor(255, 0, 0, 0))
        self.assertFalse(
            FslConverter.svg_marker_to_fsl(marker, conversion_context)
        )

        # with fill, no stroke
        marker.setSize(5)
        marker.setColor(QColor(120, 130, 140))

        self.assertEqual(
            FslConverter.svg_marker_to_fsl(marker, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'size': 19,
              'strokeColor': 'rgba(0, 0, 0, 0)',
              'strokeWidth': 1.0}]
        )

        self.assertEqual(
            FslConverter.svg_marker_to_fsl(marker, conversion_context,
                                           symbol_opacity=0.5),
            [{'color': 'rgb(120, 130, 140)',
              'size': 19,
              'opacity': 0.5,
              'strokeColor': 'rgba(0, 0, 0, 0)',
              'strokeWidth': 1.0}]
        )

        # with stroke
        marker.setStrokeColor(QColor(255, 100, 0))
        marker.setStrokeWidth(2)
        marker.setStrokeWidthUnit(QgsUnitTypes.RenderPoints)
        self.assertEqual(
            FslConverter.svg_marker_to_fsl(marker, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'size': 19,
              'strokeColor': 'rgb(255, 100, 0)',
              'strokeWidth': 3}]
        )

        # size unit
        marker.setSizeUnit(QgsUnitTypes.RenderInches)
        marker.setSize(0.5)
        self.assertEqual(
            FslConverter.svg_marker_to_fsl(marker, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'size': 48,
              'strokeColor': 'rgb(255, 100, 0)',
              'strokeWidth': 3}]
        )

    def test_font_marker_to_fsl(self):
        """
        Test font marker conversion
        """
        conversion_context = ConversionContext()

        marker = QgsFontMarkerSymbolLayer('my font', 'A')
        # invisible fills and strokes
        marker.setColor(QColor(255, 0, 0, 0))
        marker.setStrokeColor(QColor(255, 0, 0, 0))
        self.assertFalse(
            FslConverter.font_marker_to_fsl(marker, conversion_context)
        )

        # with fill, no stroke
        marker.setSize(5)
        marker.setColor(QColor(120, 130, 140))

        self.assertEqual(
            FslConverter.font_marker_to_fsl(marker, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'size': 19,
              'strokeColor': 'rgba(0, 0, 0, 0)',
              'strokeWidth': 1}]
        )

        self.assertEqual(
            FslConverter.font_marker_to_fsl(marker, conversion_context,
                                            symbol_opacity=0.5),
            [{'color': 'rgb(120, 130, 140)',
              'size': 19,
              'opacity': 0.5,
              'strokeColor': 'rgba(0, 0, 0, 0)',
              'strokeWidth': 1}]
        )

        # with stroke
        marker.setStrokeColor(QColor(255, 100, 0))
        marker.setStrokeWidth(2)
        marker.setStrokeWidthUnit(QgsUnitTypes.RenderPoints)
        self.assertEqual(
            FslConverter.font_marker_to_fsl(marker, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'size': 19,
              'strokeColor': 'rgb(255, 100, 0)',
              'strokeWidth': 3}]
        )

        # size unit
        marker.setSizeUnit(QgsUnitTypes.RenderInches)
        marker.setSize(0.5)
        self.assertEqual(
            FslConverter.font_marker_to_fsl(marker, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'size': 48,
              'strokeColor': 'rgb(255, 100, 0)',
              'strokeWidth': 3}]
        )

    def test_filled_marker(self):
        """
        Test filled marker conversion
        """
        conversion_context = ConversionContext()

        fill_symbol = QgsFillSymbol()
        fill = QgsSimpleFillSymbolLayer(color=QColor(255, 0, 0))

        # no brush
        fill.setBrushStyle(Qt.NoBrush)
        fill_symbol.changeSymbolLayer(0, fill.clone())
        marker = QgsFilledMarkerSymbolLayer()
        marker.setSubSymbol(fill_symbol.clone())
        self.assertFalse(
            FslConverter.filled_marker_to_fsl(marker, conversion_context)
        )

        # transparent color
        fill.setBrushStyle(Qt.SolidPattern)
        fill.setColor(QColor(0, 255, 0, 0))
        fill_symbol.changeSymbolLayer(0, fill.clone())
        marker.setSubSymbol(fill_symbol.clone())
        self.assertFalse(
            FslConverter.filled_marker_to_fsl(marker, conversion_context)
        )

        fill.setColor(QColor(0, 255, 0))
        fill.setStrokeWidth(3)
        fill_symbol.changeSymbolLayer(0, fill.clone())
        marker.setSubSymbol(fill_symbol.clone())
        self.assertEqual(
            FslConverter.filled_marker_to_fsl(marker, conversion_context),
            [{'color': 'rgb(0, 255, 0)',
              'size': 8,
              'strokeColor': 'rgb(35, 35, 35)',
              'strokeWidth': 11}]
        )

        fill.setStrokeWidthUnit(QgsUnitTypes.RenderPixels)
        fill_symbol.changeSymbolLayer(0, fill.clone())
        marker.setSubSymbol(fill_symbol.clone())
        self.assertEqual(
            FslConverter.filled_marker_to_fsl(marker, conversion_context),
            [{'color': 'rgb(0, 255, 0)',
              'size': 8,
              'strokeColor': 'rgb(35, 35, 35)',
              'strokeWidth': 3.0}]
        )

        self.assertEqual(
            FslConverter.filled_marker_to_fsl(marker, conversion_context,
                                              symbol_opacity=0.5),
            [{'color': 'rgb(0, 255, 0)',
              'size': 8,
              'strokeColor': 'rgb(35, 35, 35)',
              'opacity': 0.5,
              'strokeWidth': 3.0}]
        )

        marker.setSize(3)
        marker.setSizeUnit(QgsUnitTypes.RenderPoints)
        self.assertEqual(
            FslConverter.filled_marker_to_fsl(marker, conversion_context),
            [{'color': 'rgb(0, 255, 0)',
              'size': 4,
              'strokeColor': 'rgb(35, 35, 35)',
              'strokeWidth': 3.0}]
        )

    def test_point_pattern_fill_to_fsl(self):
        """
        Test point pattern fill conversion
        """
        conversion_context = ConversionContext()

        marker = QgsSimpleMarkerSymbolLayer()
        # invisible fills and strokes
        marker.setColor(QColor(255, 0, 0, 0))
        marker.setStrokeColor(QColor(255, 0, 0, 0))

        marker_symbol = QgsMarkerSymbol()
        marker_symbol.changeSymbolLayer(0, marker.clone())
        fill = QgsPointPatternFillSymbolLayer()
        fill.setSubSymbol(marker_symbol.clone())

        self.assertFalse(
            FslConverter.point_pattern_fill_to_fsl(fill, conversion_context)
        )

        marker.setStrokeColor(QColor(255, 0, 255))
        marker.setStrokeStyle(Qt.NoPen)
        marker_symbol.changeSymbolLayer(0, marker.clone())
        fill.setSubSymbol(marker_symbol.clone())
        self.assertFalse(
            FslConverter.point_pattern_fill_to_fsl(fill, conversion_context)
        )

        # with fill, no stroke
        marker.setColor(QColor(120, 130, 140))
        marker_symbol.changeSymbolLayer(0, marker.clone())
        fill.setSubSymbol(marker_symbol.clone())

        self.assertEqual(
            FslConverter.point_pattern_fill_to_fsl(fill, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )

        self.assertEqual(
            FslConverter.point_pattern_fill_to_fsl(fill, conversion_context,
                                                   symbol_opacity=0.5),
            [{'color': 'rgb(120, 130, 140)',
              'opacity': 0.5, 'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )

    def test_centroid_fill_to_fsl(self):
        """
        Test centroid fill conversion
        """
        conversion_context = ConversionContext()

        marker = QgsSimpleMarkerSymbolLayer()
        # invisible fills and strokes
        marker.setColor(QColor(255, 0, 0, 0))
        marker.setStrokeColor(QColor(255, 0, 0, 0))

        marker_symbol = QgsMarkerSymbol()
        marker_symbol.changeSymbolLayer(0, marker.clone())
        fill = QgsCentroidFillSymbolLayer()
        fill.setSubSymbol(marker_symbol.clone())

        self.assertFalse(
            FslConverter.centroid_fill_to_fsl(fill, conversion_context)
        )

        marker.setStrokeColor(QColor(255, 0, 255))
        marker.setStrokeStyle(Qt.NoPen)
        marker_symbol.changeSymbolLayer(0, marker.clone())
        fill.setSubSymbol(marker_symbol.clone())
        self.assertFalse(
            FslConverter.centroid_fill_to_fsl(fill, conversion_context)
        )

        # with fill, no stroke
        marker.setColor(QColor(120, 130, 140))
        marker_symbol.changeSymbolLayer(0, marker.clone())
        fill.setSubSymbol(marker_symbol.clone())

        self.assertEqual(
            FslConverter.centroid_fill_to_fsl(fill, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )

        self.assertEqual(
            FslConverter.centroid_fill_to_fsl(fill, conversion_context,
                                              symbol_opacity=0.5),
            [{'color': 'rgb(120, 130, 140)',
              'opacity': 0.5, 'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )

    def test_random_marker_fill_to_fsl(self):
        """
        Test random marker fill conversion
        """
        conversion_context = ConversionContext()

        marker = QgsSimpleMarkerSymbolLayer()
        # invisible fills and strokes
        marker.setColor(QColor(255, 0, 0, 0))
        marker.setStrokeColor(QColor(255, 0, 0, 0))

        marker_symbol = QgsMarkerSymbol()
        marker_symbol.changeSymbolLayer(0, marker.clone())
        fill = QgsRandomMarkerFillSymbolLayer()
        fill.setSubSymbol(marker_symbol.clone())

        self.assertFalse(
            FslConverter.random_marker_fill_to_fsl(fill, conversion_context)
        )

        marker.setStrokeColor(QColor(255, 0, 255))
        marker.setStrokeStyle(Qt.NoPen)
        marker_symbol.changeSymbolLayer(0, marker.clone())
        fill.setSubSymbol(marker_symbol.clone())
        self.assertFalse(
            FslConverter.random_marker_fill_to_fsl(fill, conversion_context)
        )

        # with fill, no stroke
        marker.setColor(QColor(120, 130, 140))
        marker_symbol.changeSymbolLayer(0, marker.clone())
        fill.setSubSymbol(marker_symbol.clone())

        self.assertEqual(
            FslConverter.random_marker_fill_to_fsl(fill, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )

        self.assertEqual(
            FslConverter.random_marker_fill_to_fsl(fill, conversion_context,
                                                   symbol_opacity=0.5),
            [{'color': 'rgb(120, 130, 140)',
              'opacity': 0.5, 'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )

    def test_marker_line_to_fsl(self):
        """
        Test marker line conversion
        """
        conversion_context = ConversionContext()

        marker = QgsSimpleMarkerSymbolLayer()
        # invisible fills and strokes
        marker.setColor(QColor(255, 0, 0, 0))
        marker.setStrokeColor(QColor(255, 0, 0, 0))

        marker_symbol = QgsMarkerSymbol()
        marker_symbol.changeSymbolLayer(0, marker.clone())
        line = QgsMarkerLineSymbolLayer()
        line.setSubSymbol(marker_symbol.clone())
        line.setPlacement(QgsMarkerLineSymbolLayer.Vertex)

        self.assertFalse(
            FslConverter.marker_line_to_fsl(line, conversion_context)
        )

        marker.setStrokeColor(QColor(255, 0, 255))
        marker.setStrokeStyle(Qt.NoPen)
        marker_symbol.changeSymbolLayer(0, marker.clone())
        line.setSubSymbol(marker_symbol.clone())
        self.assertFalse(
            FslConverter.marker_line_to_fsl(line, conversion_context)
        )

        # with fill, no stroke
        marker.setColor(QColor(120, 130, 140))
        marker_symbol.changeSymbolLayer(0, marker.clone())
        line.setSubSymbol(marker_symbol.clone())

        self.assertEqual(
            FslConverter.marker_line_to_fsl(line, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'size': 2}]
        )

        self.assertEqual(
            FslConverter.marker_line_to_fsl(line, conversion_context,
                                            symbol_opacity=0.5),
            [{'color': 'rgb(120, 130, 140)',
              'size': 2,
              'opacity': 0.5}]
        )

        # interval mode
        line.setPlacement(QgsMarkerLineSymbolLayer.Interval)
        line.setInterval(10)
        line.setIntervalUnit(QgsUnitTypes.RenderPoints)
        self.assertEqual(
            FslConverter.marker_line_to_fsl(line, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'size': 8,
              'dashArray': [8.0, 5.0]
              }]
        )

    def test_hashed_line_to_fsl(self):
        """
        Test hashed line conversion
        """
        conversion_context = ConversionContext()

        hatch = QgsSimpleLineSymbolLayer()
        # invisible hatch
        hatch.setColor(QColor(255, 0, 0, 0))

        hatch_symbol = QgsLineSymbol()
        hatch_symbol.changeSymbolLayer(0, hatch.clone())
        line = QgsHashedLineSymbolLayer()
        line.setSubSymbol(hatch_symbol.clone())
        line.setPlacement(QgsHashedLineSymbolLayer.Vertex)

        self.assertFalse(
            FslConverter.hashed_line_to_fsl(line, conversion_context)
        )

        hatch.setColor(QColor(255, 0, 255))
        hatch.setPenStyle(Qt.NoPen)
        hatch_symbol.changeSymbolLayer(0, hatch.clone())
        line.setSubSymbol(hatch_symbol.clone())
        self.assertFalse(
            FslConverter.hashed_line_to_fsl(line, conversion_context)
        )

        # with hatch
        hatch.setColor(QColor(120, 130, 140))
        hatch.setPenStyle(Qt.SolidLine)
        hatch_symbol.changeSymbolLayer(0, hatch.clone())
        line.setSubSymbol(hatch_symbol.clone())

        self.assertEqual(
            FslConverter.hashed_line_to_fsl(line, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'size': 1}]
        )

        self.assertEqual(
            FslConverter.hashed_line_to_fsl(line, conversion_context,
                                            symbol_opacity=0.5),
            [{'color': 'rgb(120, 130, 140)',
              'size': 1,
              'opacity': 0.5}]
        )

        # interval mode
        hatch.setWidth(3)
        hatch_symbol.changeSymbolLayer(0, hatch.clone())
        line.setSubSymbol(hatch_symbol.clone())
        line.setPlacement(QgsHashedLineSymbolLayer.Interval)
        line.setInterval(10)
        line.setIntervalUnit(QgsUnitTypes.RenderPoints)
        self.assertEqual(
            FslConverter.hashed_line_to_fsl(line, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'size': 11,
              'dashArray': [11.0, 2.0]
              }]
        )

    def test_arrow_to_fsl(self):
        """
        Test arrow conversion
        """
        conversion_context = ConversionContext()

        fill = QgsSimpleFillSymbolLayer()
        # invisible fill
        fill.setColor(QColor(255, 0, 0, 0))
        fill.setStrokeStyle(Qt.NoPen)

        fill_symbol = QgsFillSymbol()
        fill_symbol.changeSymbolLayer(0, fill.clone())
        line = QgsArrowSymbolLayer()
        line.setSubSymbol(fill_symbol.clone())

        self.assertFalse(
            FslConverter.arrow_to_fsl(line, conversion_context)
        )

        # with fill
        fill.setColor(QColor(120, 130, 140))
        fill_symbol.changeSymbolLayer(0, fill.clone())
        line.setSubSymbol(fill_symbol.clone())

        line.setArrowWidth(5)
        line.setArrowWidthUnit(QgsUnitTypes.RenderPoints)
        line.setArrowStartWidth(0.3)
        line.setArrowStartWidthUnit(QgsUnitTypes.RenderInches)

        self.assertEqual(
            FslConverter.arrow_to_fsl(line, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'size': 18}]
        )

        self.assertEqual(
            FslConverter.arrow_to_fsl(line, conversion_context,
                                      symbol_opacity=0.5),
            [{'color': 'rgb(120, 130, 140)',
              'size': 18,
              'opacity': 0.5}]
        )

    def test_single_symbol_renderer(self):
        """
        Test converting single symbol renderers
        """
        conversion_context = ConversionContext()

        line = QgsSimpleLineSymbolLayer(color=QColor(255, 0, 0))
        line_symbol = QgsLineSymbol()
        line_symbol.changeSymbolLayer(0, line.clone())

        renderer = QgsSingleSymbolRenderer(line_symbol.clone())
        self.assertEqual(
            FslConverter.vector_renderer_to_fsl(renderer, conversion_context),
            {'legend': {},
             'style': {'color': 'rgb(255, 0, 0)',
                       'lineCap': 'square',
                       'lineJoin': 'bevel',
                       'size': 1},
             'type': 'simple'}
        )

        self.assertEqual(
            FslConverter.vector_renderer_to_fsl(renderer, conversion_context,
                                                layer_opacity=0.5),
            {'legend': {},
             'style': {'color': 'rgb(255, 0, 0)',
                       'lineCap': 'square',
                       'lineJoin': 'bevel',
                       'opacity': 0.5,
                       'size': 1},
             'type': 'simple'}
        )

        # with casing
        line_casing = QgsSimpleLineSymbolLayer(color=QColor(255, 255, 0))
        line_casing.setWidth(10)
        line_symbol.appendSymbolLayer(line_casing.clone())
        renderer.setSymbol(line_symbol.clone())
        self.assertEqual(
            FslConverter.vector_renderer_to_fsl(renderer, conversion_context),
            {'legend': {},
             'style': [{'color': 'rgb(255, 0, 0)',
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'size': 1},
                       {'color': 'rgb(255, 255, 0)',
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'size': 38}],
             'type': 'simple'}
        )

    def test_null_symbol_renderer(self):
        """
        Test converting null symbol renderers
        """
        conversion_context = ConversionContext()

        renderer = QgsNullSymbolRenderer()
        self.assertEqual(
            FslConverter.vector_renderer_to_fsl(renderer, conversion_context),
            {'legend': {},
             'style': {'color': 'rgba(0, 0, 0, 0)',
                       'strokeColor': 'rgba(0, 0, 0, 0)'},
             'type': 'simple'}
        )

    def test_categorized_renderer(self):
        """
        Test converting categorized renderers
        """
        conversion_context = ConversionContext()

        line = QgsSimpleLineSymbolLayer(color=QColor(255, 0, 0))
        line_symbol = QgsLineSymbol()
        line_symbol.changeSymbolLayer(0, line.clone())

        line.setColor(QColor(255, 255, 0))
        line.setWidth(5)
        line_symbol.appendSymbolLayer(line.clone())

        line_symbol2 = QgsLineSymbol()
        line.setColor(QColor(255, 0, 255))
        line.setWidth(6)
        line_symbol2.changeSymbolLayer(0, line.clone())

        line_symbol3 = QgsLineSymbol()
        line.setColor(QColor(0, 255, 255))
        line.setWidth(7)
        line_symbol3.changeSymbolLayer(0, line.clone())

        categories = [
            QgsRendererCategory(1, line_symbol.clone(), 'first cat'),
            QgsRendererCategory(2, line_symbol2.clone(), 'second cat'),
            QgsRendererCategory(3, line_symbol3.clone(), 'third cat'),
        ]

        renderer = QgsCategorizedSymbolRenderer('my_field',
                                                categories)
        self.assertEqual(
            FslConverter.vector_renderer_to_fsl(renderer, conversion_context),
            {'config': {'categories': ['1', '2', '3'],
                        'categoricalAttribute': 'my_field',
                        'showOther': False},
             'legend': {'displayName': {'1': 'first cat',
                                        '2': 'second cat',
                                        '3': 'third cat'}},
             'style': [{'color': ['rgb(255, 0, 0)', 'rgb(255, 0, 255)',
                                  'rgb(0, 255, 255)'],
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'size': [1, 23, 26]},
                       {'color': 'rgb(255, 255, 0)',
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'size': 19}],
             'type': 'categorical'}
        )

        self.assertEqual(
            FslConverter.vector_renderer_to_fsl(renderer, conversion_context,
                                                layer_opacity=0.5),
            {'config': {'categories': ['1', '2', '3'],
                        'categoricalAttribute': 'my_field',
                        'showOther': False},
             'legend': {'displayName': {'1': 'first cat',
                                        '2': 'second cat',
                                        '3': 'third cat'}},
             'style': [{'color': ['rgb(255, 0, 0)', 'rgb(255, 0, 255)',
                                  'rgb(0, 255, 255)'],
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'opacity': 0.5,
                        'size': [1, 23, 26]},
                       {'color': 'rgb(255, 255, 0)',
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'opacity': 0.5,
                        'size': 19}],
             'type': 'categorical'}
        )

        # with "all others"
        line.setColor(QColor(100, 100, 100))
        line.setWidth(3)
        line_symbol3.changeSymbolLayer(0, line.clone())
        categories.append(
            QgsRendererCategory(NULL, line_symbol3.clone(), 'all others'))
        renderer = QgsCategorizedSymbolRenderer('my_field',
                                                categories)
        self.assertEqual(
            FslConverter.vector_renderer_to_fsl(renderer, conversion_context),
            {'config': {'categories': ['1', '2', '3'],
                        'categoricalAttribute': 'my_field',
                        'showOther': True},
             'legend': {'displayName': {'1': 'first cat',
                                        '2': 'second cat',
                                        '3': 'third cat',
                                        'Other': 'all others'}},
             'style': [{'color': ['rgb(255, 0, 0)',
                                  'rgb(255, 0, 255)',
                                  'rgb(0, 255, 255)',
                                  'rgb(100, 100, 100)'],
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'size': [1, 23, 26, 11]},
                       {'color': 'rgb(255, 255, 0)',
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'size': 19}],
             'type': 'categorical'}
        )

    def test_graduated_renderer(self):
        """
        Test converting graduated renderers
        """
        conversion_context = ConversionContext()

        line = QgsSimpleLineSymbolLayer(color=QColor(255, 0, 0))
        line_symbol = QgsLineSymbol()
        line_symbol.changeSymbolLayer(0, line.clone())

        line.setColor(QColor(255, 255, 0))
        line.setWidth(5)
        line_symbol.appendSymbolLayer(line.clone())

        line_symbol2 = QgsLineSymbol()
        line.setColor(QColor(255, 0, 255))
        line.setWidth(6)
        line_symbol2.changeSymbolLayer(0, line.clone())

        line_symbol3 = QgsLineSymbol()
        line.setColor(QColor(0, 255, 255))
        line.setWidth(7)
        line_symbol3.changeSymbolLayer(0, line.clone())

        ranges = [
            QgsRendererRange(1, 2, line_symbol.clone(), 'first range'),
            QgsRendererRange(2, 3, line_symbol2.clone(), 'second range'),
            QgsRendererRange(3, 4, line_symbol3.clone(), 'third range'),
        ]

        renderer = QgsGraduatedSymbolRenderer('my_field',
                                              ranges)
        self.assertEqual(
            FslConverter.vector_renderer_to_fsl(renderer, conversion_context),
            {'config': {'numericAttribute': 'my_field',
                        'steps': [1.0, 2.0, 3.0, 4.0]},
             'legend': {'displayName': {'0': 'first range',
                                        '1': 'second range',
                                        '2': 'third range'}},
             'style': [{'color': ['rgb(255, 0, 0)', 'rgb(255, 0, 255)',
                                  'rgb(0, 255, 255)'],
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'size': [1, 23, 26]},
                       {'color': 'rgb(255, 255, 0)',
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'size': 19}],
             'type': 'numeric'}
        )

        self.assertEqual(
            FslConverter.vector_renderer_to_fsl(renderer, conversion_context,
                                                layer_opacity=0.5),
            {'config': {'numericAttribute': 'my_field',
                        'steps': [1.0, 2.0, 3.0, 4.0]},
             'legend': {'displayName': {'0': 'first range',
                                        '1': 'second range',
                                        '2': 'third range'}},
             'style': [{'color': ['rgb(255, 0, 0)', 'rgb(255, 0, 255)',
                                  'rgb(0, 255, 255)'],
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'opacity': 0.5,
                        'size': [1, 23, 26]},
                       {'color': 'rgb(255, 255, 0)',
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'opacity': 0.5,
                        'size': 19}],
             'type': 'numeric'}
        )

    @unittest.skipIf(Qgis.QGIS_VERSION_INT < 32400, 'QGIS too old')
    def test_text_format_conversion(self):
        """
        Test converting text formats
        """
        context = ConversionContext()

        f = QgsTextFormat()
        font = QFont('Arial')
        f.setFont(font)
        f.setSize(13)
        f.setSizeUnit(QgsUnitTypes.RenderPixels)
        f.setColor(QColor(255, 0, 0))
        f.setOpacity(0.3)

        self.assertEqual(
            FslConverter.text_format_to_fsl(f, context),
            {'color': 'rgba(255, 0, 0, 0.3)',
             'fontSize': 13,
             'fontStyle': 'normal',
             'fontWeight': 400,
             'haloColor': 'rgba(0, 0, 0, 0)',
             'haloWidth': 4,
             'letterSpacing': 0.0,
             'lineHeight': 1.0}
        )

        # with buffer
        f.buffer().setEnabled(True)
        f.buffer().setColor(QColor(0, 255, 0))
        f.buffer().setOpacity(0.7)
        f.buffer().setSize(4)
        self.assertEqual(
            FslConverter.text_format_to_fsl(f, context),
            {'color': 'rgba(255, 0, 0, 0.3)',
             'fontSize': 13,
             'fontStyle': 'normal',
             'fontWeight': 400,
             'haloColor': 'rgba(0, 255, 0, 0.7)',
             'haloWidth': 15,
             'letterSpacing': 0.0,
             'lineHeight': 1.0}
        )

        # bold
        f.buffer().setEnabled(False)
        font.setBold(True)
        f.setFont(font)
        self.assertEqual(
            FslConverter.text_format_to_fsl(f, context),
            {'color': 'rgba(255, 0, 0, 0.3)',
             'fontSize': 13,
             'fontStyle': 'normal',
             'fontWeight': 700,
             'haloColor': 'rgba(0, 0, 0, 0)',
             'haloWidth': 15,
             'letterSpacing': 0.0,
             'lineHeight': 1.0}
        )
        # italic
        font.setBold(False)
        font.setItalic(True)
        f.setFont(font)
        self.assertEqual(
            FslConverter.text_format_to_fsl(f, context),
            {'color': 'rgba(255, 0, 0, 0.3)',
             'fontSize': 13,
             'fontStyle': 'italic',
             'fontWeight': 400,
             'haloColor': 'rgba(0, 0, 0, 0)',
             'haloWidth': 15,
             'letterSpacing': 0.0,
             'lineHeight': 1.0}
        )

        font.setItalic(False)
        # letter spacing
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 5)
        f.setFont(font)
        self.assertEqual(
            FslConverter.text_format_to_fsl(f, context),
            {'color': 'rgba(255, 0, 0, 0.3)',
             'fontSize': 13,
             'fontStyle': 'normal',
             'fontWeight': 400,
             'haloColor': 'rgba(0, 0, 0, 0)',
             'haloWidth': 15,
             'letterSpacing': 0.54,
             'lineHeight': 1.0}
        )

        # line height relative
        font = QFont()
        f.setFont(font)
        f.setLineHeight(1.5)
        f.setLineHeightUnit(QgsUnitTypes.RenderPercentage)
        self.assertEqual(
            FslConverter.text_format_to_fsl(f, context),
            {'color': 'rgba(255, 0, 0, 0.3)',
             'fontSize': 13,
             'fontStyle': 'normal',
             'fontWeight': 400,
             'haloColor': 'rgba(0, 0, 0, 0)',
             'haloWidth': 15,
             'letterSpacing': 0.0,
             'lineHeight': 1.5}
        )
        # line height absolute
        f.setLineHeight(15)
        f.setLineHeightUnit(QgsUnitTypes.RenderMillimeters)
        self.assertEqual(
            FslConverter.text_format_to_fsl(f, context),
            {'color': 'rgba(255, 0, 0, 0.3)',
             'fontSize': 13,
             'fontStyle': 'normal',
             'fontWeight': 400,
             'haloColor': 'rgba(0, 0, 0, 0)',
             'haloWidth': 15,
             'letterSpacing': 0.0,
             'lineHeight': 4.38}
        )

        # uppercase
        f.setCapitalization(QgsStringUtils.AllUppercase)
        self.assertEqual(
            FslConverter.text_format_to_fsl(f, context),
            {'color': 'rgba(255, 0, 0, 0.3)',
             'fontSize': 13,
             'fontStyle': 'normal',
             'fontWeight': 400,
             'haloColor': 'rgba(0, 0, 0, 0)',
             'haloWidth': 15,
             'letterSpacing': 0.0,
             'lineHeight': 4.38,
             'textTransform': 'uppercase'}
        )

        # lowercase
        f.setCapitalization(QgsStringUtils.AllLowercase)
        self.assertEqual(
            FslConverter.text_format_to_fsl(f, context),
            {'color': 'rgba(255, 0, 0, 0.3)',
             'fontSize': 13,
             'fontStyle': 'normal',
             'fontWeight': 400,
             'haloColor': 'rgba(0, 0, 0, 0)',
             'haloWidth': 15,
             'letterSpacing': 0.0,
             'lineHeight': 4.38,
             'textTransform': 'lowercase'}
        )

    @unittest.skipIf(Qgis.QGIS_VERSION_INT < 32400, 'QGIS too old')
    def test_label_settings(self):
        """
        Test converting label settings
        """
        context = ConversionContext()

        f = QgsTextFormat()
        font = QFont('Arial')
        f.setFont(font)
        f.setSize(13)
        f.setSizeUnit(QgsUnitTypes.RenderPixels)
        f.setColor(QColor(255, 0, 0))
        f.setOpacity(0.3)

        label_settings = QgsPalLayerSettings()
        label_settings.setFormat(f)

        # no labels
        label_settings.drawLabels = False
        self.assertIsNone(
            FslConverter.label_settings_to_fsl(label_settings, context)
        )
        label_settings.drawLabels = True
        label_settings.fieldName = ''
        self.assertIsNone(
            FslConverter.label_settings_to_fsl(label_settings, context)
        )

        # expression labels, unsupported
        label_settings.fieldName = '1 + 2'
        label_settings.isExpression = True
        self.assertIsNone(
            FslConverter.label_settings_to_fsl(label_settings, context)
        )

        # simple field
        label_settings.fieldName = 'my_field'
        label_settings.isExpression = False
        self.assertEqual(
            FslConverter.label_settings_to_fsl(label_settings, context),
            {'config': {'labelAttribute': ['my_field']},
             'label': {'color': 'rgba(255, 0, 0, 0.3)',
                       'fontSize': 13,
                       'fontStyle': 'normal',
                       'fontWeight': 400,
                       'haloColor': 'rgba(0, 0, 0, 0)',
                       'haloWidth': 4,
                       'letterSpacing': 0.0,
                       'lineHeight': 1.0,
                       'maxZoom': 24,
                       'minZoom': 1}}
        )

        # with line wrap
        label_settings.autoWrapLength = 15
        self.assertEqual(
            FslConverter.label_settings_to_fsl(label_settings, context),
            {'config': {'labelAttribute': ['my_field']},
             'label': {'color': 'rgba(255, 0, 0, 0.3)',
                       'fontSize': 13,
                       'fontStyle': 'normal',
                       'fontWeight': 400,
                       'haloColor': 'rgba(0, 0, 0, 0)',
                       'haloWidth': 4,
                       'letterSpacing': 0.0,
                       'lineHeight': 1.0,
                       'maxLineChars': 15,
                       'maxZoom': 24,
                       'minZoom': 1}}
        )
        label_settings.autoWrapLength = 0

        # zoom ranges
        label_settings.scaleVisibility = True
        label_settings.minimumScale = 5677474
        label_settings.maximumScale = 34512
        self.assertEqual(
            FslConverter.label_settings_to_fsl(label_settings, context),
            {'config': {'labelAttribute': ['my_field']},
             'label': {'color': 'rgba(255, 0, 0, 0.3)',
                       'fontSize': 13,
                       'fontStyle': 'normal',
                       'fontWeight': 400,
                       'haloColor': 'rgba(0, 0, 0, 0)',
                       'haloWidth': 4,
                       'letterSpacing': 0.0,
                       'lineHeight': 1.0,
                       'maxZoom': 14,
                       'minZoom': 6}}
        )


if __name__ == "__main__":
    suite = unittest.makeSuite(FslConversionTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
