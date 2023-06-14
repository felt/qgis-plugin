# -*- coding: utf-8 -*-
"""Felt Create Map dialog

.. note:: This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

__author__ = '(C) 2022 by Nyall Dawson'
__date__ = '22/11/2022'
__copyright__ = 'Copyright 2022, North Road'
# This will get replaced with a git SHA1 when you do a git archive
__revision__ = '$Format:%H$'

from typing import (
    Optional,
    List
)

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import (
    QWidget,
    QDialog,
    QDialogButtonBox,
    QVBoxLayout
)

from qgis.core import (
    QgsMapLayer,
    QgsApplication
)

from ..core import (
    MapUploaderTask,
    Map
)

from .constants import (
    PRIVACY_POLICY_URL,
    TOS_URL
)
from .gui_utils import (
    GuiUtils,
    FELT_STYLESHEET
)
from .felt_dialog_header import FeltDialogHeader
from .authorization_manager import AUTHORIZATION_MANAGER

WIDGET, _ = uic.loadUiType(GuiUtils.get_ui_file_path('create_map.ui'))


class CreateMapDialog(QDialog, WIDGET):
    """
    Custom dialog for creating maps

    If the dialog is accepted then the authorization process should be
    started.
    """

    def __init__(self,
                 parent: Optional[QWidget] = None,
                 layers: Optional[List[QgsMapLayer]] = None):
        super().__init__(parent)
        self.setupUi(self)

        self.setStyleSheet(FELT_STYLESHEET)
        self.button_box.button(QDialogButtonBox.Ok).setStyleSheet(
            FELT_STYLESHEET)
        self.button_box.button(QDialogButtonBox.Cancel).setStyleSheet(
            FELT_STYLESHEET)

        vl = QVBoxLayout()
        vl.setContentsMargins( 0, 0,0 ,0)
        vl.addWidget(FeltDialogHeader())
        self.widget_logo.setStyleSheet('background: solid #3d521e;')
        self.widget_logo.setLayout(vl)

        self.setWindowTitle(self.tr('Create Felt Map'))

        self.stacked_widget.setCurrentIndex(0)

        self.layers = layers

        self.button_box.button(QDialogButtonBox.Ok).setText(
            self.tr('Add to Felt')
        )
        self.button_box.button(QDialogButtonBox.Ok).clicked.connect(
            self._start
        )
        self.button_box.button(QDialogButtonBox.Cancel).clicked.connect(
            self._cancel
        )
        self.button_box.button(QDialogButtonBox.Cancel).setText(
            self.tr('Close')
        )

        self.footer_label.linkActivated.connect(self._link_activated)

        self.map_uploader_task = MapUploaderTask(
            layers=self.layers
        )
        self.created_map: Optional[Map] = None
        self.map_title_edit.setText(self.map_uploader_task.default_map_title())
        self.map_title_edit.textChanged.connect(self._validate)

        self.progress_bar.setValue(0)

        if AUTHORIZATION_MANAGER.user:
            self.label_user.setText(
                self.tr('Signed in as: {}').format(
                    AUTHORIZATION_MANAGER.user.name
                )
            )

        self.started = False
        self._validate()

    def _cancel(self):
        """
        Cancels the upload
        """
        if self.started and self.map_uploader_task:
            self.map_uploader_task.cancel()
        else:
            self.reject()

    def _link_activated(self, link: str):
        """
        Called when a hyperlink is clicked in dialog labels
        """
        if link == 'privacy_policy':
            url = QUrl(PRIVACY_POLICY_URL)
        elif link == 'terms_of_use':
            url = QUrl(TOS_URL)
        else:
            return

        QDesktopServices.openUrl(url)

    def _validate(self):
        """
        Validates the dialog
        """
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(
            self._is_valid()
        )

    def _is_valid(self) -> bool:
        """
        Returns True if the dialog contains valid settings to begin
        the upload
        """
        return bool(self.map_title_edit.text().strip())

    def _start(self):
        """
        Starts the map upload process
        """
        self.started = True
        self.button_box.button(QDialogButtonBox.Cancel).setText(
            self.tr('Cancel')
        )
        self.button_box.button(QDialogButtonBox.Ok).setText(
            self.tr('Uploading')
        )
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)

        map_title = self.map_title_edit.text().strip()
        self.map_title_label.setText(map_title)
        self.map_uploader_task.project_title = map_title

        self.stacked_widget.setCurrentIndex(1)
        self.map_uploader_task.status_changed.connect(
            self.progress_label.setText
        )

        self.map_uploader_task.taskCompleted.connect(self._upload_finished)
        self.map_uploader_task.taskTerminated.connect(self._upload_terminated)
        self.map_uploader_task.progressChanged.connect(self.set_progress)

        self.button_box.button(QDialogButtonBox.Ok).clicked.disconnect(
            self._start
        )

        QgsApplication.taskManager().addTask(self.map_uploader_task)

    def set_progress(self, progress: float):
        self.progress_bar.setValue(int(progress))

    def _upload_finished(self):
        self.created_map = self.map_uploader_task.created_map
        self.map_uploader_task = None
        self.started = False

        self.button_box.button(QDialogButtonBox.Cancel).setText(
            self.tr('Close')
        )
        self.button_box.button(QDialogButtonBox.Ok).setText(
            self.tr('Open Map')
        )
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(True)
        self.button_box.button(QDialogButtonBox.Ok).clicked.connect(
            self._view_map
        )

    def _upload_terminated(self):
        if self.map_uploader_task.was_canceled:
            self.button_box.button(QDialogButtonBox.Ok).setText(
                self.tr('Canceled')
            )
            self.progress_label.setText(self.tr('Canceled'))
            self.button_box.button(QDialogButtonBox.Ok).setText(
                self.tr('Canceled')
            )
        else:
            self.button_box.button(QDialogButtonBox.Ok).setText(
                self.tr('Upload Failed')
            )

        self.map_uploader_task = None
        self.button_box.button(QDialogButtonBox.Cancel).setText(
            self.tr('Close')
        )

        self.button_box.button(QDialogButtonBox.Ok).setEnabled(
            False
        )

    def _view_map(self):
        if not self.created_map:
            return

        QDesktopServices.openUrl(QUrl(self.created_map.url))

