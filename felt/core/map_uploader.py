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

import re
from collections import defaultdict
from pathlib import Path
from typing import (
    Optional,
    List,
    Tuple
)

from qgis.PyQt.QtCore import (
    QDate,
    pyqtSignal,
    QThread,
    QSize
)
from qgis.PyQt.QtNetwork import (
    QNetworkReply,
    QNetworkRequest
)
from qgis.core import (
    QgsMapLayer,
    QgsMapLayerUtils,
    QgsProject,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCsException,
    QgsTask,
    QgsFeedback,
    QgsBlockingNetworkRequest,
    QgsReferencedRectangle,
    QgsSettings
)
from qgis.utils import iface

from .api_client import API_CLIENT
from .exceptions import LayerPackagingException
from .layer_exporter import LayerExporter
from .logger import Logger
from .map import Map
from .map_utils import MapUtils
from .multi_step_feedback import MultiStepFeedback
from .s3_upload_parameters import S3UploadParameters
from .enums import LayerSupport


class MapUploaderTask(QgsTask):
    """
    A background task which handles map creation/uploading logic
    """

    status_changed = pyqtSignal(str)

    def __init__(self,
                 project: Optional[QgsProject] = None,
                 layers: Optional[List[QgsMapLayer]] = None,
                 target_map: Optional[Map] = None,
                 workspace_id: Optional[str] = None):
        super().__init__(
            'Sharing Map'
        )
        project = project or QgsProject.instance()
        self._workspace_id = workspace_id

        self.unsupported_layers: List[Tuple[str, str]] = []
        if layers:
            self.current_map_crs = QgsCoordinateReferenceSystem('EPSG:4326')
            self.current_map_extent = QgsMapLayerUtils.combinedExtent(
                layers,
                self.current_map_crs,
                project.transformContext()
            )
            self.layers = [
                layer.clone() for layer in layers
            ]
            self.unsupported_layer_details = {}
        else:
            if iface is not None:
                self.current_map_extent = iface.mapCanvas().extent()
                self.current_map_crs = \
                    iface.mapCanvas().mapSettings().destinationCrs()
            else:
                view_settings = project.viewSettings()
                self.current_map_extent = view_settings.defaultViewExtent()
                self.current_map_crs = view_settings.defaultViewExtent().crs()
            layer_tree_root = project.layerTreeRoot()
            visible_layers = [
                layer
                for layer in reversed(layer_tree_root.layerOrder())
                if layer_tree_root.findLayer(layer).isVisible()
            ]

            self.layers = [
                layer.clone() for layer in visible_layers if
                LayerExporter.can_export_layer(layer)[
                    0] == LayerSupport.Supported
            ]

            self._build_unsupported_layer_details(project, visible_layers)

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
        self.project_file_name = project.fileName()
        self.initial_zoom_level = \
            MapUtils.calculate_leaflet_tile_zoom_for_extent(
                QgsReferencedRectangle(
                    self.current_map_extent,
                    self.current_map_crs
                ),
                QSize(1024, 800)
            )

        self.associated_map: Optional[Map] = target_map
        self.error_string: Optional[str] = None
        self.feedback: Optional[QgsFeedback] = None
        self.was_canceled = False

    def set_workspace_id(self, workspace_id: Optional[str]):
        """
        Sets the target workspace ID
        """
        self._workspace_id = workspace_id

    def _build_unsupported_layer_details(self,
                                         project: QgsProject,
                                         layers: List[QgsMapLayer]):
        """
        Builds up details of unsupported layers, so that we can report
        these to users and to Felt
        """
        unsupported_layer_type_count = defaultdict(int)
        unsupported_layer_names = set()
        for layer in layers:
            support, reason = LayerExporter.can_export_layer(layer)
            if support == LayerSupport.Supported:
                continue

            self.unsupported_layers.append((layer.name(), reason))
            if not support.should_report():
                continue

            unsupported_layer_names.add(layer.name())
            if layer.type() == QgsMapLayer.PluginLayer:
                id_string = layer.pluginLayerType()
            else:
                id_string = '{}:{}'.format(
                    layer.__class__.__name__,
                    layer.providerType()
                )

            unsupported_layer_type_count[id_string] = (
                    unsupported_layer_type_count[id_string] + 1)

        self.unsupported_layer_details = {}
        for k, v in unsupported_layer_type_count.items():
            self.unsupported_layer_details[k] = v

        for layer_tree_layer in project.layerTreeRoot().findLayers():
            if layer_tree_layer.isVisible() and \
                    not layer_tree_layer.layer() and \
                    not layer_tree_layer.name() in unsupported_layer_names:
                self.unsupported_layers.append((layer_tree_layer.name(), ''))

    def default_map_title(self) -> str:
        """
        Returns an auto-generated title for a map
        """
        if self.project_title:
            return self.project_title

        if self.project_file_name:
            file_name_part = Path(self.project_file_name).stem
            return re.sub(r'[\-_]', ' ', file_name_part)

        date_string = QDate.currentDate().toString('yyyy-MM-dd')
        return self.tr('QGIS Map - {}').format(
            date_string
        )

    def warning_message(self) -> Optional[str]:
        """
        Returns a HTML formatted warning message, eg containing lists
        of unsupported map layers or other properties which cannot be
        exported
        """
        if not self.unsupported_layers:
            return None

        msg = '<p>' + self.tr('The following layers are not supported '
                              'and won\'t be uploaded:') + '</p><ul><li>'

        for layer_name, reason in self.unsupported_layers:
            if reason:
                msg += '<li>{}: {}</li>'.format(layer_name, reason)
            else:
                msg += '<li>{}</li>'.format(layer_name)

        msg += '</ul>'
        return msg

    # QgsTask interface
    # pylint: disable=missing-function-docstring
    def cancel(self):
        self.was_canceled = True
        if self.feedback:
            self.feedback.cancel()
        super().cancel()

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-return-statements
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    def run(self):
        if self.isCanceled():
            return False

        total_steps = (
                1 +  # create map call
                len(self.layers) +  # layer exports
                len(self.layers)  # layer uploads
        )

        self.feedback = QgsFeedback()

        upload_raster_as_styled = QgsSettings().value(
            "felt/upload_raster_as_styled", True, bool, QgsSettings.Plugins
        )

        multi_step_feedback = MultiStepFeedback(
            total_steps, self.feedback
        )
        self.feedback.progressChanged.connect(self.setProgress)

        for layer in self.layers:
            layer.moveToThread(QThread.currentThread())

        if self.isCanceled():
            return False

        if self.unsupported_layer_details:
            message = {
                "type": Logger.UNSUPPORTED_LAYER,
            }
            for k, v in self.unsupported_layer_details.items():
                message[k] = v

            Logger.instance().log_message_json(
                message
            )

        if not self.associated_map:
            self.status_changed.emit(self.tr('Creating map'))
            reply = API_CLIENT.create_map(
                self.map_center.y(),
                self.map_center.x(),
                self.initial_zoom_level,
                self.project_title,
                workspace_id=self._workspace_id,
                blocking=True,
                feedback=self.feedback
            )

            if reply.error() != QNetworkReply.NoError:
                self.error_string = reply.errorString()
                Logger.instance().log_error_json(
                    {
                        'type': Logger.MAP_EXPORT,
                        'error': 'Error creating map: {}'.format(
                            self.error_string)
                    }
                )
                return False

            if self.isCanceled():
                return False

            self.associated_map = Map.from_json(
                reply.content().data().decode())
            self.status_changed.emit(self.tr('Successfully created map'))

        multi_step_feedback.step_finished()

        exporter = LayerExporter(
            self.transform_context
        )

        if self.isCanceled():
            return False

        to_upload = {}

        for layer in self.layers:
            if self.isCanceled():
                return False

            if LayerExporter.layer_import_url(layer):
                result = LayerExporter.import_from_url(
                    layer,
                    self.associated_map,
                    multi_step_feedback)

                if 'errors' in result:
                    self.error_string = self.tr(
                        'Error occurred while exporting layer {}: {}').format(
                        layer.name(),
                        result['errors'][0]['detail']
                    )
                    self.status_changed.emit(self.error_string)

                    return False

                layer.moveToThread(None)
            else:

                self.status_changed.emit(
                    self.tr('Exporting {}').format(layer.name())
                )
                try:
                    result = exporter.export_layer_for_felt(
                        layer,
                        multi_step_feedback,
                        upload_raster_as_styled=upload_raster_as_styled
                    )
                except LayerPackagingException as e:
                    layer.moveToThread(None)
                    self.error_string = self.tr(
                        'Error occurred while exporting layer {}: {}').format(
                        layer.name(),
                        e
                    )
                    self.status_changed.emit(self.error_string)

                    return False

                layer.moveToThread(None)
                to_upload[layer] = result

            multi_step_feedback.step_finished()

        if self.isCanceled():
            return False

        for layer, details in to_upload.items():
            if self.isCanceled():
                return False

            self.status_changed.emit(
                self.tr('Uploading {}').format(layer.name())
            )

            while True:
                reply = API_CLIENT.prepare_layer_upload(
                    map_id=self.associated_map.id,
                    name=layer.name(),
                    file_names=[Path(details.filename).name],
                    style=details.style,
                    blocking=True,
                    feedback=self.feedback
                )
                if reply.attribute(
                        QNetworkRequest.HttpStatusCodeAttribute) == 429:
                    self.status_changed.emit(
                        self.tr('Rate throttled -- waiting')
                    )
                    QThread.sleep(5)
                    continue

                if reply.error() != QNetworkReply.NoError:
                    self.error_string = reply.errorString()
                    Logger.instance().log_error_json(
                        {
                            'type': Logger.MAP_EXPORT,
                            'error': 'Error preparing layer upload: {}'.format(
                                self.error_string)
                        }
                    )

                    return False
                break

            if self.isCanceled():
                return False

            upload_params = S3UploadParameters.from_json(
                reply.content().data().decode()
            )
            if not upload_params.url:
                self.error_string = self.tr('Could not prepare layer upload')
                message = "Error retrieving upload parameters: {}".format(
                    self.error_string
                )
                Logger.instance().log_error_json(
                    {
                        "type": Logger.S3_UPLOAD,
                        "error": message,
                    }
                )

                return False

            if self.isCanceled():
                return False

            with open(details.filename, "rb") as f:
                data = f.read()

            if self.isCanceled():
                return False

            request, form_content = API_CLIENT.create_upload_file_request(
                Path(details.filename).name, data, upload_params
            )
            blocking_request = QgsBlockingNetworkRequest()

            def _upload_progress(sent, total):
                if not sent or not total:
                    return

                multi_step_feedback.setProgress(int(100 * sent / total))

            blocking_request.uploadProgress.connect(_upload_progress)

            blocking_request.post(request,
                                  form_content,
                                  feedback=self.feedback)

            if blocking_request.reply().error() != QNetworkReply.NoError:
                self.error_string = blocking_request.reply().errorString()
                Logger.instance().log_error_json(
                    {
                        'type': Logger.S3_UPLOAD,
                        'error': 'Error uploading layer: {}'.format(
                            self.error_string)
                    }
                )
                return False

            if self.isCanceled():
                return False

            self.status_changed.emit(
                self.tr('Finalizing {}').format(layer.name())
            )

            while True:
                reply = API_CLIENT.finalize_layer_upload(
                    self.associated_map.id,
                    upload_params.layer_id,
                    Path(details.filename).name,
                    blocking=True,
                    feedback=self.feedback
                )
                if reply.attribute(
                        QNetworkRequest.HttpStatusCodeAttribute) == 429:
                    self.status_changed.emit(
                        self.tr('Rate throttled -- waiting')
                    )
                    QThread.sleep(5)
                    continue

                if reply.error() != QNetworkReply.NoError:
                    self.error_string = reply.errorString()
                    Logger.instance().log_error_json(
                        {
                            'type': Logger.MAP_EXPORT,
                            'error':
                                'Error finalizing layer upload: {}'.format(
                                    self.error_string)
                        }
                    )
                    return False

                break

            multi_step_feedback.step_finished()

        return True

    # pylint: enable=too-many-locals
    # pylint: enable=too-many-return-statements
    # pylint: enable=too-many-branches
    # pylint: enable=too-many-statements
