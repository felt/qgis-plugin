"""
Felt API client
"""

import json
import re
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


class PaidPlanRequiredError(Exception):
    """Raised when an API operation requires a paid plan"""
    pass


@dataclass
class FeltApiError:
    """
    Encapsulates an error response returned by the Felt API.

    The API returns errors as a JSON envelope of the form::

        {"errors": [{"title": ..., "detail": ..., "code": ...}]}

    Only the first error in the envelope is retained.
    """
    status_code: Optional[int] = None
    code: Optional[str] = None
    title: Optional[str] = None
    detail: Optional[str] = None
    # Qt's description of the failure, used when the API gave no detail
    network_error_string: Optional[str] = None
    # True if the API reported (via the x-api-limit-exceeded header) that
    # the workspace's plan does not allow (more) API calls
    api_limit_exceeded: bool = False

    # HTTP status codes used by the API when a workspace's plan does
    # not permit the operation
    PAID_PLAN_STATUS_CODES = (402, 403)

    # response header set by the API when the workspace's plan does not
    # allow (more) API calls
    API_LIMIT_EXCEEDED_HEADER = b'x-api-limit-exceeded'

    # stable error codes the API uses for plan/billing restrictions
    PAID_PLAN_ERROR_CODES = (
        'plan_upgrade_required',
        'forbidden',
        'payment_required',
        'paid_plan_required',
        'plan_required',
        'upgrade_required',
        'over_storage_limit',
        'over_processing_limit',
    )

    # fallback: keywords in the error text which indicate a plan problem
    PAID_PLAN_MESSAGE_PATTERN = re.compile(
        r'\b(plan|plans|trial|upgrade|upgraded|subscription|subscribe|'
        r'billing|payment|paid)\b',
        re.IGNORECASE
    )

    def is_paid_plan_error(self) -> bool:
        """
        Returns True if the error indicates that the operation requires
        a paid plan (or a trial of a paid plan)
        """
        if self.status_code in FeltApiError.PAID_PLAN_STATUS_CODES:
            return True

        if self.code and self.code.lower() in \
                FeltApiError.PAID_PLAN_ERROR_CODES:
            return True

        # a 429 which is caused by the workspace's plan (as opposed to
        # transient throttling) cannot be resolved by retrying
        if self.status_code == 429 and self.api_limit_exceeded:
            return True

        for text in (self.detail, self.title):
            if text and FeltApiError.PAID_PLAN_MESSAGE_PATTERN.search(text):
                return True

        return False

    def message(self) -> Optional[str]:
        """
        Returns a human readable message describing the error, preferring
        the detail returned by the API over Qt's generic description
        """
        return self.detail or self.title or self.network_error_string

    @staticmethod
    def from_content(status_code: Optional[int],
                     content: Optional[bytes],
                     network_error_string: Optional[str] = None,
                     api_limit_exceeded: bool = False) \
            -> Optional['FeltApiError']:
        """
        Parses an error from the HTTP status code and body of a reply.

        Returns None if the reply does not represent an error.
        """
        code = None
        title = None
        detail = None
        has_error_body = False

        if content:
            try:
                response = json.loads(
                    content.decode() if isinstance(content, bytes)
                    else str(content))
            except (ValueError, UnicodeDecodeError):
                response = None

            if isinstance(response, dict):
                errors = response.get('errors')
                if isinstance(errors, list) and errors:
                    has_error_body = True
                    first = errors[0]
                    if isinstance(first, dict):
                        code = first.get('code')
                        title = first.get('title')
                        detail = first.get('detail')
                    elif isinstance(first, str):
                        detail = first
                elif isinstance(response.get('error'), str):
                    has_error_body = True
                    detail = response['error']
                elif isinstance(response.get('message'), str):
                    # legacy shape used by some API error responses
                    has_error_body = True
                    detail = response['message']

        is_http_error = status_code is not None and status_code >= 400
        if not is_http_error and not has_error_body \
                and not network_error_string:
            return None

        return FeltApiError(
            status_code=status_code,
            code=code,
            title=title,
            detail=detail,
            network_error_string=network_error_string,
            api_limit_exceeded=api_limit_exceeded
        )

    @staticmethod
    def from_reply(reply: Union[QNetworkReply, QgsNetworkReplyContent]) \
            -> Optional['FeltApiError']:
        """
        Parses an error from a network reply.

        Returns None if the reply does not represent an error.
        """
        status_code = reply.attribute(
            QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        if status_code is not None:
            try:
                status_code = int(status_code)
            except (TypeError, ValueError):
                status_code = None

        network_error_string = None
        if reply.error() != QNetworkReply.NetworkError.NoError:
            network_error_string = reply.errorString()
            if status_code is None and reply.error() == \
                    QNetworkReply.NetworkError.ContentAccessDenied:
                status_code = 403

        if isinstance(reply, QgsNetworkReplyContent):
            content = bytes(reply.content())
        else:
            content = bytes(reply.readAll())

        api_limit_exceeded = False
        if reply.hasRawHeader(FeltApiError.API_LIMIT_EXCEEDED_HEADER):
            api_limit_exceeded = bytes(reply.rawHeader(
                FeltApiError.API_LIMIT_EXCEEDED_HEADER
            )).decode().strip().lower() == 'true'

        return FeltApiError.from_content(
            status_code, content, network_error_string, api_limit_exceeded)


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

    # boundary marker used when building multipart/form-data upload bodies
    MULTIPART_BOUNDARY = 'QGISFeltPluginFormBoundary'

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
        boundary = self.MULTIPART_BOUNDARY
        network_request.setRawHeader(
            b"Content-Type",
            "multipart/form-data; boundary={}".format(boundary).encode())

        delimiter = "--{}\r\n".format(boundary).encode()
        closing_delimiter = "--{}--\r\n".format(boundary).encode()

        # build the form content as bytes: PyQt6 does not permit appending
        # strings to QByteArray
        form_content = b''
        for name, value in parameters.to_form_fields().items():
            form_content += delimiter
            form_content += b"Content-Disposition: form-data; "
            form_content += f"name=\"{name}\"".encode()
            form_content += b"\r\n"
            form_content += b"\r\n"
            form_content += str(value).encode()
            form_content += b"\r\n"

        form_content += delimiter
        form_content += b"Content-Disposition: "
        form_content += \
            f"form-data; name=\"file\"; filename=\"{filename}\"\r\n".encode()
        form_content += b"Content-Type: application/octet-stream\r\n"
        form_content += b"\r\n"

        form_content += content

        form_content += b"\r\n"
        form_content += closing_delimiter

        form_data = QByteArray(form_content)
        content_length = form_data.length()
        network_request.setRawHeader(
            b"Content-Length",
            str(content_length).encode()
        )
        return network_request, form_data

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

        api_error = FeltApiError.from_reply(reply)
        if api_error and api_error.is_paid_plan_error():
            raise PaidPlanRequiredError(
                api_error.detail or api_error.title or '')

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
