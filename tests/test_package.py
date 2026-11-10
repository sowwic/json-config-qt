import json_config_qt
from PySide6 import QtWidgets


def test_package_imports():
    assert json_config_qt.__name__ == "json_config_qt"


def test_qt_application(qtbot):
    widget = QtWidgets.QWidget()
    qtbot.addWidget(widget)
    assert not widget.isVisible()
