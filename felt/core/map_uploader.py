"""
Felt API Map Uploader
"""

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Dict,
    Optional,
    List,
    Tuple
)

from qgis.PyQt.QtCore import (
    QDate,
    pyqtSignal,
    QThread,
    QSize,
    QEventLoop
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
    QgsRasterLayer,
    QgsLayerTree,
    QgsLayerTreeLayer,
    QgsLayerTreeGroup
)
from qgis.utils import iface

from .api_client import API_CLIENT
from .enums import LayerSupport
from .exceptions import LayerPackagingException
from .layer_exporter import LayerExporter
from .logger import Logger
from .map import Map
from .map_utils import MapUtils
from .multi_step_feedback import MultiStepFeedback
from .fsl_converter import ConversionContext
from .s3_upload_parameters import S3UploadParameters


@dataclass
class LayerDetails:
    """
    Encapsulates details of a layer to upload
    """
    layer: QgsMapLayer
    destination_group_name: Optional[str] = None
    ordering_key: Optional[int] = None


@dataclass
class ProjectComponent:
    """
    Encapsulates details of a project component
    """
    object_index: Optional[int] = None
    group_name: Optional[str] = None
    layer: Optional[LayerDetails] = None


class SimplifiedProjectStructure:
    """
    Represents a simplified structure of a QGIS project
    """
    def __init__(self):
        self.components: List[ProjectComponent] = []
        self._current_index: int = 0

    def append_component(self, component: ProjectComponent):
        """
        Adds a component to the project structure
        """
        component.object_index = self._current_index
        self.components.append(component)
        self._current_index += 1

    def group_ordering_key(self, group_name: str) -> Optional[int]:
        """
        Returns the ordering key for a group name
        """
        all_group_keys = self.group_ordering_keys()
        return all_group_keys.get(group_name, None)

    def group_ordering_keys(self) -> Dict[str, int]:
        """
        Returns a dictionary of group name to ordering key
        """
        res = {}
        for i, component in enumerate(self.components):
            if component.group_name:
                res[component.group_name] = len(self.components) - i
        return res

    def has_groups(self) -> bool:
        """
        Returns TRUE if there are any layer groups in the project
        """
        return any(bool(component.group_name) for component in self.components)

    def find_layer(self, layer: QgsMapLayer) -> Optional[ProjectComponent]:
        """
        Finds a layer in the project structure
        """
        for component in self.components:
            if component.layer and component.layer.layer == layer:
                return component
        return None

    @staticmethod
    def from_project(project: QgsProject) -> 'SimplifiedProjectStructure':
        """
        Creates a simplified structure of a QGIS project
        """
        tree = project.layerTreeRoot()
        res = SimplifiedProjectStructure()

        def traverse_group(group: QgsLayerTreeGroup,
                           top_level_group_name: str):
            for _child in group.children():
                if isinstance(_child, QgsLayerTreeGroup):
                    traverse_group(_child, top_level_group_name)
                elif isinstance(_child, QgsLayerTreeLayer):
                    res.append_component(
                        ProjectComponent(
                            layer=LayerDetails(
                                layer=_child.layer(),
                                destination_group_name=top_level_group_name
                            )
                        )
                    )

        for child in tree.children():
            if isinstance(child, QgsLayerTreeGroup):
                res.append_component(
                    ProjectComponent(
                        group_name=child.name()
                    )
                )
                traverse_group(child, child.name())
            elif isinstance(child, QgsLayerTreeLayer):
                res.append_component(
                    ProjectComponent(
                        layer=LayerDetails(
                            layer=child.layer(),
                        )
                    )
                )

        return res


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
        self.unsupported_styles: List[Tuple[str, List[str]]] = []
        self.project_structure = SimplifiedProjectStructure.from_project(
                project
            )

        if layers:
            self.current_map_crs = QgsCoordinateReferenceSystem('EPSG:4326')
            self.current_map_extent = QgsMapLayerUtils.combinedExtent(
                layers,
                self.current_map_crs,
                project.transformContext()
            )
            self.layers = [
                MapUploaderTask.layer_and_group(project, layer) for layer
                in layers
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
                MapUploaderTask.layer_and_group(project, layer) for layer
                in visible_layers
                if
                LayerExporter.can_export_layer(layer)[
                    0] == LayerSupport.Supported
            ]

            self._build_unsupported_layer_details(project, visible_layers)

        for layer_details in self.layers:
            if LayerExporter.layer_import_url(layer_details.layer):
                # This is a direct import URL (eg XYZ layer), so ignore
                # FSL conversion issues
                continue

            fsl_conversion_context = ConversionContext()
            LayerExporter.representative_layer_style(
                layer_details.layer, fsl_conversion_context)
            if fsl_conversion_context.warnings:
                warnings = []
                for warning in fsl_conversion_context.warnings:
                    message = warning.get('message')
                    if message and message not in warnings:
                        warnings.append(message)
                self.unsupported_styles.append((layer_details.layer.name(),
                                                warnings))

            layer_details.layer.moveToThread(None)

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

    @staticmethod
    def layer_and_group(
            project: QgsProject,
            layer: QgsMapLayer) \
            -> LayerDetails:
        """
        Clones a layer, and returns the layer details
        """
        simplified_project = SimplifiedProjectStructure.from_project(project)
        simplified_project_layer = simplified_project.find_layer(layer)

        res = MapUploaderTask.clone_layer(layer)

        layer_tree_root = project.layerTreeRoot()

        layer_tree_layer = layer_tree_root.findLayer(layer)
        parent = layer_tree_layer.parent()
        while parent:
            if parent.parent() == layer_tree_root:
                break

            parent = parent.parent()

        group_name = None
        if parent != layer_tree_root and QgsLayerTree.isGroup(parent):
            group_name = parent.name()

        ordering_key = None
        if (simplified_project_layer and
                simplified_project_layer.object_index is not None):
            object_index = simplified_project_layer.object_index
            ordering_key = len(simplified_project.components) - object_index

        return LayerDetails(
            layer=res,
            destination_group_name=group_name,
            ordering_key=ordering_key
        )

    @staticmethod
    def clone_layer(layer: QgsMapLayer) -> QgsMapLayer:
        """
        Clones a layer
        """
        res = layer.clone()
        if isinstance(layer, QgsRasterLayer):
            res.setResamplingStage(layer.resamplingStage())
            res.dataProvider().setZoomedInResamplingMethod(
                layer.dataProvider().zoomedInResamplingMethod()
            )
            res.dataProvider().setZoomedOutResamplingMethod(
                layer.dataProvider().zoomedOutResamplingMethod()
            )

        return res

    def workspace_id(self) -> Optional[str]:
        """
        Returns the target workspace ID
        """
        return self._workspace_id

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
        if not self.unsupported_layers and not self.unsupported_styles:
            return None

        msg = ''
        if self.unsupported_layers:
            msg += '<p>' + self.tr('The following layers are not supported '
                                   'and won\'t be uploaded:') + '</p><ul>'

            for layer_name, reason in self.unsupported_layers:
                if reason:
                    msg += '<li><b>{}</b>: {}</li>'.format(layer_name, reason)
                else:
                    msg += '<li><b>{}</b></li>'.format(layer_name)

            msg += '</ul>'

        if self.unsupported_styles:
            msg += ('<p>' + self.tr('The following layer styles cannot '
                                    'be fully converted to Felt:') +
                    '</p><ul>')

            for layer_name, reasons in self.unsupported_styles:
                if len(reasons) > 1:
                    msg += '<li><b>{}</b>:<ul>'.format(layer_name)
                    for reason in reasons:
                        msg += '<li>{}</li>'.format(reason)
                    msg += '</ul></li>'
                else:
                    msg += '<li><b>{}</b>: {}</li>'.format(layer_name,
                                                           reasons[0])

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
                len(self.layers) +  # layer uploads
                (1 if self.project_structure.has_groups()
                 else 0)  # for final group update
        )

        self.feedback = QgsFeedback()

        multi_step_feedback = MultiStepFeedback(
            total_steps, self.feedback
        )
        self.feedback.progressChanged.connect(self.setProgress)

        for layer_details in self.layers:
            layer_details.layer.moveToThread(QThread.currentThread())

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

        conversion_context = ConversionContext()

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
        imported_by_url = {}

        for layer_details in self.layers:
            layer = layer_details.layer

            if self.isCanceled():
                return False

            if LayerExporter.layer_import_url(layer):
                result = LayerExporter.import_from_url(
                    layer,
                    self.associated_map,
                    multi_step_feedback)

                if result.error_message:
                    self.error_string = self.tr(
                        'Error occurred while exporting layer {}: {}').format(
                        layer.name(),
                        result.error_message
                    )
                    self.status_changed.emit(self.error_string)

                    return False
                layer.moveToThread(None)

                result.ordering_key = layer_details.ordering_key
                result.group_name = layer_details.destination_group_name
                imported_by_url[layer] = result
            else:

                self.status_changed.emit(
                    self.tr('Exporting {}').format(layer.name())
                )
                try:
                    result = exporter.export_layer_for_felt(
                        layer,
                        conversion_context,
                        multi_step_feedback
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

                result.group_name = layer_details.destination_group_name
                result.ordering_key = layer_details.ordering_key
                layer.moveToThread(None)
                to_upload[layer] = result

            multi_step_feedback.step_finished()

        if conversion_context.warnings:
            Logger.instance().log_message_json(
                conversion_context.format_warnings_for_reporting()
            )

        if self.isCanceled():
            return False

        rate_limit_counter = 0

        all_group_ordering_keys = self.project_structure.group_ordering_keys()
        if all_group_ordering_keys:
            # ensure group names match their order in the QGIS project
            created_groups = API_CLIENT.create_layer_groups(
                map_id=self.associated_map.id,
                layer_group_names=list(all_group_ordering_keys.keys()),
                ordering_keys=all_group_ordering_keys
            )
            created_group_details = {
                group.name: group
                for group in created_groups
            }
        else:
            created_group_details = {}

        for layer, details in to_upload.items():
            if self.isCanceled():
                return False

            self.status_changed.emit(
                self.tr('Uploading {}').format(layer.name())
            )

            while True:
                reply = API_CLIENT.prepare_layer_upload_v2(
                    map_id=self.associated_map.id,
                    name=layer.name(),
                    feedback=self.feedback
                )

                if reply.attribute(
                        QNetworkRequest.HttpStatusCodeAttribute) == 429:
                    rate_limit_counter += 1
                    if rate_limit_counter > 3:
                        self.error_string = \
                            'Rate limit exceeded, cannot share map'
                        Logger.instance().log_error_json(
                            {
                                'type': Logger.MAP_EXPORT,
                                'error':
                                    'Error preparing layer upload: {}'.format(
                                        self.error_string)
                            }
                        )

                        return False

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

            upload_details = json.loads(reply.content().data().decode())
            upload_params = S3UploadParameters.from_json(
                upload_details)

            # unused in api v2?
            # file_names = [Path(details.filename).name],
            # style = details.style,

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

            layer_id = upload_details.get('layer_id')
            if details.style and details.style.fsl is not None:
                if not layer_id:
                    Logger.instance().log_error_json(
                        {
                            'type': Logger.S3_UPLOAD,
                            'error': 'Didn\'t get layer id '
                                     'to use for patching style'
                        }
                    )
                else:
                    reply = API_CLIENT.patch_style(
                        map_id=self.associated_map.id,
                        layer_id=layer_id,
                        fsl=details.style.fsl
                    )
                    loop = QEventLoop()
                    reply.finished.connect(loop.exit)
                    loop.exec()

            reply = None
            if details.group_name:
                group_id = created_group_details[details.group_name].group_id
                reply = API_CLIENT.update_layer_details(
                    map_id=self.associated_map.id,
                    layer_id=layer_id,
                    layer_group_id=group_id,
                    ordering_key=details.ordering_key,
                )
            elif details.ordering_key is not None:
                reply = API_CLIENT.update_layer_details(
                    map_id=self.associated_map.id,
                    layer_id=layer_id,
                    ordering_key=details.ordering_key,
                )

            if reply and reply.error() != QNetworkReply.NoError:
                self.error_string = reply.errorString()
                Logger.instance().log_error_json(
                    {
                        'type': Logger.MAP_EXPORT,
                        'error': 'Error updating layer details: {}'.format(
                            self.error_string)
                    }
                )
                return False

            multi_step_feedback.step_finished()

        for layer, details in imported_by_url.items():
            if self.isCanceled():
                return False

            self.status_changed.emit(
                self.tr('Updating {}').format(layer.name())
            )

            reply = None
            if details.group_name:
                group_id = created_group_details[details.group_name].group_id
                reply = API_CLIENT.update_layer_details(
                    map_id=self.associated_map.id,
                    layer_id=details.layer_id,
                    layer_group_id=group_id,
                    ordering_key=details.ordering_key,
                )
            elif details.ordering_key is not None:
                reply = API_CLIENT.update_layer_details(
                    map_id=self.associated_map.id,
                    layer_id=details.layer_id,
                    ordering_key=details.ordering_key,
                )

            if reply and reply.error() != QNetworkReply.NoError:
                self.error_string = reply.errorString()
                Logger.instance().log_error_json(
                    {
                        'type': Logger.MAP_EXPORT,
                        'error': 'Error updating layer details: {}'.format(
                            self.error_string)
                    }
                )
                return False

            multi_step_feedback.step_finished()

        # do this a second time because the order gets overwritten!
        if created_group_details:
            API_CLIENT.apply_layer_groups_updates(
                map_id=self.associated_map.id,
                group_details=created_group_details.values()
            )
            multi_step_feedback.step_finished()

        return True

    # pylint: enable=too-many-locals
    # pylint: enable=too-many-return-statements
    # pylint: enable=too-many-branches
    # pylint: enable=too-many-statements
