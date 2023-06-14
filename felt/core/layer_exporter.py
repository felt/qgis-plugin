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
from qgis.PyQt.QtGui import QColor

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

    def __init__(self,
                 transform_context: QgsCoordinateTransformContext):
        super().__init__()
        self.temp_dir = tempfile.TemporaryDirectory()
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
            elif isinstance(symbol_layer, QgsSimpleLineSymbolLayer):
                # line layers use fill color on Felt!
                return LayerStyle(
                    fill_color=symbol_layer.color(),
                )
            elif isinstance(symbol_layer, (
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

        res, error_message, new_filename, new_layer_name = \
            QgsVectorFileWriter.writeAsVectorFormatV3(
                layer,
                dest_file,
                self.transform_context,
                writer_options,
            )

        layer_export_result = {
            QgsVectorFileWriter.WriterError.NoError: LayerExportResult.Success,
            QgsVectorFileWriter.WriterError.ErrDriverNotFound: LayerExportResult.Error,
            QgsVectorFileWriter.WriterError.ErrCreateDataSource: LayerExportResult.Error,
            QgsVectorFileWriter.WriterError.ErrCreateLayer: LayerExportResult.Error,
            QgsVectorFileWriter.WriterError.ErrAttributeTypeUnsupported: LayerExportResult.Error,
            QgsVectorFileWriter.WriterError.ErrAttributeCreationFailed: LayerExportResult.Error,
            QgsVectorFileWriter.WriterError.ErrProjection: LayerExportResult.Error,
            QgsVectorFileWriter.WriterError.ErrFeatureWriteFailed: LayerExportResult.Error,
            QgsVectorFileWriter.WriterError.ErrInvalidLayer: LayerExportResult.Error,
            QgsVectorFileWriter.WriterError.ErrSavingMetadata: LayerExportResult.Error,
            QgsVectorFileWriter.WriterError.Canceled: LayerExportResult.Canceled,
        }[res]
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

        extent = layer.extent()
        raster_pipe = layer.pipe()
        projector = raster_pipe.projector()

        if projector:
            projector.setCrs(
                layer.crs(),
                QgsCoordinateReferenceSystem('EPSG:3857'),
                self.transform_context
            )

            to_3857_transform = QgsCoordinateTransform(
                layer.crs(),
                QgsCoordinateReferenceSystem('EPSG:3857'),
                self.transform_context
            )
            extent = to_3857_transform.transformBoundingBox(extent)

        if feedback:
            block_feedback = QgsRasterBlockFeedback()
            block_feedback.progressChanged.connect(feedback.setProgress)
            feedback.canceled.connect(block_feedback.cancel)
        else:
            block_feedback = None

        res = writer.writeRaster(
            raster_pipe,
            layer.width(),
            -1,
            extent,
            QgsCoordinateReferenceSystem('EPSG:3857'),
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

        layer_export_result = {
            QgsRasterFileWriter.WriterError.NoError: LayerExportResult.Success,
            QgsRasterFileWriter.WriterError.SourceProviderError: LayerExportResult.Error,
            QgsRasterFileWriter.WriterError.DestProviderError: LayerExportResult.Error,
            QgsRasterFileWriter.WriterError.CreateDatasourceError: LayerExportResult.Error,
            QgsRasterFileWriter.WriterError.WriteError: LayerExportResult.Error,
            QgsRasterFileWriter.WriterError.NoDataConflict: LayerExportResult.Error,
            QgsRasterFileWriter.WriterError.WriteCanceled: LayerExportResult.Canceled,
        }[res]

        return ExportResult(
            filename=dest_file,
            result=layer_export_result,
            error_message=error_message
        )