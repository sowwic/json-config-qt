# json-config-qt

![Tests](https://github.com/sowwic/json-config-qt/actions/workflows/unit_tests.yml/badge.svg)
![Code Quality](https://github.com/sowwic/json-config-qt/actions/workflows/code_quality.yml/badge.svg)

Description

## Development

```sh
uv sync            # install the project and dev dependencies
make check         # lint + tests
make help          # list all targets
```

## Releasing

1. Add a `v<version>` entry to `CHANGELOG.rst`, update `VERSION` (`make update-version`) and commit on `main`.
2. `make release VERSION=<version>` tags, pushes (triggering the GitHub release workflow) and back-merges into `develop`.

## Usage

Spawn the editor as a floating dialog from a host app by handing it a `LayeredConfig`:

```python
from json_config_qt.editor_dialog import ConfigEditorDialog

dialog = ConfigEditorDialog.show_for(config, parent=main_window)  # one dialog per config
dialog.saved.connect(on_layer_saved)  # config.values is already refreshed
```

Or embed `json_config_qt.editor_widget.ConfigEditorWidget` directly. It has no menus; its public
actions (`save_action`, `save_all_action`, `new_layer_action`, `undo_action`, `redo_action`, ...) can be
placed in the host's own UI, and shortcuts only apply while the editor has focus. Call
`confirm_discard()` from the host's close handling to get the unsaved-changes prompt.

The layer list comes from `config.layers`; edits apply to each layer's own data and are written with
`layer_manager.save()`, after which `config.resolve()` refreshes `config.values`.
Debug launcher: `uv run python -m json_config_qt.main base.json user.json` (later files override earlier ones).
