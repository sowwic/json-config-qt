# Developer Guide

This guide is for people who work on json-config-qt itself.

## Setup

```bash
uv sync
make check        # ruff + pytest (offscreen Qt)
make mkdocs       # serve these docs
```

`make help` lists every target. Ruff uses a line length of 89 and the `E`, `F` and `UP`
rules, and skips the generated `resources_rc.py`. Docstrings are Google style: the API
reference is generated from them.

The package needs **Python 3.14**: the code uses the unparenthesized
`except A, B:` form of PEP 758.

## Pages

| Page | What you learn |
| --- | --- |
| [Architecture](architecture.md) | The document, the tree model, the proxy, the delegate and the widgets, and how data flows between them. |
| [The tree](tree.md) | Nodes, value kinds, paths, commands and how undo works. |
| [Testing](testing.md) | pytest-qt, the offscreen platform and what to cover. |
| [Releasing](releasing.md) | Versions, the `json-config` dependency, resources and publishing to PyPI. |
| API reference | Generated from the docstrings (see the navigation). |
