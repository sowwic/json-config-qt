# Architecture

```text
json_config_qt
├── editor_dialog.py   ConfigEditorDialog: floating window around the widget
├── editor_widget.py   ConfigEditorWidget (+ NewLayerDialog): the UI and its actions
├── document.py        LayerDocument: one tree model and undo stack per layer
├── main.py            standalone launcher, config_from_files()
└── tree/
    ├── nodes.py       JsonNode, Kind: the JSON tree and value classification
    ├── model.py       JsonTreeModel: QAbstractItemModel over the nodes
    ├── commands.py    SetValue, InsertChild, RemoveChild: the undo commands
    ├── delegate.py    ValueDelegate: an editor per value type
    └── filter.py      FilterProxy: key filter, hides binary values
```

## Data flow

```text
LayeredConfig ──layer.get_data()──▶ JsonTreeModel ──▶ FilterProxy ──▶ QTreeView
   ▲                                     ▲   │ setData (user edit)
   │ resolve()                           │   ▼
   │                                QUndoStack ◀── commands ── model.*_at()
   └── layer.replace_data(model.to_python()) ◀── LayerDocument.save_layer()
```

The editor works on the **raw dict of each layer**, not on the typed values. That is why
it needs no `ConfigValues` class: it can edit keys the schema doesn't know about, and
what it saves is what you saw.

## The document

`LayerDocument(config)` is the model of the editor, with no widgets.

- `model_for(name)` creates a `JsonTreeModel` and a `QUndoStack` for a layer the first
  time it is asked for, loaded from `layer.get_data()`, and caches it. Switching layers
  therefore keeps edits and history.
- All stacks join one `QUndoGroup`. `set_layer` makes the layer's stack the active one, so
  the widget's undo and redo actions follow the current layer.
- A layer is dirty when its stack isn't clean (`cleanChanged` drives `dirtyChanged`).
- `save_layer(name)` copies `model.to_python()` into the layer (`replace_data`), saves the
  file through the manager, marks the stack clean, calls `config.resolve()` and emits
  `saved`. It raises `RuntimeError` for a layer without a file. `save_all` saves the dirty
  layers.
- `new_layer` registers a `ConfigLayer` on the config's manager, with at most one parent,
  and selects it. `layers` is read from `config.layers` every time, but the widget
  refreshes its selector only on `layersChanged`, which `new_layer` emits, so a layer
  registered elsewhere appears after the next such refresh.

!!! warning
    The document edits a snapshot taken when a layer's model is first created. If the
    layer's data changes outside the editor afterwards, the editor still shows the old
    data, and saving overwrites the change.

## The widget and the dialog

`ConfigEditorWidget` builds its UI in `_create_actions`, `_create_widgets`,
`_create_layouts` and `_create_connections`, called from `__init__`. The same structure
is used by `ConfigEditorDialog`, `NewLayerDialog` and other widgets in the project.

- The tree view shows `FilterProxy(document.model)`. A change of layer swaps the source
  model and reapplies the header sizes (they are ignored while there are no columns).
- Failed saves (`OSError`, `RuntimeError`) are caught in `_guarded` and shown in a message
  box; the document itself raises.
- Actions are added to the widget with `WidgetWithChildrenShortcut` so the Save, Undo and
  Redo only work with focus inside the editor.
- `ConfigEditorDialog.show_for` keeps a class-level dict `{id(config): dialog}`, removed
  when the dialog is destroyed.

## The launcher

`main.config_from_files(paths)` builds one layer per file, each depending on the previous
one, and a config with an empty `ConfigValues`. It calls `ConfigLayerManager.clear()`
first, which drops **every** named manager in the process: fine for a launcher, so don't
call it from application code.
