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
import zipfile
import math
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Optional,
    List,
    Tuple
)

from qgis.PyQt.QtCore import (
    QVariant,
    QObject
)
from qgis.PyQt.QtXml import (
    QDomDocument
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
    QgsEllipseSymbolLayer,
    QgsReadWriteContext,
    QgsRasterPipe,
    QgsRasterNuller,
    QgsRasterRange
)

from .enums import LayerExportResult
from .exceptions import LayerPackagingException
from .layer_style import LayerStyle
from .logger import Logger


@dataclass
class LayerExportDetails:
    """
    Export results
    """
    representative_filename: str
    filenames: List[str]
    result: LayerExportResult
    error_message: str
    qgis_style_xml: str
    style: Optional[LayerStyle] = None


@dataclass
class ZippedExportResult:
    """
    A zipped export results
    """
    filename: str
    result: LayerExportResult
    error_message: str
    qgis_style_xml: str
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
    def can_export_layer(layer: QgsMapLayer) -> Tuple[bool, str]:
        """
        Returns True if a layer can be exported, and an explanatory
        string if not
        """
        if isinstance(layer, QgsVectorLayer):
            # Vector layers must have some features
            if layer.featureCount() == 0:
                return False, 'Layer is empty'

            return True, ''

        if isinstance(layer, QgsRasterLayer):
            if layer.providerType() in (
                    'gdal',
                    'virtualraster'
            ):
                return True, ''

            return False, '{} raster layers are not yet supported'.format(
                layer.providerType()
            )

        return False, '{} layers are not yet supported'.format(
            layer.__class__.__name__
        )

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
        file_name = 'qgis_export_' + uuid.uuid4().hex + suffix
        return (Path(str(self.temp_dir.name)) / file_name).as_posix()

    def export_layer_for_felt(
            self,
            layer: QgsMapLayer,
            feedback: Optional[QgsFeedback] = None
    ) -> ZippedExportResult:
        """
        Exports a layer into a format acceptable for Felt
        :raises LayerPackagingException
        """
        if isinstance(layer, QgsVectorLayer):
            res = self.export_vector_layer(layer, feedback)
        elif isinstance(layer, QgsRasterLayer):
            res = self.export_raster_layer(layer, feedback)
        else:
            assert False

        # package into zip
        zip_file_path = (
            (Path(str(self.temp_dir.name)) /
             (Path(res.representative_filename).stem + '.zip')).as_posix())
        with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for filename in res.filenames:
                zipf.write(filename, Path(filename).name)

            # add QGIS layer style xml also
            zipf.writestr("qgis_style.xml", res.qgis_style_xml)

        return ZippedExportResult(
            filename=zip_file_path,
            result=res.result,
            error_message=res.error_message,
            qgis_style_xml=res.qgis_style_xml,
            style=res.style
        )

    @staticmethod
    def _get_original_style_xml(layer: QgsMapLayer) -> str:
        """
        Returns the original QGIS xml styling content for a layer
        """
        doc = QDomDocument('qgis')
        context = QgsReadWriteContext()
        layer.exportNamedStyle(doc, context)
        return doc.toString(2)

    def export_vector_layer(
            self,
            layer: QgsVectorLayer,
            feedback: Optional[QgsFeedback] = None) -> LayerExportDetails:
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

        return LayerExportDetails(
            representative_filename=dest_file,
            filenames=[dest_file],
            result=layer_export_result,
            error_message=error_message,
            qgis_style_xml=self._get_original_style_xml(layer),
            style=self.representative_layer_style(layer)
        )

    def run_raster_writer(self,
                          layer: QgsRasterLayer,
                          file_name: str,
                          use_style: bool,
                          feedback: Optional[QgsFeedback] = None) \
            -> Tuple[LayerExportResult, Optional[str]]:
        """
        Runs a raster write operation for the layer
        """
        writer = QgsRasterFileWriter(file_name)
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
        if use_style:
            raster_pipe = layer.pipe()
        else:
            raster_pipe = QgsRasterPipe()
            raster_pipe.set(layer.dataProvider().clone())
            nuller = QgsRasterNuller()
            for band in range(1, layer.dataProvider().bandCount() + 1):
                additional_no_data_values = (
                    layer.dataProvider().userNoDataValues(
                        band))
                source_no_data = layer.dataProvider().sourceNoDataValue(band)
                if not math.isnan(source_no_data):
                    additional_no_data_values.append(
                        QgsRasterRange(
                            layer.dataProvider().sourceNoDataValue(band),
                            layer.dataProvider().sourceNoDataValue(band)
                        )
                    )
                if additional_no_data_values:
                    nuller.setNoData(band, additional_no_data_values)
            raster_pipe.insert(1, nuller)

        dest_crs = layer.crs()
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

        layer_export_result = {
            QgsRasterFileWriter.WriterError.NoError:
                LayerExportResult.Success,
            QgsRasterFileWriter.WriterError.WriteCanceled:
                LayerExportResult.Canceled,
        }[res]

        return layer_export_result, error_message

    def export_raster_layer(
            self,
            layer: QgsRasterLayer,
            feedback: Optional[QgsFeedback] = None) -> LayerExportDetails:
        """
        Exports a raster layer into a format acceptable for Felt
        """
        raw_dest_file = self.generate_file_name('.tif')
        styled_dest_file = raw_dest_file.replace('.tif', '_styled.tif')

        layer_export_result, error_message = self.run_raster_writer(
            layer,
            file_name=styled_dest_file,
            use_style=True,
            feedback=feedback)

        if error_message:
            Logger.instance().log_error_json(
                {
                    'type': Logger.PACKAGING_RASTER,
                    'error': 'Error packaging layer: {}'.format(error_message)
                 }
            )
            raise LayerPackagingException(error_message)

        filenames = [styled_dest_file]
        if layer_export_result != LayerExportResult.Canceled:
            # also write raw raster

            layer_export_result, error_message = self.run_raster_writer(
                layer,
                file_name=raw_dest_file,
                use_style=False,
                feedback=feedback)

            if error_message:
                Logger.instance().log_error_json(
                    {
                        'type': Logger.PACKAGING_RASTER,
                        'error': 'Error packaging layer: {}'.format(
                            error_message)
                    }
                )
                raise LayerPackagingException(error_message)

            filenames.append(raw_dest_file)

        return LayerExportDetails(
            representative_filename=raw_dest_file,
            filenames=filenames,
            result=layer_export_result,
            error_message=error_message,
            qgis_style_xml=self._get_original_style_xml(layer)
        )
