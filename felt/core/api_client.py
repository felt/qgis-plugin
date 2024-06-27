"""
Felt API client
"""

import json
from typing import (
    Dict,
    Optional,
    List,
    Union,
    Tuple
)
from dataclasses import dataclass

from qgis.PyQt.QtCore import (
    QUrl,
    QUrlQuery,
    QByteArray
)
from qgis.PyQt.QtNetwork import (
    QNetworkRequest,
    QNetworkReply
)
from qgis.core import (
    QgsNetworkAccessManager,
    QgsNetworkReplyContent,
    QgsFeedback
)

from .layer_style import LayerStyle
from .meta import PLUGIN_METADATA_PARSER
from .s3_upload_parameters import S3UploadParameters
from .enums import UsageType
from .constants import (
    FELT_API_URL,
    FELT_APIV2_URL
)

PLUGIN_VERSION = "0.7.0"


@dataclass
class CreatedGroupDetails:
    """
    Encapsulates details of a created layer group
    """
    group_id: Optional[str] = None
    name: Optional[str] = None
    ordering_key: Optional[int] = None


class FeltApiClient:
    """
    Client for the Felt API
    """

    USER_ENDPOINT = '/user'
    WORKSPACES_ENDPOINT = '/workspaces'
    CREATE_MAP_ENDPOINT = '/maps'
    CREATE_LAYER_ENDPOINT = '/maps/{}/layers'
    FINISH_LAYER_ENDPOINT = '/maps/{}/layers/{}/finish_upload'
    URL_IMPORT_ENDPOINT = '/maps/{}/layers/url_import'
    USAGE_ENDPOINT = '/internal/reports'
    RECENT_MAPS_ENDPOINT = '/maps/recent'
    UPLOAD_V2_ENDPOINT = '/maps/{}/upload'
    PATCH_STYLE_ENDPOINT = '/maps/{}/layers/{}/style'
    UPDATE_LAYER_ENDPOINT = '/maps/{}/layers'
    LAYER_GROUPS_ENDPOINT = '/maps/{}/layer_groups'

    def __init__(self):
        # default headers to add to all requests
        self.headers = {
            'accept': 'application/json',
            'x-qgis-add-to-felt-version': PLUGIN_METADATA_PARSER.get_version()
        }
        self.token: Optional[str] = None

    def set_token(self, token: Optional[str]):
        """
        Sets the access token
        """
        self.token = token
        if self.token:
            self.headers['authorization'] = f'Bearer {self.token}'
        else:
            try:
                del self.headers['authorization']
            except KeyError:
                pass

    @staticmethod
    def build_url(endpoint: str, version: int = 1) -> QUrl:
        """
        Returns the full url of the specified endpoint
        """
        if version == 1:
            return QUrl(FELT_API_URL + endpoint)
        elif version == 2:
            return QUrl(FELT_APIV2_URL + endpoint)

    @staticmethod
    def _to_url_query(parameters: Dict[str, object]) -> QUrlQuery:
        """
        Converts query parameters as a dictionary to a URL query
        """
        query = QUrlQuery()
        for name, value in parameters.items():
            if isinstance(value, (list, tuple)):
                for v in value:
                    query.addQueryItem(name, str(v))
            else:
                query.addQueryItem(name, str(value))
        return query

    def _build_request(self, endpoint: str, headers=None, params=None,
                       version: int = 1) \
            -> QNetworkRequest:
        """
        Builds a network request
        """
        url = self.build_url(endpoint, version)

        if params:
            url.setQuery(FeltApiClient._to_url_query(params))

        network_request = QNetworkRequest(url)

        combined_headers = self.headers
        if headers:
            combined_headers.update(headers)

        for header, value in combined_headers.items():
            network_request.setRawHeader(header.encode(), value.encode())

        return network_request

    def user(self) -> QNetworkReply:
        """
        Returns information about the user
        """
        request = self._build_request(self.USER_ENDPOINT)
        return QgsNetworkAccessManager.instance().get(request)

    def workspaces_async(self) -> QNetworkReply:
        """
        Retrieve workspaces asynchronously
        """
        params = {}

        request = self._build_request(
            self.WORKSPACES_ENDPOINT,
            params=params
        )
        return QgsNetworkAccessManager.instance().get(request)

    def recent_maps_async(self,
                          cursor: Optional[str] = None,
                          filter_string: Optional[str] = None,
                          workspace_id: Optional[str] = None) \
            -> QNetworkReply:
        """
        Retrieve recent maps asynchronously
        """
        params = {}
        if cursor:
            params['cursor'] = cursor
        if filter_string:
            params['title'] = filter_string
        if workspace_id:
            params['workspace_id'] = workspace_id

        request = self._build_request(
            self.RECENT_MAPS_ENDPOINT,
            params=params
        )
        return QgsNetworkAccessManager.instance().get(request)

    # pylint: disable=unused-argument
    def create_map(self,
                   lat: float,
                   lon: float,
                   zoom: int,
                   title: Optional[str] = None,
                   basemap: Optional[str] = None,
                   layer_urls: Optional[List[str]] = None,
                   workspace_id: Optional[str] = None,
                   blocking: bool = False,
                   feedback: Optional[QgsFeedback] = None
                   ) -> Union[QNetworkReply, QgsNetworkReplyContent]:
        """
        Creates a Felt map
        """
        request = self._build_request(self.CREATE_MAP_ENDPOINT,
                                      {'Content-Type': 'application/json'})

        request_params = {
            'lat': lat,
            'lon': lon,
            'zoom': zoom
        }
        if title:
            request_params['title'] = title
        if basemap:
            request_params['basemap'] = basemap
        if workspace_id:
            request_params['workspace_id'] = workspace_id

        # TODO -- layer URLS!
        json_data = json.dumps(request_params)
        if blocking:
            return QgsNetworkAccessManager.instance().blockingPost(
                request,
                json_data.encode(),
                feedback=feedback
            )

        return QgsNetworkAccessManager.instance().post(request,
                                                       json_data.encode())

    # pylint: enable=unused-argument

    def url_import_to_map(self,
                          map_id: str,
                          name: str,
                          layer_url: str,
                          blocking: bool = False,
                          feedback: Optional[QgsFeedback] = None) \
            -> Union[QNetworkReply, QgsNetworkReplyContent]:
        """
        Prepares a layer upload
        """
        request = self._build_request(
            self.UPLOAD_V2_ENDPOINT.format(map_id),
            {'Content-Type': 'application/json'},
            version=2
        )

        request_params = {
            'name': name,
            'import_url': layer_url
        }

        json_data = json.dumps(request_params)
        if blocking:
            return QgsNetworkAccessManager.instance().blockingPost(
                request,
                json_data.encode(),
                feedback=feedback
            )

        return QgsNetworkAccessManager.instance().post(
            request,
            json_data.encode()
        )

    def prepare_layer_upload(self,
                             map_id: str,
                             name: str,
                             file_names: List[str],
                             style: Optional[LayerStyle] = None,
                             blocking: bool = False,
                             feedback: Optional[QgsFeedback] = None) \
            -> Union[QNetworkReply, QgsNetworkReplyContent]:
        """
        Prepares a layer upload
        """
        request = self._build_request(
            self.CREATE_LAYER_ENDPOINT.format(map_id),
            {'Content-Type': 'application/json'}
        )

        request_params = {
            'name': name,
            'file_names': file_names
        }
        if style and style.fill_color and style.fill_color.isValid():
            request_params['fill_color'] = style.fill_color.name()
        if style and style.stroke_color and style.stroke_color.isValid():
            request_params['stroke_color'] = style.stroke_color.name()

        json_data = json.dumps(request_params)
        if blocking:
            return QgsNetworkAccessManager.instance().blockingPost(
                request,
                json_data.encode(),
                feedback=feedback
            )

        return QgsNetworkAccessManager.instance().post(
            request,
            json_data.encode()
        )

    def prepare_layer_upload_v2(self,
                                map_id: str,
                                name: str,
                                feedback: Optional[QgsFeedback] = None) \
            -> Union[QNetworkReply, QgsNetworkReplyContent]:
        """
        Prepares a layer upload, using v2 api
        """
        request = self._build_request(
            self.UPLOAD_V2_ENDPOINT.format(map_id),
            {'Content-Type': 'application/json'},
            version=2
        )

        request_params = {
            'name': name
        }

        json_data = json.dumps(request_params)
        reply = QgsNetworkAccessManager.instance().blockingPost(
            request,
            json_data.encode(),
            feedback=feedback
        )

        return reply

    def create_upload_file_request(self,
                                   filename: str,
                                   content: bytes,
                                   parameters: S3UploadParameters) \
            -> Tuple[QNetworkRequest, QByteArray]:
        """
        Prepares a network request for a file upload
        """

        network_request = QNetworkRequest(QUrl(parameters.url))

        network_request.setRawHeader(
            b'Host',
            parameters.url[len('https://'):-1].encode()
        )
        network_request.setRawHeader(
            b"Content-Type",
            b"multipart/form-data; boundary=QGISFormBoundary2XCkqVRLJ5XMxfw5")

        form_content = QByteArray()
        for name, value in parameters.to_form_fields().items():
            form_content.append("--QGISFormBoundary2XCkqVRLJ5XMxfw5\r\n")
            form_content.append("Content-Disposition: form-data; ")
            form_content.append(f"name=\"{name}\"")
            form_content.append("\r\n")
            form_content.append("\r\n")
            form_content.append(value)
            form_content.append("\r\n")

        form_content.append("--QGISFormBoundary2XCkqVRLJ5XMxfw5\r\n")
        form_content.append("Content-Disposition: ")
        form_content.append(
            f"form-data; name=\"file\"; filename=\"{filename}\"\r\n")
        form_content.append(
            "Content-Type: application/octet-stream\r\n")
        form_content.append("\r\n")

        form_content.append(content)

        form_content.append("\r\n")
        form_content.append("--QGISFormBoundary2XCkqVRLJ5XMxfw5--\r\n")

        content_length = form_content.length()
        network_request.setRawHeader(
            b"Content-Length",
            str(content_length).encode()
        )
        return network_request, form_content

    def upload_file(self,
                    filename: str,
                    content: bytes,
                    parameters: S3UploadParameters,
                    blocking: bool = False) \
            -> Union[QNetworkReply, QgsNetworkReplyContent]:
        """
        Triggers an upload
        """
        network_request, form_content = self.create_upload_file_request(
            filename, content, parameters
        )

        if blocking:
            return QgsNetworkAccessManager.instance().blockingPost(
                network_request,
                form_content
            )

        return QgsNetworkAccessManager.instance().post(
            network_request,
            form_content
        )

    def finalize_layer_upload(self,
                              map_id: str,
                              layer_id: str,
                              filename: str,
                              blocking: bool = False,
                              feedback: Optional[QgsFeedback] = None) \
            -> Union[QNetworkReply, QgsNetworkReplyContent]:
        """
        Finalizes a layer upload
        """
        request = self._build_request(
            self.FINISH_LAYER_ENDPOINT.format(map_id, layer_id),
            {'Content-Type': 'application/json'}
        )

        request_params = {
            'filename': filename
        }
        json_data = json.dumps(request_params)
        if blocking:
            return QgsNetworkAccessManager.instance().blockingPost(
                request,
                json_data.encode(),
                feedback=feedback
            )

        return QgsNetworkAccessManager.instance().post(
            request,
            json_data.encode()
        )

    def patch_style(self,
                    map_id: str,
                    layer_id: str,
                    fsl: Dict) \
            -> QNetworkReply:
        """
        Patches a layer's style
        """
        request = self._build_request(
            self.PATCH_STYLE_ENDPOINT.format(map_id, layer_id),
            {'Content-Type': 'application/json'}
        )

        style_post_data = {
            'style': json.dumps(fsl)
        }

        return QgsNetworkAccessManager.instance().sendCustomRequest(
            request,
            b"PATCH",
            json.dumps(style_post_data).encode()
        )

    def update_layer_details(self,
                             map_id: str,
                             layer_id: str,
                             layer_group_id: Optional[str] = None,
                             name: Optional[str] = None,
                             ordering_key: Optional[int] = None,
                             subtitle: Optional[str] = None) \
            -> QgsNetworkReplyContent:
        """
        Updates a layer's details
        """
        request = self._build_request(
            self.UPDATE_LAYER_ENDPOINT.format(map_id),
            {'Content-Type': 'application/json'},
            version=2
        )

        layer_details = {
                'id': layer_id
            }
        if layer_group_id:
            layer_details['layer_group_id'] = layer_group_id
        if name:
            layer_details['name'] = name
        if ordering_key:
            layer_details['ordering_key'] = ordering_key
        if subtitle:
            layer_details['subtitle'] = subtitle

        post_data = [layer_details]

        return QgsNetworkAccessManager.instance().blockingPost(
            request,
            json.dumps(post_data).encode()
        )

    def create_layer_groups(self,
                            map_id: str,
                            layer_group_names: List[str],
                            ordering_keys: Optional[Dict[str, int]] = None) \
            -> List[CreatedGroupDetails]:
        """
        Creates layer groups for a map
        """
        request = self._build_request(
            self.LAYER_GROUPS_ENDPOINT.format(map_id),
            {'Content-Type': 'application/json'},
            version=2
        )

        if not ordering_keys:
            group_post_data = [
                {'name': g,
                 'ordering_key': i} for i, g in enumerate(layer_group_names)
            ]
        else:
            group_post_data = [
                {'name': g,
                 'ordering_key': ordering_keys[g] or 0} for g in
                layer_group_names
            ]

        reply = QgsNetworkAccessManager.instance().blockingPost(
            request,
            json.dumps(group_post_data).encode()
        )

        return [
            CreatedGroupDetails(
                group_id=group['id'],
                name=group['name'],
                ordering_key=ordering_keys.get(group['name']))
            for group in json.loads(reply.content().data().decode())
        ]

    def apply_layer_groups_updates(self,
                                   map_id: str,
                                   group_details: List[CreatedGroupDetails]) \
            -> QgsNetworkReplyContent:
        """
        Updates layer group details
        """
        request = self._build_request(
            self.LAYER_GROUPS_ENDPOINT.format(map_id),
            {'Content-Type': 'application/json'},
            version=2
        )

        group_post_data = [
            {'id': g.group_id,
             'name': g.name,
             'ordering_key': g.ordering_key} for g in
            group_details
        ]

        return QgsNetworkAccessManager.instance().blockingPost(
            request,
            json.dumps(group_post_data).encode()
        )

    def report_usage(self,
                     content: str,
                     usage_type: UsageType = UsageType.Info) -> QNetworkReply:
        """
        Reports plugin usage.

        This is a non-blocking call. It returns a QNetworkReply for the post
        operation, but this can be safely ignored if no tracking of the
        post is required.
        """
        request = self._build_request(
            self.USAGE_ENDPOINT,
            {'Content-Type': 'application/json'}
        )

        request_params = {
            'type': usage_type.to_string(),
            'content': content
        }
        json_data = json.dumps(request_params)

        return QgsNetworkAccessManager.instance().post(
            request,
            json_data.encode()
        )


API_CLIENT = FeltApiClient()
