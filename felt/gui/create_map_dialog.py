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
from qgis.PyQt.QtCore import (
    Qt,
    QUrl
)
from qgis.PyQt.QtGui import (
    QDesktopServices,
    QFontMetrics,
    QColor
)
from qgis.PyQt.QtWidgets import (
    QWidget,
    QDialog,
    QDialogButtonBox,
    QVBoxLayout
)
from qgis.core import (
    QgsMapLayer,
    QgsApplication,
    QgsProject
)
from qgis.gui import QgsGui

from .authorization_manager import AUTHORIZATION_MANAGER
from .colored_progress_bar import ColorBar
from .constants import (
    PRIVACY_POLICY_URL,
    TOS_URL
)
from .felt_dialog_header import FeltDialogHeader
from .gui_utils import (
    GuiUtils,
    FELT_STYLESHEET
)
from ..core import (
    MapUploaderTask,
    Map
)

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
        self.setObjectName('CreateMapDialog')
        QgsGui.enableAutoGeometryRestore(self)

        self.setStyleSheet(FELT_STYLESHEET)
        self.page.setStyleSheet(FELT_STYLESHEET)
        self.page_2.setStyleSheet(FELT_STYLESHEET)
        self.button_box.button(QDialogButtonBox.Ok).setStyleSheet(
            FELT_STYLESHEET)
        self.button_box.button(QDialogButtonBox.Cancel).setStyleSheet(
            FELT_STYLESHEET)

        self.progress_label.setTextInteractionFlags(
            Qt.TextBrowserInteraction
        )
        self.progress_label.setOpenExternalLinks(True)

        vl = QVBoxLayout()
        vl.setContentsMargins(0, 0, 0, 0)
        vl.addWidget(FeltDialogHeader())
        self.widget_logo.setStyleSheet('background: solid #3d521e;')
        self.widget_logo.setLayout(vl)

        self.setWindowTitle(self.tr('Add to Felt'))

        self.footer_label.setMinimumWidth(
            QFontMetrics(self.footer_label.font()).width('x') * 40
        )

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
        self.footer_label.setText(
            GuiUtils.set_link_color(self.footer_label.text())
        )

        self.map_uploader_task: Optional[MapUploaderTask]
        if self.layers is None:
            QgsProject.instance().layersRemoved.connect(
                self._create_map_uploader_task)
            QgsProject.instance().layersAdded.connect(
                self._create_map_uploader_task)
        self._create_map_uploader_task()

        self.created_map: Optional[Map] = None
        self.map_title_edit.setText(self.map_uploader_task.default_map_title())
        self.map_title_edit.textChanged.connect(self._validate)

        self.warning_label.document().setDefaultStyleSheet(
            'body, p {margin-left:0px; padding-left: 0px;}'
        )
        self.warning_label.document().setDocumentMargin(0)

        self.progress_bar = ColorBar()
        vl = QVBoxLayout()
        vl.setContentsMargins(0, 0, 0, 0)
        vl.addWidget(self.progress_bar)
        self.progress_container.setLayout(vl)
        self.progress_bar.setValue(0)

        if AUTHORIZATION_MANAGER.user:
            self.label_user.setText(
                GuiUtils.set_link_color(
                    self.tr(
                        'Logged in as: {} ({})'
                    ).format(AUTHORIZATION_MANAGER.user.name,
                             AUTHORIZATION_MANAGER.user.email) +
                    ' <a href="logout">' + self.tr('Log out') + '</a>',
                    wrap_color=False
                )
            )
        self.label_user.linkActivated.connect(self._link_activated)

        self.started = False
        self._validate()

    def _create_map_uploader_task(self):
        """
        Creates a new map uploader task for the dialog's use
        """
        self.map_uploader_task = MapUploaderTask(
            layers=self.layers
        )
        self._update_warning_label()

    def _update_warning_label(self):
        """
        Updates the upload warning shown in the dialog
        """
        warning = self.map_uploader_task.warning_message()
        if warning:
            self.warning_label.setHtml(warning)
        else:
            self.warning_label.setPlainText('')
        self.warning_label.setStyleSheet(
            "color: black; background-color: #ececec;"
        )

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
        elif link == 'logout':
            AUTHORIZATION_MANAGER.deauthorize()
            self.close()
            return
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
        self.map_title_label.setText(
            self.tr('Uploading — {}').format(map_title))
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
        """
        Sets the current progress value for the operation
        """
        self.progress_bar.setValue(int(progress))

    def _upload_finished(self):
        """
        Called when the upload operation finishes
        """
        self.created_map = self.map_uploader_task.created_map
        self.map_title_label.setText(self.tr('Upload complete — {}').format(
            self.map_title_edit.text().strip())
        )
        self.progress_label.hide()
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
        """
        Called when the upload operation is terminated or canceled
        """
        self.progress_bar.hide()
        if self.map_uploader_task.was_canceled:
            self.map_title_label.setText(
                self.tr('Upload canceled — {}').format(
                    self.map_title_edit.text().strip())
            )
            self.button_box.button(QDialogButtonBox.Ok).setText(
                self.tr('Canceled')
            )
            self.progress_label.hide()
        else:
            self.progress_label.setStyleSheet('color: red')
            self.map_title_label.setStyleSheet('color: red')

            self.map_title_label.setText(
                self.tr('Upload failed — {}').format(
                    self.map_title_edit.text().strip())
            )
            self.progress_label.setText(
                GuiUtils.set_link_color(
                    self.tr('There was an error uploading this file, please '
                            'contact <a href="mailto:support@felt.com">'
                            'support@felt.com</a> '
                            'for help fixing the issue'), False,
                    QColor('red')
                )
            )

        self.map_uploader_task = None
        self.button_box.button(QDialogButtonBox.Cancel).setText(
            self.tr('Close')
        )

        self.button_box.button(QDialogButtonBox.Ok).setEnabled(
            False
        )
        self.button_box.button(QDialogButtonBox.Ok).hide()

    def _view_map(self):
        """
        Opens the uploaded map on Felt.com
        """
        if not self.created_map:
            return

        QDesktopServices.openUrl(QUrl(self.created_map.url))
