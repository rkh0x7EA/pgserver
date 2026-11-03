# pgserver-postgres-17

Platform-specific PostgreSQL 17 binaries for pgserver. Build with `make build`,
then `python -m build --wheel`. Requires the repository's `pgbuild` directory.

See the root README for release URL/hash installation and supported platforms.
PostgreSQL 16 is the default dependency. Majors 17/18 are optional; set
`PGSERVER_VERSION=17` before importing pgserver to select this package.
