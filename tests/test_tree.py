import copy
import json
import pathlib

import pytest
from PySide6 import QtCore

from json_config_qt.document import LayerDocument
from json_config_qt.main import config_from_files
from json_config_qt.tree.filter import FilterProxy
from json_config_qt.tree.nodes import Kind, kind_of

BLOB = "A" * 80
SAMPLE = {
    "window": {"size": [800, 600], "on_top": False, "state": BLOB},
    "bridge": {"host": "127.0.0.1", "port": None},
    "style": {"color": "#4BE3FF", "speed": 160.0, "layers": [{"a": 1}]},
    "level": 20,
}


@pytest.fixture
def layer_file(tmp_path: pathlib.Path) -> pathlib.Path:
    path = tmp_path / "layer.json"
    path.write_text(json.dumps(SAMPLE))
    return path


@pytest.fixture
def doc(layer_file, qtbot) -> LayerDocument:
    return LayerDocument(config_from_files([layer_file]))


@pytest.mark.parametrize(
    ("value", "kind"),
    [
        (True, Kind.BOOL),
        (1, Kind.INT),
        (1.5, Kind.FLOAT),
        ("hello", Kind.STR),
        ("#aabbcc", Kind.COLOR),
        (BLOB, Kind.BINARY),
        (None, Kind.NULL),
        ({}, Kind.DICT),
        ([], Kind.LIST),
    ],
)
def test_kind_of(value, kind):
    assert kind_of(value) is kind


def test_round_trip_unchanged(doc, layer_file):
    doc.save_layer("layer")
    assert json.loads(layer_file.read_text()) == SAMPLE


def test_set_value_undo_redo(doc):
    model = doc.model
    node = model.node_at(("level",))
    model.set_value(node, 30)
    assert model.to_python()["level"] == 30
    assert doc.is_dirty
    doc.undo_group.activeStack().undo()
    assert model.to_python() == SAMPLE
    assert not doc.is_dirty
    doc.undo_group.activeStack().redo()
    assert model.to_python()["level"] == 30


def test_bool_check_state(doc):
    model = doc.model
    index = model.index_for(model.node_at(("window", "on_top")), 1)
    assert model.setData(
        index, QtCore.Qt.CheckState.Checked, QtCore.Qt.ItemDataRole.CheckStateRole
    )
    assert model.to_python()["window"]["on_top"] is True


def test_add_remove_key(doc):
    model = doc.model
    bridge = model.node_at(("bridge",))
    model.add_child(bridge, "token", "")
    assert model.to_python()["bridge"]["token"] == ""
    model.remove_node(model.node_at(("bridge", "host")))
    assert "host" not in model.to_python()["bridge"]
    doc.undo_group.activeStack().undo()
    doc.undo_group.activeStack().undo()
    assert model.to_python() == SAMPLE
    assert list(model.to_python()["bridge"]) == ["host", "port"]  # order restored


def test_list_remove_renumbers(doc):
    model = doc.model
    model.remove_node(model.node_at(("window", "size", 0)))
    assert model.to_python()["window"]["size"] == [600]
    assert model.node_at(("window", "size", 0)).key == 0
    doc.undo_group.activeStack().undo()
    assert model.to_python()["window"]["size"] == [800, 600]


def test_change_type_null_to_int_and_back(doc):
    model = doc.model
    node = model.node_at(("bridge", "port"))
    model.set_value(node, 8080)
    assert node.kind is Kind.INT
    model.set_value(model.node_at(("style", "layers")), {})
    assert model.to_python()["style"]["layers"] == {}
    doc.undo_group.activeStack().undo()
    assert model.to_python()["style"]["layers"] == [{"a": 1}]


def test_filter_hides_binary_and_keeps_ancestors(doc):
    proxy = FilterProxy()
    proxy.setSourceModel(doc.model)
    window = proxy.index(0, 0)
    keys = [proxy.index(r, 0, window).data() for r in range(proxy.rowCount(window))]
    assert "state" not in keys
    assert doc.model.to_python()["window"]["state"] == BLOB  # still in data

    proxy.set_filter_text("color")
    assert proxy.rowCount() == 1
    assert proxy.index(0, 0).data() == "style"


def test_sample_not_mutated():
    assert copy.deepcopy(SAMPLE) == SAMPLE


def test_filter_shows_subtree_of_matching_key(doc):
    proxy = FilterProxy()
    proxy.setSourceModel(doc.model)
    proxy.set_filter_text("bridge")
    bridge = proxy.index(0, 0)
    assert proxy.rowCount() == 1
    assert proxy.rowCount(bridge) == 2
