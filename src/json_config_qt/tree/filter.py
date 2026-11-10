from PySide6 import QtCore

from .model import KEY_COLUMN, KIND_ROLE
from .nodes import Kind


class FilterProxy(QtCore.QSortFilterProxyModel):
    """Filters the tree by key text and hides binary blobs.

    Hidden values stay in the source model, so they are preserved on save.
    """

    def __init__(self, parent: QtCore.QObject | None = None):
        """Initialize the proxy.

        Args:
            parent (QtCore.QObject | None, optional): Parent object.
        """
        super().__init__(parent)
        self.setRecursiveFilteringEnabled(True)
        self.setFilterKeyColumn(KEY_COLUMN)
        self.setFilterCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)

    def set_filter_text(self, text: str) -> None:
        """Show only keys containing *text* (case-insensitive) and their subtrees."""
        self.setFilterFixedString(text)

    def filterAcceptsRow(self, source_row, source_parent) -> bool:
        """Return whether a row is visible.

        Binary rows are always hidden; other rows are shown if their key, a
        descendant's key or an ancestor's key matches the filter.

        Args:
            source_row (int): Row in the source model.
            source_parent (QtCore.QModelIndex): Parent index in the source model.

        Returns:
            bool: True if the row is shown.
        """
        index = self.sourceModel().index(source_row, KEY_COLUMN, source_parent)
        if index.data(KIND_ROLE) == Kind.BINARY:
            return False
        if super().filterAcceptsRow(source_row, source_parent):
            return True
        return self._ancestor_matches(source_parent)

    def _ancestor_matches(self, index: QtCore.QModelIndex) -> bool:
        """Show the children of a matching key, so its whole subtree is visible."""
        regex = self.filterRegularExpression()
        while index.isValid():
            key = index.sibling(index.row(), KEY_COLUMN).data()
            if regex.match(key).hasMatch():
                return True
            index = index.parent()
        return False
