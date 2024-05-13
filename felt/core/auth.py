"""
Felt QGIS plugin
"""

import json
import urllib
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit

import requests
from qgis.PyQt.QtCore import (
    QThread,
    pyqtSignal,
    QUrl
)
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.core import (
    QgsBlockingNetworkRequest
)

from .pkce import generate_pkce_pair
from .constants import (
    FELT_API_BASE
)

OAUTH_BASE = f"{FELT_API_BASE}/oauth"
AUTH_HANDLER_REDIRECT = \
    OAUTH_BASE + "/success?client_id=8cb129bd-6962-4f65-8cc9-14b760e8436a"
AUTH_HANDLER_REDIRECT_CANCELLED = \
    OAUTH_BASE + "/denied?client_id=8cb129bd-6962-4f65-8cc9-14b760e8436a"

AUTH_HANDLER_RESPONSE = """\
<html>
  <head>
    <title>Authentication Status</title>
  </head>
  <body>
    <p>The authentication flow has completed.</p>
  </body>
</html>
"""

AUTH_HANDLER_RESPONSE_ERROR = """\
<html>
  <head>
    <title>Authentication Status</title>
  </head>
  <body>
    <p>The authentication flow encountered an error: {}.</p>
  </body>
</html>
"""

AUTH_URL = OAUTH_BASE + "/consent"
TOKEN_URL = OAUTH_BASE + "/token"

CLIENT_ID = "8cb129bd-6962-4f65-8cc9-14b760e8436a"

REDIRECT_PORT = 8989
REDIRECT_URL = f"http://127.0.0.1:{REDIRECT_PORT}/"
SCOPE = "map.write map.read profile.read layer.write"


class _Handler(BaseHTTPRequestHandler):
    """
    HTTP handle for OAuth workflows
    """

    # pylint: disable=missing-function-docstring

    def log_request(self, _format, *args):  # pylint: disable=arguments-differ
        pass

    def do_GET(self):
        params = parse_qs(urlsplit(self.path).query)
        code = params.get("code")

        if not code:
            self.server.error = 'Authorization canceled'
            self._send_response()
            return

        body = {
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "code_verifier": self.server.code_verifier,
            "code": code[0],
            "redirect_uri": REDIRECT_URL,
        }

        request = QgsBlockingNetworkRequest()
        token_body = urllib.parse.urlencode(body).encode()

        network_request = QNetworkRequest(QUrl(TOKEN_URL))
        network_request.setHeader(QNetworkRequest.ContentTypeHeader,
                                  'application/x-www-form-urlencoded')

        result_code = request.post(network_request,
                                   data=token_body,
                                   forceRefresh=True)
        if result_code != QgsBlockingNetworkRequest.NoError:
            self.server.error = request.reply().content().data().decode() \
                                or request.reply().errorString()
            self._send_response()
            return

        resp = json.loads(request.reply().content().data().decode())

        access_token = resp.get("access_token")
        expires_in = resp.get("expires_in")

        if not access_token or not expires_in:
            if not access_token:
                self.server.error = 'Could not find access_token in reply'
            elif not expires_in:
                self.server.error = 'Could not find expires_in in reply'

            self._send_response()
            return

        self.server.access_token = access_token
        self.server.expires_in = expires_in
        self._send_response()

    def _send_response(self):
        if AUTH_HANDLER_REDIRECT and self.server.error is None:
            self.send_response(302)
            self.send_header("Location", AUTH_HANDLER_REDIRECT)
            self.end_headers()
        elif AUTH_HANDLER_REDIRECT_CANCELLED and self.server.error:
            self.send_response(302)
            self.send_header("Location", AUTH_HANDLER_REDIRECT_CANCELLED)
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            if self.server.error is not None:
                self.wfile.write(
                    AUTH_HANDLER_RESPONSE_ERROR.format(
                        self.server.error).encode("utf-8"))
            else:
                self.wfile.write(AUTH_HANDLER_RESPONSE.encode("utf-8"))

    # pylint: enable=missing-function-docstring


class OAuthWorkflow(QThread):
    """
    A custom thread which handles the OAuth workflow.

    When the thread is run either the finished or error_occurred signals
    will be emitted
    """
    finished = pyqtSignal(str, int)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.server = None

        self.code_verifier, self.code_challenge = generate_pkce_pair()

        self.authorization_url = (
            f"{AUTH_URL}?"
            f"scope={SCOPE}&"
            f"response_type=code&"
            f"client_id={CLIENT_ID}&"
            f"code_challenge={self.code_challenge}&"
            f"code_challenge_method=S256&"
            f"redirect_uri={REDIRECT_URL}"
        )

    @staticmethod
    def force_stop():
        """
        Forces the local server to gracefully shutdown
        """
        # we have to dummy a dummy request in order to abort the
        # blocking handle_request() loop
        # pylint: disable=missing-timeout
        requests.get("http://127.0.0.1:{}".format(REDIRECT_PORT))
        # pylint: enable=missing-timeout

    def close_server(self):
        """
        Closes and cleans up the local server
        """
        self.server.server_close()

        del self.server
        self.server = None

    def run(self):
        """
        Starts the server thread
        """
        self.server = HTTPServer(("127.0.0.1", REDIRECT_PORT), _Handler)
        self.server.code_verifier = self.code_verifier
        self.server.access_token = None
        self.server.expires_in = None
        self.server.error = None
        QDesktopServices.openUrl(QUrl(self.authorization_url))

        self.server.handle_request()

        err = self.server.error
        access_token = self.server.access_token
        expires_in = self.server.expires_in

        if err:
            self.error_occurred.emit(err)
        else:
            self.finished.emit(access_token, expires_in)
