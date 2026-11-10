import pathlib

from json_config.api import LayeredConfig
from PySide6 import QtCore, QtGui, QtWidgets

from .document import LayerDocument
from .tree import nodes
from .tree.delegate import ValueDelegate
from .tree.filter import FilterProxy
from .tree.model import KEY_COLUMN, NODE_ROLE, TYPE_COLUMN, VALUE_COLUMN
from .tree.nodes import Kind, JsonNode

NO_PARENT = "(none — root layer)"


class NewLayerDialog(QtWidgets.QDialog):
    """Ask for the name, parent layer and file of a new layer."""

    def __init__(self, layers: list[str], current: str | None, parent=None):
        """Initialize the dialog.

        Args:
            layers (list[str]): Existing layer names offered as parent.
            current (str | None): Layer preselected as parent.
            parent (QtWidgets.QWidget | None, optional): Parent widget.
        """
        super().__init__(parent)
        self._layers = layers
        self._current = current
        self.setWindowTitle("New layer")
        self._create_widgets()
        self._create_layouts()
        self._create_connections()

    def _create_widgets(self) -> None:
        """Create and configure the widgets."""
        self.name_edit = QtWidgets.QLineEdit()
        self.parent_combo = QtWidgets.QComboBox()
        self.parent_combo.addItem(NO_PARENT)
        self.parent_combo.addItems(self._layers)
        if self._current:
            self.parent_combo.setCurrentText(self._current)
        self.path_edit = QtWidgets.QLineEdit()
        self.browse_button = QtWidgets.QPushButton("Browse…")
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )

    def _create_layouts(self) -> None:
        """Create the layouts and populate them with widgets."""
        path_layout = QtWidgets.QHBoxLayout()
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_button)

        form_layout = QtWidgets.QFormLayout()
        # macOS defaults to fields staying at their size hint.
        form_layout.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        form_layout.addRow("Name:", self.name_edit)
        form_layout.addRow("Depends on:", self.parent_combo)
        form_layout.addRow("File:", path_layout)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(form_layout)
        main_layout.addStretch()
        main_layout.addWidget(self.button_box)
        self.setMinimumWidth(480)
        self.resize(480, self.sizeHint().height())

    def _create_connections(self) -> None:
        """Connect signals to slots."""
        self.browse_button.clicked.connect(self._browse)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def _browse(self) -> None:
        """Pick the layer file; use its stem as the name if none was entered."""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Layer file", "", "JSON files (*.json);;All files (*)"
        )
        if path:
            self.path_edit.setText(path)
            if not self.name_edit.text():
                self.name_edit.setText(pathlib.Path(path).stem)

    def values(self) -> tuple[str, str | None, pathlib.Path | None]:
        """Return the entered values.

        Returns:
            tuple[str, str | None, pathlib.Path | None]: Layer name, parent layer
                name (None for a root layer) and file path (None if left empty).
        """
        parent = self.parent_combo.currentText()
        path = self.path_edit.text().strip()
        return (
            self.name_edit.text().strip(),
            None if parent == NO_PARENT else parent,
            pathlib.Path(path) if path else None,
        )


class ConfigEditorWidget(QtWidgets.QWidget):
    """Tree editor for the layers of a ``LayeredConfig``.

    The widget has no menus; hosts can place its public actions (``save_action``,
    ``save_all_action``, ``new_layer_action``, ``undo_action``, ``redo_action``,
    ``expand_all_action``, ``collapse_all_action``) wherever they like. Shortcuts
    only apply while the editor has focus.

    Attributes:
        saved (QtCore.Signal): Emitted with the layer name after a layer is saved.
    """

    saved = QtCore.Signal(str)

    def __init__(self, config: LayeredConfig, parent: QtWidgets.QWidget | None = None):
        """Initialize the editor.

        Args:
            config (LayeredConfig): The config whose layers are edited.
            parent (QtWidgets.QWidget | None, optional): Parent widget.
        """
        super().__init__(parent)
        self.document = LayerDocument(config, self)
        self.proxy = FilterProxy(self)
        self._create_actions()
        self._create_widgets()
        self._create_layouts()
        self._create_connections()
        self._refresh_combo()
        self._on_layer_changed(self.document.current_layer)

    def _create_actions(self) -> None:
        """Create and configure the actions."""
        Key = QtGui.QKeySequence.StandardKey
        self.new_layer_action = QtGui.QAction("New Layer…", self)
        self.save_action = QtGui.QAction("Save Layer", self)
        self.save_action.setShortcut(Key.Save)
        self.save_all_action = QtGui.QAction("Save All", self)
        self.undo_action = self.document.undo_group.createUndoAction(self, "Undo")
        self.undo_action.setShortcut(Key.Undo)
        self.redo_action = self.document.undo_group.createRedoAction(self, "Redo")
        self.redo_action.setShortcut(Key.Redo)
        self.expand_all_action = QtGui.QAction("Expand All", self)
        self.collapse_all_action = QtGui.QAction("Collapse All", self)

        # Keep shortcuts from leaking into a host application.
        context = QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut
        for action in (self.save_action, self.undo_action, self.redo_action):
            action.setShortcutContext(context)
            self.addAction(action)

    def _create_widgets(self) -> None:
        """Create and configure the widgets."""
        self.layer_label = QtWidgets.QLabel("Layer:")
        self.layer_combo = QtWidgets.QComboBox()
        self.new_layer_button = QtWidgets.QPushButton("New layer…")
        self.filter_edit = QtWidgets.QLineEdit()
        self.filter_edit.setPlaceholderText("Filter keys…")
        self.filter_edit.setClearButtonEnabled(True)

        self.view = QtWidgets.QTreeView()
        self.view.setModel(self.proxy)
        self.view.setItemDelegate(ValueDelegate(self.view))
        self.view.setAlternatingRowColors(True)
        self.view.setUniformRowHeights(True)
        self.view.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked
            | QtWidgets.QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self.view.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.header().setStretchLastSection(False)

    def _create_layouts(self) -> None:
        """Create the layouts and populate them with widgets."""
        layer_layout = QtWidgets.QHBoxLayout()
        layer_layout.addWidget(self.layer_label)
        layer_layout.addWidget(self.layer_combo, 1)
        layer_layout.addWidget(self.new_layer_button)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(4)
        main_layout.addLayout(layer_layout)
        main_layout.addWidget(self.filter_edit)
        main_layout.addWidget(self.view)

    def _create_connections(self) -> None:
        """Connect signals to slots."""
        self.layer_combo.activated.connect(self._on_combo_activated)
        self.new_layer_button.clicked.connect(self.new_layer_action.trigger)
        self.new_layer_action.triggered.connect(self.prompt_new_layer)
        self.save_action.triggered.connect(self.save_current)
        self.save_all_action.triggered.connect(self.save_all)
        self.expand_all_action.triggered.connect(self.view.expandAll)
        self.collapse_all_action.triggered.connect(self.view.collapseAll)
        self.document.saved.connect(self.saved)
        self.filter_edit.textChanged.connect(self._on_filter_changed)
        self.view.customContextMenuRequested.connect(self._show_context_menu)
        self.document.layersChanged.connect(self._refresh_combo)
        self.document.dirtyChanged.connect(self._refresh_combo)
        self.document.currentLayerChanged.connect(self._on_layer_changed)

    # -- layers -----------------------------------------------------------------
    def _refresh_combo(self) -> None:
        """Rebuild the layer combo box with each layer's source and dirty mark."""
        dirty = set(self.document.dirty_layers)
        current = self.document.current_layer
        self.layer_combo.blockSignals(True)
        self.layer_combo.clear()
        for name in self.document.layers:
            layer = self.document.layer(name)
            source = layer.file_path or "no file"
            mark = "*" if name in dirty else ""
            self.layer_combo.addItem(f"{name}{mark}  —  {source}", name)
            self.layer_combo.setItemData(
                self.layer_combo.count() - 1,
                f"{source}\ndepends on: {', '.join(layer.depends_on) or '—'}",
                QtCore.Qt.ItemDataRole.ToolTipRole,
            )
        if current:
            self.layer_combo.setCurrentIndex(self.document.layers.index(current))
        self.layer_combo.blockSignals(False)

    def _on_combo_activated(self, index: int) -> None:
        """Switch to the layer chosen in the combo box.

        Args:
            index (int): Index of the chosen combo item.
        """
        self.document.set_layer(self.layer_combo.itemData(index))

    def _on_layer_changed(self, name: str | None) -> None:
        """Show the model of the newly current layer.

        Args:
            name (str | None): Name of the current layer.
        """
        self.proxy.setSourceModel(self.document.model)
        self._configure_header()
        self._refresh_combo()
        self.view.expandToDepth(0)

    def _configure_header(self) -> None:
        # Needs a source model: section modes are ignored while there are no columns.
        """Set the header section sizes; Value stretches, others fit their content."""
        header = self.view.header()
        Resize = QtWidgets.QHeaderView.ResizeMode
        header.setSectionResizeMode(KEY_COLUMN, Resize.ResizeToContents)
        header.setSectionResizeMode(VALUE_COLUMN, Resize.Stretch)
        header.setSectionResizeMode(TYPE_COLUMN, Resize.ResizeToContents)

    def prompt_new_layer(self) -> None:
        """Ask for a new layer's details and register it on the config."""
        dialog = NewLayerDialog(self.document.layers, self.document.current_layer, self)
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        try:
            self.document.new_layer(*dialog.values())
        except ValueError as error:
            QtWidgets.QMessageBox.warning(self, "New layer", str(error))

    def _on_filter_changed(self, text: str) -> None:
        """Apply the filter text and expand all matches.

        Args:
            text (str): The filter text.
        """
        self.proxy.set_filter_text(text)
        if text:
            self.view.expandAll()

    # -- saving -----------------------------------------------------------------
    def save_current(self) -> bool:
        """Save the current layer, showing an error dialog on failure.

        Returns:
            bool: True if the layer was saved.
        """
        name = self.document.current_layer
        return name is not None and self._guarded(lambda: self.document.save_layer(name))

    def save_all(self) -> bool:
        """Save all layers with unsaved edits, showing an error dialog on failure.

        Returns:
            bool: True if everything was saved.
        """
        return self._guarded(self.document.save_all)

    def _guarded(self, action) -> bool:
        """Run a save action, showing an error dialog if it fails.

        Args:
            action (Callable[[], None]): The save action.

        Returns:
            bool: True if the action succeeded.
        """
        try:
            action()
        except (OSError, RuntimeError) as error:
            QtWidgets.QMessageBox.critical(self, "Save failed", str(error))
            return False
        return True

    def confirm_discard(self) -> bool:
        """Ask what to do with unsaved layers; return False if the user cancels."""
        if not self.document.is_dirty:
            return True
        Button = QtWidgets.QMessageBox.StandardButton
        names = ", ".join(self.document.dirty_layers)
        answer = QtWidgets.QMessageBox.question(
            self,
            "Unsaved changes",
            f"Save changes to: {names}?",
            Button.Save | Button.Discard | Button.Cancel,
        )
        if answer == Button.Save:
            return self.save_all()
        return answer == Button.Discard

    # -- context menu -----------------------------------------------------------
    def _show_context_menu(self, pos: QtCore.QPoint) -> None:
        """Show the add/remove/change-type menu for the row under the cursor.

        Args:
            pos (QtCore.QPoint): Cursor position in viewport coordinates.
        """
        model = self.document.model
        if model is None:
            return
        index = self.view.indexAt(pos)
        node: JsonNode | None = index.data(NODE_ROLE) if index.isValid() else None
        menu = QtWidgets.QMenu(self)

        if node is None:
            root = model.node_for(QtCore.QModelIndex())
            menu.addAction("Add key…", lambda: self.add_key(root))
        else:
            if node.kind == Kind.DICT:
                menu.addAction("Add key…", lambda: self.add_key(node))
            elif node.kind == Kind.LIST:
                menu.addAction("Append item…", lambda: self.append_item(node))
            if node.kind != Kind.BINARY:
                type_menu = menu.addMenu("Change type")
                for kind in nodes.SWITCHABLE_KINDS:
                    action = type_menu.addAction(
                        kind.value, lambda k=kind: self.change_type(node, k)
                    )
                    action.setCheckable(True)
                    action.setChecked(kind == node.kind)
            menu.addSeparator()
            menu.addAction("Remove", lambda: model.remove_node(node))
        menu.exec(self.view.viewport().mapToGlobal(pos))

    def _ask_kind(self) -> Kind | None:
        """Ask the user to choose a value type.

        Returns:
            Kind | None: The chosen type, or None if cancelled.
        """
        labels = [kind.value for kind in nodes.SWITCHABLE_KINDS]
        label, ok = QtWidgets.QInputDialog.getItem(
            self, "Value type", "Type:", labels, labels.index(Kind.STR.value), False
        )
        return Kind(label) if ok else None

    def add_key(self, parent: JsonNode) -> None:
        """Ask for a key name and type, then add it to a dict node.

        Args:
            parent (JsonNode): The dict node to add the key to.
        """
        existing = {child.key for child in parent.children}
        key, ok = QtWidgets.QInputDialog.getText(self, "Add key", "Key name:")
        if not ok or not key:
            return
        if key in existing:
            QtWidgets.QMessageBox.warning(
                self, "Add key", f"Key '{key}' already exists."
            )
            return
        kind = self._ask_kind()
        if kind is not None:
            self.document.model.add_child(parent, key, nodes.default_value(kind))
            self._expand(parent)

    def append_item(self, parent: JsonNode) -> None:
        """Ask for a type, then append a default item to a list node.

        Args:
            parent (JsonNode): The list node to append to.
        """
        kind = self._ask_kind()
        if kind is not None:
            self.document.model.add_child(
                parent, len(parent.children), nodes.default_value(kind)
            )
            self._expand(parent)

    def change_type(self, node: JsonNode, kind: Kind) -> None:
        """Replace a node's value with the default value of another type.

        Args:
            node (JsonNode): The node to convert.
            kind (Kind): The new type.
        """
        if kind != node.kind:
            self.document.model.set_value(node, nodes.default_value(kind))
            self._expand(node)

    def _expand(self, node: JsonNode) -> None:
        """Expand a node in the view, if it is visible through the filter.

        Args:
            node (JsonNode): The node to expand.
        """
        proxy_index = self.proxy.mapFromSource(self.document.model.index_for(node))
        if proxy_index.isValid() or node.parent is None:
            self.view.expand(proxy_index)
