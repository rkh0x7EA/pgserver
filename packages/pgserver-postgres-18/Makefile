.DEFAULT_GOAL := build
.PHONY: build clean

build:
	$(MAKE) -C ../../pgbuild PGSERVER_VERSION=18 all
	rm -rf src/pgserver_binaries/pg18 build
	mkdir -p src/pgserver_binaries/pg18
	cp -R ../../pgbuild/build/pg18/install/. src/pgserver_binaries/pg18/

clean:
	rm -rf src/pgserver_binaries/pg18 build
	$(MAKE) -C ../../pgbuild PGSERVER_VERSION=18 clean
