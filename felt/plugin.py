"""
Felt QGIS plugin
"""

from functools import partial
from typing import (
    Optional,
    List
)

from qgis.PyQt import sip
from qgis.PyQt.QtCore import (
    QObject,
    QCoreApplication
)
from qgis.PyQt.QtWidgets import (
    QMenu,
    QAction
)

from qgis.core import (
    QgsLayerTreeLayer,
    QgsMapLayer,
    QgsProject
)
from qgis.gui import (
    QgisInterface
)

from .core import (
    AuthState,
    LayerExporter,
    LayerSupport
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
        self._create_map_dialog: Optional[CreateMapDialog] = None

    # qgis plugin interface
    # pylint: disable=missing-function-docstring

    def initGui(self):
        # little hack to ensure the web menu is visible before we try
        # to add a submenu to it -- the public API expects plugins to only
        # add individual actions to this menu, not submenus.
        temp_action = QAction()
        self.iface.addPluginToWebMenu('Felt', temp_action)

        web_menu = self.iface.webMenu()
        self.felt_web_menu = QMenu(self.tr('Felt'))
        self.felt_web_menu.setIcon(
            GuiUtils.get_icon('icon.svg')
        )
        web_menu.addMenu(self.felt_web_menu)

        self.iface.removePluginWebMenu('Felt', temp_action)

        self.felt_web_menu.addAction(AUTHORIZATION_MANAGER.login_action)

        self.create_map_action = QAction(self.tr('Add to Felt…'))
        self.create_map_action.setIcon(
            GuiUtils.get_icon('create_map.svg')
        )
        self.felt_web_menu.addAction(self.create_map_action)
        self.create_map_action.triggered.connect(self.create_map)

        self.share_map_to_felt_action = QAction(self.tr('Add to Felt…'))
        self.share_map_to_felt_action.setIcon(
            GuiUtils.get_icon('export_to_felt.svg')
        )
        self.share_map_to_felt_action.triggered.connect(self.create_map)
        self.iface.addWebToolBarIcon(self.share_map_to_felt_action)

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

        try:
            self.iface.layerTreeView().contextMenuAboutToShow.connect(
                self._layer_tree_view_context_menu_about_to_show
            )
        except AttributeError:
            pass

        AUTHORIZATION_MANAGER.status_changed.connect(self._auth_state_changed)

        QgsProject.instance().layersRemoved.connect(
            self._update_action_enabled_states)
        QgsProject.instance().layersAdded.connect(
            self._update_action_enabled_states)
        self._update_action_enabled_states()

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

    # pylint:disable=unused-argument
    def _auth_state_changed(self, state: AuthState):
        """
        Called when the plugin authorization state changes
        """
        self._update_action_enabled_states()
    # pylint:enable=unused-argument

    def _share_layer_to_felt(self, layer: QgsMapLayer):
        """
        Triggers creation of a map with a single layer only
        """
        AUTHORIZATION_MANAGER.authorization_callback(
            partial(self._create_map_authorized, [layer])
        )

    def create_map(self):
        """
        Triggers the map creation process
        """
        AUTHORIZATION_MANAGER.authorization_callback(
            self._create_map_authorized
        )

    def _create_map_authorized(self,
                               layers: Optional[List[QgsMapLayer]] = None):
        """
        Shows the map creation dialog, after authorization completes
        """
        if self._create_map_dialog and \
                not sip.isdeleted(self._create_map_dialog):
            self._create_map_dialog.show()
            self._create_map_dialog.raise_()
            return

        def _cleanup_dialog(_dialog):
            """
            Remove references to outdated dialogs
            """
            self._create_map_dialogs = [d for d in self._create_map_dialogs
                                        if d != _dialog]
            self._create_map_dialog = None

        self._create_map_dialog = CreateMapDialog(
            self.iface.mainWindow(),
            layers
        )
        self._create_map_dialog.show()
        self._create_map_dialog.rejected.connect(
            partial(_cleanup_dialog, self._create_map_dialog)
        )
        self._create_map_dialogs.append(self._create_map_dialog)

    def _layer_tree_view_context_menu_about_to_show(self, menu: QMenu):
        """
        Triggered when the layer tree menu is about to show
        """
        if not menu:
            return

        current_node = self.iface.layerTreeView().currentNode()
        if not isinstance(current_node, QgsLayerTreeLayer):
            return

        layer = current_node.layer()
        if layer is None:
            return

        if (LayerExporter.can_export_layer(layer)[0] ==
                LayerSupport.Supported):
            menus = [action for action in menu.children() if
                     isinstance(action, QMenu) and
                     action.objectName() == 'exportMenu']
            if not menus:
                return

            export_menu = menus[0]

            share_to_felt_action = QAction(
                self.tr('Share Layer to Felt…'),
                menu
            )
            share_to_felt_action.setIcon(
                GuiUtils.get_icon('export_to_felt.svg')
            )
            export_menu.addAction(share_to_felt_action)
            share_to_felt_action.triggered.connect(
                partial(self._share_layer_to_felt, layer)
            )

    def _update_action_enabled_states(self):
        """
        Updates the enabled state of export actions
        """
        is_authorizing = AUTHORIZATION_MANAGER.status == AuthState.Authorizing
        allowed_to_export = not is_authorizing
        if self.share_map_to_felt_action:
            self.share_map_to_felt_action.setEnabled(allowed_to_export)
        if self.create_map_action:
            self.create_map_action.setEnabled(allowed_to_export)
