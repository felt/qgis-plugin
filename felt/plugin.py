# -*- coding: utf-8 -*-
"""Felt QGIS plugin

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

from functools import partial
from typing import Optional

from qgis.PyQt import sip
from qgis.PyQt.QtCore import (
    QObject,
    QCoreApplication
)
from qgis.PyQt.QtWidgets import (
    QMenu,
    QAction
)
from qgis.gui import (
    QgisInterface
)

from .gui import (
    AUTHORIZATION_MANAGER,
    CreateMapDialog,
    GuiUtils
)


class FeltPlugin(QObject):
    """
    Felt QGIS plugin
    """

    def __init__(self, iface: QgisInterface):
        super().__init__()
        self.iface: QgisInterface = iface
        self.felt_web_menu: Optional[QMenu] = None

        self.create_map_action: Optional[QAction] = None
        self.share_map_to_felt_action: Optional[QAction] = None
        self._create_map_dialogs = []

    # qgis plugin interface
    # pylint: disable=missing-function-docstring

    def initGui(self):
        # little hack to ensure the web menu is visible before we try
        # to add a submenu to it -- the public API expects plugins to only
        # add individual actions to this menu, not submenus.
        temp_action = QAction()
        self.iface.addPluginToWebMenu('Felt', temp_action)

        web_menu = self.iface.webMenu()
        self.felt_web_menu = QMenu(self.tr('Add to Felt'))
        web_menu.addMenu(self.felt_web_menu)

        self.iface.removePluginWebMenu('Felt', temp_action)

        self.felt_web_menu.addAction(AUTHORIZATION_MANAGER.login_action)

        self.create_map_action = QAction(self.tr('Create Map…'))
        self.felt_web_menu.addAction(self.create_map_action)
        self.create_map_action.triggered.connect(self.create_map)

        self.share_map_to_felt_action = QAction(self.tr('Share Map to Felt…'))
        self.share_map_to_felt_action.triggered.connect(self.create_map)

        try:
            self.iface.addProjectExportAction(self.share_map_to_felt_action)
        except AttributeError:
            # addProjectExportAction was added in QGIS 3.30
            import_export_menu = GuiUtils.get_project_import_export_menu()
            if import_export_menu:
                # find nice insertion point
                export_separator = [a for a in import_export_menu.actions() if
                                    a.isSeparator()]
                if export_separator:
                    import_export_menu.insertAction(
                        export_separator[0],
                        self.share_map_to_felt_action
                    )
                else:
                    import_export_menu.addAction(
                        self.share_map_to_felt_action
                    )

    def unload(self):
        if self.felt_web_menu and not sip.isdeleted(self.felt_web_menu):
            self.felt_web_menu.deleteLater()
        self.felt_web_menu = None

        if self.create_map_action and \
                not sip.isdeleted(self.create_map_action):
            self.create_map_action.deleteLater()
        self.create_map_action = None

        if self.share_map_to_felt_action and \
                not sip.isdeleted(self.share_map_to_felt_action):
            self.share_map_to_felt_action.deleteLater()
        self.share_map_to_felt_action = None

        for dialog in self._create_map_dialogs:
            if not sip.isdeleted(dialog):
                dialog.deleteLater()
        self._create_map_dialogs = []

        AUTHORIZATION_MANAGER.cleanup()

    # pylint: enable=missing-function-docstring

    @staticmethod
    def tr(message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('Felt', message)

    def create_map(self):
        """
        Triggers the map creation process
        """
        AUTHORIZATION_MANAGER.authorization_callback(
            self._create_map_authorized
        )

    def _create_map_authorized(self):
        """
        Shows the map creation dialog, after authorization completes
        """
        def _cleanup_dialog(_dialog):
            """
            Remove references to outdated dialogs
            """
            self._create_map_dialogs = [d for d in self._create_map_dialogs
                if d != _dialog]

        dialog = CreateMapDialog(self.iface.mainWindow())
        dialog.show()
        dialog.rejected.connect(partial(_cleanup_dialog, dialog))
        self._create_map_dialogs.append(dialog)
