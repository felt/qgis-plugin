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

from .gui import AUTHORIZATION_MANAGER


class FeltPlugin(QObject):
    """
    Felt QGIS plugin
    """

    def __init__(self, iface: QgisInterface):
        super().__init__()
        self.iface: QgisInterface = iface
        self.felt_web_menu: Optional[QMenu] = None

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

    #        AUTHORIZATION_MANAGER.start_authorization()

    def unload(self):
        if self.felt_web_menu and not sip.isdeleted(self.felt_web_menu):
            self.felt_web_menu.deleteLater()
        self.felt_web_menu = None

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
