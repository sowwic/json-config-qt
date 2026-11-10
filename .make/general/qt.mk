# Qt resources: `qrc` compiles resources/resources.qrc into resources_rc.py.
# Set BUILD_PREREQS = qrc before including general/python to compile them before every build.
# Needs PACKAGE_NAME and the colors/banner of general/python (include it first).

.PHONY: qrc
qrc: ## Generate Python resources from Qt .qrc files
	$(call banner, Generating QRC resources...)
	@uv run pyside6-rcc src/$(PACKAGE_NAME)/resources/resources.qrc -o src/$(PACKAGE_NAME)/resources/resources_rc.py
	@printf "$(GREEN)QRC generation complete.$(RESET)\n"
