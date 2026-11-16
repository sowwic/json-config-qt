# User Guide

This guide is for people who add the config editor to an application, or use it.

## Installation

```bash
pip install sowwic-json-config-qt
```

Requires Python 3.14+. It installs [PySide6](https://pypi.org/project/PySide6/) and
[sowwic-json-config](https://github.com/sowwic/json-config); the editor works on the
`LayeredConfig` of the latter and imports as `json_config_qt`.

Until a release is on PyPI, use
`pip install git+https://github.com/sowwic/json-config-qt.git`.

## Pages

| Page | What you learn |
| --- | --- |
| [Opening the dialog](dialog.md) | `ConfigEditorDialog`: showing it, one per config, the `saved` signal. |
| [Embedding the widget](widget.md) | `ConfigEditorWidget`: the actions to place in your UI, shortcuts, the unsaved-changes prompt. |
| [Editing layers](editing.md) | What the editor shows and does: types, filter, undo, new layers, and what saving writes. |

## Try it

Edit any JSON files from the command line. Each file is a layer that overrides the one
before it, named after its file stem:

```bash
python -m json_config_qt.main base.json user.json
```

The launcher builds a config with no schema, so it shows exactly what is in the files.
