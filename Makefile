.DEFAULT_GOAL := build
PGSERVER_VERSION ?= 16
PYTHON ?= python
.PHONY: build wheel install-wheel install-dev clean test

build:
	$(MAKE) -C packages/pgserver-postgres-$(PGSERVER_VERSION) build

wheel: build
	$(PYTHON) -m build --wheel
	cd packages/pgserver-postgres-$(PGSERVER_VERSION) && $(PYTHON) -m build --wheel --outdir ../../dist

install-wheel: wheel
	$(PYTHON) -m pip install --force-reinstall dist/*.whl

install-dev: build
	$(PYTHON) -m pip install -e packages/pgserver-postgres-$(PGSERVER_VERSION) -e .

clean:
	rm -rf build/ wheelhouse/ dist/ .eggs/
	$(MAKE) -C pgbuild clean

test:
	python -m pytest tests/
