# -*- coding: utf-8 -*-
"""Layer exporter for Felt

.. note:: This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

__author__ = '(C) 2023 by Nyall Dawson'
__date__ = '1/06/2023'
__copyright__ = 'Copyright 2022, North Road'
# This will get replaced with a git SHA1 when you do a git archive
__revision__ = '$Format:%H$'

import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from qgis.PyQt.QtCore import (
    QVariant,
    QObject
)
from qgis.core import (
    QgsFeedback,
    QgsMapLayer,
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsCoordinateTransformContext,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsWkbTypes,
    QgsRasterLayer,
    QgsRasterFileWriter,
    QgsRasterBlockFeedback,
    QgsSingleSymbolRenderer,
    QgsCategorizedSymbolRenderer,
    QgsGraduatedSymbolRenderer,
    QgsRuleBasedRenderer,
    QgsSymbol,
    QgsSimpleFillSymbolLayer,
    QgsSimpleLineSymbolLayer,
    QgsSimpleMarkerSymbolLayer,
    QgsEllipseSymbolLayer
)

from .enums import LayerExportResult
from .layer_style import LayerStyle
from .exceptions import LayerPackagingException
from .logger import Logger


@dataclass
class ExportResult:
    """
    Export results
    """
    filename: str
    result: LayerExportResult
    error_message: str
    style: Optional[LayerStyle] = None


class LayerExporter(QObject):
    """
    Handles exports of layers to formats acceptable for Felt
    """

    def __init__(self,
                 transform_context: QgsCoordinateTransformContext):
        super().__init__()
        # pylint: disable=consider-using-with
        self.temp_dir = tempfile.TemporaryDirectory()
        # pylint: enable=consider-using-with
        self.transform_context = transform_context

    def __del__(self):
        self.temp_dir.cleanup()

    @staticmethod
    def can_export_layer(layer: QgsMapLayer) -> bool:
        """
        Returns True if a layer can be exported
        """
        if isinstance(layer, QgsVectorLayer):
            return True

        if isinstance(layer, QgsRasterLayer):
            return layer.providerType() == 'gdal'

        return False

    @staticmethod
    def representative_layer_style(layer: QgsVectorLayer) -> LayerStyle:
        """
        Returns a decent representative style for a layer
        """
        if not layer.isSpatial() or not layer.renderer():
            return LayerStyle()

        if isinstance(layer.renderer(), QgsSingleSymbolRenderer):
            return LayerExporter.symbol_to_layer_style(
                layer.renderer().symbol()
            )
        if isinstance(layer.renderer(), QgsCategorizedSymbolRenderer) and \
                layer.renderer().categories():
            first_category = layer.renderer().categories()[0]
            return LayerExporter.symbol_to_layer_style(
                first_category.symbol()
            )
        if isinstance(layer.renderer(), QgsGraduatedSymbolRenderer) and \
                layer.renderer().ranges():
            first_range = layer.renderer().ranges()[0]
            return LayerExporter.symbol_to_layer_style(
                first_range.symbol()
            )
        if isinstance(layer.renderer(), QgsRuleBasedRenderer) and \
                layer.renderer().rootRule().children():
            for child in layer.renderer().rootRule().children():
                if child.symbol():
                    return LayerExporter.symbol_to_layer_style(
                        child.symbol()
                    )

        return LayerStyle()

    @staticmethod
    def symbol_to_layer_style(symbol: QgsSymbol) -> LayerStyle:
        """
        Tries to extract representative styling information from a symbol
        """
        for i in range(symbol.symbolLayerCount()):
            symbol_layer = symbol.symbolLayer(i)
            if isinstance(symbol_layer, QgsSimpleFillSymbolLayer):
                return LayerStyle(
                    fill_color=symbol_layer.fillColor(),
                    stroke_color=symbol_layer.strokeColor()
                )
            if isinstance(symbol_layer, QgsSimpleLineSymbolLayer):
                # line layers use fill color on Felt!
                return LayerStyle(
                    fill_color=symbol_layer.color(),
                )
            if isinstance(symbol_layer, (
                    QgsEllipseSymbolLayer,
                    QgsSimpleMarkerSymbolLayer)):
                return LayerStyle(
                    fill_color=symbol_layer.fillColor(),
                    stroke_color=symbol_layer.strokeColor()
                )

        return LayerStyle()

    def generate_file_name(self, suffix: str) -> str:
        """
        Generates a temporary file name with the given suffix
        """
        return (Path(str(self.temp_dir.name)) /
                (uuid.uuid4().hex + suffix)).as_posix()

    def export_layer_for_felt(
            self,
            layer: QgsMapLayer,
            feedback: Optional[QgsFeedback] = None
    ) -> ExportResult:
        """
        Exports a layer into a format acceptable for Felt
        :raises LayerPackagingException
        """
        if isinstance(layer, QgsVectorLayer):
            return self.export_vector_layer(layer, feedback)
        if isinstance(layer, QgsRasterLayer):
            return self.export_raster_layer(layer, feedback)
        assert False

    def export_vector_layer(
            self,
            layer: QgsVectorLayer,
            feedback: Optional[QgsFeedback] = None) -> ExportResult:
        """
        Exports a vector layer into a format acceptable for Felt
        """
        dest_file = self.generate_file_name('.gpkg')

        # from https://github.com/felt/qgis-plugin/issues/2
        writer_options = QgsVectorFileWriter.SaveVectorOptions()
        writer_options.driverName = 'GPKG'
        writer_options.layerName = 'parsed'
        writer_options.ct = QgsCoordinateTransform(
            layer.crs(),
            QgsCoordinateReferenceSystem('EPSG:4326'),
            self.transform_context
        )
        writer_options.feedback = feedback
        writer_options.forceMulti = True
        writer_options.overrideGeometryType = QgsWkbTypes.dropM(
            QgsWkbTypes.dropZ(layer.wkbType())
        )
        writer_options.includeZ = False
        writer_options.layerOptions = [
            'GEOMETRY_NAME=geom',
            'SPATIAL_INDEX=NO',
        ]

        # check FID field compatibility with GPKG and remove non-compatible
        # FID fields
        fields = layer.fields()
        fid_index = fields.lookupField('fid')
        writer_options.attributes = fields.allAttributesList()
        if fid_index >= 0:
            fid_type = fields.field(fid_index).type()
            if fid_type not in (QVariant.Int,
                                QVariant.UInt,
                                QVariant.LongLong,
                                QVariant.ULongLong):
                writer_options.attributes = [a for a in
                                             writer_options.attributes if
                                             a != fid_index]

        # pylint: disable=unused-variable
        res, error_message, new_filename, new_layer_name = \
            QgsVectorFileWriter.writeAsVectorFormatV3(
                layer,
                dest_file,
                self.transform_context,
                writer_options,
            )
        # pylint: enable=unused-variable

        if res not in (QgsVectorFileWriter.WriterError.NoError,
                       QgsVectorFileWriter.WriterError.Canceled):
            Logger.instance().log_error_json(
                {
                    'type': Logger.PACKAGING_VECTOR,
                    'error': 'Error packaging layer: {}'.format(error_message)
                 }
            )

            raise LayerPackagingException(error_message)

        layer_export_result = {
            QgsVectorFileWriter.WriterError.NoError:
                LayerExportResult.Success,
            QgsVectorFileWriter.WriterError.Canceled:
                LayerExportResult.Canceled,
        }[res]

        # validate result
        new_layer_uri = new_filename
        if new_layer_name:
            new_layer_uri += '|layername=' + new_layer_name
        res_layer = QgsVectorLayer(
            new_layer_uri, 'test', 'ogr'
        )
        if (layer.featureCount() > 0) and \
                res_layer.featureCount() != layer.featureCount():
            Logger.instance().log_error_json(
                {
                    'type': Logger.PACKAGING_VECTOR,
                    'error': 'Error packaging layer: Packaged layer '
                             'does not contain all features'
                }
            )

            raise LayerPackagingException(
                self.tr(
                    'Packaged layer does not contain all features! '
                    '(has {}, expected {})').format(
                    res_layer.featureCount(), layer.featureCount())
            )

        return ExportResult(
            filename=dest_file,
            result=layer_export_result,
            error_message=error_message,
            style=self.representative_layer_style(layer)
        )

    def export_raster_layer(
            self,
            layer: QgsRasterLayer,
            feedback: Optional[QgsFeedback] = None) -> ExportResult:
        """
        Exports a raster layer into a format acceptable for Felt
        """

        dest_file = self.generate_file_name('.tif')

        writer = QgsRasterFileWriter(dest_file)
        writer.setOutputFormat('GTiff')
        writer.setOutputProviderKey('gdal')
        writer.setTiledMode(False)

        # from https://github.com/felt/qgis-plugin/issues/6
        writer.setCreateOptions([
            'COMPRESS=DEFLATE',
            'BIGTIFF=IF_SAFER',
            'TILED=yes'
        ])

        extent = layer.extent()
        raster_pipe = layer.pipe()
        projector = raster_pipe.projector()

        dest_crs = layer.crs()
        # disable local reprojection for now - see #14
        if False:  # pylint: disable=using-constant-test
            dest_crs = QgsCoordinateReferenceSystem('EPSG:3857')
            projector.setCrs(
                layer.crs(),
                dest_crs,
                self.transform_context
            )

            to_3857_transform = QgsCoordinateTransform(
                layer.crs(),
                dest_crs,
                self.transform_context
            )
            extent = to_3857_transform.transformBoundingBox(extent)

        width = layer.width()
        if feedback:
            block_feedback = QgsRasterBlockFeedback()
            block_feedback.progressChanged.connect(feedback.setProgress)
            feedback.canceled.connect(block_feedback.cancel)
        else:
            block_feedback = None

        res = writer.writeRaster(
            raster_pipe,
            width,
            -1,
            extent,
            dest_crs,
            self.transform_context,
            block_feedback)

        error_message = {
            QgsRasterFileWriter.WriterError.NoError: None,
            QgsRasterFileWriter.WriterError.SourceProviderError:
                self.tr('Source provider error'),
            QgsRasterFileWriter.WriterError.DestProviderError:
                self.tr('Destination provider error'),
            QgsRasterFileWriter.WriterError.CreateDatasourceError:
                self.tr('Dataset creation error'),
            QgsRasterFileWriter.WriterError.WriteError:
                self.tr('Dataset writing error'),
            QgsRasterFileWriter.WriterError.NoDataConflict:
                self.tr('Nodata conflict error'),
            QgsRasterFileWriter.WriterError.WriteCanceled:
                None,
        }[res]
        if error_message:
            Logger.instance().log_error_json(
                {
                    'type': Logger.PACKAGING_RASTER,
                    'error': 'Error packaging layer: {}'.format(error_message)
                 }
            )
            raise LayerPackagingException(error_message)

        layer_export_result = {
            QgsRasterFileWriter.WriterError.NoError:
                LayerExportResult.Success,
            QgsRasterFileWriter.WriterError.WriteCanceled:
                LayerExportResult.Canceled,
        }[res]

        return ExportResult(
            filename=dest_file,
            result=layer_export_result,
            error_message=error_message
        )
