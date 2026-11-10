import json
import pathlib

import pytest
from PySide6 import QtWidgets
from PySide6.QtCore import Qt

from json_config_qt.document import LayerDocument
from json_config_qt.editor_widget import ConfigEditorWidget
from json_config_qt.main import config_from_files
from json_config_qt.editor_dialog import ConfigEditorDialog

BLOB = "A" * 80
BASE = {"level": 10, "style": {"color": "#ffffff"}, "state": BLOB}
USER = {"level": 20}


@pytest.fixture
def files(tmp_path: pathlib.Path) -> list[pathlib.Path]:
    base, user = tmp_path / "base.json", tmp_path / "user.json"
    base.write_text(json.dumps(BASE))
    user.write_text(json.dumps(USER))
    return [base, user]


@pytest.fixture
def config(files):
    return config_from_files(files)


@pytest.fixture
def doc(config, qtbot) -> LayerDocument:
    return LayerDocument(config)


def test_layers_from_config(doc, config):
    assert doc.layers == config.layers == ["base", "user"]
    assert doc.current_layer == "base"


def test_switch_loads_layer_data(doc):
    doc.set_layer("user")
    assert doc.model.to_python() == USER
    doc.set_layer("base")
    assert doc.model.to_python() == BASE


def test_save_writes_only_that_layer(doc, files, config):
    doc.set_layer("user")
    doc.model.set_value(doc.model.node_at(("level",)), 99)
    base_mtime = files[0].stat().st_mtime_ns
    assert doc.dirty_layers == ["user"]
    doc.save_layer("user")
    assert json.loads(files[1].read_text()) == {"level": 99}
    assert files[0].stat().st_mtime_ns == base_mtime
    assert not doc.is_dirty
    assert config.layer_manager.resolve()["level"] == 99


def test_undo_history_survives_switching(doc):
    doc.set_layer("user")
    doc.model.set_value(doc.model.node_at(("level",)), 1)
    doc.set_layer("base")
    assert not doc.undo_group.activeStack().canUndo()
    doc.set_layer("user")
    doc.undo_group.undo()
    assert doc.model.to_python() == USER


def test_new_layer_registers_with_parent(doc, config, tmp_path):
    path = tmp_path / "local.json"
    doc.new_layer("local", "user", path)
    assert doc.current_layer == "local"
    assert config.layer_manager["local"].depends_on == ["user"]
    assert config.layers == ["base", "user", "local"]
    doc.model.add_child(doc.model.node_at(()), "x", 1)
    doc.save_layer("local")
    assert json.loads(path.read_text()) == {"x": 1}


def test_new_layer_rejects_duplicates_and_unknown_parent(doc):
    with pytest.raises(ValueError):
        doc.new_layer("base")
    with pytest.raises(ValueError):
        doc.new_layer("other", "nope")
    with pytest.raises(ValueError):
        doc.new_layer("")


def test_save_layer_without_file_raises(doc):
    doc.new_layer("memory")
    doc.model.add_child(doc.model.node_at(()), "x", 1)
    with pytest.raises(RuntimeError):
        doc.save_layer("memory")
    assert doc.is_dirty


def test_widget_combo_and_switch(config, files, qtbot):
    widget = ConfigEditorWidget(config)
    qtbot.addWidget(widget)
    texts = [widget.layer_combo.itemText(i) for i in range(2)]
    assert texts == [f"base  —  {files[0]}", f"user  —  {files[1]}"]
    widget.layer_combo.activated.emit(1)
    assert widget.document.current_layer == "user"
    assert widget.proxy.rowCount() == 1
    model = widget.document.model
    model.set_value(model.node_at(("level",)), 5)
    assert widget.layer_combo.itemText(1).startswith("user*  —  ")


def test_widget_hides_binary_but_saves_it(config, files, qtbot):
    widget = ConfigEditorWidget(config)
    qtbot.addWidget(widget)
    keys = [widget.proxy.index(r, 0).data() for r in range(widget.proxy.rowCount())]
    assert keys == ["level", "style"]
    model = widget.document.model
    model.set_value(model.node_at(("level",)), 11)
    assert widget.save_current()
    assert json.loads(files[0].read_text())["state"] == BLOB


def test_dialog_close_prompts_when_dirty(config, qtbot, monkeypatch):
    dialog = ConfigEditorDialog(config)
    qtbot.addWidget(dialog)
    dialog.show()
    model = dialog.document.model
    model.set_value(model.node_at(("level",)), 11)
    assert dialog.windowTitle().startswith("base*")
    Button = QtWidgets.QMessageBox.StandardButton
    monkeypatch.setattr(QtWidgets.QMessageBox, "question", lambda *a, **k: Button.Cancel)
    dialog.reject()
    assert dialog.isVisible()
    monkeypatch.setattr(
        QtWidgets.QMessageBox, "question", lambda *a, **k: Button.Discard
    )
    dialog.reject()
    assert not dialog.isVisible()


def test_dialog_save_button_writes_file_and_emits(config, files, qtbot):
    dialog = ConfigEditorDialog(config)
    qtbot.addWidget(dialog)
    model = dialog.document.model
    model.set_value(model.node_at(("level",)), 12)
    with qtbot.waitSignal(dialog.saved) as blocker:
        dialog.action_buttons[0].click()
    assert blocker.args == ["base"]
    assert json.loads(files[0].read_text())["level"] == 12


def test_show_for_reuses_dialog(config, qtbot):
    first = ConfigEditorDialog.show_for(config)
    assert ConfigEditorDialog.show_for(config) is first
    first.reject()
    first.deleteLater()
    qtbot.waitUntil(lambda: id(config) not in ConfigEditorDialog._instances)


def test_widget_actions_do_not_leak_shortcuts(config, qtbot):
    widget = ConfigEditorWidget(config)
    qtbot.addWidget(widget)
    context = Qt.ShortcutContext.WidgetWithChildrenShortcut
    for action in (widget.save_action, widget.undo_action, widget.redo_action):
        assert action.shortcutContext() == context
    assert not widget.undo_action.isEnabled()
    model = widget.document.model
    model.set_value(model.node_at(("level",)), 1)
    assert widget.undo_action.isEnabled()


def test_value_column_stretches(config, qtbot):
    widget = ConfigEditorWidget(config)
    qtbot.addWidget(widget)
    widget.resize(800, 500)
    widget.show()
    qtbot.waitExposed(widget)
    header = widget.view.header()
    assert header.sectionResizeMode(1) == header.ResizeMode.Stretch
    assert header.length() >= widget.view.viewport().width() - 2
