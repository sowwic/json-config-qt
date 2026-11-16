# Testing

```bash
make pytest                                              # everything, with coverage
uv run pytest tests/test_tree.py::test_set_value_undo_redo   # one test
make pytest-pdb                                          # verbose, pdb on failure
```

`make pytest` runs with `QT_QPA_PLATFORM=offscreen`, and `tests/conftest.py` sets it too, so
no display is needed. Coverage (`--cov=json_config_qt`) is always on.

## Layout

| File | Covers |
| --- | --- |
| `tests/test_tree.py` | Value classification, the model round trip, undo and redo of every command, the filter proxy. |
| `tests/test_editor.py` | `LayerDocument` (layers, switching, saving, new layers), the widget, the dialog (close prompt, save button, `show_for` reuse, shortcuts). |
| `tests/test_package.py` | The package imports and a `QApplication` starts. |

## Conventions

- Use the `qtbot` fixture from pytest-qt for anything that creates a widget or a
  `QObject`, so it gets a `QApplication` and is cleaned up.
- Build configs from files with `config_from_files([...])` in a `tmp_path`, never from the
  repository's folders. The helper clears all `ConfigLayerManager` instances, so tests don't
  leak layers into each other.
- Blocking dialogs (`QMessageBox.question`, `QInputDialog`) hang a test: patch them with
  `monkeypatch`, as `test_dialog_close_prompts_when_dirty` does.
- Assert state, not pixels: read the model, the actions' `isEnabled()` and the document's
  dirty layers.

## What to cover

- A new value kind or editor: `kind_of`, the display text, the delegate's editor and a
  round trip that doesn't change the data.
- A new edit: the command's `redo` and `undo`, and that the stack becomes clean again after
  undoing back to the save point.
- Saving: that **only** the saved layer's file changes, and that hidden (binary) values are
  written back.
