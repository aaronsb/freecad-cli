SHELL := /bin/bash
# FreeCAD CLI

VERSION      := $(shell python3 tools/version.py)
MOD_DIR      ?= $(HOME)/.local/share/FreeCAD/v1-1/Mod
INSTALL_DIR  := $(MOD_DIR)/freecad-cli
XVFB         := xvfb-run -a -s "-screen 0 1600x1000x24"
PART         ?= patch

.DEFAULT_GOAL := help

.PHONY: help
help:  ## Show this help
	@echo "FreeCAD CLI $(VERSION)"
	@echo
	@grep -hE '^[a-z][a-zA-Z0-9_-]*:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

.PHONY: version
version:  ## Print the version and commit
	@python3 -c "import sys;sys.path.insert(0,'.');from fccli.build_info import describe;print(describe())"

.PHONY: stamp
stamp:  ## Freeze the commit into fccli/_build.py
	@python3 tools/version.py stamp

.PHONY: version-check
version-check:  ## Fail if package.xml disagrees with fccli/__init__.py
	@python3 tools/version.py check

.PHONY: test
test:  ## Run the test suite (offscreen, no FreeCAD GUI needed)
	@QT_QPA_PLATFORM=offscreen python3 tests/test_spike.py

.PHONY: lint
lint:  ## Byte-compile everything
	@python3 -m compileall -q fccli tools tests InitGui.py Init.py bin/fccli \
	  && echo "compiles clean"

.PHONY: bvt
bvt:  ## Drive a real FreeCAD GUI end to end, unattended
	@python3 tools/run_bvt.py

.PHONY: socket
socket:  ## Drive a real FreeCAD from outside, over the socket
	@python3 tools/run_socket_test.py

.PHONY: check
check: lint version-check test  ## lint + version-check + test

.PHONY: check-all
check-all: check bvt socket  ## check, plus the live GUI and socket runs

.PHONY: descriptor
descriptor:  ## Regenerate fccli/descriptor.json from FreeCAD's registries
	@python3 tools/generate_descriptor.py

.PHONY: install
install:  ## Symlink into FreeCAD's Mod directory (live dev install)
	@mkdir -p $(MOD_DIR)
	@rm -rf $(INSTALL_DIR)
	@ln -s $(CURDIR) $(INSTALL_DIR)
	@echo "linked $(INSTALL_DIR) -> $(CURDIR)"
	@echo "restart FreeCAD; the dock is under View > Panels > Command Line"

.PHONY: uninstall
uninstall:  ## Remove the Mod directory entry
	@rm -rf $(INSTALL_DIR) && echo "removed $(INSTALL_DIR)"

.PHONY: run
run:  ## Launch FreeCAD with the addon loaded
	@freecad

.PHONY: screenshot
screenshot:  ## Launch headless under Xvfb and capture the dock
	@$(XVFB) freecad tools/screenshot.py

.PHONY: bump
bump: check  ## Bump the version (PART=major|minor|patch)
	@python3 tools/version.py bump $(PART)
	@echo "now $$(python3 tools/version.py) -- edit CHANGELOG.md, then: make release"

.PHONY: release
release: check  ## Tag and push the current version
	@git diff --quiet || { echo "working tree is dirty"; exit 1; }
	@python3 tools/version.py stamp
	@git tag -a v$(VERSION) -F <(python3 tools/release_notes.py $(VERSION))
	@git push origin main
	@git push origin v$(VERSION)
	@echo "tagged v$(VERSION)"
	@python3 tools/release_notes.py $(VERSION) > /tmp/fccli-notes.md
	@command -v gh >/dev/null && gh release create v$(VERSION) \
	  --title "FreeCAD CLI $(VERSION)" \
	  --notes-file /tmp/fccli-notes.md \
	  || echo "(install gh to create the GitHub release)"
	@rm -f /tmp/fccli-notes.md

.PHONY: notes
notes:  ## Print the current version's release notes
	@python3 tools/release_notes.py

.PHONY: clean
clean:  ## Remove build leftovers
	@find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -name '*.py[co]' -delete
	@echo "cleaned"
