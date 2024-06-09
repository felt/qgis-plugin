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
    QgsPalLayerSettings,
    QgsVectorLayer,
    QgsRuleBasedRenderer,
    QgsSingleBandPseudoColorRenderer,
    QgsRasterShader,
    QgsColorRampShader,
    QgsGradientColorRamp,
    QgsPalettedRasterRenderer,
    QgsSingleBandGrayRenderer,
    QgsContrastEnhancement,
    QgsInvertedPolygonRenderer,
    QgsVectorLayerSimpleLabeling,
    QgsHeatmapRenderer
)

from .utilities import get_qgis_app
from ..core import (
    FslConverter,
    ConversionContext,
    LayerExporter
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
              'isClickable': False,
              'isHoverable': False,
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
                'isClickable': False,
                'isHoverable': False,
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
                'isClickable': False,
                'isHoverable': False,
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
                'isClickable': False,
                'isHoverable': False,
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
                'isClickable': False,
                'isHoverable': False,
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
                'isClickable': False,
                'isHoverable': False,
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
                'isClickable': False,
                'isHoverable': False,
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
                'isClickable': False,
                'isHoverable': False,
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
                'isClickable': False,
                'isHoverable': False,
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
                'isClickable': False,
                'isHoverable': False,
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
                'isClickable': False,
                'isHoverable': False,
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
                'isClickable': False,
                'isHoverable': False,
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
              'isClickable': False,
              'isHoverable': False,
              'size': 3.0}]
        )
        line.setCustomDashPatternUnit(QgsUnitTypes.RenderMillimeters)
        self.assertEqual(
            FslConverter.simple_line_to_fsl(line, conversion_context),
            [{'color': 'rgb(0, 255, 0)',
              'dashArray': [1.8895, 3.779, 5.6685, 7.558],
              'lineCap': 'round',
              'lineJoin': 'miter',
              'isClickable': False,
              'isHoverable': False,
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
                'isClickable': False,
                'isHoverable': False,
            }]
        )

    def test_simple_fill_to_fsl(self):
        """
        Test simple fill conversion
        """
        conversion_context = ConversionContext()

        fill = QgsSimpleFillSymbolLayer(color=QColor(255, 0, 0))

        fill.setStrokeStyle(Qt.NoPen)

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

        # transparent color with stroke
        fill.setStrokeStyle(Qt.DashLine)
        fill.setStrokeWidth(3)
        fill.setStrokeColor(QColor(255, 0, 0))
        self.assertEqual(
            FslConverter.simple_fill_to_fsl(fill, conversion_context),
            [{'color': 'rgb(0, 255, 0)',
              'dashArray': [2.5, 2],
              'lineJoin': 'bevel',
              'strokeColor': 'rgb(255, 0, 0)',
              'isClickable': False,
              'isHoverable': False,
              'strokeWidth': 11}]
        )
        fill.setStrokeStyle(Qt.SolidLine)
        fill.setStrokeColor(QColor(35, 35, 35))

        fill.setColor(QColor(0, 255, 0))
        fill.setStrokeWidth(3)
        self.assertEqual(
            FslConverter.simple_fill_to_fsl(fill, conversion_context),
            [{'color': 'rgb(0, 255, 0)',
              'lineJoin': 'bevel',
              'strokeColor': 'rgb(35, 35, 35)',
              'isClickable': False,
              'isHoverable': False,
              'strokeWidth': 11}]
        )

        fill.setStrokeWidthUnit(QgsUnitTypes.RenderPixels)
        self.assertEqual(
            FslConverter.simple_fill_to_fsl(fill, conversion_context),
            [{'color': 'rgb(0, 255, 0)',
              'lineJoin': 'bevel',
              'strokeColor': 'rgb(35, 35, 35)',
              'isClickable': False,
              'isHoverable': False,
              'strokeWidth': 3.0}]
        )

        fill.setPenJoinStyle(Qt.RoundJoin)
        self.assertEqual(
            FslConverter.simple_fill_to_fsl(fill, conversion_context),
            [{'color': 'rgb(0, 255, 0)',
              'lineJoin': 'round',
              'strokeColor': 'rgb(35, 35, 35)',
              'isClickable': False,
              'isHoverable': False,
              'strokeWidth': 3.0}]
        )

        fill.setPenJoinStyle(Qt.MiterJoin)
        self.assertEqual(
            FslConverter.simple_fill_to_fsl(fill, conversion_context),
            [{'color': 'rgb(0, 255, 0)',
              'lineJoin': 'miter',
              'strokeColor': 'rgb(35, 35, 35)',
              'isClickable': False,
              'isHoverable': False,
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
              'isClickable': False,
              'isHoverable': False,
              'strokeWidth': 3.0}]
        )

        fill.setStrokeStyle(Qt.DashLine)
        self.assertEqual(
            FslConverter.simple_fill_to_fsl(fill, conversion_context),
            [{'color': 'rgb(0, 255, 0)',
              'dashArray': [2.5, 2],
              'lineJoin': 'miter',
              'strokeColor': 'rgb(35, 35, 35)',
              'isClickable': False,
              'isHoverable': False,
              'strokeWidth': 3.0}]
        )
        self.assertEqual(
            FslConverter.simple_fill_to_fsl(fill, conversion_context,
                                            symbol_opacity=0.5),
            [{'color': 'rgb(0, 255, 0)',
              'dashArray': [2.5, 2],
              'lineJoin': 'miter',
              'strokeColor': 'rgb(35, 35, 35)',
              'isClickable': False,
              'isHoverable': False,
              'opacity': 0.5,
              'strokeWidth': 3.0}]
        )

        # outline, no fill
        fill.setBrushStyle(Qt.NoBrush)
        self.assertEqual(
            FslConverter.simple_fill_to_fsl(fill, conversion_context,
                                            symbol_opacity=0.5),
            [{'color': 'rgba(0, 0, 0, 0)',
              'dashArray': [2.5, 2],
              'lineJoin': 'miter',
              'strokeColor': 'rgb(35, 35, 35)',
              'opacity': 0.5,
              'isClickable': False,
              'isHoverable': False,
              'strokeWidth': 3.0}]
        )
        fill.setBrushStyle(Qt.SolidPattern)
        fill.setFillColor(QColor(255, 255, 0, 0))
        self.assertEqual(
            FslConverter.simple_fill_to_fsl(fill, conversion_context,
                                            symbol_opacity=0.5),
            [{'color': 'rgba(0, 0, 0, 0)',
              'dashArray': [2.5, 2],
              'lineJoin': 'miter',
              'strokeColor': 'rgb(35, 35, 35)',
              'isClickable': False,
              'isHoverable': False,
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
            [{'color': 'rgb(0, 255, 0)', 'isClickable': False,
              'isHoverable': False,
              'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )

        fill.setColor(QColor(0, 255, 0, 0))
        fill.setColor2(QColor(255, 255, 0, 0))
        self.assertFalse(
            FslConverter.shapeburst_fill_to_fsl(fill, conversion_context)
        )

        fill.setColor2(QColor(255, 255, 0))
        self.assertEqual(
            FslConverter.shapeburst_fill_to_fsl(fill, conversion_context),
            [{'color': 'rgb(255, 255, 0)', 'isClickable': False,
              'isHoverable': False,
              'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )

        self.assertEqual(
            FslConverter.shapeburst_fill_to_fsl(fill, conversion_context,
                                                symbol_opacity=0.5),
            [{'color': 'rgb(255, 255, 0)',
              'opacity': 0.5, 'isClickable': False,
              'isHoverable': False,
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
            [{'color': 'rgb(0, 255, 0)',
              'isClickable': False,
              'isHoverable': False,
              'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )

        fill.setColor(QColor(0, 255, 0, 0))
        fill.setColor2(QColor(255, 255, 0, 0))
        self.assertFalse(
            FslConverter.gradient_fill_to_fsl(fill, conversion_context)
        )

        fill.setColor2(QColor(255, 255, 0))
        self.assertEqual(
            FslConverter.gradient_fill_to_fsl(fill, conversion_context),
            [{'color': 'rgb(255, 255, 0)',
              'isClickable': False,
              'isHoverable': False,
              'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )

        self.assertEqual(
            FslConverter.gradient_fill_to_fsl(fill, conversion_context,
                                              symbol_opacity=0.5),
            [{'color': 'rgb(255, 255, 0)',
              'opacity': 0.5,
              'isClickable': False,
              'isHoverable': False,
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
            [{'color': 'rgb(255, 0, 255)',
              'isClickable': False,
              'isHoverable': False,
              'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )

        self.assertEqual(
            FslConverter.line_pattern_fill_to_fsl(fill, conversion_context,
                                                  symbol_opacity=0.5),
            [{'color': 'rgb(255, 0, 255)',
              'opacity': 0.5,
              'isClickable': False,
              'isHoverable': False,
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
            [{'color': 'rgb(255, 0, 255)',
              'strokeColor': 'rgba(0, 0, 0, 0)',
              'isClickable': False,
              'isHoverable': False,
              }]
        )

        self.assertEqual(
            FslConverter.svg_fill_to_fsl(fill, conversion_context,
                                         symbol_opacity=0.5),
            [{'color': 'rgb(255, 0, 255)',
              'opacity': 0.5,
              'isClickable': False,
              'isHoverable': False,
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
              'size': 9.5,
              'strokeColor': 'rgba(0, 0, 0, 0)',
              'isClickable': False,
              'isHoverable': False,
              'strokeWidth': 1}]
        )

        self.assertEqual(
            FslConverter.simple_marker_to_fsl(marker, conversion_context,
                                              symbol_opacity=0.5),
            [{'color': 'rgb(120, 130, 140)',
              'size': 9.5,
              'opacity': 0.5,
              'strokeColor': 'rgba(0, 0, 0, 0)',
              'isClickable': False,
              'isHoverable': False,
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
              'size': 9.5,
              'strokeColor': 'rgb(255, 100, 0)',
              'isClickable': False,
              'isHoverable': False,
              'strokeWidth': 3}]
        )

        # size unit
        marker.setSizeUnit(QgsUnitTypes.RenderInches)
        marker.setSize(0.5)
        self.assertEqual(
            FslConverter.simple_marker_to_fsl(marker, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'size': 24,
              'strokeColor': 'rgb(255, 100, 0)',
              'isClickable': False,
              'isHoverable': False,
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
              'size': 9.5,
              'strokeColor': 'rgba(0, 0, 0, 0)',
              'isClickable': False,
              'isHoverable': False,
              'strokeWidth': 1}]
        )

        self.assertEqual(
            FslConverter.ellipse_marker_to_fsl(marker, conversion_context,
                                               symbol_opacity=0.5),
            [{'color': 'rgb(120, 130, 140)',
              'size': 9.5,
              'opacity': 0.5,
              'strokeColor': 'rgba(0, 0, 0, 0)',
              'isClickable': False,
              'isHoverable': False,
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
              'size': 9.5,
              'strokeColor': 'rgb(255, 100, 0)',
              'isClickable': False,
              'isHoverable': False,
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
              'size': 24,
              'strokeColor': 'rgb(255, 100, 0)',
              'isClickable': False,
              'isHoverable': False,
              'strokeWidth': 3}]
        )

        marker.setSymbolHeight(51.5)
        self.assertEqual(
            FslConverter.ellipse_marker_to_fsl(marker, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'size': 34.5,
              'strokeColor': 'rgb(255, 100, 0)',
              'isClickable': False,
              'isHoverable': False,
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
              'size': 9.5,
              'strokeColor': 'rgba(0, 0, 0, 0)',
              'isClickable': False,
              'isHoverable': False,
              'strokeWidth': 1.0}]
        )

        self.assertEqual(
            FslConverter.svg_marker_to_fsl(marker, conversion_context,
                                           symbol_opacity=0.5),
            [{'color': 'rgb(120, 130, 140)',
              'size': 9.5,
              'opacity': 0.5,
              'isClickable': False,
              'isHoverable': False,
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
              'size': 9.5,
              'isClickable': False,
              'isHoverable': False,
              'strokeColor': 'rgb(255, 100, 0)',
              'strokeWidth': 3}]
        )

        # size unit
        marker.setSizeUnit(QgsUnitTypes.RenderInches)
        marker.setSize(0.5)
        self.assertEqual(
            FslConverter.svg_marker_to_fsl(marker, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'size': 24,
              'isClickable': False,
              'isHoverable': False,
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
              'size': 9.5,
              'isClickable': False,
              'isHoverable': False,
              'strokeColor': 'rgba(0, 0, 0, 0)',
              'strokeWidth': 1}]
        )

        self.assertEqual(
            FslConverter.font_marker_to_fsl(marker, conversion_context,
                                            symbol_opacity=0.5),
            [{'color': 'rgb(120, 130, 140)',
              'size': 9.5,
              'opacity': 0.5,
              'isClickable': False,
              'isHoverable': False,
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
              'size': 9.5,
              'isClickable': False,
              'isHoverable': False,
              'strokeColor': 'rgb(255, 100, 0)',
              'strokeWidth': 3}]
        )

        # size unit
        marker.setSizeUnit(QgsUnitTypes.RenderInches)
        marker.setSize(0.5)
        self.assertEqual(
            FslConverter.font_marker_to_fsl(marker, conversion_context),
            [{'color': 'rgb(120, 130, 140)',
              'size': 24,
              'isClickable': False,
              'isHoverable': False,
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

        # no brush, no stroke
        fill.setBrushStyle(Qt.NoBrush)
        fill.setStrokeStyle(Qt.NoPen)
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
              'size': 4,
              'isClickable': False,
              'isHoverable': False,
              'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )

        fill.setStrokeStyle(Qt.SolidLine)
        fill_symbol.changeSymbolLayer(0, fill.clone())
        marker.setSubSymbol(fill_symbol.clone())
        self.assertEqual(
            FslConverter.filled_marker_to_fsl(marker, conversion_context),
            [{'color': 'rgb(0, 255, 0)',
              'size': 4,
              'isClickable': False,
              'isHoverable': False,
              'strokeColor': 'rgb(35, 35, 35)',
              'strokeWidth': 11}]
        )

        fill.setStrokeWidthUnit(QgsUnitTypes.RenderPixels)
        fill_symbol.changeSymbolLayer(0, fill.clone())
        marker.setSubSymbol(fill_symbol.clone())
        self.assertEqual(
            FslConverter.filled_marker_to_fsl(marker, conversion_context),
            [{'color': 'rgb(0, 255, 0)',
              'size': 4,
              'isClickable': False,
              'isHoverable': False,
              'strokeColor': 'rgb(35, 35, 35)',
              'strokeWidth': 3.0}]
        )

        self.assertEqual(
            FslConverter.filled_marker_to_fsl(marker, conversion_context,
                                              symbol_opacity=0.5),
            [{'color': 'rgb(0, 255, 0)',
              'size': 4,
              'strokeColor': 'rgb(35, 35, 35)',
              'opacity': 0.5,
              'isClickable': False,
              'isHoverable': False,
              'strokeWidth': 3.0}]
        )

        marker.setSize(3)
        marker.setSizeUnit(QgsUnitTypes.RenderPoints)
        self.assertEqual(
            FslConverter.filled_marker_to_fsl(marker, conversion_context),
            [{'color': 'rgb(0, 255, 0)',
              'size': 2,
              'isClickable': False,
              'isHoverable': False,
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
              'isClickable': False,
              'isHoverable': False,
              'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )

        self.assertEqual(
            FslConverter.point_pattern_fill_to_fsl(fill, conversion_context,
                                                   symbol_opacity=0.5),
            [{'color': 'rgb(120, 130, 140)',
              'isClickable': False,
              'isHoverable': False,
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
              'strokeColor': 'rgba(0, 0, 0, 0)',
              'isClickable': False,
              'isHoverable': False,
              }]
        )

        self.assertEqual(
            FslConverter.centroid_fill_to_fsl(fill, conversion_context,
                                              symbol_opacity=0.5),
            [{'color': 'rgb(120, 130, 140)',
              'isClickable': False,
              'isHoverable': False,
              'opacity': 0.5,
              'strokeColor': 'rgba(0, 0, 0, 0)'}]
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
              'isClickable': False,
              'isHoverable': False,
              'strokeColor': 'rgba(0, 0, 0, 0)'}]
        )

        self.assertEqual(
            FslConverter.random_marker_fill_to_fsl(fill, conversion_context,
                                                   symbol_opacity=0.5),
            [{'color': 'rgb(120, 130, 140)',
              'isClickable': False,
              'isHoverable': False,
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
              'isClickable': False,
              'isHoverable': False,
              'size': 2}]
        )

        self.assertEqual(
            FslConverter.marker_line_to_fsl(line, conversion_context,
                                            symbol_opacity=0.5),
            [{'color': 'rgb(120, 130, 140)',
              'size': 2,
              'isClickable': False,
              'isHoverable': False,
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
              'isClickable': False,
              'isHoverable': False,
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
              'isClickable': False,
              'isHoverable': False,
              'size': 1}]
        )

        self.assertEqual(
            FslConverter.hashed_line_to_fsl(line, conversion_context,
                                            symbol_opacity=0.5),
            [{'color': 'rgb(120, 130, 140)',
              'size': 1,
              'isClickable': False,
              'isHoverable': False,
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
              'isClickable': False,
              'isHoverable': False,
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
              'isClickable': False,
              'isHoverable': False,
              'size': 18}]
        )

        self.assertEqual(
            FslConverter.arrow_to_fsl(line, conversion_context,
                                      symbol_opacity=0.5),
            [{'color': 'rgb(120, 130, 140)',
              'size': 18,
              'isClickable': False,
              'isHoverable': False,
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
                       'isClickable': False,
                       'isHoverable': False,
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
                       'isClickable': False,
                       'isHoverable': False,
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
             'style': [{'color': 'rgb(255, 255, 0)',
                        'isClickable': False,
                        'isHoverable': False,
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'size': 38},
                       {'color': 'rgb(255, 0, 0)',
                        'isClickable': False,
                        'isHoverable': False,
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'size': 1}],
             'type': 'simple'}
        )

    def test_expression_to_filter(self):
        """
        Test QGIS expression to FSL filter conversions
        """
        context = ConversionContext()

        # invalid expression
        self.assertIsNone(
            FslConverter.expression_to_filter('"Cabin Crew" = ', context)
        )

        self.assertEqual(
            FslConverter.expression_to_filter('"Cabin Crew" = 1', context),
            ["Cabin Crew", "in", [1]]
        )

        self.assertEqual(
            FslConverter.expression_to_filter('"Cabin Crew" <> 1', context),
            ["Cabin Crew", "ni", [1]]
        )

        self.assertEqual(
            FslConverter.expression_to_filter('"Cabin Crew" > 1', context),
            ["Cabin Crew", "gt", 1]
        )

        self.assertEqual(
            FslConverter.expression_to_filter('"Cabin Crew" < 1', context),
            ["Cabin Crew", "lt", 1]
        )

        self.assertEqual(
            FslConverter.expression_to_filter('"Cabin Crew" >= 1', context),
            ["Cabin Crew", "ge", 1]
        )

        self.assertEqual(
            FslConverter.expression_to_filter('"Cabin Crew" <= 1', context),
            ["Cabin Crew", "le", 1]
        )

        self.assertEqual(
            FslConverter.expression_to_filter('"Cabin Crew" IS NULL', context),
            ["Cabin Crew", "is", None]
        )

        self.assertEqual(
            FslConverter.expression_to_filter('"Cabin Crew" IS NOT NULL',
                                              context),
            ["Cabin Crew", "isnt", None]
        )

        self.assertEqual(
            FslConverter.expression_to_filter('"Cabin Crew" IN (1, 2, 3)',
                                              context),
            ['Cabin Crew', 'in', [1, 2, 3]]
        )

        self.assertEqual(
            FslConverter.expression_to_filter(
                '"Cabin Crew" NOT IN (\'a\', \'b\')', context),
            ['Cabin Crew', 'ni', ['a', 'b']]
        )

    def test_rule_based_renderer(self):
        """
        Test converting rule based renderers
        """
        conversion_context = ConversionContext()

        root_rule = QgsRuleBasedRenderer.Rule(None)
        renderer = QgsRuleBasedRenderer(root_rule)
        # no child rules!
        self.assertEqual(
            FslConverter.vector_renderer_to_fsl(renderer, conversion_context),
            {'legend': {},
             'style': {'color': 'rgba(0, 0, 0, 0)',
                       'strokeColor': 'rgba(0, 0, 0, 0)',
                       'isClickable': False,
                       'isHoverable': False, },
             'type': 'simple'}
        )

        # no filter rule
        line = QgsSimpleLineSymbolLayer(color=QColor(255, 0, 0))
        line_symbol = QgsLineSymbol()
        line_symbol.changeSymbolLayer(0, line.clone())
        child_rule = QgsRuleBasedRenderer.Rule(line_symbol.clone())
        root_rule.appendChild(child_rule)
        self.assertEqual(
            FslConverter.vector_renderer_to_fsl(renderer, conversion_context),
            {'legend': {},
             'style': {'color': 'rgb(255, 0, 0)',
                       'lineCap': 'square',
                       'lineJoin': 'bevel',
                       'isClickable': False,
                       'isHoverable': False,
                       'size': 1},
             'type': 'simple'}
        )

        # rule with filter
        child_rule.setFilterExpression('"Cabin Crew" IN (1, 2, 3)')
        self.assertEqual(
            FslConverter.vector_renderer_to_fsl(renderer, conversion_context),
            {'legend': {},
             'style': {'color': 'rgb(255, 0, 0)',
                       'lineCap': 'square',
                       'lineJoin': 'bevel',
                       'isClickable': False,
                       'isHoverable': False,
                       'size': 1},
             'type': 'simple',
             'filters': ['Cabin Crew', 'in', [1, 2, 3]]
             }
        )

        # filter which can't be converted
        child_rule.setFilterExpression('$length > 3')
        self.assertEqual(
            FslConverter.vector_renderer_to_fsl(renderer, conversion_context),
            {'legend': {},
             'style': {'color': 'rgb(255, 0, 0)',
                       'lineCap': 'square',
                       'lineJoin': 'bevel',
                       'isClickable': False,
                       'isHoverable': False,
                       'size': 1},
             'type': 'simple'}
        )

        # layer with scale based rendering, but non-convertible rule based
        # renderer
        layer = QgsVectorLayer('x', '', 'memory')
        layer.setRenderer(renderer)
        layer.setScaleBasedVisibility(True)
        layer.setMinimumScale(10000)
        self.assertEqual(
            FslConverter.vector_layer_to_fsl(layer, conversion_context),
            {'legend': {},
             'style': {'color': 'rgb(255, 0, 0)',
                       'lineCap': 'square',
                       'lineJoin': 'bevel',
                       'minZoom': 15,
                       'isClickable': False,
                       'isHoverable': False,
                       'size': 1},
             'type': 'simple'}
        )

    def test_categorical_rule_based_renderer(self):
        """
        Test converting rule based renderers which can be treated as
        categorical renderers
        """
        conversion_context = ConversionContext()

        root_rule = QgsRuleBasedRenderer.Rule(None)
        renderer = QgsRuleBasedRenderer(root_rule)

        line = QgsSimpleLineSymbolLayer(color=QColor(255, 0, 0))
        line_symbol = QgsLineSymbol()
        line_symbol.changeSymbolLayer(0, line.clone())
        child_rule = QgsRuleBasedRenderer.Rule(line_symbol.clone())
        child_rule.setLabel('rule 1')
        child_rule.setFilterExpression('"my_field"=\'a\'')
        root_rule.appendChild(child_rule)

        line = QgsSimpleLineSymbolLayer(color=QColor(255, 255, 0))
        line_symbol = QgsLineSymbol()
        line_symbol.changeSymbolLayer(0, line.clone())
        child_rule = QgsRuleBasedRenderer.Rule(line_symbol.clone())
        child_rule.setLabel('rule 2')
        child_rule.setFilterExpression('"my_field"=\'b\'')
        root_rule.appendChild(child_rule)

        line = QgsSimpleLineSymbolLayer(color=QColor(255, 255, 255))
        line_symbol = QgsLineSymbol()
        line_symbol.changeSymbolLayer(0, line.clone())
        child_rule = QgsRuleBasedRenderer.Rule(line_symbol.clone())
        child_rule.setLabel('rule 3')
        child_rule.setIsElse(True)
        root_rule.appendChild(child_rule)

        self.assertEqual(
            FslConverter.vector_renderer_to_fsl(renderer, conversion_context),
            {'config': {'categoricalAttribute': 'my_field',
                        'categories': ['a', 'b'],
                        'showOther': True},
             'legend': {'displayName': {'Other': 'rule 3', 'a': 'rule 1',
                                        'b': 'rule 2'}},
             'style': [{'color': ['rgb(255, 0, 0)',
                                  'rgb(255, 255, 0)',
                                  'rgb(255, 255, 255)'],
                        'isClickable': False,
                        'isHoverable': False,
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'size': 1}],
             'type': 'categorical'}
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
                       'isClickable': False,
                       'isHoverable': False,
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
             'style': [{'color': ['rgb(255, 255, 0)', 'rgb(255, 0, 255)',
                                  'rgb(0, 255, 255)'],
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'isClickable': False,
                        'isHoverable': False,
                        'size': [19, 23, 26]},
                       {'color': 'rgb(255, 0, 0)',
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'isClickable': False,
                        'isHoverable': False,
                        'size': 1}
                       ],
             'type': 'categorical'}
        )

        self.assertEqual(
            FslConverter.vector_renderer_to_fsl(renderer, conversion_context,
                                                layer_opacity=0.5),
            {'config': {'categoricalAttribute': 'my_field',
                        'categories': ['1', '2', '3'],
                        'showOther': False},
             'legend': {'displayName': {'1': 'first cat',
                                        '2': 'second cat',
                                        '3': 'third cat'}},
             'style': [{'color': ['rgb(255, 255, 0)',
                                  'rgb(255, 0, 255)',
                                  'rgb(0, 255, 255)'],
                        'isClickable': False,
                        'isHoverable': False,
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'opacity': 0.5,
                        'size': [19, 23, 26]},
                       {'color': 'rgb(255, 0, 0)',
                        'isClickable': False,
                        'isHoverable': False,
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'opacity': 0.5,
                        'size': 1}],
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
            {'config': {'categoricalAttribute': 'my_field',
                        'categories': ['1', '2', '3'],
                        'showOther': True},
             'legend': {'displayName': {'1': 'first cat',
                                        '2': 'second cat',
                                        '3': 'third cat',
                                        'Other': 'all others'}},
             'style': [{'color': ['rgb(255, 255, 0)',
                                  'rgb(255, 0, 255)',
                                  'rgb(0, 255, 255)',
                                  'rgb(100, 100, 100)'],
                        'isClickable': False,
                        'isHoverable': False,
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'size': [19, 23, 26, 11]},
                       {'color': 'rgb(255, 0, 0)',
                        'isClickable': False,
                        'isHoverable': False,
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'size': 1}],
             'type': 'categorical'}
        )

        # unsupported -- dash array is limited to two elements for
        # non-single symbol renderers

        line = QgsSimpleLineSymbolLayer(color=QColor(255, 0, 0))
        line.setPenStyle(Qt.PenStyle.DashDotDotLine)
        line_symbol = QgsLineSymbol()
        line_symbol.changeSymbolLayer(0, line.clone())

        line_symbol2 = QgsLineSymbol()
        line.setColor(QColor(255, 0, 255))
        line.setWidth(6)
        line_symbol2.changeSymbolLayer(0, line.clone())

        categories = [
            QgsRendererCategory(1, line_symbol.clone(), 'first cat'),
            QgsRendererCategory(2, line_symbol2.clone(), 'second cat')
        ]

        renderer = QgsCategorizedSymbolRenderer('my_field',
                                                categories)
        self.assertEqual(
            FslConverter.vector_renderer_to_fsl(renderer, conversion_context),
            {'config': {'categoricalAttribute': 'my_field',
                        'categories': ['1', '2'],
                        'showOther': False},
             'legend': {'displayName': {'1': 'first cat', '2': 'second cat'}},
             'style': [{'color': ['rgb(255, 0, 0)', 'rgb(255, 0, 255)'],
                        'dashArray': [0.5, 1.3, 0.5, 1.3, 2.5, 1.3],
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'isClickable': False,
                        'isHoverable': False,
                        'size': [1, 23]}],
             'type': 'categorical'}
        )

    def test_categorized_no_stroke(self):
        """
        Test categorized renderer with no stroke
        """
        conversion_context = ConversionContext()

        fill = QgsSimpleFillSymbolLayer(color=QColor(255, 0, 0))
        fill.setStrokeStyle(Qt.NoPen)
        fill_symbol = QgsFillSymbol()
        fill_symbol.changeSymbolLayer(0, fill.clone())

        fill_symbol2 = QgsFillSymbol()
        fill.setColor(QColor(255, 0, 255))
        fill_symbol2.changeSymbolLayer(0, fill.clone())

        categories = [
            QgsRendererCategory(1, fill_symbol.clone(), 'first cat'),
            QgsRendererCategory(2, fill_symbol2.clone(), 'second cat')
        ]

        renderer = QgsCategorizedSymbolRenderer('my_field',
                                                categories)
        self.assertEqual(
            FslConverter.vector_renderer_to_fsl(renderer,
                                                conversion_context),
            {'config': {'categories': ['1', '2'],
                        'categoricalAttribute': 'my_field',
                        'showOther': False},
             'legend': {'displayName': {'1': 'first cat',
                                        '2': 'second cat'}},
             'style': [{'color': ['rgb(255, 0, 0)', 'rgb(255, 0, 255)'],
                        'strokeColor': 'rgba(0, 0, 0, 0)',
                        'isClickable': False,
                        'isHoverable': False,
                        }],
             'type': 'categorical'}
        )

    def test_categorized_dash_array_for_one(self):
        """
        Test categorized renderer with dashes on one category only
        """
        conversion_context = ConversionContext()

        line = QgsSimpleLineSymbolLayer(color=QColor(255, 0, 0))
        line.setPenStyle(Qt.DashLine)
        line_symbol = QgsLineSymbol()
        line_symbol.changeSymbolLayer(0, line.clone())

        line_symbol2 = QgsLineSymbol()
        line.setColor(QColor(255, 0, 255))
        line.setPenStyle(Qt.SolidLine)
        line_symbol2.changeSymbolLayer(0, line.clone())

        categories = [
            QgsRendererCategory(1, line_symbol.clone(), 'first cat'),
            QgsRendererCategory(2, line_symbol2.clone(), 'second cat')
        ]

        renderer = QgsCategorizedSymbolRenderer('my_field',
                                                categories)
        self.assertEqual(
            FslConverter.vector_renderer_to_fsl(renderer,
                                                conversion_context),
            {'config': {'categoricalAttribute': 'my_field',
                        'categories': ['1', '2'],
                        'showOther': False},
             'legend': {'displayName': {'1': 'first cat', '2': 'second cat'}},
             'style': [{'color': ['rgb(255, 0, 0)', 'rgb(255, 0, 255)'],
                        'dashArray': [[2.5, 2], [1, 0]],
                        'isClickable': False,
                        'isHoverable': False,
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'size': 1}],
             'type': 'categorical'}
        )

        # flip category order and re-test
        categories = [
            QgsRendererCategory(1, line_symbol2.clone(), 'first cat'),
            QgsRendererCategory(2, line_symbol.clone(), 'second cat')
        ]

        renderer = QgsCategorizedSymbolRenderer('my_field',
                                                categories)
        self.assertEqual(
            FslConverter.vector_renderer_to_fsl(renderer,
                                                conversion_context),
            {'config': {'categoricalAttribute': 'my_field',
                        'categories': ['1', '2'],
                        'showOther': False},
             'legend': {'displayName': {'1': 'first cat', '2': 'second cat'}},
             'style': [{'color': ['rgb(255, 0, 255)', 'rgb(255, 0, 0)'],
                        'dashArray': [[1, 0], [2.5, 2]],
                        'isClickable': False,
                        'isHoverable': False,
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'size': 1}],
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
             'style': [{'color': ['rgb(255, 255, 0)',
                                  'rgb(255, 0, 255)',
                                  'rgb(0, 255, 255)'],
                        'isClickable': False,
                        'isHoverable': False,
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'size': [19, 23, 26]},
                       {'color': 'rgb(255, 0, 0)',
                        'isClickable': False,
                        'isHoverable': False,
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'size': 1}],
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
             'style': [{'color': ['rgb(255, 255, 0)',
                                  'rgb(255, 0, 255)',
                                  'rgb(0, 255, 255)'],
                        'isClickable': False,
                        'isHoverable': False,
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'opacity': 0.5,
                        'size': [19, 23, 26]},
                       {'color': 'rgb(255, 0, 0)',
                        'isClickable': False,
                        'isHoverable': False,
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'opacity': 0.5,
                        'size': 1}],
             'type': 'numeric'}
        )

        # with out of order ranges
        ranges = [
            QgsRendererRange(3, 4, line_symbol3.clone(), 'third range'),
            QgsRendererRange(1, 2, line_symbol.clone(), 'first range'),
            QgsRendererRange(2, 3, line_symbol2.clone(), 'second range'),
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
             'style': [{'color': ['rgb(255, 255, 0)',
                                  'rgb(255, 0, 255)',
                                  'rgb(0, 255, 255)'],
                        'isClickable': False,
                        'isHoverable': False,
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'size': [19, 23, 26]},
                       {'color': 'rgb(255, 0, 0)',
                        'isClickable': False,
                        'isHoverable': False,
                        'lineCap': 'square',
                        'lineJoin': 'bevel',
                        'size': 1}],
             'type': 'numeric'}
        )

    def test_heatmap_renderer(self):
        """
        Test converting heatmap renderers
        """
        conversion_context = ConversionContext()

        renderer = QgsHeatmapRenderer()
        self.assertEqual(
            FslConverter.vector_renderer_to_fsl(renderer, conversion_context),
            {'legend': {'displayName': {'0': 'Low', '1': 'High'}},
             'style': {'color': ['#ffffff',
                                 '#f7f7f7',
                                 '#eeeeee',
                                 '#e6e6e6',
                                 '#dddddd',
                                 '#d5d5d5',
                                 '#cccccc',
                                 '#c3c3c3',
                                 '#bbbbbb',
                                 '#b3b3b3',
                                 '#aaaaaa',
                                 '#a2a2a2',
                                 '#999999',
                                 '#919191',
                                 '#888888',
                                 '#808080',
                                 '#777777',
                                 '#6f6f6f',
                                 '#666666',
                                 '#5e5e5e',
                                 '#555555',
                                 '#4d4d4d',
                                 '#444444',
                                 '#3b3b3b',
                                 '#333333',
                                 '#2a2a2a',
                                 '#222222',
                                 '#191919',
                                 '#111111',
                                 '#080808'],
                       'intensity': 1,
                       'opacity': 1,
                       'size': 38},
             'type': 'heatmap'}
        )

        self.assertEqual(
            FslConverter.vector_renderer_to_fsl(renderer, conversion_context,
                                                layer_opacity=0.5),
            {'legend': {'displayName': {'0': 'Low', '1': 'High'}},
             'style': {'color': ['#ffffff',
                                 '#f7f7f7',
                                 '#eeeeee',
                                 '#e6e6e6',
                                 '#dddddd',
                                 '#d5d5d5',
                                 '#cccccc',
                                 '#c3c3c3',
                                 '#bbbbbb',
                                 '#b3b3b3',
                                 '#aaaaaa',
                                 '#a2a2a2',
                                 '#999999',
                                 '#919191',
                                 '#888888',
                                 '#808080',
                                 '#777777',
                                 '#6f6f6f',
                                 '#666666',
                                 '#5e5e5e',
                                 '#555555',
                                 '#4d4d4d',
                                 '#444444',
                                 '#3b3b3b',
                                 '#333333',
                                 '#2a2a2a',
                                 '#222222',
                                 '#191919',
                                 '#111111',
                                 '#080808'],
                       'intensity': 1,
                       'opacity': 0.5,
                       'size': 38},
             'type': 'heatmap'}
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
        self.assertEqual(
            FslConverter.label_settings_to_fsl(label_settings, context),
            {'label': {'isClickable': False, 'isHoverable': False}}
        )
        label_settings.drawLabels = True
        label_settings.fieldName = ''
        self.assertEqual(
            FslConverter.label_settings_to_fsl(label_settings, context),
            {'label': {'isClickable': False, 'isHoverable': False}}
        )

        # expression labels, unsupported
        label_settings.fieldName = '1 + 2'
        label_settings.isExpression = True
        self.assertEqual(
            FslConverter.label_settings_to_fsl(label_settings, context),
            {'label': {'isClickable': False, 'isHoverable': False}}
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
                       'minZoom': 1,
                       'isClickable': False,
                       'isHoverable': False}}
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
                       'minZoom': 1,
                       'isClickable': False,
                       'isHoverable': False}}
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
                       'minZoom': 6,
                       'isClickable': False,
                       'isHoverable': False}}
        )

    def test_layer_to_fsl(self):
        """
        Test converting whole layer to FSL
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
                       'isClickable': False,
                       'isHoverable': False,
                       'size': 1},
             'type': 'simple'}
        )
        layer = QgsVectorLayer('x', '', 'memory')
        layer.setRenderer(renderer)

        self.assertEqual(
            FslConverter.vector_layer_to_fsl(layer, conversion_context),
            {'legend': {},
             'style': {'color': 'rgb(255, 0, 0)',
                       'lineCap': 'square',
                       'lineJoin': 'bevel',
                       'isClickable': False,
                       'isHoverable': False,
                       'size': 1},
             'type': 'simple'}
        )

        # layer opacity
        layer.setOpacity(0.5)
        self.assertEqual(
            FslConverter.vector_layer_to_fsl(layer, conversion_context),
            {'legend': {},
             'style': {'color': 'rgb(255, 0, 0)',
                       'lineCap': 'square',
                       'lineJoin': 'bevel',
                       'opacity': 0.5,
                       'isClickable': False,
                       'isHoverable': False,
                       'size': 1},
             'type': 'simple'}
        )
        layer.setOpacity(1)

        # zoom range
        layer.setScaleBasedVisibility(True)
        layer.setMinimumScale(10000)
        self.assertEqual(
            FslConverter.vector_layer_to_fsl(layer, conversion_context),
            {'legend': {},
             'style': {'color': 'rgb(255, 0, 0)',
                       'lineCap': 'square',
                       'lineJoin': 'bevel',
                       'minZoom': 15,
                       'isClickable': False,
                       'isHoverable': False,
                       'size': 1},
             'type': 'simple'}
        )
        layer.setMaximumScale(1000)
        self.assertEqual(
            FslConverter.vector_layer_to_fsl(layer, conversion_context),
            {'legend': {},
             'style': {'color': 'rgb(255, 0, 0)',
                       'lineCap': 'square',
                       'lineJoin': 'bevel',
                       'minZoom': 15,
                       'maxZoom': 19,
                       'isClickable': False,
                       'isHoverable': False,
                       'size': 1},
             'type': 'simple'}
        )
        layer.setMinimumScale(0)
        self.assertEqual(
            FslConverter.vector_layer_to_fsl(layer, conversion_context),
            {'legend': {},
             'style': {'color': 'rgb(255, 0, 0)',
                       'lineCap': 'square',
                       'lineJoin': 'bevel',
                       'maxZoom': 19,
                       'isClickable': False,
                       'isHoverable': False,
                       'size': 1},
             'type': 'simple'}
        )

    @unittest.skipIf(Qgis.QGIS_VERSION_INT < 32400, 'QGIS too old')
    def test_layer_to_fsl_with_labels_no_renderer(self):
        """
        Test conversion to Fsl when labels can be converted but not
        renderer
        """
        f = QgsTextFormat()
        font = QFont('Arial')
        f.setFont(font)
        f.setSize(13)
        f.setSizeUnit(QgsUnitTypes.RenderPixels)
        f.setColor(QColor(255, 0, 0))
        f.setOpacity(0.3)

        label_settings = QgsPalLayerSettings()
        label_settings.setFormat(f)
        label_settings.fieldName = 'my_field'
        label_settings.isExpression = False

        layer = QgsVectorLayer('Polygon', '', 'memory')
        renderer = QgsInvertedPolygonRenderer()
        layer.setRenderer(renderer)

        layer.setLabelsEnabled(True)
        layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))

        conversion_context = ConversionContext()
        style = LayerExporter.representative_layer_style(layer,
                                                         conversion_context)

        self.assertEqual(
            style.fsl,
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
                       'minZoom': 1,
                       'isClickable': False,
                       'isHoverable': False},
             'version': '2.1.1'}
        )

    def test_convert_continuous_singleband_pseudocolor(self):
        """
        Convert continuous singleband pseudocolor renderer
        """
        context = ConversionContext()
        gradient = QgsGradientColorRamp(
            QColor(255, 0, 0),
            QColor(0, 255, 0)
        )
        color_ramp_shader = QgsColorRampShader(110, 140)
        color_ramp_shader.setSourceColorRamp(
            gradient.clone()
        )
        color_ramp_shader.setColorRampItemList(
            [
                QgsColorRampShader.ColorRampItem(
                    120, QColor(0, 255, 0), 'lowest'
                ),
                QgsColorRampShader.ColorRampItem(
                    125, QColor(255, 255, 0), 'mid'
                ),
                QgsColorRampShader.ColorRampItem(
                    130, QColor(0, 255, 255), 'highest'
                )
            ]
        )
        renderer = QgsSingleBandPseudoColorRenderer(None,
                                                    band=1)
        shader = QgsRasterShader()
        shader.setRasterShaderFunction(QgsColorRampShader(color_ramp_shader))
        renderer.setShader(shader)

        self.assertEqual(FslConverter.raster_renderer_to_fsl(
            renderer, context),
            {'config': {'band': 1,
                        'steps': [110.0,
                                  110.0,
                                  111.0,
                                  112.0,
                                  113.0,
                                  114.0,
                                  115.0,
                                  116.0,
                                  117.0,
                                  118.0,
                                  119.0,
                                  120.0,
                                  121.0,
                                  122.0,
                                  123.0,
                                  124.0,
                                  125.0,
                                  126.0,
                                  127.0,
                                  128.0,
                                  129.0,
                                  130.0,
                                  131.0,
                                  132.0,
                                  133.0,
                                  134.0,
                                  135.0,
                                  136.0,
                                  137.0,
                                  138.0,
                                  139.0]},
             'legend': {'displayName': {'0': '110.0',
                                        '1': '111.0',
                                        '10': '120.0',
                                        '11': '121.0',
                                        '12': '122.0',
                                        '13': '123.0',
                                        '14': '124.0',
                                        '15': '125.0',
                                        '16': '126.0',
                                        '17': '127.0',
                                        '18': '128.0',
                                        '19': '129.0',
                                        '2': '112.0',
                                        '20': '130.0',
                                        '21': '131.0',
                                        '22': '132.0',
                                        '23': '133.0',
                                        '24': '134.0',
                                        '25': '135.0',
                                        '26': '136.0',
                                        '27': '137.0',
                                        '28': '138.0',
                                        '29': '139.0',
                                        '3': '113.0',
                                        '4': '114.0',
                                        '5': '115.0',
                                        '6': '116.0',
                                        '7': '117.0',
                                        '8': '118.0',
                                        '9': '119.0'}},
             'style': {'color': ['rgb(0, 255, 0)',
                                 'rgb(0, 255, 0)',
                                 'rgb(0, 255, 0)',
                                 'rgb(0, 255, 0)',
                                 'rgb(0, 255, 0)',
                                 'rgb(0, 255, 0)',
                                 'rgb(0, 255, 0)',
                                 'rgb(0, 255, 0)',
                                 'rgb(0, 255, 0)',
                                 'rgb(0, 255, 0)',
                                 'rgb(0, 255, 0)',
                                 'rgb(51, 255, 0)',
                                 'rgb(102, 255, 0)',
                                 'rgb(153, 255, 0)',
                                 'rgb(204, 255, 0)',
                                 'rgb(255, 255, 0)',
                                 'rgb(204, 255, 51)',
                                 'rgb(153, 255, 102)',
                                 'rgb(102, 255, 153)',
                                 'rgb(51, 255, 204)',
                                 'rgb(0, 255, 255)',
                                 'rgb(0, 255, 255)',
                                 'rgb(0, 255, 255)',
                                 'rgb(0, 255, 255)',
                                 'rgb(0, 255, 255)',
                                 'rgb(0, 255, 255)',
                                 'rgb(0, 255, 255)',
                                 'rgb(0, 255, 255)',
                                 'rgb(0, 255, 255)',
                                 'rgb(0, 255, 255)'],
                       'isSandwiched': False,
                       'opacity': 1},
             'type': 'numeric'}
        )

        renderer = QgsSingleBandPseudoColorRenderer(None,
                                                    band=2)
        shader = QgsRasterShader()
        shader.setRasterShaderFunction(QgsColorRampShader(color_ramp_shader))
        renderer.setShader(shader)

        self.assertEqual(FslConverter.raster_renderer_to_fsl(
            renderer, context),
            {'config': {'band': 2,
                        'steps': [110.0,
                                  110.0,
                                  111.0,
                                  112.0,
                                  113.0,
                                  114.0,
                                  115.0,
                                  116.0,
                                  117.0,
                                  118.0,
                                  119.0,
                                  120.0,
                                  121.0,
                                  122.0,
                                  123.0,
                                  124.0,
                                  125.0,
                                  126.0,
                                  127.0,
                                  128.0,
                                  129.0,
                                  130.0,
                                  131.0,
                                  132.0,
                                  133.0,
                                  134.0,
                                  135.0,
                                  136.0,
                                  137.0,
                                  138.0,
                                  139.0]},
             'legend': {'displayName': {'0': '110.0',
                                        '1': '111.0',
                                        '10': '120.0',
                                        '11': '121.0',
                                        '12': '122.0',
                                        '13': '123.0',
                                        '14': '124.0',
                                        '15': '125.0',
                                        '16': '126.0',
                                        '17': '127.0',
                                        '18': '128.0',
                                        '19': '129.0',
                                        '2': '112.0',
                                        '20': '130.0',
                                        '21': '131.0',
                                        '22': '132.0',
                                        '23': '133.0',
                                        '24': '134.0',
                                        '25': '135.0',
                                        '26': '136.0',
                                        '27': '137.0',
                                        '28': '138.0',
                                        '29': '139.0',
                                        '3': '113.0',
                                        '4': '114.0',
                                        '5': '115.0',
                                        '6': '116.0',
                                        '7': '117.0',
                                        '8': '118.0',
                                        '9': '119.0'}},
             'style': {'color': ['rgb(0, 255, 0)',
                                 'rgb(0, 255, 0)',
                                 'rgb(0, 255, 0)',
                                 'rgb(0, 255, 0)',
                                 'rgb(0, 255, 0)',
                                 'rgb(0, 255, 0)',
                                 'rgb(0, 255, 0)',
                                 'rgb(0, 255, 0)',
                                 'rgb(0, 255, 0)',
                                 'rgb(0, 255, 0)',
                                 'rgb(0, 255, 0)',
                                 'rgb(51, 255, 0)',
                                 'rgb(102, 255, 0)',
                                 'rgb(153, 255, 0)',
                                 'rgb(204, 255, 0)',
                                 'rgb(255, 255, 0)',
                                 'rgb(204, 255, 51)',
                                 'rgb(153, 255, 102)',
                                 'rgb(102, 255, 153)',
                                 'rgb(51, 255, 204)',
                                 'rgb(0, 255, 255)',
                                 'rgb(0, 255, 255)',
                                 'rgb(0, 255, 255)',
                                 'rgb(0, 255, 255)',
                                 'rgb(0, 255, 255)',
                                 'rgb(0, 255, 255)',
                                 'rgb(0, 255, 255)',
                                 'rgb(0, 255, 255)',
                                 'rgb(0, 255, 255)',
                                 'rgb(0, 255, 255)'],
                       'isSandwiched': False,
                       'opacity': 1},
             'type': 'numeric'}
        )

    def test_convert_discrete_singleband_pseudocolor(self):
        """
        Convert discrete singleband pseudocolor renderer
        """
        context = ConversionContext()
        gradient = QgsGradientColorRamp(
            QColor(255, 0, 0),
            QColor(0, 255, 0)
        )
        color_ramp_shader = QgsColorRampShader(50, 200)
        color_ramp_shader.setColorRampType(QgsColorRampShader.Discrete)
        color_ramp_shader.setSourceColorRamp(
            gradient.clone()
        )
        color_ramp_shader.setColorRampItemList(
            [
                QgsColorRampShader.ColorRampItem(
                    120, QColor(0, 255, 0), 'lowest'
                ),
                QgsColorRampShader.ColorRampItem(
                    125, QColor(255, 255, 0), 'mid'
                ),
                QgsColorRampShader.ColorRampItem(
                    130, QColor(0, 255, 255), 'highest'
                )
            ]
        )
        renderer = QgsSingleBandPseudoColorRenderer(None,
                                                    band=1)
        shader = QgsRasterShader()
        shader.setRasterShaderFunction(QgsColorRampShader(color_ramp_shader))
        renderer.setShader(shader)

        self.assertEqual(FslConverter.raster_renderer_to_fsl(
            renderer, context),
            {'config': {'band': 1,
                        'steps': [50.0, 120.0, 125.0, 130.0]},
             'legend': {
                 'displayName': {'0': 'lowest', '1': 'mid', '2': 'highest'}},
             'style': {'color': ['#00ff00', '#ffff00', '#00ffff'],
                       'isSandwiched': False,
                       'opacity': 1},
             'type': 'numeric'}
        )

        renderer = QgsSingleBandPseudoColorRenderer(None,
                                                    band=2)
        shader = QgsRasterShader()
        shader.setRasterShaderFunction(QgsColorRampShader(color_ramp_shader))
        renderer.setShader(shader)

        self.assertEqual(FslConverter.raster_renderer_to_fsl(
            renderer, context),
            {'config': {'band': 2,
                        'steps': [50.0, 120.0, 125.0, 130.0]},
             'legend': {
                 'displayName': {'0': 'lowest', '1': 'mid', '2': 'highest'}},
             'style': {'color': ['#00ff00', '#ffff00', '#00ffff'],
                       'isSandwiched': False,
                       'opacity': 1},
             'type': 'numeric'}
        )

    def test_convert_exact_singleband_pseudocolor(self):
        """
        Convert exact singleband pseudocolor renderer
        """
        context = ConversionContext()
        gradient = QgsGradientColorRamp(
            QColor(255, 0, 0),
            QColor(0, 255, 0)
        )
        color_ramp_shader = QgsColorRampShader(50, 200)
        color_ramp_shader.setColorRampType(QgsColorRampShader.Exact)
        color_ramp_shader.setSourceColorRamp(
            gradient.clone()
        )
        color_ramp_shader.setColorRampItemList(
            [
                QgsColorRampShader.ColorRampItem(
                    120, QColor(0, 255, 0), 'lowest'
                ),
                QgsColorRampShader.ColorRampItem(
                    125, QColor(255, 255, 0), 'mid'
                ),
                QgsColorRampShader.ColorRampItem(
                    130, QColor(0, 255, 255), 'highest'
                )
            ]
        )
        renderer = QgsSingleBandPseudoColorRenderer(None,
                                                    band=1)
        shader = QgsRasterShader()
        shader.setRasterShaderFunction(QgsColorRampShader(color_ramp_shader))
        renderer.setShader(shader)

        self.assertEqual(FslConverter.raster_renderer_to_fsl(
            renderer, context),
            {'config': {'band': 1, 'categories': ['120.0', '125.0', '130.0']},
             'legend': {
                 'displayName': {'0': 'lowest', '1': 'mid', '2': 'highest'}},
             'style': {'color': ['#00ff00', '#ffff00', '#00ffff'],
                       'isSandwiched': False,
                       'opacity': 1},
             'type': 'categorical'}
        )

        renderer = QgsSingleBandPseudoColorRenderer(None,
                                                    band=2)
        shader = QgsRasterShader()
        shader.setRasterShaderFunction(QgsColorRampShader(color_ramp_shader))
        renderer.setShader(shader)

        self.assertEqual(FslConverter.raster_renderer_to_fsl(
            renderer, context),
            {'config': {'band': 2, 'categories': ['120.0', '125.0', '130.0']},
             'legend': {
                 'displayName': {'0': 'lowest', '1': 'mid', '2': 'highest'}},
             'style': {'color': ['#00ff00', '#ffff00', '#00ffff'],
                       'isSandwiched': False,
                       'opacity': 1},
             'type': 'categorical'}
        )

    def test_convert_singleband_gray_renderer(self):
        """
        Convert singleband gray renderer
        """
        context = ConversionContext()
        renderer = QgsSingleBandGrayRenderer(None, 1)
        enhancement = QgsContrastEnhancement()
        enhancement.setMinimumValue(5)
        enhancement.setMaximumValue(5)
        renderer.setContrastEnhancement(QgsContrastEnhancement(enhancement))

        self.assertEqual(FslConverter.raster_renderer_to_fsl(
            renderer, context),
            {'config': {'band': 1, 'steps': [5.0, 5.0]},
             'legend': {'displayName': {'0': '5.0', '1': '5.0'}},
             'style': {'color': ['rgb(0, 0, 0)', 'rgb(255, 255, 255)'],
                       'isSandwiched': False,
                       'opacity': 1},
             'type': 'numeric'}
        )

        renderer = QgsSingleBandGrayRenderer(None, 2)
        renderer.setGradient(QgsSingleBandGrayRenderer.Gradient.WhiteToBlack)
        renderer.setContrastEnhancement(QgsContrastEnhancement(enhancement))

        self.assertEqual(FslConverter.raster_renderer_to_fsl(
            renderer, context),
            {'config': {'band': 2, 'steps': [5.0, 5.0]},
             'legend': {'displayName': {'0': '5.0', '1': '5.0'}},
             'style': {'color': ['rgb(255, 255, 255)', 'rgb(0, 0, 0)'],
                       'isSandwiched': False,
                       'opacity': 1},
             'type': 'numeric'}
        )

    def test_convert_paletted_raster(self):
        """
        Convert raster paletted renderer
        """
        context = ConversionContext()
        class_data = [
            QgsPalettedRasterRenderer.Class(
                120, QColor(0, 255, 0), 'lowest'
            ),
            QgsPalettedRasterRenderer.Class(
                125, QColor(255, 255, 0), 'mid'
            ),
            QgsPalettedRasterRenderer.Class(
                130, QColor(0, 255, 255), 'highest'
            )
        ]
        renderer = QgsPalettedRasterRenderer(None,
                                             bandNumber=1,
                                             classes=class_data)

        self.assertEqual(FslConverter.raster_renderer_to_fsl(
            renderer, context),
            {'config': {'band': 1, 'categories': ['120.0', '125.0', '130.0']},
             'legend': {'displayName': {'120.0': 'lowest',
                                        '125.0': 'mid',
                                        '130.0': 'highest'}},
             'style': {'color': ['#00ff00', '#ffff00', '#00ffff'],
                       'isSandwiched': False,
                       'opacity': 1},
             'type': 'categorical'}
        )

        renderer = QgsPalettedRasterRenderer(None,
                                             bandNumber=2,
                                             classes=class_data)

        self.assertEqual(FslConverter.raster_renderer_to_fsl(
            renderer, context),
            {'config': {'band': 2, 'categories': ['120.0', '125.0', '130.0']},
             'legend': {'displayName': {'120.0': 'lowest',
                                        '125.0': 'mid',
                                        '130.0': 'highest'}},
             'style': {'color': ['#00ff00', '#ffff00', '#00ffff'],
                       'isSandwiched': False,
                       'opacity': 1},
             'type': 'categorical'}
        )


if __name__ == "__main__":
    suite = unittest.makeSuite(FslConversionTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
