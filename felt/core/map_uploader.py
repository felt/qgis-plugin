# -*- coding: utf-8 -*-
"""Felt API Map

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

from typing import (
    Optional,
    List
)
from pathlib import Path

from qgis.PyQt.QtCore import (
    QDate,
    pyqtSignal,
    QThread
)
from qgis.PyQt.QtNetwork import QNetworkReply

from qgis.core import (
    QgsMapLayer,
    QgsMapLayerUtils,
    QgsProject,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCsException,
    QgsTask,
    QgsVectorLayer,
    QgsVectorFileWriter
)
from qgis.utils import iface

from .api_client import API_CLIENT
from .map import Map
from .layer_exporter import LayerExporter
from .s3_upload_parameters import S3UploadParameters


class MapUploaderTask(QgsTask):
    """
    A background task which handles map creation/uploading logic
    """

    status_changed = pyqtSignal(str)

    def __init__(self,
                 project: Optional[QgsProject] = None,
                 layers: Optional[List[QgsMapLayer]] = None):
        super().__init__()
        project = project or QgsProject.instance()

        if layers:
            self.current_map_crs = QgsCoordinateReferenceSystem('EPSG:4326')
            self.current_map_extent = QgsMapLayerUtils.combinedExtent(
                layers,
                self.current_map_crs,
                project.transformContext()
            )
            self.layers = [
                l.clone() for l in layers
            ]
        else:
            if iface is not None:
                self.current_map_extent = iface.mapCanvas().extent()
                self.current_map_crs = \
                    iface.mapCanvas().mapSettings().destinationCrs()
            else:
                view_settings = project.viewSettings()
                self.current_map_extent = view_settings.defaultViewExtent()
                self.current_map_crs = view_settings.defaultViewExtent().crs()
            self.layers = [
                l.clone() for _, l in project.mapLayers().items() if isinstance(l, QgsVectorLayer)
            ]

        for layer in self.layers:
            layer.moveToThread(None)

        self.transform_context = project.transformContext()

        transform_4326 = QgsCoordinateTransform(
            self.current_map_crs,
            QgsCoordinateReferenceSystem('EPSG:4326'),
            self.transform_context
        )
        try:
            map_extent_4326 = transform_4326.transformBoundingBox(
                self.current_map_extent
            )
        except QgsCsException:
            map_extent_4326 = self.current_map_extent

        self.map_center = map_extent_4326.center()

        self.project_title = project.title()
        # TODO -- can we determine this automatically?
        self.initial_zoom_level = 5

        self.created_map: Optional[Map] = None
        self.error_string: Optional[str] = None

    def default_map_title(self):
        date_string = QDate.currentDate().toString('yyyy-MM-dd')
        if self.project_title:
            return self.tr('{} QGIS Map - {}').format(
                self.project_title,
                date_string
            )

        return self.tr('Untitled QGIS Map - {}').format(
            date_string
        )

    def run(self):
        for layer in self.layers:
            layer.moveToThread(QThread.currentThread())

        self.status_changed.emit(self.tr('Creating map'))
        reply = API_CLIENT.create_map(
            self.map_center.y(),
            self.map_center.x(),
            self.initial_zoom_level,
            self.project_title,
            blocking=True
            )

        if reply.error() != QNetworkReply.NoError:
            self.error_string = reply.errorString()
            return False

        self.created_map = Map.from_json(reply.content().data().decode())
        self.status_changed.emit(self.tr('Successfully created map'))

        exporter = LayerExporter(
            self.transform_context
        )

        to_upload = {}

        for layer in self.layers:
            self.status_changed.emit(
                self.tr('Exporting {}').format(layer.name())
            )
            result = exporter.export_layer_for_felt(
                layer
            )
            layer.moveToThread(None)
            if result.result != QgsVectorFileWriter.NoError:
                self.status_changed.emit(
                    self.tr('Error occurred while exporting layer {}: {}').format(
                    layer.name(),
                        result.error_message
                    )
                )
                return False

            to_upload[layer] = result.filename

        for layer, filename in to_upload.items():
            self.status_changed.emit(
                self.tr('Uploading {}').format(layer.name())
            )

            reply = API_CLIENT.prepare_layer_upload(
                map_id=self.created_map.id,
                name=layer.name(),
                file_names=[Path(filename).name],
                blocking=True
            )
            if reply.error() != QNetworkReply.NoError:
                self.error_string = reply.errorString()
                return False

            upload_params = S3UploadParameters.from_json(
                reply.content().data().decode()
            )
            if not upload_params.url:
                self.error_string = self.tr('Could not prepare layer upload')
                return False

            with open(filename, "rb") as f:
                data = f.read()

            reply = API_CLIENT.upload_file(
                Path(filename).name, data, upload_params, blocking=True
            )
            if reply.error() != QNetworkReply.NoError:
                self.error_string = reply.errorString()
                return False

            self.status_changed.emit(
                self.tr('Finalizing {}').format(layer.name())
            )

            reply = API_CLIENT.finalize_layer_upload(
                self.created_map.id,
                upload_params.layer_id,
                Path(filename).name,
                blocking=True
            )

            if reply.error() != QNetworkReply.NoError:
                self.error_string = reply.errorString()
                return False

        return True
