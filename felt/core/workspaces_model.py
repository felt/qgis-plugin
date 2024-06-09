"""
Workspaces item model
"""

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
    QModelIndex,
    pyqtSignal
)
from qgis.PyQt.QtNetwork import (
    QNetworkReply
)

from .api_client import API_CLIENT
from .workspace import Workspace


class WorkspacesModel(QAbstractItemModel):
    """
    Qt model for workspaces
    """

    NameRole = Qt.UserRole + 1
    UrlRole = Qt.UserRole + 2
    IdRole = Qt.UserRole + 4

    no_workspaces_found = pyqtSignal()
    workspaces_loaded = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

        self._current_reply = None
        self.workspaces: List[Workspace] = []
        self._load_results()

    def _load_results(self):
        """
        Triggered when the next page of results needs to be loaded
        """
        self._current_reply = API_CLIENT.workspaces_async()
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

        workspaces = result.get('data', [])

        self.beginInsertRows(QModelIndex(), len(self.workspaces),
                             len(self.workspaces) + len(workspaces) - 1)

        for workspace_json in workspaces:
            _workspace = Workspace.from_json(workspace_json)
            self.workspaces.append(_workspace)

        self.endInsertRows()

        if not self.workspaces:
            self.no_workspaces_found.emit()
        else:
            self.workspaces_loaded.emit()

    # Qt model interface

    # pylint: disable=missing-docstring,unused-argument
    def index(self, row, column, parent=QModelIndex()):
        if column < 0 or column >= self.columnCount():
            return QModelIndex()

        if not parent.isValid() and 0 <= row < len(self.workspaces):
            return self.createIndex(row, column)

        return QModelIndex()

    def parent(self, index):
        return QModelIndex()  # all are top level items

    def rowCount(self, parent=QModelIndex()):
        if not parent.isValid():
            return len(self.workspaces)
        # no child items
        return 0

    def columnCount(self, parent=QModelIndex()):
        return 1

    # pylint:disable=too-many-return-statements,too-many-branches
    def data(self,
             index,
             role=Qt.DisplayRole):

        _workspace = self.index2workspace(index)
        if _workspace:
            if role in (self.NameRole, Qt.DisplayRole, Qt.ToolTipRole):
                return _workspace.name
            if role == self.UrlRole:
                return _workspace.url
            if role == self.IdRole:
                return _workspace.id

        return None

    # pylint:enable=too-many-return-statements,too-many-branches

    def flags(self, index):
        f = super().flags(index)
        if not index.isValid():
            return f

        return f | Qt.ItemIsEnabled | Qt.ItemIsSelectable

    # pylint: enable=missing-docstring,unused-argument
    def index2workspace(self, index: QModelIndex) -> Optional[Workspace]:
        """
        Returns the workspace at the given model index
        """
        if not index.isValid() or index.row() < 0 or index.row() >= len(
                self.workspaces):
            return None

        return self.workspaces[index.row()]
