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

from qgis.PyQt.QtCore import QVariant

from qgis.core import (
    QgsFeedback,
    QgsMapLayer,
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsCoordinateTransformContext,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsWkbTypes,
    QgsFieldConstraints
)


@dataclass
class ExportResult:
    """
    Export results
    """
    filename: str
    result: QgsVectorFileWriter.WriterError
    error_message: str


class LayerExporter:

    def __init__(self,
                 transform_context: QgsCoordinateTransformContext):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.transform_context = transform_context

    def __del__(self):
        self.temp_dir.cleanup()

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
        return ExportResult(
            filename=dest_file,
            result=res,
            error_message=error_message
        )
