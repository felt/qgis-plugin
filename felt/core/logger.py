"""
Logger class

.. note:: This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

__author__ = '(C) 2023 by Nyall Dawson'
__date__ = '14/08/2023'
__copyright__ = 'Copyright 2022, North Road'
# This will get replaced with a git SHA1 when you do a git archive
__revision__ = '$Format:%H$'

import os
import pathlib
from typing import Optional
from inspect import (
    currentframe,
    getframeinfo
)

from qgis.PyQt.QtCore import (
    QObject,
    pyqtSlot,
    QMetaObject,
    Qt,
    Q_ARG
)

from .api_client import API_CLIENT
from .enums import UsageType


class Logger(QObject):
    """
    Base class for loggers.

    This base class does no logging.
    """

    _instance: Optional['Logger'] = None

    def __init__(self):
        super().__init__()

    @classmethod
    def instance(cls):
        return cls._instance

    @classmethod
    def set_instance(cls, logger: 'Logger'):
        cls._instance = logger

    def log_message(self, message: str):
        """
        Logs a messages
        """

    def log_error(self, error: str):
        """
        Logs an error
        """


class LogToFeltLogger(Logger):
    """
    Handles logging to Felt via the report usage API.

    (Can only be used when authenticated).

    This class is a little tricky!
    We'll be receiving calls to log_message and log_error from background
    threads. If we try and submit these requests from the background thread
    immediately, then we run the risk that the thread will finish and exit
    before the request is complete.
    Accordingly, we always need to bounce messages from the current thread
    up to the main thread (where an instance of LogToFeltLogger will always
    live), and only then do the actual network request.
    We handle this via Qt's invokeMethod function, where the invoked slot
    will always be run in the thread that the object has affinity with (i.e
    the main thread).
    """

    @pyqtSlot(str, str)
    def _submit_usage(self, message: str, usage_type: str):
        """
        Submission MUST occur on the main thread!
        """
        if not API_CLIENT.token:
            return  # can't log!

        API_CLIENT.report_usage(
            message,
            UsageType.from_string(usage_type)
        )

    def log_message(self, message: str):
        QMetaObject.invokeMethod(
            self,
            "_submit_usage",
            Qt.QueuedConnection,
            Q_ARG(str, message),
            Q_ARG(str, UsageType.Info.to_string()))

    def log_error(self, error: str):
        frame = currentframe().f_back

        # need to anonymize filename!
        filename = getframeinfo(frame).filename
        plugin_install_path = (
            pathlib.Path(__file__).parent.parent.resolve())
        filename = os.path.relpath(pathlib.Path(filename).resolve(),
                                   start=plugin_install_path)

        message = '{}:{} ({}): {}\n'.format(filename,
                                            frame.f_lineno,
                                            getframeinfo(frame).function,
                                            error)

        QMetaObject.invokeMethod(
            self,
            "_submit_usage",
            Qt.QueuedConnection,
            Q_ARG(str, message),
            Q_ARG(str, UsageType.Error.to_string()))


Logger.set_instance(LogToFeltLogger())
