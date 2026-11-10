from PySide6 import QtCore, QtGui, QtWidgets

from .model import KIND_ROLE, VALUE_COLUMN
from .nodes import Kind

INT_LIMIT = 2**31 - 1


class ValueDelegate(QtWidgets.QStyledItemDelegate):
    """Creates the editor matching the type of each value."""

    def createEditor(self, parent, option, index):
        """Create the editor matching the value's type.

        Color values open a color dialog instead and return None, as do types
        without an inline editor (dict, list, null, binary).

        Args:
            parent (QtWidgets.QWidget): Parent of the editor.
            option (QtWidgets.QStyleOptionViewItem): Style options of the cell.
            index (QtCore.QModelIndex): The cell being edited.

        Returns:
            QtWidgets.QWidget | None: The editor, or None if there is no inline editor.
        """
        kind = index.data(KIND_ROLE)
        value = index.data(QtCore.Qt.ItemDataRole.EditRole)
        if kind == Kind.INT:
            if abs(value) <= INT_LIMIT:
                editor = QtWidgets.QSpinBox(parent)
                editor.setRange(-INT_LIMIT - 1, INT_LIMIT)
                return editor
            editor = QtWidgets.QLineEdit(parent)
            editor.setValidator(
                QtGui.QRegularExpressionValidator(QtCore.QRegularExpression(r"-?\d+"))
            )
            return editor
        if kind == Kind.FLOAT:
            editor = QtWidgets.QDoubleSpinBox(parent)
            editor.setRange(-1e308, 1e308)
            editor.setDecimals(6)
            editor.setStepType(
                QtWidgets.QAbstractSpinBox.StepType.AdaptiveDecimalStepType
            )
            return editor
        if kind == Kind.COLOR:
            self._pick_color(parent, index, value)
            return None
        if kind == Kind.STR:
            return QtWidgets.QLineEdit(parent)
        return None

    @staticmethod
    def _pick_color(parent, index, value: str) -> None:
        """Let the user pick a color and write it back to the model as a hex string.

        Args:
            parent (QtWidgets.QWidget): Parent of the color dialog.
            index (QtCore.QModelIndex): The value cell being edited.
            value (str): The current hex color; 9 characters means it has alpha.
        """
        color = QtGui.QColor(value)
        has_alpha = len(value) == 9
        picked = QtWidgets.QColorDialog.getColor(
            color,
            parent.window(),
            "Pick color",
            QtWidgets.QColorDialog.ColorDialogOption.ShowAlphaChannel
            if has_alpha
            else QtWidgets.QColorDialog.ColorDialogOption(0),
        )
        if picked.isValid():
            fmt = (
                QtGui.QColor.NameFormat.HexArgb
                if has_alpha
                else QtGui.QColor.NameFormat.HexRgb
            )
            index.model().setData(index, picked.name(fmt))

    def setEditorData(self, editor, index):
        """Load the cell's value into the editor.

        Args:
            editor (QtWidgets.QWidget): The editor created by createEditor.
            index (QtCore.QModelIndex): The cell being edited.
        """
        value = index.data(QtCore.Qt.ItemDataRole.EditRole)
        if isinstance(editor, QtWidgets.QSpinBox | QtWidgets.QDoubleSpinBox):
            editor.setValue(value)
        elif isinstance(editor, QtWidgets.QLineEdit):
            editor.setText(str(value))

    def setModelData(self, editor, model, index):
        """Write the editor's value back to the model.

        Invalid integer text is ignored.

        Args:
            editor (QtWidgets.QWidget): The editor created by createEditor.
            model (QtCore.QAbstractItemModel): The model to update.
            index (QtCore.QModelIndex): The cell being edited.
        """
        if isinstance(editor, QtWidgets.QSpinBox | QtWidgets.QDoubleSpinBox):
            editor.interpretText()
            model.setData(index, editor.value())
        elif isinstance(editor, QtWidgets.QLineEdit):
            text = editor.text()
            if index.data(KIND_ROLE) == Kind.INT:
                if not text.lstrip("-").isdigit():
                    return
                model.setData(index, int(text))
            else:
                model.setData(index, text)

    def updateEditorGeometry(self, editor, option, index):
        """Make the editor fill its cell.

        Args:
            editor (QtWidgets.QWidget): The editor created by createEditor.
            option (QtWidgets.QStyleOptionViewItem): Style options of the cell.
            index (QtCore.QModelIndex): The cell being edited.
        """
        editor.setGeometry(option.rect)

    def initStyleOption(self, option, index):
        """Italicize null values.

        Args:
            option (QtWidgets.QStyleOptionViewItem): The options to fill in.
            index (QtCore.QModelIndex): The cell being painted.
        """
        super().initStyleOption(option, index)
        if index.column() == VALUE_COLUMN and index.data(KIND_ROLE) == Kind.NULL:
            option.font.setItalic(True)
