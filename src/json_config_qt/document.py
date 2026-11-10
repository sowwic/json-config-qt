import pathlib

from json_config.api import ConfigLayer, LayeredConfig
from PySide6 import QtCore, QtGui

from .tree.model import JsonTreeModel


class LayerDocument(QtCore.QObject):
    """Edit state for every layer of a ``LayeredConfig``.

    Each layer gets its own tree model and undo stack, created on first access, so
    history survives switching layers. Edits only touch a layer's own raw data.
    """

    layersChanged = QtCore.Signal()
    currentLayerChanged = QtCore.Signal(str)
    dirtyChanged = QtCore.Signal()
    saved = QtCore.Signal(str)

    def __init__(self, config: LayeredConfig, parent: QtCore.QObject | None = None):
        """Initialize the document.

        Args:
            config (LayeredConfig): The config whose layers are edited.
            parent (QtCore.QObject | None, optional): Parent object.
        """
        super().__init__(parent)
        self.config = config
        self.undo_group = QtGui.QUndoGroup(self)
        self._models: dict[str, JsonTreeModel] = {}
        self._current: str | None = None
        if config.layers:
            self.set_layer(config.layers[0])

    # -- layers -------------------------------------------------------------
    @property
    def layers(self) -> list[str]:
        """Return the layer names in topological order."""
        return self.config.layers

    @property
    def current_layer(self) -> str | None:
        """Return the name of the layer being edited, or None if there are no layers."""
        return self._current

    def layer(self, name: str) -> ConfigLayer:
        """Return the config layer registered as *name*."""
        return self.config.layer_manager[name]

    def model_for(self, name: str) -> JsonTreeModel:
        """Return the tree model of a layer, creating it on first access.

        Args:
            name (str): The layer name.

        Returns:
            JsonTreeModel: The layer's model, holding its own undo stack.
        """
        if name not in self._models:
            stack = QtGui.QUndoStack(self)
            model = JsonTreeModel(stack, self)
            model.load(self.layer(name).get_data())
            stack.cleanChanged.connect(self.dirtyChanged)
            self.undo_group.addStack(stack)
            self._models[name] = model
        return self._models[name]

    @property
    def model(self) -> JsonTreeModel | None:
        """Return the tree model of the current layer, or None if there are no layers."""
        return self.model_for(self._current) if self._current else None

    def set_layer(self, name: str) -> None:
        """Make *name* the current layer.

        Raises:
            ValueError: If *name* is not a registered layer.
        """
        if name not in self.layers:
            raise ValueError(f"Unknown layer '{name}'")
        if name == self._current:
            return
        self._current = name
        self.undo_group.setActiveStack(self.model_for(name).undo_stack)
        self.currentLayerChanged.emit(name)

    def new_layer(
        self,
        name: str,
        depends_on: str | None = None,
        file_path: pathlib.Path | None = None,
    ) -> None:
        """Register a new, empty layer and make it current.

        Raises:
            ValueError: if a layer called *name* already exists or *depends_on* is
                not a registered layer.
        """
        if not name:
            raise ValueError("Layer name must not be empty.")
        if depends_on is not None and depends_on not in self.layers:
            raise ValueError(f"Unknown layer '{depends_on}'")
        self.config.layer_manager.register(
            ConfigLayer(
                name=name,
                depends_on=[depends_on] if depends_on else [],
                file_path=pathlib.Path(file_path) if file_path else None,
            )
        )
        self.layersChanged.emit()
        self.set_layer(name)

    # -- dirty / save ---------------------------------------------------------
    @property
    def dirty_layers(self) -> list[str]:
        """Return the names of layers with unsaved edits."""
        return [n for n, m in self._models.items() if not m.undo_stack.isClean()]

    @property
    def is_dirty(self) -> bool:
        """Return whether any layer has unsaved edits."""
        return bool(self.dirty_layers)

    def save_layer(self, name: str) -> None:
        """Write one layer to its file and refresh the config's resolved values.

        Raises:
            RuntimeError: if the layer has no file path.
        """
        layer = self.layer(name)
        if layer.file_path is None:
            raise RuntimeError(f"Layer '{name}' has no file path.")
        model = self.model_for(name)
        layer.replace_data(model.to_python())
        self.config.layer_manager.save(name)
        model.undo_stack.setClean()
        self.config.resolve()
        self.saved.emit(name)

    def save_all(self) -> None:
        """Save every layer that has unsaved edits.

        Raises:
            RuntimeError: If a dirty layer has no file path.
        """
        for name in self.dirty_layers:
            self.save_layer(name)
