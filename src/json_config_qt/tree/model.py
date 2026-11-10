import typing

from PySide6 import QtCore, QtGui, QtWidgets

from . import commands
from .nodes import JsonValue, Kind, JsonNode

ModelPath = tuple[str | int, ...]

COLUMNS = ("Key", "Value", "Type")
KEY_COLUMN, VALUE_COLUMN, TYPE_COLUMN = range(3)
KIND_ROLE = QtCore.Qt.ItemDataRole.UserRole + 1
NODE_ROLE = QtCore.Qt.ItemDataRole.UserRole + 2
NON_EDITABLE_KINDS = (Kind.DICT, Kind.LIST, Kind.NULL, Kind.BINARY)


class JsonTreeModel(QtCore.QAbstractItemModel):
    """Tree model over a JSON document.

    Edits made through the view go through ``undo_stack``; the ``*_at`` methods
    mutate the tree directly and are meant to be called by those commands.
    """

    def __init__(
        self,
        undo_stack: QtGui.QUndoStack,
        parent: QtCore.QObject | None = None,
    ):
        """Initialize the model.

        Args:
            undo_stack (QtGui.QUndoStack): Stack that receives user edits.
            parent (QtCore.QObject | None, optional): Parent object.
        """
        super().__init__(parent)
        self.undo_stack = undo_stack
        self._root = JsonNode(None, {})

    # -- document -----------------------------------------------------------
    def load(self, data: dict[str, JsonValue]) -> None:
        """Replace the model's content.

        Args:
            data (dict[str, JsonValue]): The JSON object to show.
        """
        self.beginResetModel()
        self._root = JsonNode(None, data)
        self.endResetModel()

    def to_python(self) -> dict[str, JsonValue]:
        """Return the current content as plain JSON data."""
        return self._root.to_python()

    # -- path / index helpers -----------------------------------------------
    def node_at(self, path: ModelPath) -> JsonNode:
        """Return the node at *path* (keys from the root)."""
        node = self._root
        for key in path:
            node = next(child for child in node.children if child.key == key)
        return node

    @staticmethod
    def path_of(node: JsonNode) -> ModelPath:
        """Return the keys leading from the root to *node*."""
        keys: list[str | int] = []
        while node.parent is not None:
            keys.append(node.key)
            node = node.parent
        return tuple(reversed(keys))

    def node_for(self, index: QtCore.QModelIndex) -> JsonNode:
        """Return the node of *index*; the invalid index maps to the root."""
        return index.internalPointer() if index.isValid() else self._root

    def index_for(self, node: JsonNode, column: int = 0) -> QtCore.QModelIndex:
        """Return the index of *node* in a column; the root maps to the invalid index."""
        if node is self._root:
            return QtCore.QModelIndex()
        return self.createIndex(node.row, column, node)

    # -- direct mutators (used by undo commands) ----------------------------
    def assign_at(self, path: ModelPath, value: JsonValue) -> None:
        """Replace the value (and type) of the node at *path*, rebuilding children."""
        node = self.node_at(path)
        index = self.index_for(node)
        if node.children:
            self.beginRemoveRows(index, 0, len(node.children) - 1)
            node.children = []
            self.endRemoveRows()
        count = len(value) if isinstance(value, dict | list) else 0
        if count:
            self.beginInsertRows(index, 0, count - 1)
            node.assign(value)
            self.endInsertRows()
        else:
            node.assign(value)
        last = self.index_for(node, len(COLUMNS) - 1)
        self.dataChanged.emit(self.index_for(node), last)

    def insert_at(
        self, parent_path: ModelPath, row: int, key: str | int, value: JsonValue
    ) -> None:
        """Insert a child into the container at *parent_path* at position *row*."""
        parent = self.node_at(parent_path)
        parent_index = self.index_for(parent)
        self.beginInsertRows(parent_index, row, row)
        parent.children.insert(row, JsonNode(key, value, parent))
        parent.renumber()
        self.endInsertRows()
        self._refresh_summary(parent)
        self._refresh_keys(parent, row + 1)

    def remove_at(self, path: ModelPath) -> None:
        """Remove the node at *path* from its parent."""
        node = self.node_at(path)
        parent, row = node.parent, node.row
        self.beginRemoveRows(self.index_for(parent), row, row)
        parent.children.pop(row)
        parent.renumber()
        self.endRemoveRows()
        self._refresh_summary(parent)
        self._refresh_keys(parent, row)

    def _refresh_summary(self, node: JsonNode) -> None:
        """Notify views that a container's child-count summary changed.

        Args:
            node (JsonNode): The container node.
        """
        if node is not self._root:
            index = self.index_for(node, VALUE_COLUMN)
            self.dataChanged.emit(index, index)

    def _refresh_keys(self, parent: JsonNode, first_row: int) -> None:
        """Refresh the key column of list children whose index shifted."""
        if parent.kind is Kind.LIST and first_row < len(parent.children):
            top = self.index_for(parent.children[first_row], KEY_COLUMN)
            bottom = self.index_for(parent.children[-1], KEY_COLUMN)
            self.dataChanged.emit(top, bottom)

    # -- user edits (undoable) ----------------------------------------------
    def set_value(self, node: JsonNode, value: JsonValue) -> None:
        """Push an undoable edit replacing a node's value."""
        if value == node.to_python() and type(value) is type(node.to_python()):
            return
        self.undo_stack.push(commands.SetValue(self, self.path_of(node), value))

    def add_child(self, parent: JsonNode, key: str | int, value: JsonValue) -> None:
        """Push an undoable edit appending a child to a container node."""
        self.undo_stack.push(
            commands.InsertChild(
                self, self.path_of(parent), len(parent.children), key, value
            )
        )

    def remove_node(self, node: JsonNode) -> None:
        """Push an undoable edit removing a node."""
        self.undo_stack.push(commands.RemoveChild(self, self.path_of(node)))

    # -- QAbstractItemModel ---------------------------------------------------
    def index(
        self,
        row: int,
        column: int,
        parent: QtCore.QModelIndex | QtCore.QPersistentModelIndex = QtCore.QModelIndex(),
    ) -> QtCore.QModelIndex:
        """Return the index of a child row/column of *parent*.

        Args:
            row (int): Child row.
            column (int): Child column.
            parent (QtCore.QModelIndex): Parent index; invalid for top-level rows.

        Returns:
            QtCore.QModelIndex: The child index, or an invalid index if out of range.
        """
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()
        return self.createIndex(row, column, self.node_for(parent).children[row])

    def parent(self, child: QtCore.QModelIndex) -> QtCore.QModelIndex:  # ty: ignore
        """Return the parent index of *child*, invalid for top-level rows."""
        if not child.isValid():
            return QtCore.QModelIndex()
        return self.index_for(self.node_for(child).parent)

    def rowCount(self, parent=QtCore.QModelIndex()) -> int:
        """Return the number of children of *parent*; only column 0 has children."""
        if parent.column() > 0:
            return 0
        return len(self.node_for(parent).children)

    def columnCount(self, parent=QtCore.QModelIndex()) -> int:
        """Return the number of columns (key, value, type)."""
        return len(COLUMNS)

    def headerData(self, section, orientation, role=QtCore.Qt.ItemDataRole.DisplayRole):
        """Return the column titles for the horizontal header."""
        if (
            orientation == QtCore.Qt.Orientation.Horizontal
            and role == QtCore.Qt.ItemDataRole.DisplayRole
        ):
            return COLUMNS[section]
        return None

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlag:
        """Return item flags; only the value column of editable types is editable.

        Bool values are additionally user-checkable.
        """
        flags = QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable
        if index.column() != VALUE_COLUMN:
            return flags
        node = self.node_for(index)
        if node.kind is Kind.BOOL:
            flags |= QtCore.Qt.ItemFlag.ItemIsUserCheckable
        if node.kind not in NON_EDITABLE_KINDS:
            flags |= QtCore.Qt.ItemFlag.ItemIsEditable
        return flags

    def data(self, index: QtCore.QModelIndex, role=QtCore.Qt.ItemDataRole.DisplayRole):
        """Return the data of *index* for *role*.

        Besides the standard roles, KIND_ROLE returns the node's Kind and
        NODE_ROLE the JsonNode itself.

        Args:
            index (QtCore.QModelIndex): The cell.
            role (int): The item data role.

        Returns:
            Any: The data, or None if there is none for this role.
        """
        if not index.isValid():
            return None
        node, column = self.node_for(index), index.column()
        Role = QtCore.Qt.ItemDataRole
        if role == KIND_ROLE:
            return node.kind
        if role == NODE_ROLE:
            return node
        if column == KEY_COLUMN and role == Role.DisplayRole:
            return str(node.key)
        if column == TYPE_COLUMN and role == Role.DisplayRole:
            return node.kind.value
        if column != VALUE_COLUMN:
            return None
        if role == Role.DisplayRole:
            return self._display_value(node)
        if role == Role.EditRole:
            return node.value
        if role == Role.CheckStateRole and node.kind is Kind.BOOL:
            return (
                QtCore.Qt.CheckState.Checked
                if node.value
                else (QtCore.Qt.CheckState.Unchecked)
            )
        if role == Role.DecorationRole and node.kind is Kind.COLOR:
            return QtGui.QColor(node.value)
        if role == Role.ForegroundRole and node.kind is Kind.NULL:
            return QtWidgets.QApplication.palette().placeholderText()
        return None

    @staticmethod
    def _display_value(node: JsonNode) -> str:
        """Return the text shown in the value column.

        Args:
            node (JsonNode): The node to describe.

        Returns:
            str: The value, or a count summary for containers.
        """
        match node.kind:
            case Kind.DICT:
                return f"{{{len(node.children)}}}"
            case Kind.LIST:
                return f"[{len(node.children)}]"
            case Kind.NULL:
                return "null"
            case Kind.BOOL:
                return str(node.value).lower()
            case _:
                return str(node.value)

    def setData(self, index, value, role=QtCore.Qt.ItemDataRole.EditRole) -> bool:
        """Push an undoable edit for the value cell at *index*.

        Args:
            index (QtCore.QModelIndex): The cell; only the value column is editable.
            value (Any): The new value, or a check state for bool values.
            role (int): EditRole, or CheckStateRole for bool values.

        Returns:
            bool: True if the edit was accepted.
        """
        if not index.isValid() or index.column() != VALUE_COLUMN:
            return False
        node = self.node_for(index)
        if role == QtCore.Qt.ItemDataRole.CheckStateRole and node.kind is Kind.BOOL:
            value = QtCore.Qt.CheckState(value) == QtCore.Qt.CheckState.Checked
        elif role != QtCore.Qt.ItemDataRole.EditRole:
            return False
        self.set_value(node, typing.cast(JsonValue, value))
        return True
