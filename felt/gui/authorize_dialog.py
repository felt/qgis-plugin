"""
Felt Authorization dialog
"""

from typing import Optional

from qgis.PyQt import uic
from qgis.PyQt.QtCore import (
    QUrl
)
from qgis.PyQt.QtGui import (
    QDesktopServices,
    QFontMetrics
)
from qgis.PyQt.QtWidgets import (
    QWidget,
    QDialog,
    QVBoxLayout
)
from qgis.gui import QgsGui

from ..core import (
    PRIVACY_POLICY_URL,
    TOS_URL,
    SIGNUP_URL
)
from .felt_dialog_header import FeltDialogHeader
from .gui_utils import (
    GuiUtils,
    FELT_STYLESHEET
)

WIDGET, _ = uic.loadUiType(GuiUtils.get_ui_file_path('authorize.ui'))


class AuthorizeDialog(QDialog, WIDGET):
    """
    Custom dialog for authorizing the client.

    If the dialog is accepted then the authorization process should be
    started.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setupUi(self)

        self.setObjectName('AuthorizeDialog')
        QgsGui.enableAutoGeometryRestore(self)

        self.setStyleSheet(FELT_STYLESHEET)

        vl = QVBoxLayout()
        vl.setContentsMargins(0, 0, 0, 0)
        vl.addWidget(FeltDialogHeader())
        self.widget_logo.setStyleSheet('background: solid #3d521e;')
        self.widget_logo.setLayout(vl)

        self.setWindowTitle(self.tr('Authorize Felt'))

        self.sign_in_button.clicked.connect(self.accept)
        self.sign_up_button.clicked.connect(self._sign_up)

        self.footer_label.linkActivated.connect(self._link_activated)
        self.footer_label.setText(
            GuiUtils.set_link_color(self.footer_label.text())
        )

        self.footer_label.setMinimumWidth(
            QFontMetrics(self.footer_label.font()).width('x') * 40
        )

    def _sign_up(self):
        """
        Shows the signup form
        """
        QDesktopServices.openUrl(QUrl(SIGNUP_URL))

    def _link_activated(self, link: str):
        """
        Called when a hyperlink is clicked in dialog labels
        """
        if link == 'privacy_policy':
            url = QUrl(PRIVACY_POLICY_URL)
        elif link == 'terms_of_use':
            url = QUrl(TOS_URL)
        else:
            url = QUrl(link)

        QDesktopServices.openUrl(url)
