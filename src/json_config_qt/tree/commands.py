import typing

from PySide6 import QtGui

from .nodes import JsonValue

if typing.TYPE_CHECKING:
    from .model import JsonTreeModel, ModelPath


class SetValue(QtGui.QUndoCommand):
    """Replace the value at a path (also used to change a node's type)."""

    def __init__(self, model: JsonTreeModel, path: ModelPath, value: JsonValue):
        """Initialize the command.

        Args:
            model (JsonTreeModel): The model to edit.
            path (ModelPath): ModelPath of the node to replace.
            value (JsonValue): The new value.
        """
        super().__init__(f"Set {path[-1] if path else 'root'}")
        self._model = model
        self._path = path
        self._new = value
        self._old = model.node_at(path).to_python()

    def redo(self) -> None:
        """Apply the new value."""
        self._model.assign_at(self._path, self._new)

    def undo(self) -> None:
        """Restore the previous value."""
        self._model.assign_at(self._path, self._old)


class InsertChild(QtGui.QUndoCommand):
    """Add a dict key or list item."""

    def __init__(
        self,
        model: JsonTreeModel,
        parent_path: ModelPath,
        row: int,
        key: str | int,
        value: JsonValue,
    ):
        """Initialize the command.

        Args:
            model (JsonTreeModel): The model to edit.
            parent_path (ModelPath): ModelPath of the container node.
            row (int): Position to insert at.
            key (str | int): Dict key or list index of the new child.
            value (JsonValue): The child's value.
        """
        super().__init__(f"Add {key}")
        self._model = model
        self._parent_path = parent_path
        self._row = row
        self._key = key
        self._value = value

    def redo(self) -> None:
        """Insert the child."""
        self._model.insert_at(self._parent_path, self._row, self._key, self._value)

    def undo(self) -> None:
        """Remove the inserted child."""
        self._model.remove_at((*self._parent_path, self._key))


class RemoveChild(QtGui.QUndoCommand):
    """Remove a dict key or list item."""

    def __init__(self, model: JsonTreeModel, path: ModelPath):
        """Initialize the command.

        Args:
            model (JsonTreeModel): The model to edit.
            path (ModelPath): ModelPath of the node to remove.
        """
        super().__init__(f"Remove {path[-1]}")
        node = model.node_at(path)
        self._model = model
        self._path = path
        self._row = node.row
        self._value = node.to_python()

    def redo(self) -> None:
        """Remove the child."""
        self._model.remove_at(self._path)

    def undo(self) -> None:
        """Re-insert the removed child at its original position."""
        self._model.insert_at(self._path[:-1], self._row, self._path[-1], self._value)
