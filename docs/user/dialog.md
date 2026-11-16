# Opening the dialog

`ConfigEditorDialog` is a floating, non-modal window editing every layer of a
`LayeredConfig`. A host application opens it, usually from a menu action:

```python
from json_config_qt.editor_dialog import ConfigEditorDialog

def open_settings(self):
    dialog = ConfigEditorDialog.show_for(self.config, parent=self)
    dialog.saved.connect(self.on_layer_saved)
```

`show_for(config, parent=None)` shows the dialog and brings it to the front. It keeps
**one dialog per config**: calling it again while the dialog is open raises the same
window instead of opening another, so a menu action can call it without checking. The
dialog deletes itself when closed.

`saved` is emitted with the **layer name** after a layer was written. The config has
already been resolved again by then, so `config.values` is up to date:

```python
def on_layer_saved(self, layer_name: str):
    self.apply_theme(self.config.values.theme)
```

Because `show_for` returns the **same** dialog while it is open, connecting after every call
would connect your slot again each time, and it would run once per call. Connect with
`UniqueConnection` to a bound method, which ignores a repeated connection:

```python
dialog = ConfigEditorDialog.show_for(self.config, parent=self)
dialog.saved.connect(self.on_layer_saved, QtCore.Qt.ConnectionType.UniqueConnection)
```

A closed dialog is deleted, so the next `show_for` makes a new one and you connect again.

## Creating one yourself

```python
dialog = ConfigEditorDialog(config, parent=window, delete_on_close=False)
dialog.show()
```

Use the constructor when you want to keep the dialog and reopen it. `dialog.editor` is the
`ConfigEditorWidget` inside it and `dialog.document` its `LayerDocument`.

## Behavior

- The window title shows the current layer and a `*` while any layer has unsaved edits.
- The buttons at the bottom are Save Layer, Save All, Undo, Redo and Close.
- Closing it with unsaved edits asks whether to save, discard or cancel.
- It is non-modal, so the host stays usable.

!!! note
    `show_for` identifies a config by the Python object (`id(config)`). Two config
    objects for the same layers get two dialogs, and they won't see each other's edits
    until saved.
