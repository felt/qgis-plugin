# -*- coding: utf-8 -*-
"""Recent maps item model

.. note:: This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

__author__ = '(C) 2023 by Nyall Dawson'
__date__ = '21/08/2023'
__copyright__ = 'Copyright 2023, North Road'
# This will get replaced with a git SHA1 when you do a git archive
__revision__ = '$Format:%H$'


import json
from functools import partial
from typing import (
    Optional,
    List
)

from qgis.PyQt import sip
from qgis.PyQt.QtCore import (
    Qt,
    QAbstractItemModel,
    QObject,
    QModelIndex
)
from qgis.PyQt.QtNetwork import (
    QNetworkReply
)

from .api_client import API_CLIENT
from .map import Map
from .thumbnail_manager import AsyncThumbnailManager


class RecentMapsModel(QAbstractItemModel):
    """
    Qt model for recent maps
    """

    TitleRole = Qt.UserRole + 1
    UrlRole = Qt.UserRole + 2
    ThumbnailRole = Qt.UserRole + 3
    IdRole = Qt.UserRole + 4

    LIMIT = 100

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

        self._current_reply = None
        self._filter_string: Optional[str] = None
        self.maps: List[Map] = []
        self._next_page: Optional[str] = None
        self._load_next_results()

        self._thumbnail_manager = AsyncThumbnailManager()
        self._thumbnail_manager.downloaded.connect(self._thumbnail_downloaded)

    def set_filter_string(self, filter_string: str):
        """
        Sets a text filter for the view
        """
        if filter_string == self._filter_string:
            return

        self.beginResetModel()
        self._filter_string = filter_string
        self.maps = []
        self._current_reply = None
        self._next_page = None
        self.endResetModel()

        self._load_next_results()

    def _load_next_results(self):
        self._current_reply = API_CLIENT.recent_maps_async(
            filter_string=self._filter_string,
            cursor=self._next_page
        )
        self._current_reply.finished.connect(
            partial(self._reply_finished, self._current_reply))

    def _reply_finished(self, reply: QNetworkReply):
        if sip.isdeleted(self):
            return

        if reply != self._current_reply:
            # an old reply we don't care about anymore
            return

        self._current_reply = None

        if reply.error() == QNetworkReply.OperationCanceledError:
            return

        if reply.error() == QNetworkReply.ContentNotFoundError:
            self._next_page = None
            return

        if reply.error() != QNetworkReply.NoError:
            return

        result = json.loads(reply.readAll().data().decode())
        next_page = result.get('meta', {}).get('next')
        if next_page == self._next_page:
            self._next_page = None
        else:
            self._next_page = next_page

        self.beginInsertRows(QModelIndex(), len(self.maps),
                             len(self.maps) + len(result) - 1)

        thumbnail_urls = set()
        for map_json in result.get('data', []):
            _map = Map.from_json(map_json)
            self.maps.append(_map)

            if _map.thumbnail_url:
                thumbnail_urls.add(_map.thumbnail_url)

            if len(self.maps) >= self.LIMIT:
                self._next_page = None
                break

        self.endInsertRows()

        for thumbnail_url in thumbnail_urls:
            self._thumbnail_manager.download_thumbnail(thumbnail_url)

    # Qt model interface

    # pylint: disable=missing-docstring, unused-arguments
    def index(self, row, column, parent=QModelIndex()):
        if column < 0 or column >= self.columnCount():
            return QModelIndex()

        if not parent.isValid() and 0 <= row < len(self.maps):
            return self.createIndex(row, column)

        return QModelIndex()

    def parent(self, index):
        return QModelIndex()  # all are top level items

    def rowCount(self, parent=QModelIndex()):
        if not parent.isValid():
            return len(self.maps)
        # no child items
        return 0

    def columnCount(self, parent=QModelIndex()):
        return 1

    def data(self, index, role=Qt.DisplayRole):
        _map = self.index2map(index)
        if _map:
            if role in (self.TitleRole, Qt.DisplayRole, Qt.ToolTipRole):
                return _map.title
            if role == self.UrlRole:
                return _map.url
            if role == self.IdRole:
                return _map.id
            if role in (self.ThumbnailRole, Qt.DecorationRole):
                return self._thumbnail_manager.thumbnail(
                    _map.thumbnail_url)

        return None

    def flags(self, index):
        f = super().flags(index)
        if not index.isValid():
            return f

        return f | Qt.ItemIsEnabled

    def canFetchMore(self, QModelIndex):
        if not self.maps:
            return True
        return self._next_page is not None

    def fetchMore(self, QModelIndex):
        if self._current_reply:
            return

        self._load_next_results()

    # pylint: enable=missing-docstring, unused-arguments
    def index2map(self, index: QModelIndex) -> Optional[Map]:
        """
        Returns the map at the given model index
        """
        if not index.isValid() or index.row() < 0 or index.row() >= len(
                self.maps):
            return None

        return self.maps[index.row()]

    def _thumbnail_downloaded(self, url: str):
        """
        Called when a thumbnail is downloaded
        """
        for row, _map in enumerate(self.maps):
            if _map.thumbnail_url == url:
                index = self.index(row, 0)
                self.dataChanged.emit(index, index)
