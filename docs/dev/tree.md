# The tree

## Nodes and kinds

`JsonNode(key, value, parent)` is a node of the document. A container (dict or list) keeps
child nodes and no value; a leaf keeps its value. `assign(value)` rebuilds a node, and
`to_python()` turns a subtree back into plain JSON data.

`kind_of(value)` classifies a value into a `Kind`:

| Kind | Rule |
| --- | --- |
| `null` | `None` |
| `bool` | checked **before** `int`, since `bool` is a subclass of `int` |
| `int`, `float` | by type |
| `color` | a string matching `^#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$` |
| `binary` | a string of at least `BINARY_MIN_LENGTH` (64) characters, a multiple of 4 long, that decodes as strict base64 |
| `str` | any other string |
| `dict`, `list` | by type |

Anything else (a JSON file can't hold it, but a hand-built dict could) raises `TypeError`.
A long run of letters whose length is a multiple of 4 is therefore treated as binary; use a
shorter or differently shaped string if that is not what you mean.

`SWITCHABLE_KINDS` are the types a user may convert to; `binary` is excluded.
`default_value(kind)` gives the value a conversion or new key starts with.

## The model

`JsonTreeModel` is a `QAbstractItemModel` with the columns Key, Value and Type.

- Nodes are addressed by a **path**: the tuple of keys from the root (`("style", "layers",
  0)`). Commands store paths, not nodes, so they stay valid after the tree is rebuilt.
- The `*_at` methods (`assign_at`, `insert_at`, `remove_at`) change the tree and emit the
  right Qt signals. They are meant to be called by commands only.
- The user-facing methods (`set_value`, `add_child`, `remove_node`, and `setData` from the
  views) **push a command** on the undo stack. `set_value` ignores a change to an equal value
  of the same type.
- Extra roles: `KIND_ROLE` returns the node's `Kind`, `NODE_ROLE` the `JsonNode`.
- Only the Value column is editable. Bool values use the check state role.
- List children are renumbered after inserting or removing, and the key column of the
  shifted rows is refreshed.

## Commands

| Command | undo |
| --- | --- |
| `SetValue(model, path, value)` | Assigns the value the node had when the command was made. Also used to change a type. |
| `InsertChild(model, parent_path, row, key, value)` | Removes the inserted child. |
| `RemoveChild(model, path)` | Inserts the removed value again at its old row. |

Each command captures what it needs to undo when it is **created**, so create it right
before pushing it.

## The delegate and the proxy

`ValueDelegate` returns a `QSpinBox` (ints within 32 bits), a `QLineEdit` with an integer
validator (larger ints), a `QDoubleSpinBox`, or a `QLineEdit` for strings. For a color it
opens a `QColorDialog` from `createEditor` and writes the result with `setData` itself, then
returns `None`, so there is no inline editor. Text that isn't an integer is ignored for an
int field.

`FilterProxy` is a recursive `QSortFilterProxyModel` on the key column. `filterAcceptsRow`
hides binary rows always, and shows a row if its key matches, a descendant's key matches
(recursive filtering), or an **ancestor's** key matches, which is how a matching key shows
its whole subtree. Hidden rows stay in the source model, which is why binary values survive
a save.
