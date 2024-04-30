from enum import (
    Enum,
    auto
)
from typing import (
    Dict,
    List,
    Optional
)

from qgis.PyQt.QtCore import (
    Qt,
)
from qgis.PyQt.QtGui import QColor

from qgis.core import (
    QgsSymbol,
    QgsSymbolLayer,
    QgsSimpleFillSymbolLayer,
    QgsShapeburstFillSymbolLayer,
    QgsGradientFillSymbolLayer,
    QgsSimpleLineSymbolLayer,
    QgsLinePatternFillSymbolLayer,
    QgsHashedLineSymbolLayer,
    QgsMarkerLineSymbolLayer,
    QgsSimpleMarkerSymbolLayer,
    QgsEllipseSymbolLayer,
    QgsSvgMarkerSymbolLayer,
    QgsPointPatternFillSymbolLayer,
    QgsCentroidFillSymbolLayer,
    QgsFilledMarkerSymbolLayer,
    QgsSVGFillSymbolLayer,
    QgsFontMarkerSymbolLayer,
    QgsRandomMarkerFillSymbolLayer,
    QgsArrowSymbolLayer,
    QgsRenderContext,
    QgsUnitTypes
)


class LogLevel(Enum):
    """
    Logging level
    """
    Warning = auto()
    Error = auto()


class ConversionContext:

    def __init__(self):
        # TODO -- populate with correct dpi etc
        self.render_context: QgsRenderContext = QgsRenderContext()
        self.render_context.setScaleFactor(3.779)

    def push_warning(self, warning: str, level: LogLevel = LogLevel.Warning):
        """
        Pushes a warning to the context
        """


class FslConverter:

    @staticmethod
    def symbol_to_fsl(symbol: QgsSymbol, context: ConversionContext) -> List[Dict[str, object]]:
        """
        Converts a QGIS symbol to an FSL definition

        Returns None if no symbol should be used
        """
        enabled_layers = [symbol[i] for i in range(len(symbol)) if symbol[i].enabled()]
        if not enabled_layers:
            return []

        symbol_opacity = symbol.opacity()
        fsl_layers = []
        for layer in enabled_layers:
            fsl_layers.extend(
                FslConverter.symbol_layer_to_fsl(layer, context, symbol_opacity)
            )

        return fsl_layers

    @staticmethod
    def symbol_layer_to_fsl(
            layer: QgsSymbolLayer,
            context: ConversionContext,
            symbol_opacity: float) -> List[Dict[str, object]]:
        """
        Converts QGIS symbol layers to FSL symbol layers
        """
        SYMBOL_LAYER_CONVERTERS = {
            # Marker types
            QgsSimpleMarkerSymbolLayer: FslConverter.simple_marker_to_fsl,
            QgsEllipseSymbolLayer: FslConverter.ellipse_marker_to_fsl,
            QgsSvgMarkerSymbolLayer: FslConverter.svg_marker_to_fsl,
            QgsFontMarkerSymbolLayer: FslConverter.font_marker_to_fsl,
            QgsFilledMarkerSymbolLayer: FslConverter.filled_marker_to_fsl,

            # Line types
            QgsSimpleLineSymbolLayer: FslConverter.simple_line_to_fsl,
            QgsMarkerLineSymbolLayer: FslConverter.marker_line_to_fsl,
            QgsHashedLineSymbolLayer: FslConverter.hashed_line_to_fsl,
            QgsArrowSymbolLayer: FslConverter.arrow_to_fsl,

            # Fill types
            QgsSimpleFillSymbolLayer: FslConverter.simple_fill_to_fsl,
            QgsShapeburstFillSymbolLayer: FslConverter.shapeburst_fill_to_fsl,
            QgsGradientFillSymbolLayer: FslConverter.gradient_fill_to_fsl,
            QgsLinePatternFillSymbolLayer: FslConverter.line_pattern_fill_to_fsl,
            QgsSVGFillSymbolLayer: FslConverter.svg_fill_to_fsl,
            QgsPointPatternFillSymbolLayer: FslConverter.point_pattern_fill_to_fsl,
            QgsCentroidFillSymbolLayer: FslConverter.centroid_fill_to_fsl,
            QgsRandomMarkerFillSymbolLayer: FslConverter.random_marker_fill_to_fsl,

            # Nothing of interest here, there's NO properties we can convert!
            # QgsRasterFillSymbolLayer
            # QgsRasterMarkerSymbolLayer
            # QgsAnimatedMarkerSymbolLayer
            # QgsVectorFieldSymbolLayer
            # QgsGeometryGeneratorSymbolLayer
            # QgsInterpolatedLineSymbolLayer
            # QgsRasterLineSymbolLayer
            # QgsLineburstSymbolLayer
        }

        for _class, converter in SYMBOL_LAYER_CONVERTERS.items():
            if isinstance(layer, _class):
                return converter(layer, context, symbol_opacity)

        context.push_warning('{} symbol layers cannot be converted yet'.format(layer.__class__.__name__),
                             LogLevel.Error)
        return []

    @staticmethod
    def color_to_fsl(color: QColor, context: ConversionContext, opacity: float = 1) -> Optional[str]:
        """
        Converts a color to FSL, optionally reducing the opacity of the color
        """
        if not color.isValid():
            return None

        color_opacity = color.alphaF() * opacity
        if color_opacity == 1:
            return 'rgb({}, {}, {})'.format(color.red(),
                                            color.green(),
                                            color.blue())
        else:
            return 'rgba({}, {}, {}, {})'.format(color.red(),
                                                 color.green(),
                                                 color.blue(),
                                                 round(color_opacity, 2))

    @staticmethod
    def convert_to_pixels(
            size,
            size_unit: QgsUnitTypes.RenderUnit,
            context: ConversionContext,
            round_size: bool = True
    ) -> float:
        """
        Converts a size to pixels
        """
        res = context.render_context.convertToPainterUnits(
            size, size_unit
        )
        return round(res) if round_size else res

    @staticmethod
    def convert_cap_style(style: Qt.PenCapStyle) -> str:
        """
        Convert a Qt cap style to FSL
        """
        return {
            Qt.RoundCap: 'round',
            Qt.SquareCap: 'square',
            Qt.FlatCap: 'butt',
        }[style]

    @staticmethod
    def convert_join_style(style: Qt.PenJoinStyle) -> str:
        """
        Convert a Qt join style to FSL
        """
        return {
            Qt.RoundJoin: 'round',
            Qt.BevelJoin: 'bevel',
            Qt.MiterJoin: 'miter',
            Qt.SvgMiterJoin: 'miter',
        }[style]

    @staticmethod
    def convert_pen_style(style: Qt.PenStyle) -> List[float]:
        """
        Converts a Qt pen style to an array of dash/space lengths
        """
        return {
            Qt.NoPen: [],
            Qt.SolidLine: [],
            Qt.DashLine: [2.5, 2],
            Qt.DotLine: [0.5, 1.3],
            Qt.DashDotLine: [0.5, 1.3, 2.5, 1.3],
            Qt.DashDotDotLine: [0.5, 1.3, 0.5, 1.3, 2.5, 1.3]
        }[style]

    @staticmethod
    def simple_line_to_fsl(
            layer: QgsSimpleLineSymbolLayer,
            context: ConversionContext,
            symbol_opacity: float = 1) -> List[Dict[str, object]]:
        """
        Converts a QGIS simple line symbol layer to FSL
        """
        if layer.penStyle() == Qt.NoPen or not layer.color().isValid() or layer.color().alphaF() == 0:
            return []

        color_str = FslConverter.color_to_fsl(
            layer.color(), context
        )
        stroke_width = FslConverter.convert_to_pixels(layer.width(), layer.widthUnit(), context)

        res = {
            'color': color_str,
            'size': stroke_width,
            'lineCap': FslConverter.convert_cap_style(layer.penCapStyle()),
            'lineJoin': FslConverter.convert_join_style(layer.penJoinStyle())
        }

        if symbol_opacity < 1:
            res['opacity'] = symbol_opacity

        if layer.useCustomDashPattern():
            res['dashArray'] = [FslConverter.convert_to_pixels(
                part,
                layer.customDashPatternUnit(), context, round_size=False) for part in layer.customDashVector()]
        elif layer.penStyle() != Qt.SolidLine:
            res['dashArray'] = FslConverter.convert_pen_style(layer.penStyle())

        # not supported:
        # - line offset
        # - pattern offset
        # - trim lines

        return [res]

    @staticmethod
    def marker_line_to_fsl(
            layer: QgsMarkerLineSymbolLayer,
            context: ConversionContext,
            symbol_opacity: float = 1) -> List[Dict[str, object]]:
        """
        Converts a QGIS marker line symbol layer to FSL
        """
        marker_symbol = layer.subSymbol()
        if marker_symbol is None:
            return []

        converted_marker = FslConverter.symbol_to_fsl(marker_symbol, context)
        if not converted_marker:
            return []

        context.push_warning('Marker lines are not supported, converting to a solid line')

        results = []
        for converted_layer in converted_marker:
            color_str = converted_layer.get('color')
            if not color_str:
                continue

            res = {
                'color': color_str,
            }

            if layer.placement() == QgsMarkerLineSymbolLayer.Interval:
                interval_pixels = FslConverter.convert_to_pixels(layer.interval(), layer.intervalUnit(), context)
                try:
                    marker_size = float(converted_layer['size'])
                except TypeError:
                    continue

                res['dashArray'] = [marker_size, interval_pixels - marker_size]
                res['size'] = marker_size
            else:
                # hardcoded size, there's no point using the marker size as it will visually appear
                # as a much fatter line due to the missing spaces between markers
                res['size'] = 2

            if symbol_opacity < 1:
                res['opacity'] = symbol_opacity

            results.append(res)

        return results

    @staticmethod
    def hashed_line_to_fsl(
            layer: QgsHashedLineSymbolLayer,
            context: ConversionContext,
            symbol_opacity: float = 1) -> List[Dict[str, object]]:
        """
        Converts a QGIS hashed line symbol layer to FSL
        """
        hatch_symbol = layer.subSymbol()
        if hatch_symbol is None:
            return []

        converted_hatch = FslConverter.symbol_to_fsl(hatch_symbol, context)
        if not converted_hatch:
            return []

        context.push_warning('Hatched lines are not supported, converting to a solid line')

        results = []
        for converted_layer in converted_hatch:
            color_str = converted_layer.get('color')
            if not color_str:
                continue

            res = {
                'color': color_str,
            }

            if layer.placement() == QgsMarkerLineSymbolLayer.Interval:
                interval_pixels = FslConverter.convert_to_pixels(layer.interval(), layer.intervalUnit(), context)
                try:
                    hatch_size = float(converted_layer['size'])
                except TypeError:
                    continue

                res['dashArray'] = [hatch_size, interval_pixels - hatch_size]
                res['size'] = hatch_size
            else:
                # hardcoded size, there's no point using the marker size as it will visually appear
                # as a much fatter line due to the missing spaces between markers
                res['size'] = 1

            if symbol_opacity < 1:
                res['opacity'] = symbol_opacity

            results.append(res)

        return results

    @staticmethod
    def arrow_to_fsl(
            layer: QgsArrowSymbolLayer,
            context: ConversionContext,
            symbol_opacity: float = 1) -> List[Dict[str, object]]:
        """
        Converts a QGIS arrow symbol layer to FSL
        """
        fill_symbol = layer.subSymbol()
        if fill_symbol is None:
            return []

        converted_fill = FslConverter.symbol_to_fsl(fill_symbol, context)
        if not converted_fill:
            return []

        context.push_warning('Arrows are not supported, converting to a solid line')

        results = []
        for converted_layer in converted_fill:
            color_str = converted_layer.get('color')
            if not color_str:
                continue

            # take average of start/end width
            size = 0.5 * (FslConverter.convert_to_pixels(layer.arrowWidth(), layer.arrowWidthUnit(), context)
                          + FslConverter.convert_to_pixels(layer.arrowStartWidth(), layer.arrowStartWidthUnit(),
                                                           context))

            res = {
                'color': color_str,
                'size': size
            }

            if symbol_opacity < 1:
                res['opacity'] = symbol_opacity

            results.append(res)

        return results

    @staticmethod
    def simple_fill_to_fsl(
            layer: QgsSimpleFillSymbolLayer,
            context: ConversionContext,
            symbol_opacity: float = 1) -> List[Dict[str, object]]:
        """
        Converts a QGIS simple fill symbol layer to FSL
        """
        if layer.brushStyle() == Qt.NoBrush or not layer.color().isValid() or layer.color().alphaF() == 0:
            return []

        color_str = FslConverter.color_to_fsl(
            layer.color(), context
        )

        res = {
            'color': color_str,
        }

        if symbol_opacity < 1:
            res['opacity'] = symbol_opacity

        if layer.strokeStyle() != Qt.NoPen and layer.strokeColor().alphaF() > 0:
            res['strokeColor'] = FslConverter.color_to_fsl(layer.strokeColor(), context)
            res['strokeWidth'] = FslConverter.convert_to_pixels(layer.strokeWidth(), layer.strokeWidthUnit(), context)
            res['lineJoin'] = FslConverter.convert_join_style(layer.penJoinStyle())

            if layer.strokeStyle() != Qt.SolidLine:
                res['dashArray'] = FslConverter.convert_pen_style(layer.strokeStyle())

        # not supported:
        # - fill offset
        # - fill style

        return [res]

    @staticmethod
    def simple_marker_to_fsl(
            layer: QgsSimpleMarkerSymbolLayer,
            context: ConversionContext,
            symbol_opacity: float = 1) -> List[Dict[str, object]]:
        """
        Converts a QGIS simple marker symbol layer to FSL
        """
        has_fill = layer.color().isValid() and layer.color().alphaF() > 0
        has_stroke = layer.strokeColor().alphaF() > 0 and layer.strokeStyle() != Qt.NoPen
        if not has_fill and not has_stroke:
            return []

        color_str = FslConverter.color_to_fsl(
            layer.color(), context
        )
        size = FslConverter.convert_to_pixels(layer.size(), layer.sizeUnit(), context)

        stroke_width = FslConverter.convert_to_pixels(layer.strokeWidth(), layer.strokeWidthUnit(), context)

        res = {
            'color': color_str,
            'size': size,
            'strokeColor': FslConverter.color_to_fsl(layer.strokeColor(),
                                                     context) if has_stroke else "rgba(0, 0, 0, 0)",
            'strokeWidth': stroke_width
        }

        if symbol_opacity < 1:
            res['opacity'] = symbol_opacity

        # not supported:
        # - marker shape
        # - offset
        # - rotation

        return [res]

    @staticmethod
    def ellipse_marker_to_fsl(
            layer: QgsEllipseSymbolLayer,
            context: ConversionContext,
            symbol_opacity: float = 1) -> List[Dict[str, object]]:
        """
        Converts a QGIS ellipse marker symbol layer to FSL
        """
        has_fill = layer.color().isValid() and layer.color().alphaF() > 0
        has_stroke = layer.strokeColor().alphaF() > 0 and layer.strokeStyle() != Qt.NoPen
        if not has_fill and not has_stroke:
            return []

        color_str = FslConverter.color_to_fsl(
            layer.color(), context
        )
        size = max(FslConverter.convert_to_pixels(layer.symbolHeight(), layer.symbolHeightUnit(), context),
                   FslConverter.convert_to_pixels(layer.symbolWidth(), layer.symbolWidthUnit(), context))

        stroke_width = FslConverter.convert_to_pixels(layer.strokeWidth(), layer.strokeWidthUnit(), context)

        res = {
            'color': color_str,
            'size': size,
            'strokeColor': FslConverter.color_to_fsl(layer.strokeColor(),
                                                     context) if has_stroke else "rgba(0, 0, 0, 0)",
            'strokeWidth': stroke_width
        }

        if symbol_opacity < 1:
            res['opacity'] = symbol_opacity

        # not supported:
        # - marker shape
        # - offset
        # - rotation

        return [res]

    @staticmethod
    def svg_marker_to_fsl(
            layer: QgsSvgMarkerSymbolLayer,
            context: ConversionContext,
            symbol_opacity: float = 1) -> List[Dict[str, object]]:
        """
        Converts a QGIS SVG marker symbol layer to FSL. Simplistic color/size conversion only.
        """
        has_fill = layer.fillColor().isValid() and layer.fillColor().alphaF() > 0
        has_stroke = layer.strokeColor().alphaF() > 0
        if not has_fill and not has_stroke:
            return []

        context.push_warning('SVG markers are not supported, converting to a solid marker')

        color_str = FslConverter.color_to_fsl(
            layer.fillColor(), context
        )
        size = FslConverter.convert_to_pixels(layer.size(), layer.sizeUnit(), context)

        stroke_width = FslConverter.convert_to_pixels(layer.strokeWidth(), layer.strokeWidthUnit(), context)

        res = {
            'color': color_str,
            'size': size,
            'strokeColor': FslConverter.color_to_fsl(layer.strokeColor(),
                                                     context) if has_stroke else "rgba(0, 0, 0, 0)",
            'strokeWidth': stroke_width
        }

        if symbol_opacity < 1:
            res['opacity'] = symbol_opacity

        # not supported:
        # - SVG graphic
        # - offset
        # - rotation

        return [res]

    @staticmethod
    def font_marker_to_fsl(
            layer: QgsFontMarkerSymbolLayer,
            context: ConversionContext,
            symbol_opacity: float = 1) -> List[Dict[str, object]]:
        """
        Converts a QGIS font marker symbol layer to FSL. Simplistic color/size conversion only.
        """
        has_fill = layer.color().isValid() and layer.color().alphaF() > 0
        has_stroke = layer.strokeColor().alphaF() > 0
        if not has_fill and not has_stroke:
            return []

        context.push_warning('Font markers are not supported, converting to a solid marker')

        color_str = FslConverter.color_to_fsl(
            layer.color(), context
        )
        size = FslConverter.convert_to_pixels(layer.size(), layer.sizeUnit(), context)

        stroke_width = FslConverter.convert_to_pixels(layer.strokeWidth(), layer.strokeWidthUnit(), context)

        res = {
            'color': color_str,
            'size': size,
            'strokeColor': FslConverter.color_to_fsl(layer.strokeColor(),
                                                     context) if has_stroke else "rgba(0, 0, 0, 0)",
            'strokeWidth': stroke_width
        }

        if symbol_opacity < 1:
            res['opacity'] = symbol_opacity

        # not supported:
        # - font graphic
        # - offset
        # - rotation

        return [res]

    @staticmethod
    def filled_marker_to_fsl(
            layer: QgsFontMarkerSymbolLayer,
            context: ConversionContext,
            symbol_opacity: float = 1) -> List[Dict[str, object]]:
        """
        Converts a QGIS filled marker symbol layer to FSL. Simplistic color/size conversion only.
        """
        converted_subsymbol = FslConverter.symbol_to_fsl(layer.subSymbol(), context)
        if not converted_subsymbol:
            return []

        context.push_warning('Filled markers are not supported, converting to a solid marker')
        results = []
        for converted_layer in converted_subsymbol:
            color_str = converted_layer.get('color')
            stroke_color_str = converted_layer.get('strokeColor')
            stroke_width = converted_layer.get('strokeWidth')

            size = FslConverter.convert_to_pixels(layer.size(), layer.sizeUnit(), context)

            res = {
                'size': size,
                'color': color_str or "rgba(0, 0, 0, 0)",
                'strokeColor': stroke_color_str or "rgba(0, 0, 0, 0)",
            }
            if stroke_width is not None:
                res['strokeWidth'] = stroke_width

            if symbol_opacity < 1:
                res['opacity'] = symbol_opacity

            results.append(res)

        # not supported:
        # - marker shape
        # - offset
        # - rotation

        return results

    @staticmethod
    def shapeburst_fill_to_fsl(
            layer: QgsShapeburstFillSymbolLayer,
            context: ConversionContext,
            symbol_opacity: float = 1) -> List[Dict[str, object]]:
        """
        Converts a QGIS shapeburst fill symbol layer to FSL
        """
        color = layer.color() if layer.color().isValid() and layer.color().alphaF() > 0 else layer.color2()
        if not color.isValid() or color.alphaF() == 0:
            return []

        context.push_warning('Shapeburst fills are not supported, converting to a solid fill')

        color_str = FslConverter.color_to_fsl(
            color, context
        )

        res = {
            'color': color_str,
        }

        if symbol_opacity < 1:
            res['opacity'] = symbol_opacity

        res['strokeColor'] = "rgba(0, 0, 0, 0)"

        return [res]

    @staticmethod
    def gradient_fill_to_fsl(
            layer: QgsGradientFillSymbolLayer,
            context: ConversionContext,
            symbol_opacity: float = 1) -> List[Dict[str, object]]:
        """
        Converts a QGIS gradient fill symbol layer to FSL
        """
        color = layer.color() if layer.color().isValid() and layer.color().alphaF() > 0 else layer.color2()
        if not color.isValid() or color.alphaF() == 0:
            return []

        context.push_warning('Gradient fills are not supported, converting to a solid fill')

        color_str = FslConverter.color_to_fsl(
            color, context
        )

        res = {
            'color': color_str,
        }

        if symbol_opacity < 1:
            res['opacity'] = symbol_opacity

        res['strokeColor'] = "rgba(0, 0, 0, 0)"

        return [res]

    @staticmethod
    def line_pattern_fill_to_fsl(
            layer: QgsLinePatternFillSymbolLayer,
            context: ConversionContext,
            symbol_opacity: float = 1) -> List[Dict[str, object]]:
        """
        Converts a QGIS line pattern fill symbol layer to FSL
        """
        line_symbol = layer.subSymbol()
        if line_symbol is None:
            return []

        converted_line = FslConverter.symbol_to_fsl(line_symbol, context)
        if not converted_line:
            return []

        # very basic conversion, best we can do is take the color of the line fill...
        color = layer.subSymbol().color()
        if not color.isValid() or color.alphaF() == 0:
            return []

        context.push_warning('Line pattern fills are not supported, converting to a solid fill')

        color_str = FslConverter.color_to_fsl(
            color, context
        )

        res = {
            'color': color_str,
        }

        if symbol_opacity < 1:
            res['opacity'] = symbol_opacity

        res['strokeColor'] = "rgba(0, 0, 0, 0)"

        return [res]

    @staticmethod
    def point_pattern_fill_to_fsl(
            layer: QgsPointPatternFillSymbolLayer,
            context: ConversionContext,
            symbol_opacity: float = 1) -> List[Dict[str, object]]:
        """
        Converts a QGIS point pattern fill symbol layer to FSL
        """
        marker_symbol = layer.subSymbol()
        if marker_symbol is None:
            return []

        converted_marker = FslConverter.symbol_to_fsl(marker_symbol, context)
        if not converted_marker:
            return []

        context.push_warning('Point pattern fills are not supported, converting to a solid fill')
        results = []
        for converted_layer in converted_marker:
            color_str = converted_layer.get('color')
            if not color_str:
                continue

            res = {
                'color': color_str,
                'strokeColor': "rgba(0, 0, 0, 0)",
            }

            if symbol_opacity < 1:
                res['opacity'] = symbol_opacity

            results.append(res)

        return results

    @staticmethod
    def centroid_fill_to_fsl(
            layer: QgsCentroidFillSymbolLayer,
            context: ConversionContext,
            symbol_opacity: float = 1) -> List[Dict[str, object]]:
        """
        Converts a QGIS centroid fill symbol layer to FSL
        """
        marker_symbol = layer.subSymbol()
        if marker_symbol is None:
            return []

        converted_marker = FslConverter.symbol_to_fsl(marker_symbol, context)
        if not converted_marker:
            return []

        context.push_warning('Centroid fills are not supported, converting to a solid fill')

        results = []
        for converted_layer in converted_marker:
            color_str = converted_layer.get('color')
            if not color_str:
                continue

            res = {
                'color': color_str,
                'strokeColor': "rgba(0, 0, 0, 0)",
            }

            if symbol_opacity < 1:
                res['opacity'] = symbol_opacity

            results.append(res)

        return results

    @staticmethod
    def random_marker_fill_to_fsl(
            layer: QgsRandomMarkerFillSymbolLayer,
            context: ConversionContext,
            symbol_opacity: float = 1) -> List[Dict[str, object]]:
        """
        Converts a QGIS random marker fill symbol layer to FSL
        """
        marker_symbol = layer.subSymbol()
        if marker_symbol is None:
            return []

        converted_marker = FslConverter.symbol_to_fsl(marker_symbol, context)
        if not converted_marker:
            return []

        context.push_warning('Random marker fills are not supported, converting to a solid fill')

        results = []
        for converted_layer in converted_marker:
            color_str = converted_layer.get('color')
            if not color_str:
                continue

            res = {
                'color': color_str,
                'strokeColor': "rgba(0, 0, 0, 0)",
            }

            if symbol_opacity < 1:
                res['opacity'] = symbol_opacity

            results.append(res)

        return results

    @staticmethod
    def svg_fill_to_fsl(
            layer: QgsSVGFillSymbolLayer,
            context: ConversionContext,
            symbol_opacity: float = 1) -> List[Dict[str, object]]:
        """
        Converts a QGIS SVG fill symbol layer to FSL
        """
        # very basic conversion, best we can do is take the color of the fill
        color = layer.svgFillColor()
        if not color.isValid() or color.alphaF() == 0:
            return []

        context.push_warning('SVG fills are not supported, converting to a solid fill')

        color_str = FslConverter.color_to_fsl(
            color, context
        )

        res = {
            'color': color_str,
        }

        if symbol_opacity < 1:
            res['opacity'] = symbol_opacity

        res['strokeColor'] = "rgba(0, 0, 0, 0)"

        return [res]
