.DEFAULT_GOAL := build
.PHONY: build clean

build:
	$(MAKE) -C ../../pgbuild PGSERVER_VERSION=16 all
	rm -rf src/pgserver_binaries/pg16 build
	mkdir -p src/pgserver_binaries/pg16
	cp -R ../../pgbuild/build/pg16/install/. src/pgserver_binaries/pg16/

clean:
	rm -rf src/pgserver_binaries/pg16 build
	$(MAKE) -C ../../pgbuild PGSERVER_VERSION=16 clean
