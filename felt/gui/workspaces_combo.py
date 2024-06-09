"""
Widgets for selection from Workspaces
"""

from typing import Optional

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (
    QWidget,
    QComboBox,
)
from ..core import WorkspacesModel


class WorkspacesComboBox(QComboBox):
    """
    Custom combo box for workspace selection
    """

    workspace_changed = pyqtSignal(str)
    no_workspaces_found = pyqtSignal()
    workspaces_loaded = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._model = WorkspacesModel(self)
        self._model.no_workspaces_found.connect(self.no_workspaces_found)
        self._model.workspaces_loaded.connect(self.workspaces_loaded)
        self.setModel(self._model)

        self.currentIndexChanged.connect(self._index_changed)

    def set_workspace(self, workspace: str):
        """
        Sets the current workspace to show
        """
        idx = self.findData(workspace, WorkspacesModel.IdRole)
        if idx >= 0:
            self.setCurrentIndex(idx)

    def current_workspace_id(self) -> Optional[str]:
        """
        Returns the current selected workspace ID
        """
        return self.currentData(WorkspacesModel.IdRole)

    def _index_changed(self, index):
        """
        Called when the current selected workspace is changed
        """
        self.workspace_changed.emit(
            self.currentData(
                WorkspacesModel.IdRole
            )
        )
