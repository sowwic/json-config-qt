import typing

from json_config.api import LayeredConfig
from PySide6 import QtCore, QtWidgets

from .editor_widget import ConfigEditorWidget


class ConfigEditorDialog(QtWidgets.QDialog):
    """Floating, non-modal dialog editing the layers of a ``LayeredConfig``.

    Intended to be spawned by a host application, which owns it through *parent*.

    Attributes:
        saved (QtCore.Signal): Emitted with the layer name after a layer is saved.
    """

    saved = QtCore.Signal(str)
    _instances: typing.ClassVar[dict[int, ConfigEditorDialog]] = {}

    def __init__(
        self,
        config: LayeredConfig,
        parent: QtWidgets.QWidget | None = None,
        delete_on_close: bool = False,
    ):
        """Initialize the dialog.

        Args:
            config (LayeredConfig): The config whose layers are edited.
            parent (QtWidgets.QWidget | None, optional): Parent widget.
            delete_on_close (bool, optional): Delete the dialog once it is closed.
        """
        super().__init__(parent)
        self.setModal(False)
        self.setWindowFlag(QtCore.Qt.WindowType.WindowMinimizeButtonHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, delete_on_close)
        self.resize(900, 700)
        self.editor = ConfigEditorWidget(config, self)
        self.document = self.editor.document
        self._create_widgets()
        self._create_layouts()
        self._create_connections()
        self._update_title()

    @classmethod
    def show_for(
        cls, config: LayeredConfig, parent: QtWidgets.QWidget | None = None
    ) -> ConfigEditorDialog:
        """Show the editor for *config*, reusing the open one if there is one.

        Args:
            config (LayeredConfig): The config whose layers are edited.
            parent (QtWidgets.QWidget | None, optional): Parent widget for a new dialog.

        Returns:
            ConfigEditorDialog: The shown dialog, deleted when closed.
        """
        key = id(config)
        dialog = cls._instances.get(key)
        if dialog is None:
            dialog = cls(config, parent, delete_on_close=True)
            cls._instances[key] = dialog
            dialog.destroyed.connect(lambda *_: cls._instances.pop(key, None))
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        return dialog

    def _create_widgets(self) -> None:
        """Create and configure the widgets."""
        self.action_buttons = []
        for action in (
            self.editor.save_action,
            self.editor.save_all_action,
            self.editor.undo_action,
            self.editor.redo_action,
        ):
            button = QtWidgets.QToolButton()
            button.setDefaultAction(action)
            button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly)
            self.action_buttons.append(button)
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close
        )

    def _create_layouts(self) -> None:
        """Create the layouts and populate them with widgets."""
        button_layout = QtWidgets.QHBoxLayout()
        for button in self.action_buttons:
            button_layout.addWidget(button)
        button_layout.addStretch()
        button_layout.addWidget(self.button_box)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self.editor)
        main_layout.addLayout(button_layout)

    def _create_connections(self) -> None:
        """Connect signals to slots."""
        self.button_box.rejected.connect(self.reject)
        self.editor.saved.connect(self.saved)
        self.document.dirtyChanged.connect(self._update_title)
        self.document.currentLayerChanged.connect(self._update_title)

    def _update_title(self) -> None:
        """Show the current layer and dirty mark in the window title."""
        layer = self.document.current_layer or "no layer"
        mark = "*" if self.document.is_dirty else ""
        self.setWindowTitle(f"{layer}{mark} — Config editor")

    def reject(self) -> None:
        """Close the dialog unless the user cancels the unsaved-changes prompt."""
        if self.editor.confirm_discard():
            super().reject()
