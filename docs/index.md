# json-config-qt

A Qt (PySide6) editor for the layers of a [json-config](https://github.com/sowwic/json-config)
`LayeredConfig`. It shows each layer's JSON as a tree with typed values, edits it with
undo and redo, and writes the layer's file back.

```python
from json_config_qt.editor_dialog import ConfigEditorDialog

dialog = ConfigEditorDialog.show_for(config, parent=main_window)
dialog.saved.connect(on_layer_saved)    # config.values is already refreshed
```

- A **dialog** for a host application to open, or a **widget** to embed in its own UI.
- A tree with an editor per type: spin boxes, check boxes, a color picker, text.
- **One undo history per layer**, kept while you switch between layers.
- Binary blobs (base64 strings) are hidden but always saved back untouched.
- A standalone launcher to edit any set of JSON files.

| If you want to... | Read |
| --- | --- |
| Add the editor to an application, or use it | [User Guide](user/index.md) |
| Work on json-config-qt itself | [Developer Guide](dev/index.md) |
| Look up a class or method | API reference (see the navigation) |
