"""
Logger class
"""

import json

import os
import pathlib
from inspect import (
    currentframe,
    getframeinfo
)
from typing import (
    Optional,
    Dict
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

    PACKAGING_RASTER = 'packaging_raster'
    PACKAGING_VECTOR = 'packaging_vector'
    FSL_CONVERSION = 'unsupported_style'
    MAP_EXPORT = 'map_export'
    S3_UPLOAD = 's3_upload'
    UNSUPPORTED_LAYER = "unsupported_layer"

    def __init__(self):  # pylint: disable=useless-parent-delegation
        super().__init__()

    @classmethod
    def instance(cls) -> 'Logger':
        """
        Returns the singleton instance of the logger
        """
        return cls._instance

    @classmethod
    def set_instance(cls, logger: 'Logger'):
        """
        Sets the singleton instance of the logger
        """
        cls._instance = logger

    def log_message(self, message: str):
        """
        Logs a messages
        """

    def log_message_json(self, message: Dict):
        """
        Logs a message using a JSON dictionary value
        """

    def log_error(self, error: str):
        """
        Logs an error
        """

    def log_error_json(self, error: Dict):
        """
        Logs an error using a JSON dictionary value
        """

    @staticmethod
    def anonymize_filename(filename: str) -> str:
        """
        Removes user-sensitive details from a filename, by making
        it a relative filename to the plugin install directory
        """
        plugin_install_path = (
            pathlib.Path(__file__).parent.parent.resolve())
        return os.path.relpath(pathlib.Path(filename).resolve(),
                               start=plugin_install_path)


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

    def log_message_json(self, message: Dict):
        message_str = json.dumps(message)
        QMetaObject.invokeMethod(
            self,
            "_submit_usage",
            Qt.QueuedConnection,
            Q_ARG(str, message_str),
            Q_ARG(str, UsageType.Info.to_string()))

    def log_error(self, error: str):
        frame = currentframe().f_back
        filename = self.anonymize_filename(getframeinfo(frame).filename)
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

    def log_error_json(self, error: Dict):
        frame = currentframe().f_back
        filename = self.anonymize_filename(getframeinfo(frame).filename)

        error['source_file'] = filename
        error['source_line'] = frame.f_lineno
        error['source_function'] = getframeinfo(frame).function

        QMetaObject.invokeMethod(
            self,
            "_submit_usage",
            Qt.QueuedConnection,
            Q_ARG(str, json.dumps(error)),
            Q_ARG(str, UsageType.Error.to_string()))


Logger.set_instance(LogToFeltLogger())
