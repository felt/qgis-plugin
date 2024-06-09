"""
QGIS to FSL conversion
"""

import math
from collections import defaultdict
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
    NULL,
    QgsMapLayer,
    QgsVectorLayer,
    QgsRasterLayer,
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
    QgsUnitTypes,
    QgsFeatureRenderer,
    QgsSingleSymbolRenderer,
    QgsNullSymbolRenderer,
    QgsCategorizedSymbolRenderer,
    QgsGraduatedSymbolRenderer,
    QgsRuleBasedRenderer,
    QgsPalLayerSettings,
    QgsTextFormat,
    QgsStringUtils,
    QgsExpression,
    QgsExpressionNode,
    QgsExpressionNodeBinaryOperator,
    QgsExpressionNodeInOperator,
    QgsExpressionContext,
    QgsRasterRenderer,
    QgsSingleBandPseudoColorRenderer,
    QgsPalettedRasterRenderer,
    QgsSingleBandGrayRenderer,
    QgsRasterPipe,
    QgsRasterDataProvider,
    QgsColorRampShader,
    QgsHeatmapRenderer
)

from .logger import Logger
from .map_utils import MapUtils


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
        self.warnings: List[Dict[str, object]] = []

    def push_warning(self, warning: str, level: LogLevel = LogLevel.Warning,
                     detail: Optional[Dict[str, object]] = None):
        """
        Pushes a warning to the context
        """
        if not detail:
            detail = {}

        detail['message'] = warning
        detail['level'] = level.name
        self.warnings.append(detail)

    def format_warnings_for_reporting(self) -> Dict[str, object]:
        """
        Collates and formats warnings for reporting via the API
        """
        collated_warnings = defaultdict(int)
        for warning in self.warnings:
            summary = warning.get('summary')
            if not summary:
                continue

            collated_warnings[summary] += 1

        res = {
            'type': Logger.FSL_CONVERSION,
            'warnings': self.warnings,
        }

        for k, v in collated_warnings.items():
            res[k] = v

        return res


class FslConverter:
    NULL_COLOR = "rgba(0, 0, 0, 0)"
    COLOR_RAMP_INTERPOLATION_STEPS = 30
    SOLID_LINE_DASH_HACK = [1, 0]

    @staticmethod
    def create_symbol_dict() -> Dict[str, object]:
        """
        Creates a default symbol dict, to use as a starting point
        for symbol definitions
        """
        return {
            'isClickable': False,
            'isHoverable': False
        }

    @staticmethod
    def expression_to_filter(
            expression: str,
            context: ConversionContext,
            layer: Optional[QgsVectorLayer] = None
    ) -> Optional[List]:
        """
        Attempts to convert a QGIS expression to a FSL filter

        Returns None if conversion fails
        """
        exp = QgsExpression(expression)
        expression_context = QgsExpressionContext()
        if layer:
            expression_context.appendScope(
                layer.createExpressionContextScope())

        exp.prepare(expression_context)

        if exp.hasParserError():
            context.push_warning(
                'Invalid expressions cannot be converted',
                detail={
                    'object': 'expression',
                    'expression': expression,
                    'cause': 'parser_error',
                    'summary': 'invalid expression'
                }
            )
            return None

        if exp.rootNode():
            success, res = (
                FslConverter.walk_expression(exp.rootNode(), context))
            if success:
                return res

        context.push_warning(
            'Empty expressions cannot be converted',
            detail={
                'object': 'expression',
                'expression': expression,
                'cause': 'no_root_node',
                'summary': 'expression with no root node'
            }
        )
        return None

    @staticmethod
    def walk_expression(node: QgsExpressionNode, context: ConversionContext):
        """
        Visitor for QGIS expression nodes
        """
        if node is None:
            return False, None
        elif node.nodeType() == QgsExpressionNode.ntBinaryOperator:
            return FslConverter.handle_binary(node, context)
        elif node.nodeType() == QgsExpressionNode.ntInOperator:
            return FslConverter.handle_in(node, context)
        elif node.nodeType() == QgsExpressionNode.ntLiteral:
            return True, node.value()
        elif node.nodeType() == QgsExpressionNode.ntColumnRef:
            return True, node.name()

        context.push_warning(
            'Expression is not supported',
            detail={
                'object': 'expression',
                'expression': node.dump(),
                'cause': 'unhandled_node_type',
                'summary': 'unhandled expression node type {}'.format(
                    node.nodeType())
            }
        )

        return False, None

    @staticmethod
    def handle_binary(node: QgsExpressionNodeBinaryOperator,
                      context: ConversionContext):
        """
        Convert a binary node
        """
        left_ok, left = FslConverter.walk_expression(node.opLeft(), context)
        if not left_ok:
            return False, None
        right_ok, right = FslConverter.walk_expression(node.opRight(), context)
        if not right_ok:
            return False, None

        if node.op() == QgsExpressionNodeBinaryOperator.BinaryOperator.boEQ:
            return True, [left, "in", [right]]
        if node.op() == QgsExpressionNodeBinaryOperator.BinaryOperator.boNE:
            return True, [left, "ni", [right]]
        if node.op() == QgsExpressionNodeBinaryOperator.BinaryOperator.boGT:
            return True, [left, "gt", right]
        if node.op() == QgsExpressionNodeBinaryOperator.BinaryOperator.boLT:
            return True, [left, "lt", right]
        if node.op() == QgsExpressionNodeBinaryOperator.BinaryOperator.boGE:
            return True, [left, "ge", right]
        if node.op() == QgsExpressionNodeBinaryOperator.BinaryOperator.boLE:
            return True, [left, "le", right]
        if node.op() == QgsExpressionNodeBinaryOperator.BinaryOperator.boIs:
            return True, [left, "is", right]
        if node.op() == QgsExpressionNodeBinaryOperator.BinaryOperator.boIsNot:
            return True, [left, "isnt", right]

        context.push_warning(
            'Expression is not supported',
            detail={
                'object': 'expression',
                'expression': node.dump(),
                'cause': 'unhandled_binary_node',
                'summary': 'unhandled expression binary '
                           'node operator {}'.format(
                    node.op())
            }
        )
        return False, None

    @staticmethod
    def handle_in(node: QgsExpressionNodeInOperator,
                  context: ConversionContext):
        """
        Convert an In node
        """
        left_ok, left = FslConverter.walk_expression(node.node(), context)
        if not left_ok:
            return False, None

        converted_list = []
        for v in node.list().list():
            val_ok, val = FslConverter.walk_expression(v, context)
            if not val_ok:
                return False, None
            converted_list.append(val)

        if node.isNotIn():
            return True, [left, "ni", converted_list]

        return True, [left, "in", converted_list]

    @staticmethod
    def vector_layer_to_fsl(
            layer: QgsVectorLayer,
            context: ConversionContext
    ) -> Optional[Dict[str, object]]:
        """
        Converts a vector layer to FSL
        """
        fsl = FslConverter.vector_renderer_to_fsl(
            layer.renderer(), context, layer.opacity()
        )
        if not fsl:
            fsl = {}

        FslConverter.add_common_layer_properties_to_fsl(
            layer, fsl, context
        )

        return fsl or None

    @staticmethod
    def vector_renderer_to_fsl(renderer: QgsFeatureRenderer,
                               context: ConversionContext,
                               layer_opacity: float = 1) \
            -> Optional[Dict[str, object]]:
        """
        Converts a QGIS vector renderer to FSL
        """
        if not renderer:
            return None

        RENDERER_CONVERTERS = {
            QgsSingleSymbolRenderer: FslConverter.single_renderer_to_fsl,
            QgsCategorizedSymbolRenderer:
                FslConverter.categorized_renderer_to_fsl,
            QgsGraduatedSymbolRenderer:
                FslConverter.graduated_renderer_to_fsl,
            QgsRuleBasedRenderer:
                FslConverter.rule_based_renderer_to_fsl,
            QgsNullSymbolRenderer: FslConverter.null_renderer_to_fsl,
            QgsHeatmapRenderer: FslConverter.heatmap_renderer_to_fsl,

            # No meaningful conversions for these types:
            # Qgs25DRenderer
            # QgsEmbeddedSymbolRenderer
            # QgsPointClusterRenderer
            # QgsPointDisplacementRenderer
            # QgsInvertedPolygonRenderer
        }

        for _class, converter in RENDERER_CONVERTERS.items():
            if isinstance(renderer, _class):
                return converter(renderer, context, layer_opacity)

        context.push_warning('{} renderers cannot be converted yet'.format(
            renderer.__class__.__name__),
            LogLevel.Error,
            detail={
                'object': 'renderer',
                'renderer': renderer.__class__.__name__,
                'cause': 'unhandled_renderer',
                'summary': 'unhandled renderer {}'.format(
                    renderer.__class__.__name__)
            })
        return None

    @staticmethod
    def single_renderer_to_fsl(renderer: QgsSingleSymbolRenderer,
                               context: ConversionContext,
                               layer_opacity: float = 1) \
            -> Optional[Dict[str, object]]:
        """
        Converts a QGIS single symbol renderer to an FSL definition
        """
        if not renderer.symbol():
            context.push_warning(
                'Renderer without a symbol cannot be converted',
                LogLevel.Error,
                detail={
                    'object': 'renderer',
                    'renderer': 'single',
                    'cause': 'no_symbol',
                    'summary': 'single symbol renderer with no symbol'
                })
            return None

        converted_symbol = FslConverter.symbol_to_fsl(renderer.symbol(),
                                                      context,
                                                      layer_opacity)
        if not converted_symbol:
            return None

        return {
            "style": converted_symbol[0] if len(converted_symbol) == 1
            else converted_symbol,
            "legend": {},
            "type": "simple"
        }

    @staticmethod
    def rule_based_renderer_to_fsl(
            renderer: QgsRuleBasedRenderer,
            context: ConversionContext,
            layer_opacity: float = 1) \
            -> Optional[Dict[str, object]]:
        """
        Converts a QGIS rule based renderer to an FSL definition
        """
        if not renderer.rootRule().children():
            # treat no rules as a null renderer
            return {
                "style": {
                    "color": FslConverter.NULL_COLOR,
                    "strokeColor": FslConverter.NULL_COLOR,
                    "isClickable": False,
                    "isHoverable": False
                },
                "legend": {},
                "type": "simple"
            }

        # single rule
        if (len(renderer.rootRule().children()) == 1 and
                not renderer.rootRule().children()[0].children()):

            target_rule = renderer.rootRule().children()[0]
            converted_symbol = FslConverter.symbol_to_fsl(
                target_rule.symbol(),
                context,
                layer_opacity)
            if not converted_symbol:
                return None

            res = {
                "style": converted_symbol[0] if len(converted_symbol) == 1
                else converted_symbol,
                "legend": {},
                "type": "simple"
            }

            if target_rule.filterExpression():
                converted_filter = FslConverter.expression_to_filter(
                    target_rule.filterExpression(),
                    context
                )
                if converted_filter is not None:
                    res['filters'] = converted_filter

            return res

        # multiple rules. can we treat this as a categorized renderer?
        filter_attribute = None
        converted_symbols = []
        category_values = []
        other_symbol = None
        legend_text = {}

        for rule in renderer.rootRule().children():
            if rule.children():
                # rule has nested children, can't convert
                context.push_warning(
                    'Rule based renderer with nested rules '
                    'cannot be converted',
                    LogLevel.Error,
                    detail={
                        'object': 'renderer',
                        'renderer': 'rule_based',
                        'cause': 'nested_rules',
                        'summary': 'rule based renderer with nested rules'
                    })
                return None

            if not rule.symbol():
                # no symbol rule, can't convert
                context.push_warning(
                    'Rule based renderer with a rule without a '
                    'symbol cannot be converted',
                    LogLevel.Error,
                    detail={
                        'object': 'renderer',
                        'renderer': 'rule_based',
                        'cause': 'null_symbol_rule',
                        'summary': 'rule based renderer with rule with '
                                   'no symbol'
                    })
                return None

            if rule.dependsOnScale():
                # rule has scale based visibility, can't convert
                context.push_warning(
                    'Rule based renderer with scale based rule '
                    'visibility cannot be converted',
                    LogLevel.Error,
                    detail={
                        'object': 'renderer',
                        'renderer': 'rule_based',
                        'cause': 'scale_based_rule',
                        'summary': 'rule based renderer with scaled '
                                   'based rules'
                    })
                return None

            filter_expression = rule.filterExpression()
            if not filter_expression:
                # multiple symbol per feature, can't convert
                context.push_warning(
                    'Rule based renderer with rules without '
                    'filters cannot be converted',
                    LogLevel.Error,
                    detail={
                        'object': 'renderer',
                        'renderer': 'rule_based',
                        'cause': 'no_filter_rule',
                        'summary': 'rule based renderer with no filter rule'
                    })
                return None

            if not rule.isElse():
                res, field, value = QgsExpression.isFieldEqualityExpression(
                    filter_expression
                )
                if not res:
                    # not a simple field=value expression, can't convert
                    context.push_warning(
                        'Rule based renderer with complex '
                        'filters cannot be converted',
                        LogLevel.Error,
                        detail={
                            'object': 'renderer',
                            'renderer': 'rule_based',
                            'cause': 'complex_filter_rule',
                            'filter': filter_expression,
                            'summary': 'rule based renderer with '
                                       'complex filter'
                        })
                    return None

                if filter_attribute and filter_attribute != field:
                    # rules depend on different attributes, can't convert
                    context.push_warning(
                        'Rule based renderer with complex '
                        'filters cannot be converted',
                        LogLevel.Error,
                        detail={
                            'object': 'renderer',
                            'renderer': 'rule_based',
                            'cause': 'mixed_attribute_filter_rules',
                            'summary': 'rule based renderer with '
                                       'mixed attribute rules'
                        })
                    return None

                filter_attribute = field

            converted_symbol = FslConverter.symbol_to_fsl(rule.symbol(),
                                                          context,
                                                          layer_opacity)
            if not converted_symbol:
                # can't convert symbol
                return None

            if rule.isElse():
                if other_symbol:
                    # multiple ELSE rules, can't convert
                    context.push_warning(
                        'Rule based renderer with multiple '
                        'ELSE rules cannot be converted',
                        LogLevel.Error,
                        detail={
                            'object': 'renderer',
                            'renderer': 'rule_based',
                            'cause': 'multiple_else_rules',
                            'summary': 'rule based renderer with '
                                       'multiple else rules'
                        })
                    return None
                other_symbol = converted_symbol
                legend_text['Other'] = rule.label()
            else:
                converted_symbols.append(converted_symbol)
                legend_text[str(value)] = rule.label()
                category_values.append(str(value))

        all_symbols = converted_symbols
        if other_symbol:
            all_symbols.append(other_symbol)

        if not all_symbols:
            return None

        style = FslConverter.create_varying_style_from_list(
            all_symbols
        )

        return {
            "config": {
                "categoricalAttribute": filter_attribute,
                "categories": category_values,
                "showOther": bool(other_symbol)
            },
            "legend": {
                "displayName": legend_text
            },
            "style": style,
            "type": "categorical"
        }

    @staticmethod
    def heatmap_renderer_to_fsl(renderer: QgsHeatmapRenderer,
                                context: ConversionContext,
                                layer_opacity: float = 1) \
            -> Optional[Dict[str, object]]:
        """
        Converts a QGIS heatmap renderer to an FSL definition
        """
        colors = []
        ramp = renderer.colorRamp()
        for i in range(FslConverter.COLOR_RAMP_INTERPOLATION_STEPS):
            val = i / FslConverter.COLOR_RAMP_INTERPOLATION_STEPS
            color = ramp.color(val)
            colors.append(color.name())

        if renderer.weightExpression():
            context.push_warning(
                'Heatmap point weighting cannot be converted',
                LogLevel.Warning,
                detail={
                    'object': 'renderer',
                    'renderer': 'heatmap',
                    'cause': 'heatmap_point_weight',
                    'summary': 'heatmap with point weighting'
                })

        return {
            "style": {
                "color": colors,
                "opacity": layer_opacity,
                "size": FslConverter.convert_to_pixels(
                    renderer.radius(), renderer.radiusUnit(),
                    context),
                "intensity": 1
            },
            "legend": {"displayName": {"0": "Low", "1": "High"}},
            "type": "heatmap"
        }

    @staticmethod
    def null_renderer_to_fsl(renderer: QgsNullSymbolRenderer,
                             context: ConversionContext,
                             layer_opacity: float = 1) \
            -> Optional[Dict[str, object]]:
        """
        Converts a QGIS null renderer to an FSL definition
        """
        return {
            "style": {
                "color": FslConverter.NULL_COLOR,
                "strokeColor": FslConverter.NULL_COLOR,
                "isClickable": False,
                "isHoverable": False
            },
            "legend": {},
            "type": "simple"
        }

    @staticmethod
    def create_varying_style_from_list(
            styles: List[List[Dict[str, object]]]) -> List[Dict[str, object]]:
        """
        Given a list of individual styles, try to create a single
        varying style from them
        """
        if len(styles) < 1:
            return []

        any_has_dash_array = False
        for symbol in styles:
            for layer in symbol:
                if 'dashArray' in layer:
                    any_has_dash_array = True

        result = []
        # upgrade all properties in first symbol to lists
        first_symbol = styles[0]
        for layer in first_symbol:
            list_dict = {}
            for key, value in layer.items():
                list_dict[key] = [value]

            if any_has_dash_array and 'dashArray' not in list_dict:
                list_dict['dashArray'] = [FslConverter.SOLID_LINE_DASH_HACK]
            result.append(list_dict)

        for symbol in styles[1:]:
            for layer_idx, target_layer in enumerate(result):
                if layer_idx >= len(symbol):
                    source_layer = None
                else:
                    source_layer = symbol[layer_idx]

                for key, value in target_layer.items():
                    # if property doesn't exist in this layer, copy from first
                    # symbol
                    if source_layer and key in source_layer:
                        value.append(source_layer[key])
                    elif key == 'dashArray':
                        value.append(FslConverter.SOLID_LINE_DASH_HACK)
                    else:
                        value.append(value[0])

        res = FslConverter.simplify_style(result)

        return res

    @staticmethod
    def simplify_style(style: List[Dict[str, object]]) \
            -> List[Dict[str, object]]:
        """
        Tries to simplify a style, by collapsing lists of the same
        value to a single value
        """
        # re-collapse single value lists to single values
        cleaned_style = []
        for layer in style:
            cleaned_layer = {}
            for key, value in layer.items():
                if (isinstance(value, list) and
                        all(v == value[0] for v in value)):
                    cleaned_layer[key] = value[0]
                else:
                    cleaned_layer[key] = value
            cleaned_style.append(cleaned_layer)
        return cleaned_style

    @staticmethod
    def categorized_renderer_to_fsl(
            renderer: QgsCategorizedSymbolRenderer,
            context: ConversionContext,
            layer_opacity: float = 1) \
            -> Optional[Dict[str, object]]:
        """
        Converts a QGIS categorized symbol renderer to an FSL definition
        """
        if not renderer.categories():
            context.push_warning(
                'Categorized renderer with no categories cannot be converted',
                LogLevel.Error,
                detail={
                    'object': 'renderer',
                    'renderer': 'categorized',
                    'cause': 'no_categories',
                    'summary': 'categorized renderer with no categories'
                })
            return None

        converted_symbols = []
        category_values = []
        other_symbol = None
        legend_text = {}
        for category in renderer.categories():
            converted_symbol = FslConverter.symbol_to_fsl(category.symbol(),
                                                          context,
                                                          layer_opacity)
            if converted_symbol:
                if category.value() == NULL:
                    other_symbol = converted_symbol
                    legend_text['Other'] = category.label()
                else:
                    converted_symbols.append(converted_symbol)
                    legend_text[str(category.value())] = category.label()
                    category_values.append(str(category.value()))

        all_symbols = converted_symbols
        if other_symbol:
            all_symbols.append(other_symbol)

        if not all_symbols:
            return None

        style = FslConverter.create_varying_style_from_list(
            all_symbols
        )

        return {
            "config": {
                "categoricalAttribute": renderer.classAttribute(),
                "categories": category_values,
                "showOther": bool(other_symbol)
            },
            "legend": {
                "displayName": legend_text
            },
            "style": style,
            "type": "categorical"
        }

    @staticmethod
    def graduated_renderer_to_fsl(
            renderer: QgsGraduatedSymbolRenderer,
            context: ConversionContext,
            layer_opacity: float = 1) \
            -> Optional[Dict[str, object]]:
        """
        Converts a QGIS categorized symbol renderer to an FSL definition
        """
        if not renderer.ranges():
            context.push_warning(
                'Graduated renderer with no ranges cannot be converted',
                LogLevel.Error,
                detail={
                    'object': 'renderer',
                    'renderer': 'graduated',
                    'cause': 'no_ranges',
                    'summary': 'graduated renderer with no ranges'
                })
            return None

        converted_symbols = []
        range_breaks = []
        legend_text = {}

        # we have to sort ranges in ascending order for FSL compatiblity
        ranges = renderer.ranges()
        ranges.sort(key=lambda r: r.lowerValue())

        for idx, _range in enumerate(ranges):
            converted_symbol = FslConverter.symbol_to_fsl(_range.symbol(),
                                                          context,
                                                          layer_opacity)
            if converted_symbol:
                converted_symbols.append(converted_symbol)
                legend_text[str(idx)] = _range.label()
                if idx == 0:
                    range_breaks.append(_range.lowerValue())
                range_breaks.append(_range.upperValue())

        if not converted_symbols:
            return None

        style = FslConverter.create_varying_style_from_list(
            converted_symbols
        )

        return {
            "config": {
                "numericAttribute": renderer.classAttribute(),
                "steps": range_breaks
            },
            "legend": {
                "displayName": legend_text
            },
            "style": style,
            "type": "numeric"
        }

    @staticmethod
    def symbol_to_fsl(symbol: QgsSymbol,
                      context: ConversionContext,
                      opacity: float = 1) \
            -> List[Dict[str, object]]:
        """
        Converts a QGIS symbol to an FSL definition

        Returns an empty list if no symbol should be used
        """
        enabled_layers = [symbol[i] for i in range(len(symbol)) if
                          symbol[i].enabled()]
        if not enabled_layers:
            return []

        enabled_layers.reverse()

        symbol_opacity = opacity * symbol.opacity()
        fsl_layers = []
        for layer in enabled_layers:
            fsl_layers.extend(
                FslConverter.symbol_layer_to_fsl(layer, context,
                                                 symbol_opacity)
            )

        if fsl_layers and symbol.hasDataDefinedProperties():
            context.push_warning(
                'Data defined properties cannot be converted',
                LogLevel.Warning,
                detail={
                    'object': 'symbol',
                    'cause': 'symbol_data_defined_properties',
                    'summary': 'symbol data defined properties'
                })

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
            QgsLinePatternFillSymbolLayer:
                FslConverter.line_pattern_fill_to_fsl,
            QgsSVGFillSymbolLayer: FslConverter.svg_fill_to_fsl,
            QgsPointPatternFillSymbolLayer:
                FslConverter.point_pattern_fill_to_fsl,
            QgsCentroidFillSymbolLayer: FslConverter.centroid_fill_to_fsl,
            QgsRandomMarkerFillSymbolLayer:
                FslConverter.random_marker_fill_to_fsl,

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
                if layer.hasDataDefinedProperties():
                    context.push_warning(
                        'Data defined properties cannot be converted',
                        LogLevel.Warning,
                        detail={
                            'object': 'symbol_layer',
                            'cause': 'layer_data_defined_properties',
                            'summary': 'symbol layer data defined properties'
                        })
                return converter(layer, context, symbol_opacity)

        context.push_warning('{} symbol layers cannot be converted yet'.format(
            layer.__class__.__name__),
            LogLevel.Error,
            detail={
                'object': 'symbol_layer',
                'layer_type': layer.__class__.__name__,
                'cause': 'not_supported',
                'summary': 'unhandled symbol layer type {}'.format(
                    layer.__class__.__name__)
            })
        return []

    @staticmethod
    def color_to_fsl(color: QColor, context: ConversionContext,
                     opacity: float = 1) -> Optional[str]:
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
    def convert_stroke_to_pixels(
            size,
            size_unit: QgsUnitTypes.RenderUnit,
            context: ConversionContext
    ):
        """
        Converts a stroke size to pixels
        """
        if size == 0:
            # handle hairline sizes
            return 1

        res = FslConverter.convert_to_pixels(
            size, size_unit, context, True
        )
        # round up to at least 1 pixel
        return max(res, 1)

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
        if (layer.penStyle() == Qt.NoPen or
                not layer.color().isValid() or
                layer.color().alphaF() == 0):
            return []

        color_str = FslConverter.color_to_fsl(
            layer.color(), context
        )
        stroke_width = FslConverter.convert_stroke_to_pixels(
            layer.width(),
            layer.widthUnit(),
            context)

        res = FslConverter.create_symbol_dict()
        res['color'] = color_str
        res['size'] = stroke_width
        res['lineCap'] = FslConverter.convert_cap_style(layer.penCapStyle())
        res['lineJoin'] = FslConverter.convert_join_style(layer.penJoinStyle())

        if symbol_opacity < 1:
            res['opacity'] = symbol_opacity

        if layer.useCustomDashPattern():
            res['dashArray'] = [FslConverter.convert_to_pixels(
                part,
                layer.customDashPatternUnit(), context, round_size=False) for
                part in layer.customDashVector()]
        elif layer.penStyle() != Qt.SolidLine:
            res['dashArray'] = FslConverter.convert_pen_style(layer.penStyle())

        # not supported:
        # - line offset
        # - pattern offset
        # - trim lines

        if layer.offset():
            context.push_warning(
                'Offsets for line symbols cannot be converted',
                LogLevel.Warning,
                detail={
                    'object': 'symbol_layer',
                    'cause': 'line_offset',
                    'summary': 'simple line with offset'
                })

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

        context.push_warning(
            'Marker lines are not supported, converting to a solid line',
            LogLevel.Warning,
            detail={
                'object': 'symbol_layer',
                'cause': 'marker_line',
                'summary': 'marker line'
            })

        results = []
        for converted_layer in converted_marker:
            color_str = converted_layer.get('color')
            if not color_str:
                continue

            res = FslConverter.create_symbol_dict()
            res['color'] = color_str

            if layer.placement() == QgsMarkerLineSymbolLayer.Interval:
                interval_pixels = FslConverter.convert_to_pixels(
                    layer.interval(), layer.intervalUnit(), context)
                try:
                    # FSL size is radius, not diameter
                    marker_size = float(converted_layer['size']) * 2
                except TypeError:
                    continue

                res['dashArray'] = [marker_size, interval_pixels - marker_size]
                res['size'] = marker_size
            else:
                # hardcoded size, there's no point using the marker size as it
                # will visually appear as a much fatter line due to the
                # missing spaces between markers
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

        context.push_warning(
            'Hatched lines are not supported, converting to a solid line',
            LogLevel.Warning,
            detail={
                'object': 'symbol_layer',
                'cause': 'hatched_line',
                'summary': 'hatched line'
            })

        results = []
        for converted_layer in converted_hatch:
            color_str = converted_layer.get('color')
            if not color_str:
                continue

            res = FslConverter.create_symbol_dict()
            res['color'] = color_str

            if layer.placement() == QgsMarkerLineSymbolLayer.Interval:
                interval_pixels = FslConverter.convert_to_pixels(
                    layer.interval(), layer.intervalUnit(), context)
                try:
                    hatch_size = float(converted_layer['size'])
                except TypeError:
                    continue

                res['dashArray'] = [hatch_size, interval_pixels - hatch_size]
                res['size'] = hatch_size
            else:
                # hardcoded size, there's no point using the marker size as it
                # will visually appear as a much fatter line due to the
                # missing spaces between markers
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

        context.push_warning(
            'Arrows lines are not supported, converting to a solid line',
            LogLevel.Warning,
            detail={
                'object': 'symbol_layer',
                'cause': 'arrow',
                'summary': 'arrow line'
            })

        results = []
        for converted_layer in converted_fill:
            color_str = converted_layer.get('color')
            if not color_str:
                continue

            # take average of start/end width
            size = 0.5 * (FslConverter.convert_to_pixels(
                layer.arrowWidth(),
                layer.arrowWidthUnit(),
                context) +
                          FslConverter.convert_to_pixels(
                              layer.arrowStartWidth(),
                              layer.arrowStartWidthUnit(),
                              context))
            res = FslConverter.create_symbol_dict()
            res['color'] = color_str
            res['size'] = size

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
        has_invisible_fill = (layer.brushStyle() == Qt.NoBrush or
                              not layer.color().isValid() or
                              layer.color().alphaF() == 0)
        has_invisible_stroke = (layer.strokeStyle() == Qt.NoPen or
                                not layer.strokeColor().isValid() or
                                layer.strokeColor().alphaF() == 0)
        if has_invisible_fill and has_invisible_stroke:
            return []

        color_str = FslConverter.color_to_fsl(
            layer.color(), context
        ) if not has_invisible_fill else FslConverter.NULL_COLOR

        res = FslConverter.create_symbol_dict()
        res['color'] = color_str

        if symbol_opacity < 1:
            res['opacity'] = symbol_opacity

        if not has_invisible_stroke:
            res['strokeColor'] = FslConverter.color_to_fsl(layer.strokeColor(),
                                                           context)
            res['strokeWidth'] = FslConverter.convert_stroke_to_pixels(
                layer.strokeWidth(), layer.strokeWidthUnit(), context)
            res['lineJoin'] = FslConverter.convert_join_style(
                layer.penJoinStyle())

            if layer.strokeStyle() != Qt.SolidLine:
                res['dashArray'] = FslConverter.convert_pen_style(
                    layer.strokeStyle())
        else:
            res['strokeColor'] = FslConverter.NULL_COLOR

        # not supported:
        # - fill offset
        # - fill style

        if layer.brushStyle() not in (Qt.SolidPattern, Qt.NoBrush):
            context.push_warning(
                'Fill patterns are not supported, converting to a solid fill',
                LogLevel.Warning,
                detail={
                    'object': 'symbol_layer',
                    'cause': 'non_solid_fill_pattern',
                    'summary': 'simple fill with pattern'
                })

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
        has_stroke = (layer.strokeColor().alphaF() > 0 and
                      layer.strokeStyle() != Qt.NoPen)
        if not has_fill and not has_stroke:
            return []

        color_str = FslConverter.color_to_fsl(
            layer.color(), context
        )
        size = FslConverter.convert_to_pixels(layer.size(), layer.sizeUnit(),
                                              context)

        stroke_width = FslConverter.convert_stroke_to_pixels(
            layer.strokeWidth(),
            layer.strokeWidthUnit(),
            context
        )

        res = FslConverter.create_symbol_dict()
        res['color'] = color_str
        res['size'] = size / 2  # FSL size is radius, not diameter
        res['strokeColor'] = (FslConverter.color_to_fsl(layer.strokeColor(),
                                                        context) if has_stroke
                              else FslConverter.NULL_COLOR)
        res['strokeWidth'] = stroke_width

        if symbol_opacity < 1:
            res['opacity'] = symbol_opacity

        if layer.shape() != QgsSimpleMarkerSymbolLayer.Circle:
            context.push_warning(
                'Marker shapes are not supported, converting '
                'to a circle marker',
                LogLevel.Warning,
                detail={
                    'object': 'symbol_layer',
                    'cause': 'non_circle_marker',
                    'summary': 'non circle marker'
                })

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
        has_stroke = (layer.strokeColor().alphaF() > 0 and
                      layer.strokeStyle() != Qt.NoPen)
        if not has_fill and not has_stroke:
            return []

        color_str = FslConverter.color_to_fsl(
            layer.color(), context
        )
        size = max(FslConverter.convert_to_pixels(layer.symbolHeight(),
                                                  layer.symbolHeightUnit(),
                                                  context),
                   FslConverter.convert_to_pixels(layer.symbolWidth(),
                                                  layer.symbolWidthUnit(),
                                                  context))

        stroke_width = FslConverter.convert_stroke_to_pixels(
            layer.strokeWidth(),
            layer.strokeWidthUnit(),
            context
        )

        res = FslConverter.create_symbol_dict()
        res['color'] = color_str
        res['size'] = size / 2  # FSL size is radius, not diameter
        res['strokeColor'] = (FslConverter.color_to_fsl(layer.strokeColor(),
                                                        context)
                              if has_stroke else FslConverter.NULL_COLOR)
        res['strokeWidth'] = stroke_width

        if symbol_opacity < 1:
            res['opacity'] = symbol_opacity

        if layer.shape() != QgsEllipseSymbolLayer.Circle:
            context.push_warning(
                'Marker shapes are not supported, converting '
                'to a circle marker',
                LogLevel.Warning,
                detail={
                    'object': 'symbol_layer',
                    'cause': 'non_circle_marker',
                    'summary': 'non circle ellipse marker'
                })

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
        Converts a QGIS SVG marker symbol layer to FSL. Simplistic color/size
        conversion only.
        """
        has_fill = (layer.fillColor().isValid() and
                    layer.fillColor().alphaF() > 0)
        has_stroke = layer.strokeColor().alphaF() > 0
        if not has_fill and not has_stroke:
            return []

        context.push_warning(
            'SVG markers are not supported, converting to a solid marker',
            LogLevel.Warning,
            detail={
                'object': 'symbol_layer',
                'cause': 'svg_marker',
                'summary': 'svg marker'
            })

        color_str = FslConverter.color_to_fsl(
            layer.fillColor(), context
        )
        size = FslConverter.convert_to_pixels(layer.size(), layer.sizeUnit(),
                                              context)

        stroke_width = FslConverter.convert_stroke_to_pixels(
            layer.strokeWidth(),
            layer.strokeWidthUnit(),
            context
        )

        res = FslConverter.create_symbol_dict()
        res['color'] = color_str
        res['size'] = size / 2  # FSL size is radius, not diameter
        res['strokeColor'] = (FslConverter.color_to_fsl(layer.strokeColor(),
                                                        context)
                              if has_stroke else FslConverter.NULL_COLOR)
        res['strokeWidth'] = stroke_width

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
        Converts a QGIS font marker symbol layer to FSL. Simplistic color/size
        conversion only.
        """
        has_fill = layer.color().isValid() and layer.color().alphaF() > 0
        has_stroke = layer.strokeColor().alphaF() > 0
        if not has_fill and not has_stroke:
            return []

        context.push_warning(
            'Font markers are not supported, converting to a solid marker',
            LogLevel.Warning,
            detail={
                'object': 'symbol_layer',
                'cause': 'font_marker',
                'summary': 'font marker'
            })

        color_str = FslConverter.color_to_fsl(
            layer.color(), context
        )
        size = FslConverter.convert_to_pixels(layer.size(), layer.sizeUnit(),
                                              context)

        stroke_width = FslConverter.convert_stroke_to_pixels(
            layer.strokeWidth(),
            layer.strokeWidthUnit(),
            context
        )

        res = FslConverter.create_symbol_dict()
        res['color'] = color_str
        res['size'] = size / 2  # FSL size is radius, not diameter
        res['strokeColor'] = (FslConverter.color_to_fsl(layer.strokeColor(),
                                                        context)
                              if has_stroke else FslConverter.NULL_COLOR)
        res['strokeWidth'] = stroke_width

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
        Converts a QGIS filled marker symbol layer to FSL. Simplistic
        color/size conversion only.
        """
        converted_subsymbol = FslConverter.symbol_to_fsl(layer.subSymbol(),
                                                         context)
        if not converted_subsymbol:
            return []

        context.push_warning(
            'Filled markers are not supported, converting to a solid marker',
            LogLevel.Warning,
            detail={
                'object': 'symbol_layer',
                'cause': 'filled_marker',
                'summary': 'filled marker'
            })

        results = []
        for converted_layer in converted_subsymbol:
            color_str = converted_layer.get('color')
            stroke_color_str = converted_layer.get('strokeColor')
            stroke_width = converted_layer.get('strokeWidth')

            size = FslConverter.convert_to_pixels(layer.size(),
                                                  layer.sizeUnit(), context)

            res = FslConverter.create_symbol_dict()
            res['size'] = size / 2  # FSL size is radius, not diameter
            res['color'] = color_str or FslConverter.NULL_COLOR
            res['strokeColor'] = stroke_color_str or FslConverter.NULL_COLOR
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
        color = (layer.color() if (layer.color().isValid() and
                                   layer.color().alphaF() > 0)
                 else layer.color2())
        if not color.isValid() or color.alphaF() == 0:
            return []

        context.push_warning(
            'Shapeburst markers are not supported, converting '
            'to a solid marker',
            LogLevel.Warning,
            detail={
                'object': 'symbol_layer',
                'cause': 'shapeburst',
                'summary': 'shapeburst'
            })

        color_str = FslConverter.color_to_fsl(
            color, context
        )

        res = FslConverter.create_symbol_dict()
        res['color'] = color_str

        if symbol_opacity < 1:
            res['opacity'] = symbol_opacity

        res['strokeColor'] = FslConverter.NULL_COLOR

        return [res]

    @staticmethod
    def gradient_fill_to_fsl(
            layer: QgsGradientFillSymbolLayer,
            context: ConversionContext,
            symbol_opacity: float = 1) -> List[Dict[str, object]]:
        """
        Converts a QGIS gradient fill symbol layer to FSL
        """
        color1_valid = layer.color().isValid() and layer.color().alphaF() > 0
        color = layer.color() if color1_valid else layer.color2()
        if not color.isValid() or color.alphaF() == 0:
            return []

        context.push_warning(
            'Gradient fills are not supported, converting to a solid fill',
            LogLevel.Warning,
            detail={
                'object': 'symbol_layer',
                'cause': 'gradient_fill',
                'summary': 'gradient fill'
            })

        color_str = FslConverter.color_to_fsl(
            color, context
        )

        res = FslConverter.create_symbol_dict()
        res['color'] = color_str

        if symbol_opacity < 1:
            res['opacity'] = symbol_opacity

        res['strokeColor'] = FslConverter.NULL_COLOR

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

        # very basic conversion, best we can do is take the color of
        # the line fill...
        color = layer.subSymbol().color()
        if not color.isValid() or color.alphaF() == 0:
            return []

        context.push_warning(
            'Line pattern fills are not supported, converting to a solid fill',
            LogLevel.Warning,
            detail={
                'object': 'symbol_layer',
                'cause': 'line_pattern_fill',
                'summary': 'line pattern fill'
            })

        color_str = FslConverter.color_to_fsl(
            color, context
        )

        res = FslConverter.create_symbol_dict()
        res['color'] = color_str

        if symbol_opacity < 1:
            res['opacity'] = symbol_opacity

        res['strokeColor'] = FslConverter.NULL_COLOR

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

        context.push_warning(
            'Point pattern fills are not supported, converting '
            'to a solid fill',
            LogLevel.Warning,
            detail={
                'object': 'symbol_layer',
                'cause': 'point_pattern_fill',
                'summary': 'point pattern fill'
            })

        results = []
        for converted_layer in converted_marker:
            color_str = converted_layer.get('color')
            if not color_str:
                continue

            res = FslConverter.create_symbol_dict()
            res['color'] = color_str
            res['strokeColor'] = FslConverter.NULL_COLOR

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

        context.push_warning(
            'Centroid fills are not supported, converting to a solid fill',
            LogLevel.Warning,
            detail={
                'object': 'symbol_layer',
                'cause': 'centroid_fill',
                'summary': 'centroid fill'
            })

        results = []
        for converted_layer in converted_marker:
            color_str = converted_layer.get('color')
            if not color_str:
                continue

            res = FslConverter.create_symbol_dict()
            res['color'] = color_str
            res['strokeColor'] = FslConverter.NULL_COLOR

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

        context.push_warning(
            'Random marker fills are not supported, converting '
            'to a solid fill',
            LogLevel.Warning,
            detail={
                'object': 'symbol_layer',
                'cause': 'random_marker_fill',
                'summary': 'random marker fill'
            })

        results = []
        for converted_layer in converted_marker:
            color_str = converted_layer.get('color')
            if not color_str:
                continue

            res = FslConverter.create_symbol_dict()
            res['color'] = color_str
            res['strokeColor'] = FslConverter.NULL_COLOR

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

        context.push_warning(
            'SVG fills are not supported, converting to a solid fill',
            LogLevel.Warning,
            detail={
                'object': 'symbol_layer',
                'cause': 'svg_fill',
                'summary': 'svg fill'
            })

        color_str = FslConverter.color_to_fsl(
            color, context
        )

        res = FslConverter.create_symbol_dict()
        res['color'] = color_str

        if symbol_opacity < 1:
            res['opacity'] = symbol_opacity

        res['strokeColor'] = FslConverter.NULL_COLOR

        return [res]

    @staticmethod
    def label_settings_to_fsl(settings: QgsPalLayerSettings,
                              context: ConversionContext) \
            -> Optional[Dict[str, object]]:
        """
        Converts label settings to FSL
        """
        if not settings.drawLabels or not settings.fieldName:
            return {
                'label': {"isClickable": False, "isHoverable": False}
            }

        if settings.isExpression:
            context.push_warning('Expression based labels are not supported',
                                 LogLevel.Warning,
                                 detail={
                                     'object': 'labels',
                                     'cause': 'expression_based_label',
                                     'summary': 'expression based label'
                                 })
            return {
                'label': {"isClickable": False, "isHoverable": False}
            }

        converted_format = FslConverter.text_format_to_fsl(
            settings.format(), context
        )
        # disable clicks
        converted_format['isClickable'] = False
        converted_format['isHoverable'] = False

        if settings.autoWrapLength > 0:
            converted_format['maxLineChars'] = settings.autoWrapLength
        if settings.scaleVisibility:
            converted_format[
                'minZoom'] = MapUtils.map_scale_to_leaflet_tile_zoom(
                settings.minimumScale)
            converted_format[
                'maxZoom'] = MapUtils.map_scale_to_leaflet_tile_zoom(
                settings.maximumScale)
        else:
            # these are mandatory!
            converted_format['minZoom'] = 1
            converted_format['maxZoom'] = 24

        res = {
            'config': {
                'labelAttribute': [settings.fieldName]
            },
            'label': converted_format
        }

        # For now, we don't convert these and leave them to the Felt
        # defaults -- there's too many other unsupported placement
        # related configuration settings in QGIS which impact on the
        # actual placement of labels in QGIS, we are likely to get an
        # inferior result if we force an offset/fixed placement in Felt
        # to just the corresponding values from the QGIS layer...
        # - offset
        # - placement

        return res

    @staticmethod
    def text_format_to_fsl(text_format: QgsTextFormat,
                           context: ConversionContext) \
            -> Dict[str, object]:
        """
        Converts a QGIS text format to FSL
        """
        res = {
            'color': FslConverter.color_to_fsl(
                text_format.color(), context,
                opacity=text_format.opacity()),
            'fontSize': FslConverter.convert_to_pixels(
                text_format.size(), text_format.sizeUnit(),
                context
            ),
            'fontStyle': 'italic' if text_format.font().italic() else 'normal',
            'fontWeight': 700 if text_format.font().bold() else 400,
            'haloColor': FslConverter.color_to_fsl(
                text_format.buffer().color(), context,
                text_format.buffer().opacity()
            ) if text_format.buffer().enabled() else FslConverter.NULL_COLOR,
            'haloWidth': FslConverter.convert_to_pixels(
                text_format.buffer().size(),
                text_format.buffer().sizeUnit(),
                context
            )
        }

        # letterSpacing
        absolute_spacing = FslConverter.convert_to_pixels(
            text_format.font().letterSpacing(),
            QgsUnitTypes.RenderPoints, context
        )
        res['letterSpacing'] = round(absolute_spacing / res['fontSize'], 2)

        # line height conversion
        try:
            if text_format.lineHeightUnit() == QgsUnitTypes.RenderPercentage:
                res['lineHeight'] = round(text_format.lineHeight(), 2)
            else:
                # absolute line height, convert to relative to font size
                line_height_pixels = FslConverter.convert_to_pixels(
                    text_format.lineHeight(),
                    text_format.lineHeightUnit(),
                    context)
                res['lineHeight'] = round(
                    line_height_pixels / res['fontSize'], 2)
        except AttributeError:
            # QGIS < 3.28, don't convert line height
            pass

        if text_format.capitalization() == QgsStringUtils.AllUppercase:
            res['textTransform'] = 'uppercase'
        elif text_format.capitalization() == QgsStringUtils.AllLowercase:
            res['textTransform'] = 'lowercase'
        elif text_format.capitalization() != QgsStringUtils.MixedCase:
            try:
                context.push_warning(
                    'Text transform {} is not supported'.format(
                        text_format.capitalization().name))
            except AttributeError:
                context.push_warning(
                    'Text transform option {} is not supported'.format(
                        text_format.capitalization()))

        return res

    @staticmethod
    def add_common_layer_properties_to_fsl(
            layer: QgsMapLayer,
            fsl: Dict[str, object],
            context: ConversionContext,
    ):
        """
        Modifies FSL dict in place to add common layer properties
        """
        if layer.hasScaleBasedVisibility():
            if 'style' not in fsl:
                fsl['style'] = {}

            if layer.minimumScale():
                if isinstance(fsl['style'], list):
                    for style in fsl['style']:
                        style['minZoom'] = (
                            MapUtils.map_scale_to_leaflet_tile_zoom(
                                layer.minimumScale()))
                else:
                    fsl['style']['minZoom'] = (
                        MapUtils.map_scale_to_leaflet_tile_zoom(
                            layer.minimumScale()))
            if layer.maximumScale():
                if isinstance(fsl['style'], list):
                    for style in fsl['style']:
                        style['maxZoom'] = (
                            MapUtils.map_scale_to_leaflet_tile_zoom(
                                layer.maximumScale()))
                else:
                    fsl['style']['maxZoom'] = (
                        MapUtils.map_scale_to_leaflet_tile_zoom(
                            layer.maximumScale()))

    @staticmethod
    def raster_layer_to_fsl(
            layer: QgsRasterLayer,
            context: ConversionContext
    ) -> Optional[Dict[str, object]]:
        """
        Converts a raster layer to FSL
        """
        fsl = FslConverter.raster_renderer_to_fsl(
            layer.renderer(), context, layer.opacity()
        )
        if not fsl:
            fsl = {}

        # resampling only applies to numeric rasters
        if fsl.get('type') == 'numeric':
            is_early_resampling = (layer.resamplingStage() ==
                                   QgsRasterPipe.ResamplingStage.Provider)
            if (is_early_resampling and
                    (layer.dataProvider().zoomedInResamplingMethod() !=
                     QgsRasterDataProvider.ResamplingMethod.Nearest or
                     layer.dataProvider().zoomedOutResamplingMethod() !=
                     QgsRasterDataProvider.ResamplingMethod.Nearest)):
                fsl['config']['rasterResampling'] = "linear"
            else:
                fsl['config']['rasterResampling'] = "nearest"

        FslConverter.add_common_layer_properties_to_fsl(
            layer, fsl, context
        )

        return fsl or None

    @staticmethod
    def raster_renderer_to_fsl(
            renderer: QgsRasterRenderer,
            context: ConversionContext,
            opacity: float = 1
    ) -> Optional[Dict[str, object]]:
        """
        Converts a raster renderer to FSL
        """
        if isinstance(renderer, QgsSingleBandPseudoColorRenderer):
            return FslConverter.singleband_pseudocolor_renderer_to_fsl(
                renderer, context, opacity
            )
        if isinstance(renderer, QgsSingleBandGrayRenderer):
            return FslConverter.singleband_gray_renderer_to_fsl(
                renderer, context, opacity
            )
        if isinstance(renderer, QgsPalettedRasterRenderer):
            return FslConverter.paletted_renderer_to_fsl(
                renderer, context, opacity
            )

        context.push_warning('Unsupported raster renderer: {}'.format(
            renderer.__class__.__name__
        ),
            LogLevel.Error,
            detail={
                'object': 'raster',
                'renderer': renderer.__class__.__name__,
                'cause': 'unsupported_renderer',
                'summary': 'unsupported raster renderer {}'.format(
                    renderer.__class__.__name__
                )
            })
        return None

    @staticmethod
    def singleband_pseudocolor_renderer_to_fsl(
            renderer: QgsSingleBandPseudoColorRenderer,
            context: ConversionContext,
            opacity: float = 1
    ) -> Optional[Dict[str, object]]:
        """
        Converts a singleband pseudocolor renderer to FSL
        """

        shader = renderer.shader()
        shader_function = shader.rasterShaderFunction()
        if shader_function.colorRampType() == QgsColorRampShader.Discrete:
            return FslConverter.discrete_pseudocolor_renderer_to_fsl(
                renderer, context, opacity
            )
        elif (shader_function.colorRampType() ==
              QgsColorRampShader.Interpolated):
            return FslConverter.continuous_pseudocolor_renderer_to_fsl(
                renderer, context, opacity
            )

        return FslConverter.exact_pseudocolor_renderer_to_fsl(
            renderer, context, opacity
        )

    @staticmethod
    def discrete_pseudocolor_renderer_to_fsl(
            renderer: QgsSingleBandPseudoColorRenderer,
            context: ConversionContext,
            opacity: float = 1
    ):
        """
        Converts a discrete singleband pseudocolor renderer to FSL
        """
        shader = renderer.shader()
        shader_function = shader.rasterShaderFunction()
        steps = [shader_function.minimumValue()]
        colors = []
        labels = {}
        for i, item in enumerate(shader_function.colorRampItemList()):
            if math.isinf(item.value):
                steps.append(shader_function.maximumValue())
            else:
                steps.append(item.value)
            colors.append(item.color.name())
            labels[str(i)] = item.label
        return {
            "config": {
                "band": renderer.band(),
                "steps": steps
            },
            "legend": {
                "displayName": labels
            },

            "style": {
                "isSandwiched": False,
                "opacity": opacity,
                "color": colors
            },
            "type": "numeric"
        }

    @staticmethod
    def exact_pseudocolor_renderer_to_fsl(
            renderer: QgsSingleBandPseudoColorRenderer,
            context: ConversionContext,
            opacity: float = 1
    ):
        """
        Converts an exact singleband pseudocolor renderer to FSL
        """
        shader = renderer.shader()
        shader_function = shader.rasterShaderFunction()

        categories = []
        colors = []
        labels = {}
        for i, item in enumerate(shader_function.colorRampItemList()):
            if math.isinf(item.value):
                continue

            categories.append(str(item.value))
            colors.append(item.color.name())
            labels[str(i)] = item.label

        return {
            "config": {
                "band": renderer.band(),
                "categories": categories
            },
            "legend": {
                "displayName": labels
            },

            "style": {
                "isSandwiched": False,
                "opacity": opacity,
                "color": colors
            },
            "type": "categorical"
        }

    @staticmethod
    def continuous_pseudocolor_renderer_to_fsl(
            renderer: QgsSingleBandPseudoColorRenderer,
            context: ConversionContext,
            opacity: float = 1
    ):
        """
        Converts a continuous singleband pseudocolor renderer to FSL
        """
        shader = renderer.shader()
        shader_function = shader.rasterShaderFunction()

        min_value = shader_function.minimumValue()
        max_value = shader_function.maximumValue()

        # build 30 linear color steps between min and max value
        steps = [shader_function.minimumValue()]
        colors = []
        labels = {}
        for i in range(FslConverter.COLOR_RAMP_INTERPOLATION_STEPS):
            val = (i * (max_value - min_value) /
                   FslConverter.COLOR_RAMP_INTERPOLATION_STEPS + min_value)
            ok, red, green, blue, alpha = shader_function.shade(val)
            if ok:
                steps.append(val)
                colors.append(FslConverter.color_to_fsl(
                    QColor(red, green, blue, alpha), context, opacity))
                labels[str(i)] = str(round(val, 3))

        return {
            "config": {
                "band": renderer.band(),
                "steps": steps
            },
            "legend": {
                "displayName": labels
            },

            "style": {
                "isSandwiched": False,
                "opacity": opacity,
                "color": colors
            },
            "type": "numeric"
        }

    @staticmethod
    def singleband_gray_renderer_to_fsl(
            renderer: QgsSingleBandGrayRenderer,
            context: ConversionContext,
            opacity: float = 1
    ) -> Optional[Dict[str, object]]:
        """
        Converts a singleband gray renderer to FSL
        """
        steps = [renderer.contrastEnhancement().minimumValue(),
                 renderer.contrastEnhancement().maximumValue()]
        if (renderer.gradient() ==
                QgsSingleBandGrayRenderer.Gradient.BlackToWhite):
            colors = ["rgb(0, 0, 0)", "rgb(255, 255, 255)"]
        else:
            colors = ["rgb(255, 255, 255)", "rgb(0, 0, 0)"]

        return {
            "config": {
                "band": renderer.grayBand(),
                "steps": steps
            },
            "legend": {
                "displayName": {"0": str(steps[0]),
                                "1": str(steps[1])}
            },

            "style": {
                "isSandwiched": False,
                "opacity": opacity,
                "color": colors
            },
            "type": "numeric"
        }

    @staticmethod
    def paletted_renderer_to_fsl(
            renderer: QgsPalettedRasterRenderer,
            context: ConversionContext,
            opacity: float = 1
    ) -> Optional[Dict[str, object]]:
        """
        Converts a paletted raster renderer to FSL
        """

        categories = []
        colors = []
        labels = {}
        for _class in renderer.classes():
            categories.append(str(_class.value))
            colors.append(_class.color.name())
            labels[str(_class.value)] = _class.label
        return {
            "config": {
                "band": renderer.band(),
                "categories": categories
            },
            "legend": {
                "displayName": labels
            },

            "style": {
                "isSandwiched": False,
                "opacity": opacity,
                "color": colors
            },
            "type": "categorical"
        }
