.DEFAULT_GOAL := build
.PHONY: build clean

build:
	$(MAKE) -C ../../pgbuild PGSERVER_VERSION=17 all
	rm -rf src/pgserver_binaries/pg17 build
	mkdir -p src/pgserver_binaries/pg17
	cp -R ../../pgbuild/build/pg17/install/. src/pgserver_binaries/pg17/

clean:
	rm -rf src/pgserver_binaries/pg17 build
	$(MAKE) -C ../../pgbuild PGSERVER_VERSION=17 clean
