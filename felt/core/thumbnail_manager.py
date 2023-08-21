# -*- coding: utf-8 -*-
"""Async thumbnail download manager

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


from functools import partial
from typing import Dict, Optional

from qgis.PyQt.QtCore import (
    QUrl,
    QObject,
    pyqtSignal
)
from qgis.PyQt.QtGui import QImage
from qgis.PyQt.QtNetwork import (
    QNetworkReply,
    QNetworkRequest
)

from qgis.core import QgsNetworkAccessManager


class AsyncThumbnailManager(QObject):
    """
    A generic async thumbnail manager
    """

    downloaded = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.thumbnails: Dict[str, QImage] = {}
        self.queued_replies = set()

    def thumbnail(self, url: str) -> Optional[QImage]:
        return self.thumbnails.get(url)

    def download_thumbnail(self, url: str):
        if url in self.thumbnails:
            return self.thumbnails[url]
        else:
            reply = QgsNetworkAccessManager.instance().get(QNetworkRequest(QUrl(url)))
            self.queued_replies.add(reply)
            if reply.isFinished():
                self.thumbnail_downloaded(reply)
            else:
                reply.finished.connect(partial(self.thumbnail_downloaded, reply))

    def thumbnail_downloaded(self, reply):
        self.queued_replies.remove(reply)
        if reply.error() == QNetworkReply.NoError:
            url = reply.url().toString()
            img = QImage()
            img.loadFromData(reply.readAll())
            self.thumbnails[url] = img
            self.downloaded.emit(url)
