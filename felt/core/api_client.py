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
    List
)

from qgis.PyQt.QtCore import (
    QUrl,
    QUrlQuery
)
from qgis.PyQt.QtNetwork import (
    QNetworkRequest,
    QNetworkReply
)
from qgis.core import QgsNetworkAccessManager


class FeltApiClient:
    """
    Client for the Felt API
    """

    URL = 'https://felt.com/api/v1'
    USER_ENDPOINT = '/user'
    CREATE_MAP_ENDPOINT = '/maps'
    CREATE_LAYER_ENDPOINT = '/maps/{}/layers'

    def __init__(self):
        # default headers to add to all requests
        self.headers = {
            'accept': 'application/json'
        }
        self.token: Optional[str] = None

    def set_token(self, token: str):
        """
        Sets the access token
        """
        self.token = token
        self.headers['authorization'] = f'Bearer {self.token}'

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
                   ) -> QNetworkReply:
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
        return QgsNetworkAccessManager.instance().post(request,
                                                       json_data.encode())

    def prepare_layer_upload(self,
                             map_id: str,
                             name: str,
                             file_names: List[str]):
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
        json_data = json.dumps(request_params)
        return QgsNetworkAccessManager.instance().post(request,
                                                       json_data.encode())



API_CLIENT = FeltApiClient()
