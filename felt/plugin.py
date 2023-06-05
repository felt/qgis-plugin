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
    QCoreApplication,
    QTimer
)
from qgis.gui import (
    QgisInterface
)

from .core import OAuthWorkflow


class FeltPlugin(QObject):
    """
    Felt QGIS plugin
    """

    def __init__(self, iface: QgisInterface):
        super().__init__()
        self.iface: QgisInterface = iface

        self.oauth: Optional[OAuthWorkflow] = None

    # qgis plugin interface
    # pylint: disable=missing-function-docstring

    def initGui(self):
        print('loaded')

        self.oauth = OAuthWorkflow()

        self.oauth.finished.connect(self._auth_finished)
        self.oauth.error_occurred.connect(self._auth_error_occurred)
        self.oauth.start()

    def unload(self):
        if self.oauth:
            self.oauth.force_stop()

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

    def _auth_finished(self, key):
        if self.oauth and not sip.isdeleted(self.oauth):
            self.oauth_close_timer = QTimer(self)
            self.oauth_close_timer.setSingleShot(True)
            self.oauth_close_timer.setInterval(1000)
            self.oauth_close_timer.timeout.connect(self._close_auth_server)
            self.oauth_close_timer.start()

        if not key:
            return

        print(key)

    def _auth_error_occurred(self, error: str):
        print(error)

    def _close_auth_server(self, force_close=False):
        if self.oauth_close_timer and not sip.isdeleted(
                self.oauth_close_timer):
            self.oauth_close_timer.timeout.disconnect(
                self._close_auth_server)
            self.oauth_close_timer.deleteLater()
        self.oauth_close_timer = None

        if self.oauth and not sip.isdeleted(self.oauth):
            if force_close:
                self.oauth.force_stop()

            self.oauth.close_server()
            self.oauth.quit()
            self.oauth.wait()
            self.oauth.deleteLater()

        self.oauth = None