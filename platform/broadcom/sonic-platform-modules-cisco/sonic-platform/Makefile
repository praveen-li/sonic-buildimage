# tools
PYTHON2 ?= python2.7
PYTHON3 ?= python3.7
MKDIR ?= mkdir
CP ?= cp

# envs
BASE_DIR       ?= $(CURDIR)
MODULE_SRC     := $(BASE_DIR)/src
BUILD_DIR      := $(BASE_DIR)/build

# packaging
PACKAGE_NAME ?= cisco
PY2_PACKAGE_NAME ?= $(PACKAGE_NAME)
PY3_PACKAGE_NAME ?= $(PACKAGE_NAME)

DESTDIR         ?= $(CURDIR)/install
PY2_DESTDIR     ?= $(DESTDIR)
PY3_DESTDIR     ?= $(DESTDIR)

# build
PY_BUILD_ARGS ?=
PY2_BUILD_ARGS ?= $(PY_BUILD_ARGS) --build-base=$(BUILD_DIR)/python2.7
PY3_BUILD_ARGS ?= $(PY_BUILD_ARGS) --build-base=$(BUILD_DIR)/python3.7

all:
	@echo "Nothing to do."
#
# build targets
#


build-py2:
	$(PYTHON2) setup.py build $(PY2_BUILD_ARGS)

build-py3:
	$(PYTHON3) setup.py build $(PY3_BUILD_ARGS)

build: build-py2 build-py3

#
# clean targets
#

clean-py2:
	$(PYTHON2) setup.py clean $(PY2_BUILD_ARGS)
	find $(BASE_DIR)/ -iname '*.pyc' -delete

clean-py3:
	$(PYTHON3) setup.py clean $(PY3_BUILD_ARGS)
	find $(BASE_DIR)/ -iname '__pycache__' -exec rm -rf {} +

clean: clean-py2 clean-py3

distclean: clean
	$(RM) -r $(BASE_DIR)/*.egg-info $(BASE_DIR)/build $(BASE_DIR)/install

#
# install targets
#

install-py2:
	$(MKDIR) -p $(PY2_DESTDIR)
	$(PYTHON2) setup.py install --root=$(PY2_DESTDIR) $(PY_INSTALL_ARGS)

install-py3:
	$(MKDIR) -p $(PY3_DESTDIR)
	$(PYTHON3) setup.py install --root=$(PY3_DESTDIR) $(PY_INSTALL_ARGS)

install: install-py2 install-py3


