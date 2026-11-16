# Editing layers

## What you see

A selector lists every layer of the config in dependency order, with its file and a `*` while
it has unsaved edits. Hover an entry for its file and the layers it depends on. Below it, a
filter box and a tree with three columns: **Key**, **Value** and **Type**.

Each layer shows **its own data only**, not the merged result. A layer whose file holds just
`{"level": 20}` shows one row.

## Value types

The editor decides the type of each value from its content:

| Type | Editor | Notes |
| --- | --- | --- |
| `dict`, `list` | none | The value column shows the item count. Add and remove through the context menu. |
| `bool` | check box | |
| `int` | spin box | Integers beyond 32 bits get a text field with digits only. |
| `float` | spin box | Six decimals. |
| `str` | text field | |
| `color` | color dialog | A string like `#RRGGBB` or `#RRGGBBAA`. The alpha channel is offered only if the value has one. |
| `binary` | hidden | A base64 string of at least 64 characters. |
| `null` | none | Shown in italics. |

Double-click a value (or press the edit key) to change it. A bool toggles in place.

!!! note
    Binary values are hidden from the tree, not removed. They stay in the layer and are
    written back when you save.

## Context menu

Right-click the tree:

- **Add key…** on a dict (or on empty space for the top level), asks for a key and a type. A
  key that exists already is refused.
- **Append item…** on a list.
- **Change type** replaces the value with the default of another type (`0`, `""`, `false`,
  `#ffffff`, an empty list or dict, or `null`).
- **Remove** deletes the key or item. Later list items are renumbered.

## Filter

Type in the filter box to show only keys containing the text, case-insensitively. A match
keeps its parents visible and shows its whole subtree, and matches are expanded.

## Undo and redo

Every edit (value, add, remove, change type) is one undoable step. Each layer has **its own
history**, which is kept while you switch layers: undo goes back through the edits of the
layer you are looking at. A layer is clean again when you undo back to where it was saved.

## New layers

**New layer…** asks for:

- a **name**, which must be unique,
- the layer it **depends on**, or none for a root layer,
- an optional **file**. The name is filled from the file name if empty.

The new layer is registered on the config and selected. A layer without a file can be edited
but not saved: saving it shows an error.

## Saving

**Save Layer** writes the current layer, **Save All** every layer with edits.

The editor writes **exactly the layer's data as shown**. That differs from
`LayeredConfig.save()`, which removes values equal to what lower layers provide. Here an
override you wrote stays, even if it equals the inherited value, so you decide what a
layer holds.

After a save the config is resolved again, so `config.values` reflects the new files, and
the dialog's `saved` signal is emitted with the layer name. The file is written as JSON with
four-space indentation.

If the write fails, an error dialog shows the reason and the layer stays dirty.
