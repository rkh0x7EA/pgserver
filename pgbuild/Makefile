SHELL := /bin/bash
.DEFAULT_GOAL := all
.DELETE_ON_ERROR:
PGSERVER_VERSION ?= 16
PYTHON ?= python3
JOBS ?= 4
PG16_VERSION := 16.13
PG17_VERSION := 17.6
PG18_VERSION := 18.0
# From https://ftp.postgresql.org/pub/source/v<VERSION>/postgresql-<VERSION>.tar.gz.sha256
PG16_SHA256 := 9b767d0dfd156424b0b8f02b65eebb4b6958ef6413ebf7c8349e28b0b91e6b09
PG17_SHA256 := 2910b85283674da2dae6ac13fe5ebbaaf3c482446396cba32e6728d3cc736d86
PG18_SHA256 := 30e97fc1f1594a7226580ea51080d3d883f4a0fb6ff716dbf7ad09e9f7e93ab2
POSTGRES_VERSION := $(PG$(PGSERVER_VERSION)_VERSION)
ifeq ($(POSTGRES_VERSION),)
$(error PGSERVER_VERSION must be 16, 17 or 18)
endif
PGVECTOR_VERSION := 0.8.1
PGVECTOR_SHA256 := a9094dfb85ccdde3cbb295f1086d4c71a20db1d26bf1d6c39f07a7d164033eb4
BUILD := $(CURDIR)/build/pg$(PGSERVER_VERSION)
INSTALL_PREFIX := $(BUILD)/install
POSTGRES_SRC := $(BUILD)/postgresql-$(POSTGRES_VERSION)
PGVECTOR_SRC := $(BUILD)/pgvector-$(PGVECTOR_VERSION)
POSTGRES_ARCHIVE := downloads/postgresql-$(POSTGRES_VERSION).tar.gz
PGVECTOR_ARCHIVE := downloads/pgvector-$(PGVECTOR_VERSION).tar.gz
ifeq ($(shell uname -s),Darwin)
export MACOSX_DEPLOYMENT_TARGET ?= 11.0
endif

.PHONY: all postgres pgvector clean clean-all
all: $(BUILD)/.relocated
postgres: $(BUILD)/.postgres-installed
pgvector: $(BUILD)/.vector-installed

$(POSTGRES_ARCHIVE):
	mkdir -p downloads
	curl --fail --location --retry 3 -o $@.tmp https://ftp.postgresql.org/pub/source/v$(POSTGRES_VERSION)/postgresql-$(POSTGRES_VERSION).tar.gz
	mv $@.tmp $@

$(PGVECTOR_ARCHIVE):
	mkdir -p downloads
	curl --fail --location --retry 3 -o $@.tmp https://github.com/pgvector/pgvector/archive/refs/tags/v$(PGVECTOR_VERSION).tar.gz
	mv $@.tmp $@

$(POSTGRES_SRC)/configure: $(POSTGRES_ARCHIVE) Makefile
	$(PYTHON) -c 'import hashlib; from pathlib import Path; assert hashlib.sha256(Path("$<").read_bytes()).hexdigest() == "$(PG$(PGSERVER_VERSION)_SHA256)", "PostgreSQL checksum mismatch"'
	mkdir -p $(BUILD)
	tar xzf $< -C $(BUILD)
	touch $@

$(POSTGRES_SRC)/config.status: $(POSTGRES_SRC)/configure
	cd $(POSTGRES_SRC) && ./configure --prefix=$(INSTALL_PREFIX) --without-readline --without-icu --without-zlib

$(BUILD)/.postgres-installed: $(POSTGRES_SRC)/config.status
	$(MAKE) -C $(POSTGRES_SRC) MAKELEVEL=0 -j$(JOBS)
	$(MAKE) -C $(POSTGRES_SRC) MAKELEVEL=0 install
	mkdir -p $(INSTALL_PREFIX)/share/licenses
	cp $(POSTGRES_SRC)/COPYRIGHT $(INSTALL_PREFIX)/share/licenses/PostgreSQL.txt
	touch $@

$(PGVECTOR_SRC)/Makefile: $(PGVECTOR_ARCHIVE) Makefile
	$(PYTHON) -c 'import hashlib; from pathlib import Path; assert hashlib.sha256(Path("$<").read_bytes()).hexdigest() == "$(PGVECTOR_SHA256)", "pgvector checksum mismatch"'
	mkdir -p $(PGVECTOR_SRC)
	tar xzf $< -C $(PGVECTOR_SRC) --strip-components=1
	touch $@

$(BUILD)/.vector-installed: $(PGVECTOR_SRC)/Makefile $(BUILD)/.postgres-installed
	$(MAKE) -C $(PGVECTOR_SRC) MAKELEVEL=0 PG_CONFIG=$(INSTALL_PREFIX)/bin/pg_config OPTFLAGS= -j$(JOBS)
	$(MAKE) -C $(PGVECTOR_SRC) MAKELEVEL=0 PG_CONFIG=$(INSTALL_PREFIX)/bin/pg_config OPTFLAGS= install
	cp $(PGVECTOR_SRC)/LICENSE $(INSTALL_PREFIX)/share/licenses/pgvector.txt
	touch $@

$(BUILD)/.relocated: $(BUILD)/.vector-installed relocate.py
	$(PYTHON) relocate.py $(INSTALL_PREFIX)
	touch $@

clean:
	rm -rf $(BUILD)

clean-all:
	rm -rf build downloads
