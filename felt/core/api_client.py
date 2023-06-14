# -*- coding: utf-8 -*-
"""Felt API client

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

import json
from typing import (
    Dict,
    Optional,
    List,
    Union,
    Tuple
)

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

from .s3_upload_parameters import S3UploadParameters
from .layer_style import LayerStyle


class FeltApiClient:
    """
    Client for the Felt API
    """

    URL = 'https://felt.com/api/v1'
    USER_ENDPOINT = '/user'
    CREATE_MAP_ENDPOINT = '/maps'
    CREATE_LAYER_ENDPOINT = '/maps/{}/layers'
    FINISH_LAYER_ENDPOINT = '/maps/{}/layers/{}/finish_upload'

    def __init__(self):
        # default headers to add to all requests
        self.headers = {
            'accept': 'application/json'
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
    def build_url(endpoint: str) -> QUrl:
        """
        Returns the full url of the specified endpoint
        """
        return QUrl(FeltApiClient.URL + endpoint)

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

    def _build_request(self, endpoint: str, headers=None, params=None) \
            -> QNetworkRequest:
        """
        Builds a network request
        """
        url = self.build_url(endpoint)

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

    def create_map(self,
                   lat: float,
                   lon: float,
                   zoom: int,
                   title: Optional[str]=None,
                   basemap: Optional[str]=None,
                   layer_urls: List[str]=[],
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
        # TODO -- layer URLS!
        json_data = json.dumps(request_params)
        if blocking:
            return QgsNetworkAccessManager.instance().blockingPost(
                request,
                json_data.encode(),
                feedback=feedback
            )
        else:
            return QgsNetworkAccessManager.instance().post(request,
                                                           json_data.encode())

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

        else:
            return QgsNetworkAccessManager.instance().post(
                request,
                json_data.encode()
            )

    def create_upload_file_request(self,
                                   filename: str,
                                   content: bytes,
                                   parameters: S3UploadParameters) \
            -> Tuple[QNetworkRequest, QByteArray]:
        """
        Prepares a network request for a file upload
        """

        network_request = QNetworkRequest(QUrl(parameters.url))

        network_request.setRawHeader(b'Host',
                                     parameters.url[
                                     len('https://'):-1].encode())
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
        else:
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

        else:
            return QgsNetworkAccessManager.instance().post(
                request,
                json_data.encode()
            )


API_CLIENT = FeltApiClient()
