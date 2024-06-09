"""
Felt Create Map dialog
"""

from typing import (
    Optional,
    List
)

from qgis.PyQt import uic
from qgis.PyQt.QtCore import (
    Qt,
    QUrl,
    QSize
)
from qgis.PyQt.QtGui import (
    QDesktopServices,
    QFontMetrics,
    QColor,
    QPalette
)
from qgis.PyQt.QtWidgets import (
    QWidget,
    QDialog,
    QDialogButtonBox,
    QVBoxLayout,
    QLabel,
    QMenu,
    QAction,
    QToolButton
)
from qgis.core import (
    QgsMapLayer,
    QgsApplication,
    QgsProject,
    QgsSettings
)
from qgis.gui import QgsGui

from .authorization_manager import AUTHORIZATION_MANAGER
from .colored_progress_bar import ColorBar

from .felt_dialog_header import FeltDialogHeader
from .gui_utils import (
    GuiUtils,
    FELT_STYLESHEET
)
from .workspaces_combo import WorkspacesComboBox
from ..core import (
    LayerExporter,
    LayerSupport,
    MapUploaderTask,
    Map,
    PRIVACY_POLICY_URL,
    TOS_URL
)

WIDGET, _ = uic.loadUiType(GuiUtils.get_ui_file_path('create_map.ui'))


class CreateMapDialog(QDialog, WIDGET):
    """
    Custom dialog for creating maps

    If the dialog is accepted then the authorization process should be
    started.
    """

    def __init__(self,  # pylint: disable=too-many-statements
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
        header = FeltDialogHeader()
        vl.addWidget(header)
        self.widget_logo.setLayout(vl)

        self.header_label = QLabel(
            """<style> a { text-decoration: none; }</style>"""
            """<a href="privacy_policy">Privacy</a>&nbsp;&nbsp;&nbsp;"""
            """<a href="terms_of_use">Terms</a>&nbsp;&nbsp;&nbsp;"""
            """<a href="mailto:support@felt.com">Contact us</a></p>"""
        )
        self.header_label.setMouseTracking(True)
        self.header_label.linkActivated.connect(self._link_activated)
        self.header_label.setText(
            GuiUtils.set_link_color(self.header_label.text(),
                                    color='rgba(255,255,255,.7)')
        )

        header_label_vl = QVBoxLayout()
        header_label_vl.setContentsMargins(0, 0, 0, 0)
        header_label_vl.addStretch()
        header_label_vl.addWidget(self.header_label)

        header_label_widget = QWidget()
        header_label_widget.setLayout(header_label_vl)

        header.push_widget(header_label_widget)

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

        self.setting_menu = QMenu(self)
        palette = self.setting_menu.palette()
        palette.setColor(QPalette.Active, QPalette.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.Active, QPalette.Text, QColor(0, 0, 0))
        palette.setColor(QPalette.Active, QPalette.Highlight,
                         QColor('#3d521e'))
        palette.setColor(QPalette.Active, QPalette.HighlightedText,
                         QColor(255, 255, 255))
        self.setting_menu.setPalette(palette)

        self.upload_raster_as_styled_action = QAction(
            self.tr('Upload Raster Layers as Styled Images'),
            self.setting_menu)
        self.upload_raster_as_styled_action.setCheckable(True)
        self.upload_raster_as_styled_action.setChecked(
            QgsSettings().value(
                "felt/upload_raster_as_styled", True, bool, QgsSettings.Plugins
            )
        )

        def upload_raster_as_styled_toggled():
            """
            Called when upload raster as style action is toggled
            """
            QgsSettings().setValue(
                "felt/upload_raster_as_styled",
                self.upload_raster_as_styled_action.isChecked(),
                QgsSettings.Plugins
            )

        self.upload_raster_as_styled_action.toggled.connect(
            upload_raster_as_styled_toggled)
        # Hidden, now we default to uploading styled whenever we can't
        # convert the layer to FSL
        # self.setting_menu.addAction(self.upload_raster_as_styled_action)

        self.setting_menu.addSeparator()
        self.logout_action = QAction(self.tr('Log Out'), self.setting_menu)
        self.setting_menu.addAction(self.logout_action)
        self.logout_action.triggered.connect(self._logout)

        palette = self.setting_button.palette()
        palette.setColor(QPalette.Active, QPalette.Button, QColor('#ececec'))
        self.setting_button.setPalette(palette)

        self.setting_button.setMenu(self.setting_menu)
        self.setting_button.setIcon(GuiUtils.get_icon('setting_icon.svg'))
        self.setting_button.setPopupMode(QToolButton.InstantPopup)
        self.setting_button.setStyleSheet(
            """QToolButton::menu-indicator { image: none }
            QToolButton {
            background: #f9f9f9;
            border: 1px solid #bdbdbd;
            border-radius: 2px; }
            """
        )
        self.setting_button.setFixedHeight(
            self.button_box.button(QDialogButtonBox.Cancel).height()
        )
        self.setting_button.setFixedWidth(
            int(self.setting_button.size().height() * 1.8)
        )
        self.setting_button.setIconSize(
            QSize(int(self.setting_button.size().width() * 0.6),
                  int(self.setting_button.size().height() * 0.6)
                  ))
        # setting the setting button to a fixed height doesn't always
        # guarantee that the height exactly matches the Close/Add buttons.
        # So let's play it safe and force them to match always:
        for b in (QDialogButtonBox.Cancel, QDialogButtonBox.Ok):
            self.button_box.button(b).setFixedHeight(
                self.setting_button.size().height()
            )

        # pylint: disable=import-outside-toplevel
        from .recent_maps_list_view import RecentMapsWidget
        # pylint: enable=import-outside-toplevel
        self.maps_widget = RecentMapsWidget()
        self.workspace_combo = WorkspacesComboBox()
        self.workspace_combo.no_workspaces_found.connect(self._no_workspace)
        self.workspace_combo.workspaces_loaded.connect(self._workspaces_loaded)
        self.workspace_combo.workspace_changed.connect(self._workspace_changed)
        self.workspace_combo.setFixedHeight(
            int(QFontMetrics(self.workspace_combo.font()).height() * 1.5)
        )
        self.workspace_combo.setStyleSheet(
            """
            QComboBox{
                background: white;
                color: black;
                selection-background-color: #fed9e3 !important;
                selection-color: black !important;
                border: 1px solid #bdbdbd;
                border-top-right-radius: 2px;
                border-top-left-radius: 2px;
                border-bottom-right-radius: 2px;
                border-bottom-left-radius: 2px;
            }
            QComboBox:hover {
                background: white;
                color: black;
                selection-background-color: #fed9e3 !important;
                selection-color: black !important;
            }
            QComboBox:on {
                background: white;
                color: black;
                selection-background-color: #fed9e3 !important;
                selection-color: black !important;
            }
            QComboBox QAbstractItemView, QComboBox QListView {
                background: white;
                color: black;
                selection-background-color: #fed9e3 !important;
                selection-color: black !important;
            }
            QComboBox::drop-down:editable:hover {
               background-color: @darkalternativegradient;
            }
            """
        )

        maps_layout = QVBoxLayout()
        maps_layout.setContentsMargins(0, 0, 0, 0)
        maps_layout.addWidget(self.workspace_combo)
        maps_layout.addWidget(self.maps_widget)
        self.maps_frame.setLayout(maps_layout)

        self.map_uploader_task: Optional[MapUploaderTask]
        self._map_title: Optional[str] = None
        if self.layers is None:
            QgsProject.instance().layersRemoved.connect(
                self._create_map_uploader_task)
            QgsProject.instance().layersAdded.connect(
                self._create_map_uploader_task)
        self._create_map_uploader_task()

        self.created_map: Optional[Map] = None
        self.maps_widget.set_new_map_title(
            self.map_uploader_task.default_map_title())

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
            self.footer_label.setText(
                AUTHORIZATION_MANAGER.user.email
            )

        self.started = False
        self._validate_initial()
        self.maps_widget.filter_line_edit().setFocus()

    def _fatal_error(self, error: str):
        """
        Called when a fatal error which prevents sharing occurs
        """
        self.stacked_widget.setCurrentIndex(2)
        self.error_label.setText(error)
        self.button_box.button(QDialogButtonBox.Ok).deleteLater()

    def _no_workspace(self):
        """
        Called when no workspaces are available
        """
        self._fatal_error(
            self.tr("You don’t have edit access for any workspaces. "
                    "Ask your workspace admin for edit access, "
                    "or create your own workspace."
                    )
        )

    def _workspaces_loaded(self):
        """
        Called when available workspaces have been loaded
        """
        last_workspace = QgsSettings().value(
            "felt/last_workspace", '', str, QgsSettings.Plugins
        )
        if not last_workspace:
            return

        self.workspace_combo.set_workspace(last_workspace)

    def _validate_initial(self):
        """
        Performs an initial one-time validated of the environment
        """
        error: Optional[str] = None

        export_layers = self.layers if self.layers else \
            QgsProject.instance().mapLayers().values()
        for layer in export_layers:
            support, reason = LayerExporter.can_export_layer(layer)
            if support == LayerSupport.UnsavedEdits:
                error = self.tr(
                        'Layer "{}" has unsaved changes. Please save '
                        'the layer before sharing to Felt.').format(
                        layer.name())
                break

        if error:
            self._fatal_error(error)
        else:
            self._validate()

    def _workspace_changed(self, workspace_id: str):
        """
        Called when the selected workspace is changed
        """
        self.maps_widget.set_workspace_id(workspace_id)
        self.map_uploader_task.set_workspace_id(workspace_id)

    def _create_map_uploader_task(self):
        """
        Creates a new map uploader task for the dialog's use
        """
        self.map_uploader_task = MapUploaderTask(
            layers=self.layers,
            workspace_id=self.workspace_combo.current_workspace_id()
        )
        self._update_warning_label()

    def _update_warning_label(self):
        """
        Updates the upload warning shown in the dialog
        """
        warning = self.map_uploader_task.warning_message()
        if warning:
            self.warning_label.setHtml(warning)
            self.warning_label.document().adjustSize()
            self.warning_label.setFixedHeight(
                int(self.warning_label.document().size().height())
            )
        else:
            self.warning_label.setPlainText('')
            self.warning_label.setFixedHeight(0)

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

    def _logout(self):
        """
        Triggers a logout
        """
        AUTHORIZATION_MANAGER.deauthorize()
        self.close()

    def _link_activated(self, link: str):
        """
        Called when a hyperlink is clicked in dialog labels
        """
        if link == 'privacy_policy':
            url = QUrl(PRIVACY_POLICY_URL)
        elif link == 'terms_of_use':
            url = QUrl(TOS_URL)
        elif link == 'logout':
            self._logout()
            return
        else:
            url = QUrl(link)

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
        return True

    def _start(self):
        """
        Starts the map upload process
        """
        QgsSettings().setValue(
            "felt/last_workspace",
            self.map_uploader_task.workspace_id(),
            QgsSettings.Plugins
        )

        self.started = True
        self.button_box.button(QDialogButtonBox.Cancel).setText(
            self.tr('Cancel')
        )
        self.button_box.button(QDialogButtonBox.Ok).setText(
            self.tr('Uploading')
        )
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)

        target_map = self.maps_widget.selected_map()
        self.map_uploader_task.associated_map = target_map

        self._map_title = target_map.title if target_map else \
            self.map_uploader_task.default_map_title()

        self.map_title_label.setText(
            self.tr('Uploading — {}').format(self._map_title))
        self.map_uploader_task.project_title = self._map_title

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
        self.created_map = self.map_uploader_task.associated_map
        self.map_title_label.setText(self.tr('Upload complete — {}').format(
            self._map_title)
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
                    self._map_title)
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
                    self._map_title)
            )

            error_message = \
                self.tr('There was an error uploading this file, please '
                        'contact <a href="mailto:support@felt.com">'
                        'support@felt.com</a> '
                        'for help fixing the issue')

            if self.map_uploader_task.error_string:
                error_message += '<p><b>{}</b></p>'.format(
                    self.map_uploader_task.error_string
                )

            self.progress_label.setText(
                GuiUtils.set_link_color(
                    error_message, False,
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
