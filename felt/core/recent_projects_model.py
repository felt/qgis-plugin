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
import math
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
    QModelIndex,
    pyqtSignal,
    QDateTime
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
    MapRole = Qt.UserRole + 5
    SubTitleRole = Qt.UserRole + 6
    IsNewMapRole = Qt.UserRole + 7

    LIMIT = 100

    first_results_found = pyqtSignal()
    no_results_found = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

        self._current_reply = None
        self._new_map_title: Optional[str] = None
        self._filter_string: Optional[str] = None
        self.maps: List[Map] = []
        self._clear_maps_on_results = False
        self._no_results_found = False
        self._next_page: Optional[str] = None
        self._load_next_results()

        self._thumbnail_manager = AsyncThumbnailManager()
        self._thumbnail_manager.downloaded.connect(self._thumbnail_downloaded)

    def set_new_map_title(self, title: str):
        """
        Sets the title to use for the new map item
        """
        self._new_map_title = title
        self.dataChanged.emit(self.index(0, 0), self.index(0, 0))

    def filter_string(self) -> Optional[str]:
        """
        Returns the filter text
        """
        return self._filter_string

    def set_filter_string(self, filter_string: str):
        """
        Sets a text filter for the view
        """
        if filter_string == self._filter_string:
            return

        self._clear_maps_on_results = True
        self._filter_string = filter_string
        self._current_reply = None
        self._next_page = None

        self._load_next_results()

    def _load_next_results(self):
        """
        Triggered when the next page of results needs to be loaded
        """
        self._current_reply = API_CLIENT.recent_maps_async(
            filter_string=self._filter_string,
            cursor=self._next_page
        )
        self._current_reply.finished.connect(
            partial(self._reply_finished, self._current_reply))

    def _reply_finished(self, reply: QNetworkReply):
        """
        Triggered when an open network request is finished
        """

        if sip.isdeleted(self) or reply != self._current_reply:
            return

        self._current_reply = None

        if reply.error() == QNetworkReply.ContentNotFoundError:
            self._next_page = None
            return

        if reply.error() != QNetworkReply.NoError:
            return

        result = json.loads(reply.readAll().data().decode())
        next_page = result.get('meta', {}).get('next')
        self._next_page = next_page if next_page != self._next_page else None

        was_first_page = self._clear_maps_on_results or not self.maps

        if self._clear_maps_on_results:
            if self.maps:
                self.beginRemoveRows(QModelIndex(),
                                     1,
                                     1 + len(self.maps))
                self.maps = []
                self.endRemoveRows()
            self._clear_maps_on_results = False

        new_maps = result.get('data', [])
        if not new_maps:
            self._next_page = None

        self._no_results_found = not new_maps

        self.beginInsertRows(QModelIndex(), 1 + len(self.maps),
                             1 + len(self.maps) + len(new_maps) - 1)

        thumbnail_urls = set()
        for map_json in new_maps:
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

        if was_first_page and not new_maps:
            self.no_results_found.emit()
        elif was_first_page:
            self.first_results_found.emit()

    # Qt model interface

    # pylint: disable=missing-docstring,unused-argument
    def index(self, row, column, parent=QModelIndex()):
        if column < 0 or column >= self.columnCount():
            return QModelIndex()

        if not parent.isValid() and 0 <= row < 1 + len(self.maps):
            return self.createIndex(row, column)

        return QModelIndex()

    def parent(self, index):
        return QModelIndex()  # all are top level items

    def rowCount(self, parent=QModelIndex()):
        if not parent.isValid():
            return 1 + len(self.maps)
        # no child items
        return 0

    def columnCount(self, parent=QModelIndex()):
        return 1

    # pylint:disable=too-many-return-statements
    def pretty_format_date(self, date: QDateTime) -> str:
        """
        Creates a pretty format for a date difference, like '3 days ago'
        """
        now = QDateTime.currentDateTime()

        if date.date() == now.date():
            secs_diff = date.secsTo(now)
            if secs_diff < 60:
                return self.tr("just now")
            if secs_diff < 3600:
                minutes = math.floor(secs_diff / 60)
                return self.tr("{} minutes ago").format(
                    minutes) if minutes > 1 else self.tr("1 minute ago")

            hours = math.floor(secs_diff / 3600)
            return self.tr("{} hours ago").format(
                hours) if hours > 1 else self.tr("1 hour ago")

        days_diff = date.daysTo(now)
        if days_diff == 1:
            return self.tr("yesterday")
        if days_diff < 7:
            return self.tr("{} days ago").format(days_diff)
        if days_diff < 30:
            weeks = math.floor(days_diff / 7)
            return self.tr("{} weeks ago").format(
                weeks) if weeks > 1 else self.tr("1 week ago")
        if days_diff < 365:
            months = math.floor(days_diff / 30)
            return self.tr("{} months ago").format(
                months) if months > 1 else self.tr("1 month ago")

        years = math.floor(days_diff / 365)
        return self.tr("{} years ago").format(years) if years > 1 else self.tr(
            "1 year ago")
    # pylint:enable=too-many-return-statements

    # pylint:disable=too-many-return-statements,too-many-branches
    def data(self,
             index,
             role=Qt.DisplayRole):
        if index.row() == 0 and not index.parent().isValid():
            # special "New map" item
            if role in (self.TitleRole, Qt.DisplayRole, Qt.ToolTipRole):
                return self._new_map_title
            if role == self.SubTitleRole:
                return self.tr('New map')
            if role in (self.ThumbnailRole, Qt.DecorationRole):
                # pylint: disable=import-outside-toplevel
                from ..gui import GuiUtils
                # pylint: enable=import-outside-toplevel
                return GuiUtils.get_svg_as_image('plus.svg', 189, 142)
            if role == self.IsNewMapRole:
                return True

            return None

        _map = self.index2map(index)
        if _map:
            if role == self.MapRole:
                return _map
            if role in (self.TitleRole, Qt.DisplayRole, Qt.ToolTipRole):
                return _map.title
            if role == self.SubTitleRole and _map.last_visited:
                date_string = self.pretty_format_date(_map.last_visited)
                return self.tr('Last visited {}'.format(date_string))
            if role == self.UrlRole:
                return _map.url
            if role == self.IdRole:
                return _map.id
            if role in (self.ThumbnailRole, Qt.DecorationRole):
                return self._thumbnail_manager.thumbnail(
                    _map.thumbnail_url)
            if role == self.IsNewMapRole:
                return False

        return None

    # pylint:enable=too-many-return-statements,too-many-branches

    def flags(self, index):
        f = super().flags(index)
        if not index.isValid():
            return f

        return f | Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def canFetchMore(self, index: QModelIndex):
        if self._no_results_found:
            return False
        if not self.maps:
            return True
        return self._next_page is not None

    def fetchMore(self, index: QModelIndex):
        if self._current_reply:
            return

        self._load_next_results()

    # pylint: enable=missing-docstring,unused-argument
    def index2map(self, index: QModelIndex) -> Optional[Map]:
        """
        Returns the map at the given model index
        """
        if not index.isValid() or index.row() < 1 or index.row() >= 1 + len(
                self.maps):
            return None

        return self.maps[index.row() - 1]

    def _thumbnail_downloaded(self, url: str):
        """
        Called when a thumbnail is downloaded
        """
        for row, _map in enumerate(self.maps):
            if _map.thumbnail_url == url:
                index = self.index(1 + row, 0)
                self.dataChanged.emit(index, index)
