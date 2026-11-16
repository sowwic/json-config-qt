# Common targets come from sowwic/makefiles, fetched into .make/ (commit it). `make update-make` fetches them again.
APP_NAME = sowwic-json-config-qt
PACKAGE_NAME = json_config_qt
RELEASE_BRANCH ?= main
DEVELOP_BRANCH ?= develop
PYTEST_CMD = QT_QPA_PLATFORM=offscreen uv run pytest tests
BUILD_PREREQS = qrc clean-ds-store

MAKEFILES_REF ?= v1
MAKEFILES_URL ?= https://raw.githubusercontent.com/sowwic/makefiles/$(MAKEFILES_REF)
MAKEFILES_MODULES = general/python general/repo general/qt general/pypi

.make/%.mk:
	@mkdir -p $(dir $@)
	@curl -fsSL $(MAKEFILES_URL)/$*.mk -o $@
include $(MAKEFILES_MODULES:%=.make/%.mk)

.PHONY: clean-ds-store
clean-ds-store: ## Remove macOS .DS_Store files (the build packages them)
	@find . -name .DS_Store -not -path "./.git/*" -not -path "./.venv/*" -delete

clean:: clean-ds-store
