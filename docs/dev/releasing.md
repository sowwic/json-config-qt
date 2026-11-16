# Releasing

## Branches and versions

`develop` is the default and PR branch; `main` is the release branch. Work on a feature
branch named after the GitHub issue.

The version lives in `VERSION` and is copied into `pyproject.toml` (`make update-version`).
Add a section at the top of `CHANGELOG.rst` for each release, one bullet per user-visible
change with the issue number where there is one.

```bash
make release VERSION=1.2.3 [RELEASE_TITLE="..."]
```

tags `main`, pushes, and merges back into `develop`. The tag triggers
`.github/workflows/release.yml`, which creates the GitHub release from the changelog.

## Generated resources

`src/json_config_qt/resources/resources_rc.py` is generated from `resources.qrc` by
`make qrc`, and committed. `make build` regenerates it first. Run `make qrc` after changing
an icon or the `.qrc` file.

## The json-config dependency

The editor depends on **sowwic-json-config**, the distribution of
[json-config](https://github.com/sowwic/json-config) (it imports as `json_config`). During
development `pyproject.toml` resolves it from git through `[tool.uv.sources]`.

!!! warning
    `[tool.uv.sources]` is **not** part of the published metadata. A release on PyPI
    asks for `sowwic-json-config` from PyPI, so that package has to be published first. Once it
    is, delete the git source (or point it at the release tag) and add a lower bound to the
    dependency, e.g. `"sowwic-json-config>=1.0.7"`. Do not publish with the git source still in
    place: the build would work and every user's install would fail.

The name `json-config` on PyPI belongs to a different project. Always depend on
`sowwic-json-config`.

## Publishing to PyPI

The distribution is `sowwic-json-config-qt`, imported as `json_config_qt`. Targets come from
the `general/pypi` module of [sowwic/makefiles](https://github.com/sowwic/makefiles):

```bash
make pypi-publish-dev     # build and upload to TestPyPI
make pypi-publish         # build and upload to PyPI
```

Both clean and build first. `uv publish` reads the token from `UV_PUBLISH_TOKEN`, so set it
for the run only:

```bash
UV_PUBLISH_TOKEN=pypi-... make pypi-publish
```

PyPI and TestPyPI have separate accounts and tokens. The first upload needs an account-wide
token, because a project-scoped token can only exist once the project does. A published
version can't be replaced: bump `VERSION` and publish again. To hide a bad one, yank it on
pypi.org.

TestPyPI doesn't host dependencies such as PySide6, so install a test upload with
`--extra-index-url`:

```bash
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ sowwic-json-config-qt
```

## CI

The workflows in `.github/workflows/` call the shared ones of `sowwic/gh-workflows`: tests
(Python 3.14, offscreen Qt, on Linux and Windows and then macOS), lint, docs deployment and release.
Dependabot opens weekly PRs against `develop` for the lockfile and the Actions, and holds
back PySide6 major versions.
