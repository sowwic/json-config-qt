# Embedding the widget

To put the editor inside your own window, or to use your own buttons, embed
`ConfigEditorWidget`:

```python
from json_config_qt.editor_widget import ConfigEditorWidget

editor = ConfigEditorWidget(config, parent=self)
layout.addWidget(editor)
editor.saved.connect(self.on_layer_saved)
```

The widget has the layer selector, the filter box and the tree. It has **no menus or
buttons of its own** for saving and history: it exposes them as `QAction`s that you place
where you like.

| Action | Does |
| --- | --- |
| `save_action` | Save the current layer (the standard Save shortcut). |
| `save_all_action` | Save every layer with unsaved edits. |
| `new_layer_action` | Ask for a name, parent and file, and add a layer. |
| `undo_action`, `redo_action` | Undo and redo in the current layer. |
| `expand_all_action`, `collapse_all_action` | Expand or collapse the tree. |

```python
toolbar.addAction(editor.save_action)
toolbar.addAction(editor.undo_action)
edit_menu.addAction(editor.redo_action)
```

The undo and redo actions follow the layer being edited, and show the text of the command
they would run.

## Shortcuts

Save, Undo and Redo have standard key sequences, but they only apply **while the editor has
focus** (`WidgetWithChildrenShortcut`), so they never fight with the shortcuts of the host.
If you want an application-wide shortcut, set it on your own copy of the action.

## Unsaved changes

Call `confirm_discard()` from your own close handling:

```python
def closeEvent(self, event):
    if self.editor.confirm_discard():
        event.accept()
    else:
        event.ignore()
```

It returns `True` at once when nothing is dirty. Otherwise it asks to save, discard or
cancel, and returns `False` on cancel, or when a save fails.

## Saving from code

```python
editor.save_current()   # True when written; an error dialog is shown on failure
editor.save_all()
```

Both show a dialog and return `False` on a failed write instead of raising. For
headless use, work with `editor.document` ([`LayerDocument`](../dev/architecture.md#the-document)),
where `save_layer(name)` and `save_all()` raise.
